# Steel Pipe Machine Monitoring System (SPMMS)

## Development

**Created by:** `@MineKyuuCha`
**GitHub Repository:** [steel-pipe-machine-monitoring](https://github.com/MineKyuuCha/steel-pipe-machine-monitoring.git)

## Official Project Handover & User Guide

> **A practical step toward smarter production monitoring --- built to
> be useful today, and a foundation for what the company can develop
> tomorrow.**

This document is the operational and technical handover guide for the
working prototype.

------------------------------------------------------------------------

## Technologies

- ESP32-S3
- C/C++ (Arduino)
- Python
- Flask
- PostgreSQL
- Streamlit
- Tailscale

# 1. Project Overview

The **Steel Pipe Machine Monitoring System** is an IoT-based monitoring
prototype for observing the ON/OFF operational status of machines in
real time.

The current prototype monitors two machine inputs:

-   **Machine A**
-   **Machine B**

The system records:

-   Machine ON/OFF status
-   Event timestamps
-   Current machine status
-   Running time
-   Daily ON/OFF duration
-   Daily utilization percentage
-   Recent machine events
-   A visual real-time monitoring dashboard

The system is built around a monitoring PC running Flask, PostgreSQL,
and Streamlit.

### Important scope note

The current prototype is intended as a **machine-status monitoring
system**. It should not be interpreted as a complete production-line
monitoring system.

For the SS7 prototype, the monitored signal is associated with the
selected machine/input. Other machines in the production process may
stop or continue independently.

------------------------------------------------------------------------

# 2. System Architecture

``` text
┌───────────────────────────────────────────────┐
│              MACHINE / INPUT LAYER            │
│                                               │
│  Machine status → Relay / dry-contact input   │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────┐
│                  ESP32-S3                     │
│                                               │
│  Reads Machine A / Machine B ON/OFF status    │
└──────────────────────┬────────────────────────┘
                       │ Wi-Fi + HTTP
                       ▼
┌───────────────────────────────────────────────┐
│                MONITORING PC                  │
│                                               │
│  Flask Receiver :5000                         │
│          ↓                                    │
│  PostgreSQL Database :5432                    │
│          ↓                                    │
│  Streamlit Dashboard :8501                    │
└──────────────────────┬────────────────────────┘
                       │
                       │ Optional remote access
                       ▼
┌───────────────────────────────────────────────┐
│                  TAILSCALE                    │
│                                               │
│  Tailnet + MagicDNS + Tailscale Serve        │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
          Authorized PC / Phone / Tablet
```

### Data flow

``` text
Machine
   ↓
Relay dry contact
   ↓
ESP32-S3
   ↓
Wi-Fi
   ↓
Flask receiver
   ↓
PostgreSQL
   ↓
Streamlit
   ↓
Browser
```

### Important network distinction

There are two separate network paths:

1.  **ESP32 → Monitoring PC**
    -   Used to send machine-status events.
    -   Uses the local Wi-Fi/network.
    -   Sends HTTP requests to Flask on port `5000`.
2.  **Authorized user → Dashboard**
    -   Uses Tailscale when remote/private access is required.
    -   Provides access to Streamlit.
    -   Tailscale is **not required for the ESP32-to-Flask data path**.

------------------------------------------------------------------------

# 3. Final Hardware Configuration

The final prototype uses an **ESP32-S3 N16R8** as the controller.

  Machine       ESP32 GPIO Input logic
  ----------- ------------ ----------------------
  Machine A     **GPIO 4** LOW = ON, HIGH = OFF
  Machine B     **GPIO 6** LOW = ON, HIGH = OFF

> **Important:** The final firmware uses **Machine A = GPIO 4** and
> **Machine B = GPIO 6**. This is the authoritative mapping for the
> current prototype.

The ESP32 firmware configures the inputs using:

``` cpp
pinMode(pin, INPUT_PULLUP);
```

## Relay dry-contact wiring

For each relay input:

``` text
Relay COM ───── ESP32 GND
Relay NO  ───── ESP32 GPIO
```

### OFF state

``` text
Relay contact OPEN
       ↓
GPIO = HIGH
       ↓
Machine = OFF
```

### ON state

``` text
Relay contact CLOSED
       ↓
GPIO = LOW
       ↓
Machine = ON
```

## Safety

**Never connect 220 VAC directly to an ESP32 GPIO.**

Only the isolated/dry-contact side of an appropriately rated relay
should be connected to the ESP32.

Any work involving industrial mains voltage must be performed by
qualified personnel using appropriate electrical safety procedures.

------------------------------------------------------------------------

# 4. Final Firmware Behavior

The ESP32 firmware:

1.  Connects to the configured Wi-Fi.
2.  Reads Machine A on GPIO 4.
3.  Reads Machine B on GPIO 6.
4.  Uses debounce logic to avoid false state changes.
5.  Sends an event immediately when a machine state changes.
6.  Sends a heartbeat containing the current state every **30 seconds**.
7.  Sends the initial state of both inputs when the ESP32 boots.

Example:

``` text
Sent A -> OFF | HTTP code: 200
Sent B -> ON  | HTTP code: 200
```

The heartbeat is useful because the server periodically receives the
current state even when no machine state change has occurred.

------------------------------------------------------------------------

# 5. Project Files

The clean handover package should use the following names:

  File / Folder                     Purpose
  --------------------------------- ----------------------------------------------
  `app.py`                          Streamlit monitoring dashboard
  `database.py`                     PostgreSQL connection and database functions
  `receiver.py`                     Flask HTTP server receiving ESP32 events
  `requirements.txt`                Python package dependencies
  `.env.example`                    Safe database configuration template
  `.env`                            Local database credentials; **keep private**
  `esp32_firmware_dual_relay.ino`   Final ESP32 firmware
  `.streamlit/`                     Optional Streamlit configuration

### About the supplied working files note

Do not change the working code logic merely for renaming.

------------------------------------------------------------------------

# 6. Software Requirements

The monitoring PC requires:

-   Windows PC
-   Python
-   PostgreSQL
-   Python packages listed in `requirements.txt`
-   Arduino IDE for ESP32 firmware maintenance
-   Tailscale, if remote dashboard access is required

------------------------------------------------------------------------

# 7. Python Installation

Open PowerShell.

Check Python:

``` powershell
python --version
```

Install project dependencies:

``` powershell
python -m pip install -r requirements.txt
```

If the PC has multiple Python installations, make sure the same Python
installation is used when installing packages and running the project.

------------------------------------------------------------------------

# 8. Python Dependencies

The working `requirements.txt` contains:

``` text
streamlit
pandas
plotly
streamlit-autorefresh
streamlit-option-menu
flask
requests
psycopg2-binary
python-dotenv
```

Install them with:

``` powershell
python -m pip install -r requirements.txt
```

------------------------------------------------------------------------

# 9. PostgreSQL Setup

The project uses a local PostgreSQL database.

### Database name

``` text
steel_pipe_db
```

The `.env` configuration should contain:

``` env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=steel_pipe_db
DB_USER=postgres
DB_PASSWORD=YOUR_POSTGRES_PASSWORD
```

Replace:

``` text
YOUR_POSTGRES_PASSWORD
```

with the password configured for the local PostgreSQL `postgres` user.

### Important terminology

`DB_NAME` is the **database name**.

It is not the PostgreSQL server name.

### Security

Never put the real password into:

-   `database.py`
-   `README.md`
-   public Git repositories
-   screenshots
-   shared documentation

Keep `.env` private.

------------------------------------------------------------------------

# 10. Create the PostgreSQL Database

The project expects:

``` text
steel_pipe_db
```

to already exist.

The Python function `init_db()` creates the required table and index
**inside the database**, but it does not replace the step of creating
the PostgreSQL database itself.

Using pgAdmin:

1.  Open pgAdmin.
2.  Connect to the local PostgreSQL server.
3.  Create a database named:

``` text
steel_pipe_db
```

4.  Make sure the username/password in `.env` can access it.

------------------------------------------------------------------------

# 11. Initialize the Database Table

After PostgreSQL and `steel_pipe_db` are ready, open PowerShell in the
project directory:

``` powershell
python -c "from database import init_db; init_db()"
```

The program creates:

``` text
machine_events
```

The table stores:

  Field            Meaning
  ---------------- --------------------
  `id`             Event ID
  `machine_name`   Machine identifier
  `status`         `ON` or `OFF`
  `timestamp`      Event time

The database also creates an index to improve event queries.

------------------------------------------------------------------------

# 12. Flask Receiver

The Flask receiver accepts ESP32 machine-status events.

Start it with:

``` powershell
python receiver.py
```

The server listens on:

``` text
0.0.0.0:5000
```

The ESP32 sends events to:

``` text
http://<MONITORING-PC-IP>:5000/event
```

Example:

``` text
http://192.168.2.222:5000/event
```

The IP address is only an example. Use the current reachable IP of the
monitoring PC.

------------------------------------------------------------------------

# 13. Flask Health Check

Open a browser on the monitoring PC:

``` text
http://localhost:5000/
```

Expected response:

``` text
ESP32 receiver is running.
```

If this works, the Flask application is running.

------------------------------------------------------------------------

# 14. Flask Event Format

The ESP32 sends JSON similar to:

``` json
{
  "machine": "A",
  "status": "ON"
}
```

or:

``` json
{
  "machine": "B",
  "status": "OFF"
}
```

The receiver validates:

-   machine name
-   machine status

Valid machine names:

``` text
A
B
```

Valid status values:

``` text
ON
OFF
```

Accepted events are inserted into PostgreSQL.

------------------------------------------------------------------------

# 15. Streamlit Dashboard

Open a **second PowerShell window**.

Start Streamlit:

``` powershell
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

Dashboard port:

``` text
8501
```

### Local access

From the monitoring PC:

``` text
http://localhost:8501/
```

### LAN access

From an allowed device on the same network:

``` text
http://<MONITORING-PC-IP>:8501/
```

Example:

``` text
http://192.168.2.222:8501/
```

------------------------------------------------------------------------

# 16. Dashboard Functions

The current dashboard provides:

-   Total machines
-   Machines currently ON
-   Machines currently OFF
-   Combined ON time
-   Current machine status
-   Time since the current state began
-   Running/OFF duration
-   Total ON time for today
-   Status timeline
-   Recent events
-   Daily summary
-   First ON time
-   Total ON time
-   Total OFF time
-   Utilization percentage

The dashboard automatically refreshes its displayed data.

------------------------------------------------------------------------

# 17. Dashboard Navigation

The current interface contains:

``` text
Dashboard
Machines
History
Reports
Settings
```

The main working monitoring functionality is currently concentrated in
the Dashboard.

Other sections may contain placeholder/"coming soon" content in the
current prototype.

------------------------------------------------------------------------

# 18. Understanding the Dashboard Data Path

The ESP32 does **not** communicate directly with Streamlit.

Correct architecture:

``` text
ESP32
  ↓
Flask
  ↓
PostgreSQL
  ↓
Streamlit
```

The Streamlit dashboard accesses PostgreSQL through:

``` text
database.py
```

This separation makes troubleshooting easier.

------------------------------------------------------------------------

# 19. Understanding IP Addresses

The monitoring PC normally receives an IP address from DHCP.

Example:

``` text
IPv4 Address : 192.168.2.222
```

The address may change if the network connection changes or DHCP assigns
another address.

Check the current address:

``` powershell
ipconfig
```

Look for the active Wi-Fi adapter.

Example:

``` text
Wireless LAN adapter Wi-Fi:

IPv4 Address. . . . . . : xxx.xxx.xxx.xxx
```

------------------------------------------------------------------------

# 20. ESP32 Configuration

Before uploading the final firmware, configure:

``` cpp
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* SERVER_URL =
    "http://<MONITORING-PC-IP>:5000/event";
```

Example:

``` cpp
const char* SERVER_URL =
    "http://192.168.2.222:5000/event";
```

Replace the example IP with the actual monitoring PC address reachable
by the ESP32.

### Final GPIO mapping

``` text
Machine A → GPIO 4
Machine B → GPIO 6
```

Do not swap these definitions unless the physical wiring is also
changed.

------------------------------------------------------------------------

# 21. ESP32-to-Server Verification

Open Arduino IDE Serial Monitor at:

``` text
115200 baud
```

A successful startup should include:

``` text
WiFi connected. IP: ...
```

A successful event may look like:

``` text
Sent A -> OFF | HTTP code: 200
Sent B -> OFF | HTTP code: 200
```

The Flask terminal should simultaneously show events such as:

``` text
Received: Machine A -> OFF
Received: Machine B -> OFF
```

### HTTP 200

Means:

> The Flask receiver successfully received and accepted the event.

### HTTP -1

Means:

> The ESP32 could not establish a successful HTTP connection to the
> server.

Check:

1.  ESP32 Wi-Fi connection
2.  Monitoring PC IP
3.  `receiver.py`
4.  Port 5000
5.  Windows Firewall
6.  Network/security policy
7.  Whether the ESP32 and monitoring PC can communicate on the network

------------------------------------------------------------------------

# 22. Windows Firewall

If the monitoring PC must accept ESP32 connections on port 5000, an
inbound firewall rule may be required.

Example PowerShell command:

``` powershell
New-NetFirewallRule -DisplayName "Flask ESP32 Port 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

Only apply firewall changes according to company IT/security procedures.

------------------------------------------------------------------------

# 23. Database Verification

To inspect recent events in PostgreSQL:

``` sql
SELECT *
FROM machine_events
ORDER BY timestamp DESC
LIMIT 20;
```

This helps determine whether events are reaching the database.

A useful troubleshooting split is:

``` text
ESP32 → Flask
```

versus:

``` text
PostgreSQL → Streamlit
```

------------------------------------------------------------------------

# 24. Local Access vs Remote Access

## Local access

``` text
http://localhost:8501/
```

This means Streamlit is running on the monitoring PC itself.

## Remote/private access

Tailscale can provide private access to the monitoring PC:

``` text
Remote device
     ↓
Tailscale
     ↓
Monitoring PC
     ↓
Streamlit :8501
```

------------------------------------------------------------------------

# 25. Tailscale

Tailscale creates a private network called a **tailnet** between
authorized users/devices.

For this project, it can allow authorized users to access the dashboard
while the dashboard remains hosted on the company's monitoring PC.

Tailscale is separate from the ESP32 data path.

``` text
ESP32 ──Wi-Fi──> Flask ──> PostgreSQL
                              ↑
                              │
                         Streamlit
                              ↑
                              │
                         Tailscale
                              ↑
                       Authorized users
```

------------------------------------------------------------------------

# 26. Tailscale Users and Accounts

Each person should use their **own Tailscale identity/account**.

Do not share:

-   another person's Google password
-   Tailscale password
-   private authentication credentials

The Tailscale administrator can control which users/devices receive
access.

------------------------------------------------------------------------

# 27. MagicDNS

**MagicDNS** provides DNS names for devices in a Tailscale network.

Instead of remembering a Tailscale IP such as:

``` text
100.x.x.x
```

an authorized device can use a hostname.

This makes private services easier to access and maintain.

------------------------------------------------------------------------

# 28. Tailscale `.ts.net` Service Address

The deployed monitoring system uses:

``` text
https://ss-machine-status-monitoring.tail4daa8c.ts.net/
```

This is the private Tailscale service address used for the monitoring
dashboard.

It should not be treated as a normal public Internet website.

A user/device needs appropriate Tailscale access for the address to
work.

If the address ever changes, verify the current configuration with:

``` powershell
tailscale serve status
```

------------------------------------------------------------------------

# 29. Tailscale Serve

Tailscale Serve can publish a local service to authorized devices in the
tailnet.

Architecture:

``` text
Streamlit
localhost:8501
       ↓
Tailscale Serve
       ↓
https://ss-machine-status-monitoring.tail4daa8c.ts.net/
```

Check the current configuration:

``` powershell
tailscale serve status
```

Check the Tailscale connection:

``` powershell
tailscale status
```

### Important security distinction

**Tailscale Serve** is intended for private access within the tailnet.

Do not use **Tailscale Funnel** unless there is an explicit requirement
and appropriate security approval to expose the dashboard publicly.

------------------------------------------------------------------------

# 30. Daily Startup Procedure

After the monitoring PC starts:

## Step 1 --- PostgreSQL

Confirm the PostgreSQL service is running.

Confirm:

``` text
steel_pipe_db
```

exists.

## Step 2 --- Flask

Open PowerShell in the project directory:

``` powershell
python receiver.py
```

Keep the terminal running.

## Step 3 --- Streamlit

Open another PowerShell:

``` powershell
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

Keep the terminal running.

## Step 4 --- Tailscale

If remote dashboard access is required:

``` powershell
tailscale status
```

## Step 5 --- Tailscale Serve

``` powershell
tailscale serve status
```

## Step 6 --- Open dashboard

Local:

``` text
http://localhost:8501/
```

Tailscale:

``` text
https://ss-machine-status-monitoring.tail4daa8c.ts.net/
```

## Step 7 --- Verify machine data

Change a test machine/input and confirm:

1.  ESP32 detects the change.
2.  ESP32 sends the event.
3.  Flask receives the event.
4.  PostgreSQL records the event.
5.  Streamlit displays the updated state.

------------------------------------------------------------------------

# 31. Shutdown Procedure

1.  Stop Streamlit with `Ctrl + C`.
2.  Stop Flask with `Ctrl + C`.
3.  Leave PostgreSQL running if required by other applications.
4.  Power down the ESP32/controller if required.
5.  Follow the company's normal PC shutdown procedure.

------------------------------------------------------------------------

# 32. Troubleshooting

  -----------------------------------------------------------------------
  Problem                             First checks
  ----------------------------------- -----------------------------------
  `receiver.py` fails                 PostgreSQL, database, `.env`,
                                      Python packages

  `no password supplied`              `.env` / PostgreSQL password

  Database connection fails           PostgreSQL service, database name,
                                      username, password, port

  Streamlit fails                     Python packages / Python version

  ESP32 does not connect to Wi-Fi     SSID / password / Wi-Fi
                                      availability

  ESP32 `HTTP -1`                     PC IP, Wi-Fi, Flask, port 5000,
                                      firewall/network policy

  ESP32 gets HTTP 200                 ESP32 → Flask path is working

  Flask receives events but dashboard PostgreSQL / Streamlit
  does not update                     

  `localhost:8501` works but LAN does Streamlit binding / firewall /
  not                                 network

  Tailscale URL fails                 Tailscale status / Serve status /
                                      user access

  Tailscale works on one device but   Device Tailscale connection /
  not another                         account access

  Dashboard unavailable after reboot  PostgreSQL, Flask, Streamlit,
                                      Tailscale
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 33. Troubleshooting by Layer

Use the following order rather than changing several components at once:

``` text
1. Machine / Relay
        ↓
2. ESP32 GPIO
        ↓
3. ESP32 Wi-Fi
        ↓
4. Network path
        ↓
5. Flask :5000
        ↓
6. PostgreSQL :5432
        ↓
7. Streamlit :8501
        ↓
8. Tailscale / user access
```

### Layer 1 --- Machine / Relay

Check:

-   Relay operates correctly.
-   Dry contact is actually opening/closing.
-   COM/NO wiring is correct.
-   No mains voltage is connected to ESP32 GPIO.

### Layer 2 --- ESP32

Check:

``` text
Machine A → GPIO 4
Machine B → GPIO 6
```

Check Serial Monitor.

### Layer 3 --- Wi-Fi

Check that the ESP32 reports:

``` text
WiFi connected
```

### Layer 4 --- Network

Check the monitoring PC IP:

``` powershell
ipconfig
```

Make sure the ESP32 firmware's `SERVER_URL` points to the correct
address.

### Layer 5 --- Flask

Check:

``` text
http://localhost:5000/
```

Expected:

``` text
ESP32 receiver is running.
```

### Layer 6 --- PostgreSQL

Check that events appear in:

``` text
machine_events
```

### Layer 7 --- Streamlit

Check:

``` text
http://localhost:8501/
```

### Layer 8 --- Tailscale

Check:

``` powershell
tailscale status
tailscale serve status
```

------------------------------------------------------------------------

# 34. Security Recommendations

Never share:

-   PostgreSQL password
-   `.env`
-   Tailscale account password
-   Google account password
-   Private keys
-   Other authentication credentials

Recommended:

-   Use individual Tailscale accounts.
-   Give users only the access they need.
-   Keep repositories private when appropriate.
-   Never commit `.env`.
-   Do not expose PostgreSQL directly to the Internet.
-   Do not expose Flask port 5000 publicly unless specifically required
    and reviewed.
-   Keep industrial electrical work under appropriate company safety
    procedures.

------------------------------------------------------------------------

# 35. Backup and Recovery

Important historical machine events are stored in PostgreSQL.

Follow the company's backup and data-retention policy.

At minimum, preserve:

``` text
Project source code
ESP32 firmware
PostgreSQL database backup
.env configuration (stored securely)
Tailscale access/configuration information
```

A database backup is important because it contains historical machine
events.

The `.env` file should be recreated securely rather than placed in
public repositories or shared documentation.

------------------------------------------------------------------------

# 36. Adding More Machines

The current software configuration uses:

``` python
MACHINES = ["A", "B"]
```

Adding additional machines requires both software and hardware
consideration:

1.  ESP32 GPIO availability
2.  Relay/sensor input
3.  Electrical isolation
4.  Machine signal source
5.  Wi-Fi coverage
6.  Database machine identifier
7.  Dashboard configuration
8.  Physical installation and safety

For larger deployments, multiple ESP32 controllers may be preferable.

The current architecture can be extended toward more machines and
production areas.

------------------------------------------------------------------------

# 37. Port Reference

    Port Service      Purpose
  ------ ------------ ----------------------
    5000 Flask        ESP32 machine events
    5432 PostgreSQL   Database
    8501 Streamlit    Dashboard

``` text
ESP32
  │
  └── HTTP → PC:5000/event

Streamlit
  │
  └── PostgreSQL → PC:5432

Browser
  │
  └── Streamlit → PC:8501
```

------------------------------------------------------------------------

# 38. System Health Checklist

Before considering the system operational:

-   [ ] PostgreSQL is running
-   [ ] `steel_pipe_db` exists
-   [ ] `.env` is configured
-   [ ] `receiver.py` starts successfully
-   [ ] Flask listens on port 5000
-   [ ] Streamlit starts successfully
-   [ ] Dashboard opens locally
-   [ ] ESP32 connects to Wi-Fi
-   [ ] ESP32 uses GPIO 4 for Machine A
-   [ ] ESP32 uses GPIO 6 for Machine B
-   [ ] ESP32 sends events
-   [ ] Flask receives events
-   [ ] PostgreSQL records events
-   [ ] Dashboard displays current state
-   [ ] Tailscale is connected, if required
-   [ ] Tailscale Serve is active, if required
-   [ ] `.ts.net` dashboard address works for an authorized device, if
    required

------------------------------------------------------------------------

# 39. Quick Reference

## Start Flask

``` powershell
python receiver.py
```

## Start Streamlit

``` powershell
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

## Check PC IP

``` powershell
ipconfig
```

## Check Tailscale

``` powershell
tailscale status
```

## Check Tailscale Serve

``` powershell
tailscale serve status
```

## Local dashboard

``` text
http://localhost:8501/
```

## Tailscale dashboard

``` text
https://ss-machine-status-monitoring.tail4daa8c.ts.net/
```

## ESP32 server endpoint

``` text
http://<MONITORING-PC-IP>:5000/event
```

## Final ESP32 GPIO mapping

``` text
Machine A → GPIO 4
Machine B → GPIO 6
```

------------------------------------------------------------------------

# 40. Project Handover

The system is designed so that the company can operate and continue
developing it independently.

For future maintenance, identify which layer has the problem:

``` text
Machine / Relay
      ↓
ESP32
      ↓
Network
      ↓
Flask Receiver
      ↓
PostgreSQL
      ↓
Streamlit
      ↓
Tailscale / User Access
```

When troubleshooting, check each layer from top to bottom rather than
changing multiple components at once.

------------------------------------------------------------------------

# 41. Future Development

The current implementation is a practical prototype and foundation.

Possible future development includes:

-   More machines
-   More production lines
-   More warehouses
-   Centralized production monitoring
-   Historical production analysis
-   Machine utilization analysis
-   Maintenance monitoring
-   Alerts and notifications
-   Production performance indicators
-   Machine naming based on actual plant identifiers
-   Integration with other industrial systems
-   More robust industrial signal acquisition
-   Automated startup/service management

Any future expansion should be validated against actual machine signals,
network conditions, electrical safety requirements, and company IT
policies.

------------------------------------------------------------------------

# 42. Handover Notes

The most important points for future maintainers are:

### Hardware

``` text
ESP32-S3 N16R8

Machine A → GPIO 4
Machine B → GPIO 6

LOW  = ON
HIGH = OFF
```

### Software

``` text
ESP32
   ↓
Flask :5000
   ↓
PostgreSQL :5432
   ↓
Streamlit :8501
```

### Remote access

``` text
Authorized device
       ↓
Tailscale
       ↓
Streamlit
```

### Configuration

``` text
.env
```

contains private PostgreSQL credentials and must not be publicly shared.

### Final firmware behavior

The ESP32 sends:

-   an event when the machine state changes
-   the current state every 30 seconds as a heartbeat

------------------------------------------------------------------------

# 43. Final Note

This project represents a practical first step toward more connected and
data-driven production monitoring.

**The system works today. The architecture is there for tomorrow.**

The intention is not to stop at the current prototype. The system can
serve as a reference for future monitoring improvements, additional
machines, and broader production digitalization.

> **A small monitoring system can become the first step toward a larger
> digital production environment.**

We hope this project can serve as a guide and a light for the company's
future development --- providing not only a working system today, but
also a clear foundation for what can be built tomorrow.
