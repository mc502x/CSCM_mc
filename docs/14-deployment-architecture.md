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

Unchanged in structure from v1 (14-deployment-architecture.md v1 §3): CI builds and tests on every push; tagged release produces a versioned artifact published to an **on-premises** artifact store (not a cloud package registry, unless the organization's existing on-prem mirror/proxy of a public registry is used for dependency resolution only — the application's own artifacts are never published externally); deployment to Staging automatic on tag, Production manual-approval gated; standard stop → backup → deploy → migrate → start → smoke-test → confirm-or-rollback sequence; brief planned outage acceptable per NFR-002.

## 5. Master Database Export Process

CSCM Tool's production database is the Master Database (08-system-architecture.md §6) — there is no external master system it synchronizes with. Two, and only two, ways data leaves the system, both Administrator-gated:

1. **Catalogue export** (CSV/JSON/PDF) — role-scoped per 11-security-architecture.md §3, generated on demand, never automatic/scheduled in MVP, used by Technical Publications and other downstream consumers.
2. **Full-database export/backup** — Administrator-only (SEC-015), a raw SQLite backup file, used for disaster recovery, environment migration, or handing a complete dataset to an authorized downstream consumer under separate organizational process. This is distinct from the nightly backup procedure (§6) in that it is a manually-triggered, audited (`FULL_DATABASE_EXPORT`, 12-audit-compliance.md §2), on-demand action rather than a scheduled operational job — though it uses the same underlying SQLite Online Backup mechanism.

No system pushes data into CSCM Tool; all status codes are authored inside the application by design (01-executive-summary.md §1).

## 6. Backup Procedure

Unchanged in mechanism from v1 (§5): nightly SQLite Online Backup API snapshot (never a raw file copy), copied within 1 hour to an on-premises storage location separate from the application server, 35 daily + 12 monthly retention, 7-day WAL archiving for point-in-time recovery, weekly automated restore-and-checksum verification against an on-prem scratch environment. No backup target is ever a cloud storage service.

## 7. Recovery Procedure

Unchanged in mechanism and RPO/RTO targets from v1 (§6): RPO ≤ 24h (≤ 1h with WAL), RTO ≤ 4h, on-prem restore procedure with smoke test and row-count/audit cross-check.

## 8. Monitoring

Unchanged in mechanism from v1 (§7): health-check endpoint, error-rate/latency thresholds against NFR-001, disk-space monitoring, failed-login-spike detection — all shipped to an **on-premises** log/monitoring store, never a cloud observability SaaS product, unless the organization already runs such tooling entirely within its own infrastructure (self-hosted, not a hosted cloud offering).

## 9. Logging

Unchanged from v1 (§8): structured JSON application logs shipped to an on-prem central log store; reverse-proxy access logs retained per organizational standard; the `audit_log_entry` compliance record lives in the application database itself, never in log files.

## 10. Environment Parity

Unchanged from v1 (§9): Staging kept at application-version and OS/runtime parity with Production, synthetic data volume scaled to meet or exceed NFR-001's sizing assumption, now distributed realistically across all nine Functional System Groups rather than a single Controller Type split.
