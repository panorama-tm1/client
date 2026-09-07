"""Application configuration and constants."""

PUBLIC_KEY = """-----BEGIN RSA PUBLIC KEY-----
MIIBCgKCAQEA5OAnPhiOjcudWksctYeBOPwmc02UE+7TfRjU4nwABxcERWf6RKPx
204epemfn8fEuQ3qDiqrtDAcThutPs3y+75SgQXBAWaeYYK1j4E7uv0Fsiwo+cNF
03dL6lWmlljRf1u3h2BCWtiaV4vuJDz/q+O/aHXE1v7fkR3CHypGZZJsaYCl90Nz
LIGl1cba+/W27VGOOua5e8HOizWE4pCiYpN9mwJJsCn/PSwVzlZbBWrIoDuls1ix
cpWU+g59q1voi61E8/geleM27N5Hx5ZEWJNoSMZfz4BK3O6c5KBLwwnHQZsiOsMN
/FP9j7/ojoQiHcyHb+6quEnhRPvOOdwkPwIDAQAB
-----END RSA PUBLIC KEY-----"""

STEPS = ['Method', 'Admin Host', 'Server', 'Security Mode', 'Authentication', 'Download']

# Security modes
SECURITY_MODES = {
    1: 'TM1',
    2: 'Integrated',
    3: 'CAM',
    4: 'CAM SSO',
    5: 'LDAP'
}

DEFAULT_SERVER = "localhost"
DEFAULT_PORT = "8010"
DEFAULT_USER = "admin"
DEFAULT_ADMIN_PORT = "5895"
DEFAULT_NAMESPACE = ""
