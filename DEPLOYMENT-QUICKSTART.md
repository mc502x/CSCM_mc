# CSCM Tool — Quick deployment guide

For a new machine. Two paths: **A. try it** (about 10 minutes, one person, no server setup) and **B. install it for the team** (Windows Server or Linux, runs as a service). The full reference is [docs/14-deployment-architecture.md](docs/14-deployment-architecture.md) §4a.

The tool runs entirely on-premises. The only thing it downloads is the Python packages of `cscm_tool/requirements.txt` (use `PIP_INDEX_URL` for an internal mirror).

## What you need

- **Python 3.12 or newer** — check with `python --version` (on Linux often `python3 --version`).
- **Git**, and read access to https://github.com/mc502x/CSCM_mc (branch `dev`).
- Windows 10/11/Server or Linux. SQLite is built in; there is no database server to install.

## A. Try it on a new machine (development mode)

### 1. Get the code and find your place

Use **any** terminal: PowerShell, Command Prompt, or Git Bash. The commands below are the same in all of them.

```bash
git clone -b dev https://github.com/mc502x/CSCM_mc.git
cd CSCM_mc
```

If you already cloned it, you are probably in the right place. Check: the folder you are in must contain a folder named `cscm_tool` (`dir` in PowerShell/cmd, `ls` in Git Bash). **Do not `cd CSCM_mc` a second time**: if the prompt already ends in `CSCM_mc`, stay there.

### 2. Run the first start

```bash
python cscm_tool/scripts/first_start.py
```

Linux or macOS: `python3 cscm_tool/scripts/first_start.py`.

The script works from whatever folder you are in and does everything, in order, telling you each step:

1. checks the Python version,
2. creates the virtual environment `cscm_tool/.venv` (an existing one is left alone),
3. installs the packages (about a minute),
4. creates `cscm_tool/.env` from `.env.example` (an existing one is kept),
5. creates the database `cscm_tool/instance/cscm.db`,
6. asks for the **first Administrator** (name, e-mail, password) if there is none yet.

It then prints the command that starts the tool. It is safe to run again: finished steps are skipped. `--dry-run` shows the steps without changing anything; `--port 5002` changes the printed port; `--no-admin` skips the Administrator.

### 3. Start it

Run the command the script printed, inside `cscm_tool`:

| Shell | Start command |
|---|---|
| PowerShell or Command Prompt | `cd cscm_tool` then `.venv\Scripts\python.exe dev_server.py 5001` |
| Git Bash | `cd cscm_tool` then `.venv/Scripts/python.exe dev_server.py 5001` |
| Linux / macOS | `cd cscm_tool` then `.venv/bin/python dev_server.py 5001` |

Open http://localhost:5001 and log in with the Administrator you created. Create the other users (Engineer, Reviewer, Chief Engineer, StCd Owner, Viewer) on the user administration page (`/admin/users`).

You do not need to "activate" the virtual environment: these commands use its Python directly, which is why they work the same in every shell.

### 4. Check that it works

1. `http://localhost:5001/api/v1/health` shows `{"status": "ok", "version": "4.15.0"}`; the same version is at the foot of the menu and of the login page.
2. `http://localhost:5001/api/v1/health/ready` reports database, schema, audit chain and backup state.
3. Import the sample programs: *Import from .st files* → choose `cscm_tool/tests/fixtures/st/*.st` → preview → create Drafts.
4. Run the automated tests (about 20 minutes for everything; `-m "not performance"` skips the load tests). Inside `cscm_tool`: `.venv\Scripts\python.exe -m pytest -m "not performance"` (Git Bash: `.venv/Scripts/python.exe`, Linux: `.venv/bin/python`).

### The same by hand (only if you cannot use the script)

Inside `cscm_tool`:

| Step | PowerShell / cmd | Git Bash | Linux |
|---|---|---|---|
| Environment | `python -m venv .venv` | `python -m venv .venv` | `python3 -m venv .venv` |
| Activate | `.venv\Scripts\activate` | `source .venv/Scripts/activate` | `source .venv/bin/activate` |
| Packages | `pip install -r requirements.txt` | same | same |
| Settings | `copy .env.example .env` | `cp .env.example .env` | `cp .env.example .env` |
| Database | `flask db upgrade` | same | same |
| Administrator | `flask create-admin` | same | same |

## B. Install for the team (production)

Run from a checkout of the repository, as an administrator.

**Windows Server**
```powershell
cd CSCM_mc\cscm_tool
powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1 -DryRun    # prints every step, changes nothing
powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1             # installs to C:\CSCM
```

**Linux (systemd)**
```bash
cd CSCM_mc/cscm_tool
sudo deploy/linux/install.sh --dry-run
sudo deploy/linux/install.sh                                   # installs to /opt/cscm
```

The installer creates the directories and service account, builds the virtual environment, writes the configuration **once** with freshly generated `SECRET_KEY`, `AUDIT_HMAC_KEY` and `MANIFEST_SIGNING_KEY`, runs the migrations, creates the first Administrator, and sets up the web server plus the nightly verified backup, weekday reminders and the weekly audit-chain check. It never overwrites configuration, data or backups, so **running it again is also the upgrade**.

**Then, before people use it**

1. **Keep a copy of the three keys** from `C:\CSCM\config\cscm.env` (Linux: `/etc/cscm/cscm.env`) in your password safe. They cannot be recovered, and a backup is useless without them.
2. **Put a reverse proxy with TLS in front** (IIS/ARR or nginx; example: `deploy/linux/nginx-cscm.conf`). The application listens on `127.0.0.1:8000` only; set `CSCM_TRUSTED_PROXY` to the proxy's address.
3. **Sign-in with the Windows account** (optional): set `AUTH_MODE=windows` (or `both` while testing) and `WINDOWS_AUTH_TRUSTED_PROXIES` to the proxy address. The proxy must authenticate against Active Directory and set the `X-Remote-User` header itself. Every user needs an account whose e-mail equals their user principal name.
4. **Backups:** point `BACKUP_DIR` at storage on a different machine. Test a restore once: `flask verify-backup <file>`.
5. Check `/api/v1/health/ready` through the proxy.

## If something goes wrong

Read the message, find it in the left column. **Most first-start problems are "wrong folder" or "wrong shell".** `pwd` (Git Bash, Linux), `cd` (cmd) or `Get-Location` (PowerShell) tells you where you are.

| Message | Cause and fix |
|---|---|
| `cd: CSCM_mc/cscm_tool: No such file or directory` | You are already inside `CSCM_mc`. Do not change folder again; run `python cscm_tool/scripts/first_start.py` from where you are. |
| `Could not open requirements file` / `cp: cannot stat '.env.example'` / `can't open file '...dev_server.py'` | You are not in `cscm_tool`. Use the script (it finds the right folder itself), or `cd cscm_tool` first. |
| `flask: command not found` / `'flask' is not recognized` | The virtual environment is not active or was not created. Use the script and the start command it prints; `.venv/.../python -m flask ...` needs no activation. |
| `Permission denied: '...\.venv\Scripts\python.exe'` (while creating `.venv`) | You tried to recreate `.venv` while it is active or in use. Close other terminals using it, run `deactivate`, delete the `.venv` folder, run the script again. The script never recreates an existing `.venv`. |
| `unable to open database file` | Fixed in v4.13.3: `git pull`. On an older checkout open `.env` and delete or comment out the line `DATABASE_URL=sqlite:///instance/cscm.db`. To put the database elsewhere use an **absolute** path, e.g. `DATABASE_URL=sqlite:///C:/CSCM/data/cscm.db`. |
| `no such table` / empty pages | The database was not created: run the script again, or `flask db upgrade` in `cscm_tool`. |
| `Refusing to start in production` | `SECRET_KEY` is missing, short, or still `change-me...`. Set 32+ random characters in `.env`. |
| `A new release of pip is available` | Only a notice. Ignore it. |
| Python is older than 3.12 | Install Python 3.12 or newer and run the script with it (on Windows: `py -3.12 cscm_tool/scripts/first_start.py`). |

## Moving existing data to a new machine

On the old machine: `flask backup-db --dest <folder>`. Copy the backup file, install the tool on the new machine as above, stop the web server, replace `cscm.db` in the data folder (`instance/` or `C:\CSCM\data`) with the backup, run `flask db upgrade`, start the server and run `flask audit-verify`. The new machine needs the **same** `AUDIT_HMAC_KEY` and `MANIFEST_SIGNING_KEY` as the old one.

## Upgrading

`git pull`, then run the installer again (production) or the first-start script again (development: it installs new packages and applies new migrations). The production installer takes a backup before it migrates.

## Known limits (be honest with yourself before go-live)

The installers are tested in dry-run and by the automated tests, but **not yet on a clean Windows Server or Linux host**, and the Windows sign-in is proven against the Windows handshake of a test gateway, not against your domain controller or IIS. Do a trial installation on a spare machine first and work through the pre-go-live checklist in [docs/20-traceability-matrix.md](docs/20-traceability-matrix.md) §6. The development first-start script was run end to end on a clean copy (new environment, packages, database, first Administrator, second run) and by an automated dry-run test.
