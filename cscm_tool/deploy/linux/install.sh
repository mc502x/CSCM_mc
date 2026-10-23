#!/usr/bin/env bash
# CSCM Tool - on-premises installer for Linux (systemd). docs/14-deployment-architecture.md section 4.
#
#   sudo ./install.sh                 install or upgrade from this checkout
#   sudo ./install.sh --dry-run       print what would be done, change nothing
#
# Idempotent: running it again upgrades the code, applies pending migrations and leaves the
# configuration, the database and the backups alone. Nothing is downloaded except the Python
# packages in requirements.txt - point pip at your internal mirror (PIP_INDEX_URL) if the server
# has no internet access, which is the expected case.
#
# Layout:  /opt/cscm/app        code (replaced on upgrade)
#          /opt/cscm/venv       virtual environment
#          /etc/cscm/cscm.env   configuration (mode 640, created once)
#          /var/lib/cscm        database and instance files (attachments, imports, audit anchor)
#          /var/backups/cscm    verified backups      /var/log/cscm   application log
set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP=/opt/cscm/app
VENV=/opt/cscm/venv
CONF=/etc/cscm
ENVFILE="$CONF/cscm.env"
DATA=/var/lib/cscm
BACKUPS=/var/backups/cscm
LOGS=/var/log/cscm
SERVICE_USER=cscm

step() { echo "==> $*"; }
run() {
  if [ "$DRY_RUN" -eq 1 ]; then echo "    [dry-run] $*"; else "$@"; fi
}

if [ "$DRY_RUN" -eq 0 ] && [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (sudo ./install.sh), or use --dry-run." >&2
  exit 1
fi
[ -f "$SRC/wsgi.py" ] || { echo "Run this from a CSCM checkout: $SRC/wsgi.py not found." >&2; exit 1; }
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null || { echo "$PYTHON not found (Python 3.12 or newer is required)." >&2; exit 1; }
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' \
  || { echo "Python 3.12 or newer is required." >&2; exit 1; }

step "Service account and directories"
id "$SERVICE_USER" >/dev/null 2>&1 || run useradd --system --home-dir /opt/cscm --shell /usr/sbin/nologin "$SERVICE_USER"
run install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 750 /opt/cscm "$DATA" "$DATA/instance" "$BACKUPS" "$LOGS"
run install -d -o root -g "$SERVICE_USER" -m 750 "$CONF"

step "Application code -> $APP"
run install -d -o root -g "$SERVICE_USER" -m 755 "$APP"
run cp -a "$SRC/app" "$SRC/migrations" "$SRC/scripts" "$SRC/wsgi.py" "$SRC/requirements.txt" "$SRC/pyproject.toml" "$APP/"
run install -d -m 755 "$APP/../docs/artifacts"
run cp -a "$SRC/../docs/artifacts/schema.sql" "$SRC/../docs/artifacts/schema-fts5.sql" "$APP/../docs/artifacts/"

step "Virtual environment -> $VENV"
[ -d "$VENV" ] || run "$PYTHON" -m venv "$VENV"
run "$VENV/bin/pip" install --quiet --upgrade pip
run "$VENV/bin/pip" install --quiet -r <(sed '/^# --- dev/,$d' "$SRC/requirements.txt")

step "Configuration -> $ENVFILE"
if [ -f "$ENVFILE" ]; then
  echo "    exists - left untouched"
else
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "    [dry-run] create $ENVFILE with generated SECRET_KEY, AUDIT_HMAC_KEY, MANIFEST_SIGNING_KEY"
  else
    umask 027
    {
      echo "FLASK_APP=wsgi.py"
      echo "FLASK_ENV=production"
      echo "SECRET_KEY=$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))')"
      echo "AUDIT_HMAC_KEY=$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))')"
      echo "MANIFEST_SIGNING_KEY=$("$PYTHON" -c 'import secrets; print(secrets.token_urlsafe(48))')"
      echo "DATABASE_URL=sqlite:///$DATA/cscm.db"
      echo "CSCM_INSTANCE_PATH=$DATA/instance"
      echo "BACKUP_DIR=$BACKUPS"
      echo "LOG_FILE=$LOGS/cscm.log"
      echo "CSCM_HOST=127.0.0.1"
      echo "CSCM_PORT=8000"
      echo "CSCM_TRUSTED_PROXY=127.0.0.1"
    } > "$ENVFILE"
    chown root:"$SERVICE_USER" "$ENVFILE"
    chmod 640 "$ENVFILE"
    echo "    created. Keep a copy of the three keys in the password safe: they cannot be recovered."
  fi
fi

flask_as_service() {
  # Runs "flask <args>" as the service account with the production environment.
  runuser -u "$SERVICE_USER" -- env -C "$APP" bash -c \
    "set -a; . '$ENVFILE'; set +a; exec '$VENV/bin/flask' $*"
}

step "Database migrations"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "    [dry-run] flask db upgrade   (a backup of an existing database is taken first)"
else
  if [ -f "$DATA/cscm.db" ]; then
    flask_as_service backup-db || echo "    WARNING: pre-upgrade backup failed; continuing is your decision" >&2
  fi
  flask_as_service db upgrade -d "$APP/migrations"
fi

step "First Administrator"
if [ "$DRY_RUN" -eq 1 ]; then
  echo "    [dry-run] flask create-admin (only if the database has no users)"
elif [ "$(runuser -u "$SERVICE_USER" -- "$VENV/bin/python" -c \
    "import sqlite3; print(sqlite3.connect('$DATA/cscm.db').execute('select count(*) from user').fetchone()[0])" \
    2>/dev/null || echo 0)" = "0" ]; then
  echo "    No users yet. Choose the administrator account:"
  flask_as_service create-admin
else
  echo "    users exist - skipped"
fi

step "systemd units and timers"
for unit in cscm.service cscm-backup.service cscm-backup.timer cscm-reminders.service \
            cscm-reminders.timer cscm-audit-verify.service cscm-audit-verify.timer; do
  run install -m 644 "$SRC/deploy/linux/$unit" "/etc/systemd/system/$unit"
done
run systemctl daemon-reload
run systemctl enable --now cscm.service cscm-backup.timer cscm-reminders.timer cscm-audit-verify.timer
run systemctl restart cscm.service

step "Done"
echo "    Application: http://127.0.0.1:8000  (put the reverse proxy in front: deploy/linux/nginx-cscm.conf)"
echo "    Check:       curl -s http://127.0.0.1:8000/api/v1/health/ready"
