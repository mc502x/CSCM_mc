# CSCM Tool — Quick deployment guide

For a new machine. Two paths: **A. try it** (10 minutes, one person, no server setup) and **B. install it for the team** (Windows Server or Linux, runs as a service). The full reference is [docs/14-deployment-architecture.md](docs/14-deployment-architecture.md) §4a.

The tool runs entirely on-premises. The only thing it downloads is the Python packages of `cscm_tool/requirements.txt` (use `PIP_INDEX_URL` for an internal mirror).

## What you need

- **Python 3.12 or newer** (`python --version`)
- **Git**, and read access to https://github.com/mc502x/CSCM_mc (branch `dev`)
- Windows 10/11/Server or Linux. SQLite is built in, no database server to install.

## A. Try it on a new machine (development mode)

```bash
git clone -b dev https://github.com/mc502x/CSCM_mc.git
cd CSCM_mc/cscm_tool

python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env            # Linux/macOS: cp .env.example .env
flask db upgrade                  # creates instance/cscm.db with the schema and seed data
flask create-admin                # asks for the first Administrator (name, e-mail, password)
python dev_server.py 5001         # or: flask run
```

Open http://localhost:5001 and log in with the Administrator you just created. Create the other users (Engineer, Reviewer, Chief Engineer, StCd Owner, Viewer) on the user administration page (`/admin/users`).

**Check that it works**

1. `http://localhost:5001/api/v1/health` shows `{"status": "ok"}`.
2. `http://localhost:5001/api/v1/health/ready` reports database, schema, audit chain and backup state.
3. Import the sample programs: *Import from .st files* → choose `cscm_tool/tests/fixtures/st/*.st` → preview → create Drafts.
4. Run the automated tests (about 20 minutes for everything, `-m "not performance"` skips the load tests):
   ```bash
   pytest -m "not performance"
   ```

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

| Message | Cause and fix |
|---|---|
| `unable to open database file` | Fixed in v4.13.3. On an older checkout, open `.env` and delete or comment out the line `DATABASE_URL=sqlite:///instance/cscm.db`; the default puts the file at `cscm_tool/instance/cscm.db`. To put the database elsewhere use an **absolute** path whose folder exists, for example `DATABASE_URL=sqlite:///C:/CSCM/data/cscm.db`. |
| `no such table` / empty pages | The database has not been created yet: run `flask db upgrade` once in `cscm_tool/` with the virtual environment active. |
| `Refusing to start in production` | `SECRET_KEY` is missing, short, or still `change-me...`. Set 32+ random characters in `.env`. |
| `flask` is not found | The virtual environment is not active: `.venv\Scriptsctivate`. |

## Moving existing data to a new machine

On the old machine: `flask backup-db --dest <folder>`. Copy the backup file, install the tool on the new machine as above, stop the web server, replace `cscm.db` in the data folder (`instance/` or `C:\CSCM\data`) with the backup, run `flask db upgrade`, start the server and run `flask audit-verify`. The new machine needs the **same** `AUDIT_HMAC_KEY` and `MANIFEST_SIGNING_KEY` as the old one.

## Upgrading

`git pull`, then run the installer again (production) or `pip install -r requirements.txt` and `flask db upgrade` (development). The installer takes a verified backup before it migrates.

## Known limits (be honest with yourself before go-live)

The installers are tested in dry-run and by the automated tests, but **not yet on a clean Windows Server or Linux host**, and the Windows sign-in is proven against the Windows handshake of a test gateway, not against your domain controller or IIS. Do a trial installation on a spare machine first and work through the pre-go-live checklist in [docs/20-traceability-matrix.md](docs/20-traceability-matrix.md) §6.
