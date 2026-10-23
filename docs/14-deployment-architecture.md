# 14. Deployment Architecture — CSCM Tool

## 1. Deployment Principle: Fully On-Premises, No Cloud

The system runs **entirely on local, on-premises servers**. No public cloud (SaaS/PaaS/IaaS) component is used anywhere — not for compute, not for the database, not for backups, not for authentication, not for logging/monitoring shipment. This is a hard constraint (C-004a, new in v2), not a default that may quietly drift: every environment below is a physical or on-prem-virtualized server inside the corporate network, and every future integration point in this package (08-system-architecture.md §6–§7) is explicitly scoped to stay on-premises. See 11-security-architecture.md §12 for the standing verification checklist.

## 2. Environment Overview

| Environment | Purpose | Data | Access | Location |
|---|---|---|---|---|
| Development | Individual developer workstations | Local seeded fixtures, disposable SQLite file | Developers only | On-prem workstation |
| Test / CI | Automated test execution | Ephemeral, recreated per run | CI runner only | On-prem CI server |
| Staging | Pre-production validation, UAT, performance/security testing | Synthetic production-scale dataset | Project team, UAT participants | On-prem server |
| Production | Live system of record (the Master Database, 08-system-architecture.md §6) | Real governed status code data | All licensed end users, per RBAC | On-prem server |

## 3. Infrastructure

- **Compute:** one application server (physical or on-prem VM) per environment; minimum 2 vCPU / 4 GB RAM for MVP load (NFR-004).
- **OS:** Windows Server (IIS + Waitress WSGI) or Linux (nginx + gunicorn), whichever matches the organization's standard on-prem server platform.
- **Storage:** local attached disk for the SQLite database file, export/backup working directory, and full-database export output (11-security-architecture.md §7), on a volume covered by the organization's standard on-prem encryption-at-rest and antivirus/EDR policy.
- **Network:** internal corporate network only; no public internet ingress or egress is required or permitted for any core function. Reverse proxy terminates TLS on the internal network and forwards to the Flask WSGI process on a private interface.
- **DNS/TLS certificates:** issued by the organization's internal CA, renewed per its standard rotation process — never a public cloud-issued certificate service if that would imply an external dependency; an internet-facing public CA (e.g. for TLS only) is acceptable only if the organization's policy already treats that as compatible with an otherwise fully on-prem system — flagged here for the platform team to confirm, since it is the one edge case where "no cloud" and "valid TLS certificate" can appear to be in tension.
- **Identity:** on-premises Active Directory / ADFS only for any future SSO integration (08-system-architecture.md §7, 11-security-architecture.md §2) — never a cloud identity provider.

## 4. Application Deployment Process

CI builds and tests on every push (`scripts/ci.py`, defined for the internal Git server in `.gitea/workflows/ci.yml` and `.gitlab-ci.yml`; NFR-013); tagged release produces a versioned artifact published to an **on-premises** artifact store (not a cloud package registry, unless the organization's existing on-prem mirror/proxy of a public registry is used for dependency resolution only — the application's own artifacts are never published externally); deployment to Staging automatic on tag, Production manual-approval gated and done with the installer below; standard stop → backup → deploy → migrate → start → smoke-test → confirm-or-rollback sequence; brief planned outage acceptable per NFR-002.

## 5. Master Database Export Process

CSCM Tool's production database is the Master Database (08-system-architecture.md §6) — there is no external master system it synchronizes with. Two, and only two, ways data leaves the system, both Administrator-gated:

1. **Catalogue export** (CSV/JSON/XLSX/PDF) — role-scoped per 11-security-architecture.md §3, generated on demand, never automatic/scheduled in MVP, used by Technical Publications and other downstream consumers.
2. **Full-database export/backup** — Administrator-only (SEC-015), a raw SQLite backup file, used for disaster recovery, environment migration, or handing a complete dataset to an authorized downstream consumer under separate organizational process. This is distinct from the nightly backup procedure (§6) in that it is a manually-triggered, audited (`FULL_DATABASE_EXPORT`, 12-audit-compliance.md §2), on-demand action rather than a scheduled operational job — though it uses the same underlying SQLite Online Backup mechanism.

No system pushes data into CSCM Tool; all status codes are authored inside the application by design (01-executive-summary.md §1). *(v4)* Catalogue exports can be shaped by profile, audience, language and software version and carry a manifest (FR-100 … FR-111); machine consumers may pull with scoped API tokens, poll the change feed or receive signed webhooks — all inside the network (08-system-architecture.md §6).

### 4a. Installation and Upgrade *(v4, NFR-013)*

`cscm_tool/deploy/` holds one installer per platform; both are idempotent, take **nothing** from the internet except the Python packages of `requirements.txt` (point `PIP_INDEX_URL` at the internal mirror), never overwrite configuration, data or backups, and offer a dry run that prints every step and changes nothing.

| | Linux (systemd) | Windows Server |
|---|---|---|
| Run | `sudo deploy/linux/install.sh [--dry-run]` | `powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1 [-DryRun] [-InstallDir C:\CSCM] [-RunAs <account>]` |
| Code, environment | `/opt/cscm/app`, `/opt/cscm/venv` | `C:\CSCM\app`, `C:\CSCM\venv` |
| Configuration (created once, generated keys) | `/etc/cscm/cscm.env`, mode 640 | `C:\CSCM\config\cscm.env`, ACL: Administrators and the service account |
| Data (database, attachments, imports, audit anchor) | `/var/lib/cscm` (`CSCM_INSTANCE_PATH`) | `C:\CSCM\data` |
| Backups, log | `/var/backups/cscm`, `/var/log/cscm/cscm.log` | `C:\CSCM\backups`, `C:\CSCM\logs\cscm.log` |
| Web server | `cscm.service` → `scripts/serve.py` (Waitress, unprivileged user, systemd hardening) | scheduled task *CSCM Tool – web server* at start-up |
| Jobs | `cscm-backup.timer` 02:15 daily, `cscm-reminders.timer` weekdays 07:30, `cscm-audit-verify.timer` Sundays 03:30 | tasks *nightly backup*, *reminders*, *audit chain check* with the same times |
| Reverse proxy | `deploy/linux/nginx-cscm.conf` (TLS from the internal CA, `X-Forwarded-*`, `/metrics` limited to the monitoring network) | IIS/ARR or nginx, same headers |

**PDF fonts (v4.7, FR-165).** The Noto fonts for the PDF export are part of the code (`app/static/fonts/`, SIL Open Font License, licence file included), so nothing is installed on the server; the only addition to `requirements.txt` is the binary wheel `uharfbuzz`, which an on-premises package mirror must carry like the others.

What the installer does, in order: create the service account and directories; copy the code (and `docs/artifacts/schema.sql`, which the baseline migration executes); build the virtual environment from the runtime part of `requirements.txt`; create the configuration **once** with freshly generated `SECRET_KEY`, `AUDIT_HMAC_KEY` and `MANIFEST_SIGNING_KEY` (**keep a copy in the password safe — they cannot be recovered**); take a verified backup of an existing database, then `flask db upgrade`; ask for the first Administrator if the database has no users (`flask create-admin`, which also reads `CSCM_ADMIN_USERNAME`, `…_EMAIL`, `…_FULL_NAME`, `…_PASSWORD` for unattended installs); install and start the units or tasks. `scripts/serve.py` refuses to start in production with a missing, default or short `SECRET_KEY` (SEC-002) and honours `CSCM_HOST`, `CSCM_PORT`, `CSCM_THREADS` and `CSCM_TRUSTED_PROXY` (so the login rate limit sees the real client address behind the proxy). `deploy/windows/uninstall.ps1` removes the tasks and never deletes data. The settings are listed in `cscm_tool/.env.example`; a test checks that every setting the installers write is read by the application.

**Windows sign-in (v4.7, FR-163, SEC-033).** In a deployment people sign in with their Windows account, not a password. The proxy authenticates the user against Active Directory (IIS or ARR with Windows authentication; Apache with Kerberos; nginx with spnego), **removes** any `X-Remote-User` header the client sent and sets its own from the authenticated session; the application is reachable only through the proxy. In `cscm.env`: `AUTH_MODE=windows` (`both` keeps the password form for the transition; `password` is the default), `WINDOWS_AUTH_TRUSTED_PROXIES=<address of the proxy>` (required: without it the header is ignored), optionally `WINDOWS_AUTH_HEADER` and `WINDOWS_AUTH_EMAIL_DOMAIN` (for `CORP

**The Windows sign-in tested with a real Windows identity (v4.9, TC-062).** `scripts/windows_gateway.py` is a small stand-in for IIS: it answers a request without credentials with a `401` that offers `Negotiate` and `NTLM`, completes the handshake with the Windows SSPI of the operating system (`secur32` through `ctypes`, no package to install), takes the user name from the security context, drops any identity header the client sent and passes the user on in `X-Remote-User`. `tests/system/test_windows_gateway.py` runs the real handshake — a client with the credentials of the Windows user who runs the tests against the SSPI server side of the gateway — and then the whole chain client, gateway, application; these tests run on Windows only. By hand: `python scripts/windows_gateway.py --listen 127.0.0.1:8080 --upstream http://127.0.0.1:5000` with `AUTH_MODE=windows` and `WINDOWS_AUTH_TRUSTED_PROXIES` set to the address the gateway connects from (`--source`, default `127.0.0.2`), then `curl.exe --ntlm -u : http://127.0.0.1:8080/login/windows`. What it proves: the application signs in the account that the operating system names, refuses an unknown or deactivated account and ignores the header when it does not come from the gateway. What it does not prove: Kerberos, a domain controller, IIS or ARR. On a computer that is not in a domain the identity is the local account `COMPUTER\user`, which the application matches through the user name (FR-163); a browser sends integrated credentials only to hosts of the intranet zone, so a development browser does not sign in through `127.0.0.1`.
ame` identities). The account is found by e-mail address, so every user needs an account with the address of their user principal name, created by an Administrator (nobody is created on the fly). `WINDOWS_AUTH_SIMULATE` exists for developer machines only; the application refuses to start in production with it. The pre-go-live checklist gains: a real sign-in through the proxy, a request that carries the header but comes from another address (must be ignored), and a deactivated account (must be refused).

**What cannot be proven on a development machine** and is therefore on the pre-go-live checklist (20-traceability-matrix.md §6): a real install on a clean Windows Server and a clean Linux host, systemd's own verification of the units, TLS termination and the proxy headers, the Windows sign-in through the real gateway (the simulation and the test gateway of the paragraph above prove the application's side and the operating system's handshake, not Kerberos, a domain controller or IIS), and the egress block on the production server.

## 6. Backup Procedure

Nightly SQLite Online Backup API snapshot (never a raw file copy) by `flask backup-db --keep 35` (the shipped timer; the command's own default is 14 generations), copied within 1 hour to an on-premises storage location separate from the application server (`BACKUP_DIR` should be that location or be replicated to it), 12 monthly copies kept by the organisation's own tooling, 7-day WAL archiving for point-in-time recovery. No backup target is ever a cloud storage service.

**Every backup is proven (v4, FR-150, NFR-012).** After copying, the job runs `PRAGMA integrity_check` on the copy, restores it into a scratch database and compares the row counts of the key tables with the live database, checks the audit hash chain of the copy, and writes `backup_status.json` (file, size, SHA-256, `ok`, the time of the last *verified* success). A backup that fails any check is kept for diagnosis but never counts as the last good one, the command exits non-zero (the scheduler shows the unit as failed) and the readiness probe reports `degraded` (`last_attempt_failed`, or `stale` when the newest verified backup is older than `BACKUP_MAX_AGE_HOURS`, default 36). `flask verify-backup <file>` repeats the proof for any file.

**Audit archive (AUD-073).** `flask audit-archive --dest <dir> [--older-than-years 7]` writes entries past the retention period to a compressed file with a `.sha256`, records an `AUDIT_ARCHIVE` entry and deletes nothing; run it yearly.

## 7. Recovery Procedure

RPO ≤ 24 h (≤ 1 h with WAL), RTO ≤ 4 h.

**Restore runbook.**
1. Stop the web service (`systemctl stop cscm` / stop the scheduled task).
2. Choose the newest generation named `last_good_file` in `backup_status.json`; run `flask verify-backup <file>` — it must print `"ok": true` (integrity, restore test, audit chain).
3. Move the damaged `cscm.db` (and its `-wal` / `-shm` files) aside; copy the backup to the database path.
4. Run `flask db upgrade` (a no-op when the backup is at the current schema, an upgrade when it is older).
5. Start the service; `GET /api/v1/health/ready` must answer `ok` or `degraded` (degraded only because no backup is younger than 36 h yet).
6. Run `flask audit-verify` (the first run after a restore may report that the log is shorter than at the last verification — delete `audit_chain_anchor.json` in the data directory to accept the restored state, and note this in the incident record) and spot-check the newest status codes in the UI.
7. Run `flask backup-db` once so the readiness probe is green again.

**Quarterly drill.** Perform steps 2–6 on a scratch host with the latest backup, record the time taken and the result; the test suite proves the mechanics (`test_a_restored_backup_runs_the_application`, `test_a_tampered_audit_log_inside_a_backup_is_flagged`) but not your hardware.

## 8. Monitoring

`GET /api/v1/health` (liveness) and `GET /api/v1/health/ready` (readiness: database, schema at the Alembic head, newest audit rows, last verified backup; 200 `ok`/`degraded`, 503 `unavailable`) for the load balancer and monitoring; `GET /metrics` (Prometheus text) from the monitoring network only — `METRICS_ALLOWED_CIDRS` (default loopback and RFC 1918) or `METRICS_TOKEN`; each worker process is scraped separately. Suggested alerts: readiness not 200; `cscm_backup_ok == 0` or `cscm_backup_age_hours > 36`; `cscm_cr_waiting{level="red"}` rising; `cscm_db_lock_wait_seconds` p95 above 1 s; 5xx rate above 0.1 % (NFR-001); disk space; failed-login spikes. All shipped to an **on-premises** log/monitoring store, never a cloud observability SaaS product, unless the organization already runs such tooling entirely within its own infrastructure (self-hosted, not a hosted cloud offering).

## 9. Logging

Structured JSON request logs (one line per request with the request id, never credentials or tokens) on stderr and, with `LOG_FILE`, in a rotating file (10 MB × 5) for the log shipper, shipped to an on-prem central log store; reverse-proxy access logs retained per organizational standard; the `audit_log_entry` compliance record lives in the application database itself, never in log files.

## 10. Environment Parity

Staging kept at application-version and OS/runtime parity with Production, synthetic data volume scaled to meet or exceed NFR-001's sizing assumption, now distributed realistically across all nine Functional System Groups rather than a single Controller Type split.
