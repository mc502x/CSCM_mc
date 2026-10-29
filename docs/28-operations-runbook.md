# 28. Operations Runbook — CSCM Tool

> **For:** the Software Owner and Administrator and their deputy. **What it is:** the routine, the upgrade and its rollback, the incident procedures and the administration of the mapping, in one place, as checklists. **What it is not:** a second copy of the installation (14, §4a), the backup and restore procedure (14, §6 – §7) or the key rules (11, SEC-030); this document points to them and adds what was missing between them. Commands are run in the `cscm_tool` folder with the environment of the service (`.venv\Scripts\python.exe -m flask …` on Windows, `.venv/bin/python -m flask …` on Linux).

## 1. Routine

| When | Check | How | Normal | If not |
|---|---|---|---|---|
| Daily | The tool is up and healthy | `GET /api/v1/health/ready` (or the monitoring check) | `ok`, or `degraded` only because no verified backup is younger than 36 h | §4 (restore), §5 (chain) |
| Daily | Last night's backup is verified | `backup_status.json` in the backup folder: `ok: true`, time of the last verified success | younger than 36 h | run `flask backup-db`; read the message; free disk space; §3 |
| Weekly | The audit chain is intact | The Sunday job `flask audit-verify` (timer or scheduled task) | `ok` | §5 |
| Weekly | Stalled requests and mapping requests that wait | *Stalled Requests*, *Mapping changes* (menu counts) | none older than the SLA | ask the approvers, §8 |
| Monthly | Disk space; log size; number of users and their roles | Operations page, `/metrics` | > 30 % free | clean imports and staging, move backups off the host |
| Quarterly | **Restore drill** on a scratch host | 14, §7, steps 2 – 6; record the time and the result in the drill record (§10) | restored database passes `verify-backup`; the tool starts; the newest codes are there | fix the backup chain before anything else |
| Yearly | Audit archive | `flask audit-archive --dest <dir> --older-than-years 7`; store the file with its `.sha256` | one archive per year | — |
| Every release | Release documents and the decks | `python scripts/ci.py --pdf`, then `scripts/build_showcase.py --pdf` | files in `releases/v<version>/` | — |

## 2. Upgrade and rollback

**Before.** Tell the users the time. Check that the version to install passed the full pipeline (the test report of that version says `PASS`). Have the previous version's tag at hand.

**Upgrade.** Run the installer of the platform (14, §4a). It takes a backup of an existing database first, installs the packages, runs `flask db upgrade`, loads the initial mapping into an *empty* mapping table only, and reports what the new version changed in the interface text (`translation-impact`, notices to the StCd Owner). On a development or trial machine: `git pull`, `python cscm_tool/scripts/first_start.py` (safe to repeat).

**Smoke test (ten minutes, always).**
1. `GET /api/v1/health` shows the new version; `/health/ready` is `ok`.
2. Log in as an Administrator and as an Engineer; open the dashboard, *Status Codes*, one code, *Mapping*, *Mapping changes*.
3. Create a **sandbox** code and delete it (the sandbox cannot harm the catalogue).
4. Run `flask audit-verify`; it must be `ok`.
5. Take a backup (`flask backup-db`) and check `backup_status.json`.

**Rollback.** The migrations are one-way in practice: do **not** try to downgrade the database. Roll back by restoring:
1. Stop the service.
2. Take the *pre-upgrade backup* the installer made (the newest generation before the upgrade); `flask verify-backup <file>` must print `"ok": true`.
3. Put the previous code version in place (the previous tag); keep the configuration file (it holds the keys).
4. Restore the database as in 14, §7, steps 3 – 4, using the **previous** version's environment (no `db upgrade`).
5. Start; run the smoke test; tell the users what was lost (everything entered since the backup).
6. Open an incident record (§10) and keep the failing database file for the analysis.

## 3. Backup problems

| Sign | Cause usually | Action |
|---|---|---|
| `backup_status.json` older than 36 h | The job did not run or failed its checks | Run `flask backup-db` by hand and read the output; the failing check is named (integrity, restore test, row counts, chain) |
| Backup `ok: false` with *chain* | The audit chain of the live database is broken | §5 first; a backup of a broken chain is still kept |
| Disk full | Backups, attachments, imports | `--keep` the generations, move to the second volume, delete finished import folders |
| Backups only on the application server | Single point of failure (I-45) | Copy every night to a second host; test the copy with `verify-backup` |

## 4. Restore

14, §7 is the procedure. Add to the record: who decided, which generation, the time taken (target RTO 4 h), the state of the audit chain, what was lost.

## 5. The audit chain does not verify

`flask audit-verify` (or the weekly job) reports a broken chain. **Never repair by editing rows and never delete the anchor to make the message go away.**

1. Keep the database file and the newest backups unchanged; copy them to a protected place.
2. Read the output (JSON): `first_bad_id` is the first row that does not fit and `reason` says how - *broken link* (a row was removed or reordered), *row content does not match its hash* (a row was edited), *a row without a hash follows hashed rows*, or *the log is shorter than at the last verification* (rows at the end were removed; then `first_bad_id` is empty).
3. Run `flask verify-backup` on older generations to find the **last good** one — that bounds the time of the change.
4. Compare the rows around the break between the live database and the last good backup; ask who had access to the database file and the key at that time.
5. Inform the Software Owner and information security the same day (an unexplained change of the audit log is a security incident, not a bug).
6. Only after the cause is understood and written down does the StCd Owner decide, in writing, whether to continue from the live state (the anchor is then replaced, as after a restore, see 14, §7 step 6) or to restore the last good backup.

A *shorter* log after a **restore** is expected; the first verification after a restore needs the anchor to be replaced (14, §7 step 6).

## 6. Keys, accounts and secrets

| Item | Where | If lost or leaked |
|---|---|---|
| `SECRET_KEY` | the protected configuration file | Everybody is signed out when it changes; never put it in a ticket or a chat |
| `AUDIT_HMAC_KEY` | same; **a copy in the password safe** | Without it the chain of an existing database cannot be verified; with a *new* key the existing rows no longer verify. Rotation has no tool yet (I-48): until then the key is never changed on a running installation |
| `MANIFEST_SIGNING_KEY` | same; copy in the password safe | Manifests signed with the old key can only be verified with it; keep every retired key in the key archive with the dates it was in use |
| First Administrator | `flask create-admin` | Another Administrator resets the password in *Users*; if none exists, run `flask create-admin` again with a new name |
| Lists of initial passwords | any file or mail that hands out first passwords | Hand out, **delete the file the same day**, and force a change at first sign-in; a plain-text password list in the data folder is a finding in every audit |
| Test accounts | a development or trial database | Never copy such a database to production; remove `test_*` accounts first |

## 7. Accounts and roles

* Create people in *Users* (Administrator). The StCd Owner may change roles between Viewer, Engineer and Reviewer; everything above needs an Administrator (BR-024).
* Deactivate, do not delete, an account that has history; the person cannot sign in and everything they did stays attributable. Deleting erases the personal data and keeps the audit entries (BR-025).
* Engineers need their **engineering domains** tagged before they can give cross-domain sign-offs.
* At least **two Administrators** must exist; the tool refuses to remove the last one.

## 8. The mapping

*Who must be in place:* an **StCd Owner**, a **Chief Engineer** and **two Administrators** (one asks, another approves; the same person cannot do both). A request cannot be decided by its requester, and the three roles must be three different people (BR-027).

| Task | Procedure |
|---|---|
| Load the initial mapping | After the first installation `flask mapping-seed` (the installer runs it). It loads only into an **empty** table. Check the counts per status that the command and the audit entry `MAPPING_SEEDED` report: a workbook that carries `APPROVED` rows makes approved numbers without any recorded approval |
| Correct many rows | *Mapping → XLSX* (download) → correct in Excel → *Compare a workbook* → one request with the new and the different rows → the three approvals |
| Approve what is only proposed | Tick the rows (use *Show all* for a whole filter) → *Make the request* (CONFIRM) → the three approvals; a row without a type or an up/down counter is refused with its number named |
| A request is "stale" | Another request changed one of its rows. The requester withdraws it and asks again; the approvals already given on it are void |
| An approver is absent | Today: the Administrator changes the role of the deputy for the period (recorded in the audit log; the deputy must be a different person from the requester and from the other two roles) and changes it back. This is an interim rule; deputies as a feature are I-70 |
| A lookup label is renamed | The mapping holds the **label** of an access level (D-4 in document 27). Before renaming a label, search the mapping for it; after a rename, run a workbook comparison: rows with the old label are refused with the level named |
| A catalogue code must follow a changed mapping | The mapping does not change codes that already exist. Open a revision of the code (or a change set for many) and re-import the program: the preview shows the difference |

## 9. The first import of a corpus

1. Put the programs into one folder (sub-folders are read).
2. `flask corpus-report <folder> --out corpus.xlsx` — reads every program as the import would, **creates nothing**, and writes the summary, the reasons (numbers and names taken out, so that fifty alike are one line) and one row per program.
3. Read the reasons from the top. A *blocks* line with *is not in the mapping* means rows to request; *has no type* means rows to complete; *header gives legacy number* means a difference between the program and the mapping to settle.
4. Repeat until the blocked count is what you accept; then import in batches by functional group (the change set keeps the batch together).

## 10. Records to keep

**Incident record:** date and time, who found it, what was seen, the database and backups preserved (names, SHA-256), the decision and by whom, the cause, the fix, what was changed in the procedures.

**Restore drill record:** date, host, generation restored (`last_good_file`), time from start to a working tool, result of `verify-backup`, `audit-verify` after the restore, number of codes found, problems.

**Key custody record:** which key, where the copies are, who has them, date of the last check that a copy can be read.

## 11. Contacts

Software Owner and Administrator: Bastian Ritter, bastian.ritter@senvion.in. The StCd Owner, the Chief Engineer and the deputies are named in the project's role table, which is kept with the key custody record.
