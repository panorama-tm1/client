"""Main TM1 connection wizard."""

import asyncio
from datetime import datetime
from tkinter import Tk, filedialog
from nicegui import ui, app

from config import (
    STEPS, SECURITY_MODES,
    DEFAULT_SERVER, DEFAULT_PORT, DEFAULT_USER, DEFAULT_ADMIN_PORT, DEFAULT_NAMESPACE
)

# Short labels for dropdown display
SECURITY_LABELS = {1: 'TM1', 2: 'INT', 3: 'CAM', 4: 'SSO', 5: 'LDAP'}
from styles import APP_STYLES, FILE_ICON_SVG
from services.tm1 import (
    discover_servers, parse_server_info, fetch_tm1_data, explain_error, explain_admin_error
)
from services.encryption import encrypt_data
from ui.components import radio_option, labeled_input, progress_bar, step_header, error_details


class TM1Wizard:
    """6-step wizard to fetch and encrypt TM1 server data."""

    def __init__(self):
        self.step = 0
        self.use_admin = False
        self.discovered = {}
        self.encrypted = None
        self.fix_step = 4

        self.server = DEFAULT_SERVER
        self.port = DEFAULT_PORT
        self.user = DEFAULT_USER
        self.pwd = ""
        self.ssl = True
        self.security_mode = 1  # TM1 Native
        self.namespace = DEFAULT_NAMESPACE

    def build(self):
        """Build the wizard UI."""
        ui.add_head_html(APP_STYLES)

        with ui.column().classes('w-full min-h-screen items-center justify-center'):
            with ui.column().classes('w-[480px] gap-0'):
                step_header(self.step, STEPS[self.step])
                progress_bar(6, self.step)
                self.content = ui.column().classes('w-full')
                self._render_step()
                self._render_nav()

    def _render_step(self):
        """Render current step content."""
        self.content.clear()
        with self.content:
            steps = {
                0: self._step_method,
                1: self._step_admin,
                2: self._step_server,
                3: self._step_security_mode,
                4: self._step_auth,
                5: self._step_download
            }
            steps[self.step]()

    def _step_method(self):
        """Step 0: Choose connection method."""
        radio_option('Manual', not self.use_admin, lambda: self._set_method(False))
        radio_option('Admin Host', self.use_admin, lambda: self._set_method(True))

    def _step_admin(self):
        """Step 1: Admin Host discovery."""
        with ui.row().classes('w-full gap-2 mb-3 items-end'):
            self.inp_ah = labeled_input('Host', 'localhost', classes='flex-1')
            self.inp_ap = labeled_input('Port', DEFAULT_ADMIN_PORT, classes='w-16')
            self.btn_disc = ui.button('Discover', on_click=self._discover).classes(
                'bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-[11px] h-[40px] px-4'
            ).props('flat dense')

        with ui.row().classes('w-full items-center gap-2 mb-2'):
            self.spinner = ui.spinner('dots', size='sm', color='neutral')
            self.spinner.visible = False
            self.lbl_disc = ui.label('').classes('flex-1 min-w-0 break-words text-[11px] text-neutral-400')

        self.disc_details = ui.column().classes('w-full gap-0')

        with ui.column().classes('w-full gap-0.5'):
            ui.label('Server').classes('text-[11px] text-neutral-500')
            self.sel_srv = ui.select(options=[], on_change=self._on_server_select).classes('w-full').props('dense outlined dark dropdown-icon=none')
            self.sel_srv.disable()

    def _step_server(self):
        """Step 2: Manual server configuration."""
        with ui.row().classes('w-full gap-2 mb-2'):
            self.inp_srv = labeled_input('Address', self.server, classes='flex-1')
            self.inp_port = labeled_input('Port', self.port, classes='w-20')

        with ui.row().classes('w-full items-center justify-between'):
            ui.label('SSL').classes('text-[11px] text-neutral-400')
            self.tog_ssl = ui.switch(value=self.ssl).props('dark dense color=grey-5')

    def _step_security_mode(self):
        """Step 3: Select TM1 security mode."""
        for mode_id, mode_name in SECURITY_MODES.items():
            radio_option(
                mode_name,
                self.security_mode == mode_id,
                lambda m=mode_id: self._set_security_mode(m)
            )

    def _step_auth(self):
        """Step 4: Authentication based on security mode."""
        if self.security_mode == 2:  # Integrated
            ui.label('Windows Integrated Authentication').classes('text-[12px] text-neutral-400')
            ui.label('No credentials required').classes('text-[11px] text-neutral-500 mt-2')
        elif self.security_mode in (3, 5):  # CAM or LDAP
            with ui.column().classes('w-full gap-2'):
                self.inp_ns = labeled_input('Namespace', self.namespace, classes='w-full')
                with ui.row().classes('w-full gap-2'):
                    self.inp_u = labeled_input('Username', self.user, classes='flex-1')
                    self.inp_pw = labeled_input('Password', self.pwd, password=True, classes='flex-1')
        elif self.security_mode == 4:  # CAM SSO
            self.inp_ns = labeled_input('Namespace', self.namespace, classes='w-full')
            ui.label('Single Sign-On enabled').classes('text-[11px] text-neutral-500 mt-2')
        else:  # TM1 Native (1)
            with ui.row().classes('w-full gap-2'):
                self.inp_u = labeled_input('Username', self.user, classes='flex-1')
                self.inp_pw = labeled_input('Password', self.pwd, password=True, classes='flex-1')

    def _step_download(self):
        """Step 5: Fetch and download."""
        with ui.column().classes('w-full items-center py-6') as self.dl_box:
            self.dl_spinner = ui.spinner('dots', size='lg', color='neutral')
            self.dl_icon = ui.html(FILE_ICON_SVG, sanitize=False).classes('text-neutral-400')
            self.dl_icon.visible = False

            self.lbl_st = ui.label('Connecting...').classes(
                'text-[13px] text-neutral-400 mt-4 text-center whitespace-normal break-words'
            )

            self.bar = ui.linear_progress(value=0, show_value=False).classes('w-full mt-4').props('color=grey-6')
            self.bar.style('height: 2px')

            with ui.row().classes('gap-2 mt-4'):
                self.btn_fix = ui.button('Change settings', on_click=lambda: self._go_to(self.fix_step)).classes(
                    'bg-neutral-200 hover:bg-neutral-300 text-neutral-900 text-[12px] h-8 px-6'
                ).props('flat')
                self.btn_fix.visible = False

                self.btn_dl = ui.button('Download', on_click=self._save).classes(
                    'bg-neutral-200 hover:bg-neutral-300 text-neutral-900 text-[12px] h-8 px-6'
                ).props('flat')
                self.btn_dl.visible = False

                self.btn_quit = ui.button('Quit', on_click=self._quit).classes(
                    'bg-neutral-800 hover:bg-neutral-700 text-neutral-300 text-[12px] h-8 px-6'
                ).props('flat')
                self.btn_quit.visible = False

        asyncio.create_task(self._fetch())

    def _render_nav(self):
        """Render navigation buttons."""
        with ui.row().classes('w-full justify-between mt-3'):
            self.btn_back = ui.button('Back', on_click=self._back).classes(
                'text-neutral-500 text-[11px] h-7 px-3'
            ).props('flat')
            if self.step == 0:
                self.btn_back.disable()

            if self.step == 5:
                ui.element('div')
            else:
                txt = 'Fetch' if self.step == 4 else 'Continue'
                self.btn_next = ui.button(txt, on_click=self._next).classes(
                    'bg-neutral-200 hover:bg-neutral-300 text-neutral-900 text-[11px] h-7 px-4'
                ).props('flat')

    def _set_method(self, use_admin: bool):
        """Set connection method and navigate."""
        self.use_admin = use_admin
        ui.navigate.to('/app')

    def _set_security_mode(self, mode: int):
        """Set security mode and navigate."""
        self.security_mode = mode
        ui.navigate.to('/app')

    def _on_server_select(self, e):
        """Handle server selection from dropdown."""
        # Map display name to real server name
        real_name = getattr(self, 'server_display_map', {}).get(e.value, e.value)
        if real_name in self.discovered:
            server = self.discovered[real_name]
            self.server, self.port, self.ssl, self.security_mode = parse_server_info(server)

    async def _discover(self):
        """Discover servers from Admin Host."""
        self.btn_disc.disable()
        self.spinner.visible = True
        self.lbl_disc.text = 'Discovering servers...'
        self.disc_details.clear()

        try:
            host = self.inp_ah.value.strip()
            port = self.inp_ap.value.strip() or DEFAULT_ADMIN_PORT
            if not port.isdigit():
                self.lbl_disc.text = 'Port must be a number'
                return

            self.discovered = await asyncio.get_event_loop().run_in_executor(
                None, lambda: discover_servers(host, int(port))
            )

            if not self.discovered:
                self.lbl_disc.text = 'No TM1 server found on this Admin Host'
                return

            # Build display names with security mode prefix
            self.server_display_map = {}  # display_name -> real_name
            display_names = []
            for name, server in self.discovered.items():
                _, _, _, sec_mode = parse_server_info(server)
                label = SECURITY_LABELS.get(sec_mode, 'TM1')
                display = f'[{label}] {name}'
                display_names.append(display)
                self.server_display_map[display] = name

            self.sel_srv.options = display_names
            self.sel_srv.value = display_names[0]
            self.sel_srv.enable()
            self.lbl_disc.text = f'{len(display_names)} server{"s" if len(display_names) > 1 else ""} found'
            self._on_server_select(type('E', (), {'value': display_names[0]})())

        except Exception as ex:
            self.lbl_disc.text = explain_admin_error(ex)
            with self.disc_details:
                error_details(self._error_detail(ex))
        finally:
            self.spinner.visible = False
            self.btn_disc.enable()

    def _back(self):
        """Navigate to previous step."""
        if self.step > 0:
            new_step = self.step - 1
            # Skip steps based on mode
            if self.use_admin and new_step == 2:
                new_step = 1
            elif not self.use_admin and new_step == 1:
                new_step = 0
            self.step = new_step
            ui.navigate.to('/app')

    def _go_to(self, step: int):
        """Navigate to a given step."""
        self.step = step
        ui.navigate.to('/app')

    def _next(self):
        """Navigate to next step."""
        self._save_step_values()

        if self.step < 5:
            new_step = self.step + 1
            # Skip steps based on mode
            if self.use_admin and new_step == 2:
                new_step = 3
            elif not self.use_admin and new_step == 1:
                new_step = 2
            self.step = new_step
            ui.navigate.to('/app')

    def _save_step_values(self):
        """Save current step input values."""
        if self.step == 2:
            if hasattr(self, 'inp_srv'):
                self.server = self.inp_srv.value
            if hasattr(self, 'inp_port'):
                self.port = self.inp_port.value
            if hasattr(self, 'tog_ssl'):
                self.ssl = self.tog_ssl.value
        elif self.step == 4:
            if hasattr(self, 'inp_u'):
                self.user = self.inp_u.value
            if hasattr(self, 'inp_pw'):
                self.pwd = self.inp_pw.value
            if hasattr(self, 'inp_ns'):
                self.namespace = self.inp_ns.value

    async def _fetch(self):
        """Fetch data from TM1 server and encrypt."""
        if not self.port.strip().isdigit():
            self._show_fetch_error('Port must be a number', 'server')
            return

        try:
            self.lbl_st.text = 'Connecting...'
            self.bar.value = 0.1

            self.lbl_st.text = 'Fetching data...'
            self.bar.value = 0.4

            data = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: fetch_tm1_data(
                    address=self.server.strip(),
                    port=int(self.port.strip()),
                    ssl=self.ssl,
                    user=self.user.strip() if self.security_mode != 2 else None,
                    password=self.pwd if self.security_mode not in (2, 4) else None,
                    security_mode=self.security_mode,
                    namespace=self.namespace.strip() if self.security_mode in (3, 4, 5) else None
                )
            )

            self.lbl_st.text = 'Encrypting...'
            self.bar.value = 0.8

            self.encrypted = await asyncio.get_event_loop().run_in_executor(
                None, lambda: encrypt_data(data)
            )

            self.dl_spinner.visible = False
            self.dl_icon.visible = True
            self.lbl_st.text = f'{self.server}_{datetime.now():%Y-%m-%d}.txt'
            self.bar.value = 1.0
            self.btn_dl.visible = True
            self.btn_quit.visible = True

        except Exception as ex:
            cause, setting = explain_error(ex)
            self._show_fetch_error(cause, setting, ex)

    def _show_fetch_error(self, cause: str, setting: str | None, ex: Exception = None):
        """Show why the fetch failed, with a shortcut to the step to fix."""
        self.dl_spinner.visible = False
        self.lbl_st.text = cause
        self.bar.value = 0
        # Address, port and SSL live on the Server step, credentials on Authentication
        self.fix_step = 2 if setting == 'server' else 4
        self.btn_fix.visible = True
        if ex is not None:
            with self.dl_box:
                error_details(self._error_detail(ex))

    def _error_detail(self, ex: Exception) -> str:
        """Full error text for support, without the password."""
        detail = f'{type(ex).__name__}: {ex}'
        if self.pwd:
            detail = detail.replace(self.pwd, '***')
        return detail

    async def _save(self):
        """Save encrypted data to file."""
        if not self.encrypted:
            return

        filename = f'{self.server}_{datetime.now():%Y-%m-%d}.txt'

        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text files', '*.txt'), ('All files', '*.*')],
            initialfile=filename
        )
        root.destroy()

        if path:
            with open(path, 'w') as f:
                f.write(self.encrypted)
            self.lbl_st.text = 'Saved'

    def _quit(self):
        """Return to landing page."""
        self._reset()
        ui.navigate.to('/')

    def _reset(self):
        """Reset wizard state."""
        self.step = 0
        self.use_admin = False
        self.discovered = {}
        self.encrypted = None
        self.server = DEFAULT_SERVER
        self.port = DEFAULT_PORT
        self.user = DEFAULT_USER
        self.pwd = ""
        self.ssl = True
        self.security_mode = 1
        self.namespace = DEFAULT_NAMESPACE
