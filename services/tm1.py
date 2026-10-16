"""TM1 server discovery and data fetching."""

import http.client
import json
import re

import requests
from TM1py import TM1Service
from TM1py.Exceptions import TM1pyTimeout
from TM1py.Utils import get_all_servers_from_adminhost

try:
    from TM1py.Exceptions import TM1pyNetworkException
except ImportError:  # older TM1py 2.x, HTML answers come as TM1pyRestException
    TM1pyNetworkException = ()


def discover_servers(host: str, port: int) -> dict:
    """Discover TM1 servers from Admin Host.

    Args:
        host: Admin Host address
        port: Admin Host port

    Returns:
        Dictionary mapping server names to server objects
    """
    servers = get_all_servers_from_adminhost(adminhost=host, port=port)
    return {s.name: s for s in servers} if servers else {}


def parse_server_info(server) -> tuple[str, str, bool, int]:
    """Extract connection info from discovered server.

    Returns:
        Tuple of (address, port, ssl, security_mode)
    """
    addr = getattr(server, 'ip_address', '') or ''
    if not addr:
        host = getattr(server, 'host', '') or ''
        addr = host.replace('https://', '').replace('http://', '').split(':')[0]

    address = addr or 'localhost'
    port = str(getattr(server, 'http_port_number', '8010') or '8010')
    ssl = bool(getattr(server, 'using_ssl', True))

    # Parse IntegratedSecurityMode from Admin Host
    # Values: 1=TM1, 2=Mixed, 3=Integrated, 4=CAM, 5=CAM+TM1
    raw_mode = getattr(server, 'integrated_security_mode', None)
    if raw_mode is None:
        raw_mode = getattr(server, 'IntegratedSecurityMode', 1)

    # Map TM1 modes to our security modes
    mode_map = {
        1: 1,        # TM1 Native
        2: 1,        # Mixed -> default to TM1
        3: 2,        # Integrated only
        4: 3,        # CAM
        5: 3,        # CAM + TM1 -> CAM
        'TM1': 1,
        'Mixed': 1,
        'Integrated': 2,
        'CAM': 3,
    }
    security_mode = mode_map.get(raw_mode, 1)

    return address, port, ssl, security_mode


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0].strip() if lines else ''


def explain_admin_error(ex: Exception) -> str:
    """Turn an Admin Host discovery error into a short cause."""
    # get_all_servers_from_adminhost uses http.client, not requests:
    # network failures are OSError, a port that is not an Admin Host
    # answers something that is not the expected JSON.
    if isinstance(ex, (json.JSONDecodeError, KeyError, TypeError)):
        return 'Not an Admin Host: check host and port'
    if isinstance(ex, OSError):
        return 'Admin Host unreachable: check host and port'
    if isinstance(ex, http.client.HTTPException):
        return 'Not an Admin Host: check host and port'
    return _first_line(str(ex)) or type(ex).__name__


def explain_error(ex: Exception) -> tuple[str, str | None]:
    """Turn a TM1 connection or read error into a short cause.

    Returns:
        Tuple of (message, setting to fix: 'server', 'login' or None)
    """
    status = getattr(ex, 'status_code', None)
    if status == 401:
        return 'Wrong user, password or namespace', 'login'
    if isinstance(ex, TM1pyNetworkException) or status == 404:
        return 'No TM1 REST API at this address and port', 'server'
    if status == 403:
        return 'This TM1 account cannot read the model', 'login'
    if isinstance(ex, requests.exceptions.SSLError):
        return 'SSL problem: try switching SSL', 'server'
    if isinstance(ex, requests.exceptions.ConnectTimeout):
        return 'Server unreachable: check address and HTTP port', 'server'
    if isinstance(ex, requests.exceptions.ConnectionError):
        # Plain HTTP sent to an SSL port: TM1 drops the connection
        if re.search(r'RemoteDisconnected|Connection aborted|reset by peer', str(ex), re.IGNORECASE):
            return 'Server closed the connection: try switching SSL', 'server'
        return 'Server unreachable: check address and HTTP port', 'server'
    if isinstance(ex, (requests.exceptions.Timeout, TM1pyTimeout)):
        return 'TM1 did not answer in time', None
    if status is not None:
        # str() of a TM1py REST error dumps the response headers: keep TM1's own message
        try:
            message = json.loads(ex.response)['error']['message']
        except Exception:
            message = _first_line(getattr(ex, 'response', '') or '')
        return (f'TM1 error {status}: {message}' if message else f'TM1 error {status}'), None
    return _first_line(str(ex)) or type(ex).__name__, None


def fetch_tm1_data(
    address: str,
    port: int,
    ssl: bool,
    user: str = None,
    password: str = None,
    security_mode: int = 1,
    namespace: str = None
) -> dict:
    """Fetch data from TM1 server.

    Args:
        address: TM1 server address
        port: TM1 HTTP port
        ssl: Use SSL
        user: Username (not needed for Integrated)
        password: Password (not needed for Integrated/CAM SSO)
        security_mode: 1=TM1, 2=Integrated, 3=CAM, 4=CAM SSO, 5=LDAP
        namespace: CAM/LDAP namespace

    Returns:
        Dictionary with Process, Cube, and Dimension data
    """
    params = {
        'address': address,
        'port': port,
        'ssl': ssl
    }

    if security_mode == 1:  # TM1 Native
        params['user'] = user
        params['password'] = password
    elif security_mode == 2:  # Integrated Windows
        params['integrated_login'] = True
    elif security_mode == 3:  # CAM
        params['user'] = user
        params['password'] = password
        params['namespace'] = namespace
    elif security_mode == 4:  # CAM SSO
        params['namespace'] = namespace
        params['gateway'] = f"https://{address}:{port}"
    elif security_mode == 5:  # LDAP
        params['user'] = user
        params['password'] = password
        params['namespace'] = namespace

    with TM1Service(**params) as tm1:
        data = {'Process': [], 'Cube': [], 'Dimension': []}

        # Process payload shape matches what worker-io's import pipeline reads.
        # All four procedure sections (Prolog/Metadata/Data/Epilog) are
        # consumed by `edges_process.js` to build variable-flow + datasource
        # edges. DataSource keys mirror the TM1 REST naming so the importer's
        # switch on `Type` ("TM1CubeView" / "ASCII" / "NULL" / …) keeps working.
        for name in tm1.processes.get_all_names():
            try:
                process = tm1.processes.get(name)
                data['Process'].append({
                    'Name': process.name,
                    'Prolog': process.prolog_procedure or '',
                    'Epilog': process.epilog_procedure or '',
                    'Metadata': process.metadata_procedure or '',
                    'Data': process.data_procedure or '',
                    'DataSource': {
                        'Type': getattr(process, 'datasource_type', None) or 'NULL',
                        'DataSource_Name_For_Client': getattr(
                            process, 'datasource_data_source_name_for_client', None
                        ) or '',
                    },
                })
            except:
                pass

        # Cube: `Dimensions` (canonical name expected by edges_dependencies.js)
        # is an array of dimension names — `Object.entries` on JS side
        # iterates it the same way as an object, both work. `Rules` is the raw
        # text of the cube's rule script; `str(cube.rules)` collapses TM1py's
        # Rules object to its text form. Empty string when the cube has no
        # rules at all (the common case in TM1).
        for name in tm1.cubes.get_all_names():
            try:
                cube = tm1.cubes.get(name)
                data['Cube'].append({
                    'Name': cube.name,
                    'Dimensions': cube.dimensions,
                    'Rules': str(cube.rules) if cube.rules else '',
                })
            except:
                pass

        for name in tm1.dimensions.get_all_names():
            data['Dimension'].append({'Name': name})

        return data
