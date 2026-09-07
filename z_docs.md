# Panorama - TM1 Data Fetcher

## Project Structure

```
client/
├── main.py              # Entry point, routes
├── splash.py            # Animated splash screen (Vanta.js)
├── config.py            # Constants (PUBLIC_KEY, STEPS, SECURITY_MODES, defaults)
├── styles.py            # CSS styles
├── services/
│   ├── __init__.py
│   ├── tm1.py           # TM1 connection, discovery, data fetching
│   └── encryption.py    # RSA-OAEP encryption
├── ui/
│   ├── __init__.py
│   ├── components.py    # Reusable UI components
│   └── wizard.py        # Main 6-step wizard
└── z_docs.md            # This documentation
```

---

## Overview

A 6-step wizard to fetch and encrypt TM1 server data.

---

## Step 1: Method

Choose connection method:

| Option | Description |
|--------|-------------|
| **Manual** | Enter server details manually (skips Step 2) |
| **Admin Host** | Auto-discover servers via TM1 Admin Host (skips Step 3) |

---

## Step 2: Admin Host *(only if Admin Host mode)*

Configure Admin Host connection to discover available TM1 servers.

| Field | Default | Description |
|-------|---------|-------------|
| Host | `localhost` | Admin Host address |
| Port | `5895` | Admin Host port |

**Actions:**
- **Discover** - Query Admin Host for available servers
- **Server** - Select a discovered server (auto-fills Address, Port, SSL, Security Mode)

---

## Step 3: Server *(only if Manual mode)*

Configure TM1 server connection details manually.

| Field | Default | Description |
|-------|---------|-------------|
| Address | `localhost` | TM1 server address |
| Port | `8010` | TM1 HTTP port |
| SSL | `On` | Use HTTPS connection |

---

## Step 4: Security Mode

Select TM1 authentication mode:

| Mode | ID | Description |
|------|----|----|
| **TM1** | 1 | Native TM1 authentication (user/password) |
| **Integrated** | 2 | Windows Integrated Authentication (no credentials) |
| **CAM** | 3 | Cognos Access Manager (namespace + user/password) |
| **CAM SSO** | 4 | CAM with Single Sign-On (namespace only) |
| **LDAP** | 5 | LDAP authentication (namespace + user/password) |

---

## Step 5: Authentication

Fields vary based on security mode:

| Mode | Fields |
|------|--------|
| **TM1** | Username, Password |
| **Integrated** | *(none - Windows auth)* |
| **CAM** | Namespace, Username, Password |
| **CAM SSO** | Namespace |
| **LDAP** | Namespace, Username, Password |

**Actions:**
- **Fetch** - Proceeds to Step 6 and starts data fetching

---

## Step 6: Download

Shows fetch progress and allows downloading the encrypted file.

**States:**
1. **Loading** - Spinner with progress bar (Connecting → Fetching → Encrypting)
2. **Ready** - File icon with filename, Download button enabled

**Actions:**
- **Download** - Save encrypted `.txt` file

---

## Flow Diagram

```
                    ┌─────────────┐
                    │  1. Method  │
                    │             │
                    │ Manual /    │
                    │ Admin Host  │
                    └──────┬──────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
           ▼ (Admin Host)                  ▼ (Manual)
   ┌─────────────┐                 ┌─────────────┐
   │ 2. Admin    │                 │  3. Server  │
   │    Host     │                 │             │
   │ Discover &  │                 │ Address,    │
   │ Select      │                 │ Port & SSL  │
   └──────┬──────┘                 └──────┬──────┘
          │                               │
          └───────────────┬───────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ 4. Security   │
                  │    Mode       │
                  │               │
                  │ TM1/CAM/etc.  │
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ 5. Auth       │
                  │               │
                  │ Credentials   │
                  │ (varies)      │
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ 6. Download   │
                  │               │
                  │ Fetch &       │
                  │ Download      │
                  └───────────────┘
```

---

## Modules

### config.py
- `PUBLIC_KEY` - RSA public key for encryption
- `STEPS` - Wizard step names (6 steps)
- `SECURITY_MODES` - TM1 authentication modes
- `DEFAULT_*` - Default connection values

### styles.py
- `APP_STYLES` - CSS for dark theme and Quasar overrides
- `FILE_ICON_SVG` - Download icon

### services/tm1.py
- `discover_servers(host, port)` - Query Admin Host for servers
- `parse_server_info(server)` - Extract address, port, SSL from server object
- `fetch_tm1_data(...)` - Fetch Process, Cube, Dimension data (supports all security modes)

### services/encryption.py
- `encrypt_data(data)` - RSA-OAEP encrypt data in 190-byte chunks

### ui/components.py
- `radio_option(label, active, on_click)` - Styled radio button
- `labeled_input(label, value, password, classes)` - Input with label
- `progress_bar(steps, current)` - Step progress indicator
- `step_header(step, name)` - Step number and name

### ui/wizard.py
- `TM1Wizard` - Main wizard class with all step logic

---

## Data Fetched

- **Processes** - Name, Prolog
- **Cubes** - Name, Dimensions
- **Dimensions** - Name

---

## Output

Encrypted JSON file: `{server}_{date}.txt`

RSA-OAEP encryption with 2048-bit public key, 190-byte chunks.

---

## Running
 
```bash d
# Production (native window)
python main.py

# Development (browser with hot reload)
python main.py --dev
```
