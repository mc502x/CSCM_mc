# 27. Product Review, Test Findings and Roadmap — CSCM Tool

> **Status:** proposal for decision · **Version reviewed:** 4.18.0 (2026-10-28) · **Prepared for:** the Software Owner and Administrator, the StCd Owner, the Chief Engineer and the cross-functional steering group
>
> This document answers one request: *run a full test of the application, find the gaps in the testing, review the design, propose the next level, check the documentation, say how the tool can work with Confluence and replace the MasterDB, and describe how the organisation approves and introduces it.* Every number in part 2 was measured on the day; every statement about the code was checked in the code; everything about systems the project cannot see (Confluence, SharePoint, the MasterDB itself) is marked **to confirm**.

## 0. Summary

**Verdict.** The tool is in good technical shape for a pilot: every test passes (1,283 tests, 93 % line coverage, all five quality and security gates green), no page of the live application fails for any of the six roles, the contract holds, and the performance targets are met with room to spare. The review found **no defect that blocks a pilot**. It found **one class of defect that the existing tests could not see** (an identifier or a text outside the expected range gave a server error), which is fixed in v4.18.1 and now has a permanent fuzz test.

**The five findings that matter most**

1. **The tests prove the right inputs work, not that wrong ones are refused.** A property-based fuzz of all 171 API operations (new, part 2.3) found 52 operations that answered with a server error for an identifier wider than the database's integers, and one stored control character that broke the XLSX template for everybody. Fixed centrally; the fuzz is now part of the suite (TC-082). A first version of that fuzz passed *without being signed in* — every answer was 401 — which is why the suite now proves, before fuzzing, that the session works.
2. **There is no test that drives a real browser.** The weakest layers by coverage are the web layer (`ui/`: 85 %, with `release_views`, `auth_views` and `publication_views` at 70 – 75 %) and the command line (`cli.py`, 54 % before the tests of this review); the JavaScript (filters, the new multi-select, theme, subgroup dependency) is checked only by looking at the HTML. A short Playwright/Edge suite is the single best investment in testing (part 3).
3. **The mapping is the new single point of failure of the migration** — in three ways: its approvals cannot be delegated (an absent StCd Owner stops all new numbers), it refers to access levels by their *label* (renaming a label in Lookup administration silently orphans mapping rows), and a change of the mapping does not reach the codes that were already imported (part 4).
4. **The real corpus has never been run.** The 1,200 generated programs have not been imported; the tool has been proved on six fixtures. A *corpus regression run* (every file parsed, every program classified, a report of what blocks and why) is the cheapest way to find the remaining 10 % of surprises (part 3, T-01).
5. **The next level is a platform, not more screens.** The catalogue, the workflow and the release engine are the hard part and they work. What turns the tool from "a better MasterDB" into the place the whole organisation goes to is: a **parameter registry** with the same governance, a **generator round trip** (the tool, not a database nobody can open, feeds the controller programs), **publication into Confluence**, and **field intelligence** from the fleet's occurrences (part 5).

**What is asked of the steering group** (details in part 9): approve the pilot on one functional group; name the deputies for the three approval roles; decide whether the Confluence is Data Center (on-premises) or Cloud; release the MasterDB schema and the SharePoint documentation for analysis; decide the works-council and data-protection route.

---

## 1. Scope and method

| What | How |
|---|---|
| Functional tests | The complete suite, three times: in file order with coverage; in shuffled order on a real SQLite file (proves independence of order and of the in-memory database); the performance suite. |
| Exploratory test of the running application | A crawler logged in as each of the six roles and requested all 161 `GET` routes of the live application (dev database with 1,165 mapping rows): looked for server errors, unrendered templates and slow pages. |
| Property-based fuzz | schemathesis (already a dependency, until now unused) generated paths, queries and bodies for **all 171 operations** of `docs/artifacts/openapi.yaml`, valid and invalid, as an Administrator on a throw-away database. |
| Coverage analysis | Line coverage by module from the full run, read against the test strategy (13) and the traceability matrix (20). |
| Design review | Documents 02, 04, 08, 11, 14, 21 and the code of the services, read for risks, limits and missing capabilities. |
| Documentation review | Documents 00 – 26 searched for statements that the code no longer makes true, for open markers and for what a new person would miss; the consistency tests (links, counts, requirement coverage) were run. |
| What was **not** possible | A real turbine controller, the 1,200-file corpus, the MasterDB, Confluence, SharePoint, a second browser engine, a screen reader, a penetration tester. These are listed as gaps, not guessed. |

---

## 2. Test results

### 2.1 The three runs

| Run | What | Result |
|---|---|---|
| 1 | The functional suite in file order, with coverage (before the tests written in this review) | **1,080 passed**, 35 min 25 s; line coverage **91.5 %** (the report of document 24 gives the figure of the final run) |
| 2 | The suite shuffled (seed 11) on a real SQLite file instead of memory | **Stopped after 7 %**: on a file database the suite needs about 2½ hours on this machine, which is the reason it is not a per-change gate. The proof of independence from order is given by the shuffled pipeline of run 4 |
| 3 | The performance suite (NFR-001, NFR-004) | **9 passed**, 68.6 s: search p95 ≈ 140 ms and single read p95 ≈ 11 ms at 20,000 revisions; 50 concurrent users p95 ≈ 180 ms; 64 concurrent identifier allocations p95 ≈ 108 ms |
| 4 | The final pipeline of v4.18.1, **twice: shuffled (seed 11) and in file order** — the whole suite including the new fuzz, hardening and corpus tests, the five quality and security gates, the report and the release documents | Shuffled: 1,282 tests run, 1,279 passed, 0 failed, 3 skipped on purpose (the three operations the fuzz leaves out). File order (the committed report): **1,283 run, 1,280 passed, 0 failed, 3 skipped**; 28 min; black, ruff, mypy, bandit and pip-audit all pass; line coverage **93 %** (13,857 of 14,923 statements). Document 24 holds the full report |

Measured by hand on a copy of the mapping with 1,165 rows: seed 0.7 s; a request for 1,161 rows 0.6 s to make and 0.6 s to apply; the mapping page 0.11 s, *Show all* (569 KB) 0.05 s, the XLSX export 0.24 s.

### 2.2 Crawl of the live application

161 `GET` routes × 6 roles (Engineer, Reviewer, Chief Engineer, StCd Owner, Administrator, Viewer): **no server error and no unrendered template**. One page was slow: the **Translations** page took **about 6 s on an idle machine** (8 s under load). Profiling found the cause: for every request it read the hundred templates 37 times (once per language and check), and the source tree here is on a network drive. **Fixed in v4.18.1:** the scan is kept for a few seconds and the digests for the request; the page now takes 0.5 s (2 s for the first visit after a start); a test counts that a second visit reads no template (I-66).

### 2.3 API fuzz

| | |
|---|---|
| Operations fuzzed | 168 of 171 (login, logout and the full-database export are left out on purpose) |
| First run | 54 to 58 operations failed (two runs): 52 `OverflowError` (an integer path or body value above 2^63 reaches SQLite and gives a 500), 1 `IllegalCharacterError` (a control character stored in a lookup breaks the XLSX import template for every user), 1 flaky replay (stateful), the rest the same overflow |
| Fix | one central handler: an identifier the database cannot hold is *not found* (404); one central check: a write whose text contains a control character is refused with 422 (passwords exempt); the XLSX writers drop characters a worksheet cannot hold; tests TC-081 (13 cases) and TC-082 (the fuzz, 5 examples per operation, deterministic) |
| After the fix | all operations answer without a server error |

**Lesson for the test strategy:** the 1,089 existing tests were written from the requirements, so they test what a person thought of. The fuzz tests what nobody thought of. Both are needed; the second was one `pip install` away from the start.

### 2.4 Findings and what was done

| # | Finding | Severity | Status |
|---|---|---|---|
| F-1 | Identifiers above 2^63 in a path, query or body give 500 (52 operations) | medium (robustness; no data risk) | **fixed** v4.18.1 |
| F-2 | A control character in any stored text can break XLSX/PDF output for everybody | medium | **fixed** (input refused; output cleaned) |
| F-3 | Documents still described the removed `hc_proposal`, `default_category` and per-program category of the `.st` import (09, 10, 23, 06) | low (misleading) | **fixed** |
| F-4 | Seed workbook status handling was described as "always PROPOSED" while the code takes the status from the workbook | low | **fixed** (code unchanged, documents and the audit entry say it) |
| F-5 | `docs/Unbenannt.canvas`, an empty editor file, was part of the repository | trivial | **removed** |
| F-6 | A plain-text list of initial passwords of real accounts lies in `cscm_tool/instance/new_user_passwords.txt` (the folder is excluded from git, but the file is on disk) | **medium (security hygiene)** | **open — needs the owner**: rotate those passwords and delete the file |
| F-7 | The Translations page took about 6 s (a hundred templates scanned 37 times per request on a network drive) | low | **fixed** v4.18.1: 0.5 s |
| F-8 | The development database contains test accounts and a test approval (`test_*`, "for test purposes only") | info | by design; never carry this database into production |

---

## 3. Gaps in the testing

Strengths first: 1,283 tests, 93 % line coverage, every requirement traced, contract tests against the OpenAPI document, a two-process test for the rate limiter, upgrade tests for older schemas, a verified-restore test for backups, an installer test for Linux, WCAG contrast tests, migration, security-header, CSRF, injection and session tests, and the PostgreSQL-readiness ratchet. That is well above the norm for an internal tool. The gaps:

| ID | Gap | Why it matters | Proposal | Effort |
|---|---|---|---|---|
| T-01 | **The real programs have never been run through the import** — six fixtures only | The first real run will show the unknown: unusual set conditions, files with several programs, encodings, numbers not in the mapping | **Tool delivered in v4.18.1:** `flask corpus-report <folder> --out corpus.xlsx` reads every file as the import would, creates nothing, and reports the states and the reasons grouped (TC-083, runbook §9). **Still to do (you):** run it on the 1,200 files and keep the anonymised summary as the regression baseline | S (run) |
| T-02 | **No real-browser (end-to-end) test** | The weakest coverage is the web layer; JavaScript is untested; the multi-select, theme switch, subgroup dependency and the confirm dialogs work only if someone looks | Playwright (or Selenium) with Edge in CI: ten journeys — log in, create a code, review, approve, publish, filter with several values, import preview, mapping request and the three approvals, language switch, dark mode; screenshots compared (the showcase demo database already builds the data) | M |
| T-03 | **No JavaScript unit tests** (`app.js`, `theme.js`) | A refactor of the filter or theme code is blind | A few Jest/Node tests, or move the logic into small modules testable in the browser suite | S |
| T-04 | **Accessibility is tested for contrast and markup, not with a checker or a screen reader** | The tool promises WCAG; the new panels and the mapping pages are unverified by a tool | axe-core inside the browser suite (T-02); one manual pass with NVDA per release | S |
| T-05 | **No dynamic security scan** (DAST) | pip-audit and bandit cover dependencies and code, not the running behaviour | OWASP ZAP baseline against the running test instance in CI; an external penetration test once before the company-wide roll-out | S + external |
| T-06 | **Mutation and state-machine tests missing** (I-59) | 93 % line coverage says lines ran, not that a wrong line would be caught | `mutmut` on the lifecycle, the numbering and the approvals (the most valuable 2,000 lines); a Hypothesis state machine for the lifecycle | M |
| T-07 | **Load is tested for reading, not for a working week.** The performance suite proves search p95 ≈ 140 ms and read p95 ≈ 11 ms at 20,000 revisions and 50 concurrent users at p95 ≈ 180 ms (document 24, §4) — all reads and identifier allocation | The first real peak is *all* engineers importing, editing and reviewing in the same week; writes are serialised by SQLite | A mixed scenario (Locust or k6) against the Waitress server: 20 users editing, reviewing and approving while one imports 1,200 programs and another exports; the single-writer limit measured, with a decision point for PostgreSQL (I-41) | M |
| T-08 | **The Windows installer and the Windows service are tested by dry run only** | Production is most probably a Windows server | A CI job on a Windows runner that runs `install.ps1` against a temporary folder and starts the service | S |
| T-09 | **Upgrade of a *populated* database from each released version** | The migrations are tested on schemas, less on large real data | Keep an anonymised snapshot per release; the CI upgrades every snapshot to head and runs the integrity check | S |
| T-10 | **Concurrency of the approvals** | Two people of one role deciding in the same second is handled in code (unique constraint) but not tested | A two-thread test for `decide`, and for two requests that change one row | S |
| T-11 | **Translations are checked mechanically and by an AI pre-check, not by people** (haircut 4 – 16 % by language) | German, French and the Indian languages will be read by the people who use them | The in-app review workflow exists (FR-164): assign one reader per language before the pilot | S (people) |
| T-12 | **No test of Confluence/webhook consumers** | Webhooks make one attempt (I-46) | A local receiver in the test that fails twice then succeeds; becomes essential with part 6 | S |
| T-14 | **No software bill of materials or licence report** | The security and procurement review (G1) will ask for it; the dependencies are pinned, so it is cheap | CycloneDX file and a licence table in `releases/v<version>/` | S |
| T-13 | **Test data is small** | 6 `.st` files, a handful of codes | A generator of realistic catalogues (the showcase demo is a start) for load and browser tests | S |

Order of value: **T-01, T-02, T-07, T-08, T-05, T-10**, then the rest.

---

## 4. Review of the design

### 4.1 What is right and should be kept

* **A modular monolith with a clean service layer** — presentation → service → repository; the API and the pages call the same services. This is why the mapping, the multi-select and the sign-off move were small changes.
* **Governance as code**: three decision points, segregation of duties, step-up re-authentication, a hash-chained audit log, signed release manifests, bulk work with sample inspection. This is the part a MasterDB can never have and the reason to replace it.
* **The schema file is the contract** (`schema.sql`), migrations are generated from it, a test fails if a fresh and an upgraded database differ.
* **On-premises by rule** with a test that fails when a cloud dependency appears. It is also the constraint that shapes part 6.
* **Honest data**: since v4.16.1 the import assumes nothing, and since v4.17 the facts the programs do not carry live in one governed place.

### 4.2 Caveats and risks

| ID | Caveat | Consequence | Proposal |
|---|---|---|---|
| D-1 | **One writer.** SQLite serialises all writes; imports run in a thread of the web process | Fine for a team; one 1,200-program import blocks other writers for its duration; a restart loses a running import (I-44) | Measure with T-07; move imports to a separate worker process (I-44); plan PostgreSQL only if the measurement says so |
| D-2 | **One server, no standby.** Backups are verified but on the same machine (I-45) | A disk failure costs the day since the last off-host copy | Off-host backup copy, restore drill every quarter, a written recovery time target |
| D-3 | **Approval roles cannot be delegated** (BR-027) | If the StCd Owner is on leave, no new number can be approved; if one person holds two roles, the rule cannot be met at all | Name a **deputy per role** in the roles table; allow a *recorded, dated* deputy only for the mapping, never silently; alert when a request waits longer than N days (the SLA engine exists) |
| D-4 | **Access levels are stored in the mapping as label text** | Renaming a label in Lookup administration orphans the mapping rows without a message; the import then lists the audience as "not an active level" | Store the lookup *code* (stable), or make the rename refuse while mapping rows use the label, or cascade it in one audited step |
| D-5 | **A change of the mapping does not reach existing codes** | The catalogue and the mapping can drift apart for a code that was imported earlier | A **drift report** (mapping vs catalogue per field) and a *propagate* action that opens revisions in a change set (reuses I-63, I-49, FR-180) |
| D-6 | **A request for 961 rows takes three decisions and no sample inspection** (measured on the pilot copy: proposal 0.6 s, the third approval applying all rows 0.6 s) | The bulk sample inspection exists for change requests (FR-180) but not for mapping requests | Require a sample inspection for a mapping request above a threshold (default 25 rows), same engine |
| D-7 | **The German name of a program is not kept anywhere in the catalogue** except in the comment | The glossary check compares the title with a name that is only in the file | Store `source_name` on the imported revision (a field, not a comment) |
| D-8 | **The mapping seed trusts the status written in the workbook** | A workbook with `APPROVED` rows loaded into an empty table has no approvals behind it | Keep the behaviour (it is how the first approved baseline can enter) but require the Administrator to confirm the counts per status in the UI, and audit it (audited since v4.18.1) |
| D-9 | **Every account is created by hand, and nothing follows the company directory.** Windows sign-in exists behind an authenticating gateway (FR-163, SEC-033) and matches the person by e-mail address, but an Administrator must still create each user and give the role; a leaver stays active until somebody remembers | Password lists to hand out (see F-6) when the gateway is not used; no automatic leaver handling; roles drift | Run the pilot behind the gateway (TC-062 proves it with a real Windows identity); add **group-to-role provisioning and deactivation** from directory groups (extends I-47): nobody asks for another password and a leaver loses access the same day |
| D-10 | **No notification outside the tool** | Approvers only learn of work when they open the tool | Optional SMTP is built; switch it on for the three approval roles and the SLA reminders; add a daily digest |
| D-11 | **Translations and PDFs are heavy on the request path** | Slow Translations page; PDF export of large sets | Cache by fingerprint; build PDFs in the worker |
| D-13 | **Dependencies are pinned and audited (pip-audit is green) but nobody refreshes them on a schedule.** On the day of the review 51 of the 111 installed packages (runtime and test tools) had a newer release, among them the migration tool (alembic 1.13 → 1.20), the database layer (SQLAlchemy 2.0 → 2.1), the type checker (mypy 1.11 → 2.4) and the formatter (black 24 → 26) | Security fixes arrive only when the audit fails; a late jump costs more than small steps | A monthly refresh job (branch, upgrade, full pipeline, merge when green); a software bill of materials (CycloneDX) in the release documents for the security review of G1 |
| D-12 | **Everything is one process on one port** | A fault in an export can slow the editors | Waitress with several threads is in place; a second instance for read-only publication is a later step |

---

## 5. The next level

The question to ask is not *which screens are missing* but *what does the organisation lose today that a governed catalogue could prevent*: a controller that shows a code nobody documented; a parameter changed in one place and not in another; a service technician who cannot find the remedy; a release whose documentation was written by hand from a spreadsheet. Seven moves answer that.

| # | Move | What it means | Builds on | Value | Effort |
|---|---|---|---|---|---|
| N-1 | **Parameter registry** (parameter releases) | A second governed catalogue next to the status codes: parameter name, type, unit, range, default, owner, applicable controller versions, revisions, releases — same workflow, same approvals, same audit. The `StCd14000SetDelayGpTi` and `*5s` of the mapping become *references to a governed parameter* instead of text; the import's list of "unknown parameters" disappears. | Revision engine, workflow, release builder | The thing the MasterDB never had; makes a *parameter release* a first-class object | L |
| N-2 | **Generator round trip** | The tool exports exactly what the generator needs (or generates the `.st` programs itself from the catalogue) and a CI step compares a controller build against the released baseline (I-71 *drift report*). Then the catalogue is not a copy of the truth, it is the source of it. | Export profiles, import parser, release manifests | Ends "is the controller what we approved?" | L |
| N-3 | **Publication into Confluence and the document set** | Every release publishes its documentation (release notes, status code tables per group, diff to the previous release, parameter tables) into a Confluence space, idempotently, per language and audience. Part 6. | Webhooks, change feed, exports, manifests | Documentation is never written twice | M |
| N-4 | **MasterDB retirement path** | Reconciliation, parallel run, per-group cut-over, read-only archive; the SharePoint documentation indexed and linked to the codes. Part 7. | Reconciliation (I-05), mapping, import | The reason the project exists | L |
| N-5 | **Field intelligence** | Occurrences from the fleet (file import today, I-28) become a live view: *top codes by frequency without a remedy text*, *codes that co-occur* (a cause graph learned from data and compared with the set conditions the tool already parses), *regression after a release*. | Occurrence import, connections graph, release data | Turns the catalogue from a reference into a service tool; prioritises the writing work | M |
| N-6 | **Assisted authoring, on-premises** | A description/remedy linter (I-55) first; then suggestions for a new code from the nearest existing codes (search index already has typo tolerance), translation memory (I-54), duplicate detection by meaning, with a **local** model only and a human always deciding. | Search, duplicate detection, translations | Faster, more consistent text; fewer rejected reviews | M |
| N-7 | **The technician's lookup** | An offline page and QR codes on cabinets that open the released code in the technician's language with the remedy, the related codes and the parameters (I-74, I-24, I-57). | Offline bundle, audience publication | The visible benefit for service and customers | M |

A note on the *standard* these names appear to come from: the logical nodes of the mapping (`WROT`, `WCNV`, `WGEN`, `WTUR`, `WNAC`, `WTOW`, `WTRF`, `WTRM`, `WYAW`) are named like the logical nodes of the wind turbine communication standard **IEC 61400-25** (**to confirm** with Controls Engineering; `WPPD` is not one of them to my knowledge). If the match is real, recording for each code its node and data object would let SCADA and condition-monitoring systems consume the catalogue without translation — a cheap addition (a field and an export) with a large integration effect (I-81 below).

### 5.1 Functional gaps in the current tool (smaller than the moves, in order of benefit)

| ID | Gap | Proposal |
|---|---|---|
| G-1 | The approver has no inbox beyond the menu count | An *approver page*: what waits for me, how long, from whom, with the rows (mapping and change requests together), e-mail digest |
| G-2 | The mapping list can be filtered but not edited like a table | A grid edit mode that creates *one* request from many cell edits; paste from Excel |
| G-3 | A blocked program in the import preview cannot be fixed from there | "Request this row" opens the new-row form of the mapping filled from the program (number, legacy number, German name) |
| G-4 | Select-all covers only the loaded rows | "Select all N matching" as a server-side selection (filter + count), with the sample-inspection rule of D-6 |
| G-5 | No comments per mapping row or per request row | Field comments exist for change requests (FR-127); reuse them |
| G-6 | No history view of one mapping row | A timeline from the requests that touched it (data exists: `mapping_change_item`) |
| G-7 | Saved searches exist for codes, not for mapping and requests | Same service |
| G-8 | Release comparison is by code, not by *meaning* | A release diff page: added / changed text / changed type / changed access / withdrawn, per group, as a table that goes straight into the release notes |
| G-9 | The catalogue cannot be asked "what was true on date X" | An *as-of* view over revisions and releases (the data is there) |
| G-10 | No bulk "apply the mapping to existing codes" | See D-5 |
| G-11 | Roles are fixed at six | Fine; add *deputies* (D-3) rather than new roles |
| G-12 | Exports are files | An **API read model per audience** that the controller HMI, SCADA and the service tablet can call (tokens exist) |

### 5.2 Usability

| ID | Observation | Proposal |
|---|---|---|
| U-1 | Dense forms with 60 fields (code form) | Group into steps with a progress list; show only what the controller type needs (partly exists) |
| U-2 | Many role-specific screens | A **Home per role** ("My work today") instead of one dashboard |
| U-3 | Error messages come from the service layer in English for long lists | Show a list with row links (the mapping already does for requests) |
| U-4 | The multi-select panels are new | Add "select all / none" and a count in the summary when more than three are chosen |
| U-5 | No guided first use | A five-step first-run tour per role using the demo data; the showcase deck screenshots are the storyboard |
| U-6 | Two screens called *mapping* (catalogue view and the table) | Rename the catalogue view "Legacy numbers in the catalogue" and merge it into the mapping page as a tab |
| U-7 | The browser pane showed that a narrow window stacks all filters | A two-column filter bar from 900 px |

---

## 6. Connecting to Confluence

### 6.1 What would you do with it

| Use | Direction | Content |
|---|---|---|
| **Software release pages** | tool → Confluence | When a catalogue release is published: a *Release* page (version, date, targeted controller software versions, counts, what changed), child pages per functional group with a table of released codes (identifier, title, type, remedy), the diff to the previous release, the manifest hash, links back into the tool |
| **Status code documentation** | tool → Confluence | One page per code *optional* (large), or one table per group *recommended*; each table row is rendered from released data only, in the language and audience of the space |
| **Parameter releases** | tool → Confluence | After N-1: the same for parameters; before N-1: a page *Parameters referenced by released codes* built from the mapping and the import (the parameter names are already known) |
| **Links the other way** | Confluence → tool | A code's page in the tool shows *Documentation* links to Confluence pages (the existing `standard_references` field, extended to a typed link); a Confluence page embeds a live code card through a small macro that calls the read-only API with a token |
| **MasterDB knowledge** | SharePoint → Confluence → tool | Part 7 |
| **Process documentation** | Confluence only | The governance handbook, the user manual and the training material live where people already read; the tool links to them |

### 6.2 Architecture (on-premises, outbound only, opt-in)

```
   CSCM Tool ──(release published, webhook / change feed)──▶  Publisher worker  ──REST──▶  Confluence (Data Center)
        ▲                                                      │  outbox table, retries,        │
        │  read-only API, token (links, cards)                 │  dead-letter view (I-46)       │ space "Controller Releases"
        └──────────────────────────────────────────────────────┴────────────────────────────────┘
```

* **Pattern:** *outbox*. On `RELEASE_PUBLISH` the tool writes rows to an `integration_outbox` table; a worker (a second process of the same code base, so the web process is not blocked — this is also I-44) renders and sends them, retries with back-off, and shows failures in an operations page. The webhooks and the change feed (I-29) are the existing hooks; the outbox is the missing reliability (I-46).
* **Idempotent pages:** a page is found by a *content property* (`cscm.release_id`, `cscm.group`) and updated, never duplicated; a version comment names the release and the manifest hash. Labels (`cscm`, `release-4.19`, `wcnv`) make the pages findable and drive Confluence's *Content by Label*.
* **Machine-readable tables:** each code row is a *Page Properties* block so that Confluence's *Page Properties Report* can aggregate across releases without scripts.
* **Content:** only **Released** data of the audience the space belongs to (`audience` and `Covert` rules of FR-102/D-02 apply; unapproved data is never sent — the export rule FR-175 is reused). One space per audience: *Engineering* (everything released), *Service*, *Customer* (reduced) — the access rights of a space are then the audience's.
* **Authentication:** Confluence **Personal Access Token** of a technical user (Data Center), stored in `.env`, never in the database; the technical user has *create/edit page* in one space only. Every send is audited (`INTEGRATION_SEND`) with page id and hash.
* **Network:** an allow-list of one host in the configuration; nothing else leaves; the integration is **off** unless configured; the no-cloud test keeps failing for any other external URL.
* **Failure mode:** Confluence unavailable → the release is not affected; the outbox waits; the operations page shows it; a manual "re-send" is available.
* **Format:** Confluence *storage format* (XHTML with `ac:` macros) generated from templates under `app/integrations/confluence/templates/`, covered by golden-file tests (the same technique as the PDF tests).

### 6.3 The constraint that decides everything: Cloud or Data Center?

The tool's rule is *no cloud component of any kind* (security document 11, standing check at every architecture review). Therefore:

* **Confluence Data Center (on-premises):** fits. Everything above works as written. **To confirm:** version, base URL, whether PATs are enabled, the space keys, the macros that are allowed (Page Properties is bundled).
* **Atlassian Cloud:** would be the *first deliberate exception* to the rule. It needs a separate, written decision by IT security (as for SEC-005), an OAuth 2.0 app instead of a PAT, a data-protection assessment (customer-facing documentation leaving the company network) and a cap on what is published (released, audience-public data only). The design above works unchanged otherwise. Recommendation: **decide this before any code is written**; it changes the authentication and the legal review, not the architecture.

### 6.4 Steps

| Step | Result | Effort |
|---|---|---|
| 1 | Decision *Cloud or Data Center*; technical user, PAT, test space | S (people) |
| 2 | Outbox + worker + the operations page (reused by other integrations) | M |
| 3 | Release page and the group tables, templates with golden tests, idempotent update | M |
| 4 | Documentation links in the code detail; read-only macro for a live code card | S |
| 5 | Audience spaces, labels, the *Page Properties Report* on a landing page | S |
| 6 | Parameters (after N-1) | M |

A pilot version (steps 1 – 3) is about **three weeks of work** once the decision and the test space exist.

---

## 7. Replacing the MasterDB

**Known:** the MasterDB is the database from which the status-code generator produces the controller programs (the header of every program names its source database); it has **no user interface**; its documentation exists **only in SharePoint**. The Excel exports used for the mapping (*Statuscode 4XM Rise0B*, *HC Status Code Number*) are its visible surface. **To confirm:** the database product and version, who can read it, whether the generator reads it directly, what else reads it (reports, scripts), where its change history is.

### 7.1 Principle: strangler, not big bang

```
  today:        MasterDB ──(generator)──▶ .st programs ──▶ controller
  parallel:     MasterDB ──(read-only extract, nightly)──▶ reconciliation vs CSCM Tool   (differences listed, owners named)
  per group:    CSCM Tool becomes the source for one functional group; MasterDB write access for that group is withdrawn
  end state:    CSCM Tool ──(export / generator round trip, N-2)──▶ .st programs;   MasterDB = read-only archive
```

### 7.2 Work packages

| WP | What | Output |
|---|---|---|
| 1 | **Inventory:** tables, columns, owners, readers (the generator, reports, scripts); a *field parity matrix* — every MasterDB column mapped to a catalogue field, a mapping column, or *dropped with a reason* (the Rise0B columns already give most of it: description, functional group, logical node, type, trigger snapshot, alarm, up/down counter, access levels, repeats) | Parity matrix (a table in the repository, reviewed by the StCd Owner) |
| 2 | **SharePoint documentation:** list it, classify it (design, procedure, data, obsolete), decide per document *migrate to Confluence / link / archive*. Because the tool never talks to a cloud, IT exports the library once to a folder (or SharePoint Server on-premises can be read through its REST API); a script inventories titles, owners, dates and extracts text for search | Inventory workbook; the *Controller Knowledge* space in Confluence for what is kept |
| 3 | **Data extract and reconciliation:** a repeatable extract; the existing reconciliation report (I-05) compares it with the catalogue and the mapping; every difference has an owner and a decision | Reconciliation report, repeated until empty |
| 4 | **Generator interface:** specify what the generator reads; either the tool exports exactly that (CSV/JSON in the generator's format) or the generator is replaced by the tool's own `.st` writer (N-2) | Interface specification and a test that generates a known program byte for byte |
| 5 | **Parallel run:** one functional group (suggestion: **WCNV**, the converter group — about 130 codes, the best-understood) for six weeks: changes are made in the tool only; the extract proves that the generator output is identical | Sign-off by the Chief Engineer |
| 6 | **Cut-over per group** in order of risk; MasterDB write access withdrawn group by group | Cut-over log |
| 7 | **Archive:** MasterDB read-only, full export stored with the documents, retention decided by Quality | Decommission note |

**Exit criteria for each cut-over:** reconciliation empty; generator output identical; the three approval roles staffed with deputies; backups restored once on a second machine; the training given (part 9).

---

## 8. Documentation review

**Method:** every document was read for statements the code no longer makes true; the consistency tests (links, counts, requirement coverage, audit catalogue, translations) were run; open markers were searched.

**Result.** The set is unusually complete for an internal tool: requirements with identifiers and tests, a traceability matrix, a data dictionary, an OpenAPI contract with a conformance test, an audit catalogue that a test keeps complete, a test report generated from the run, a user manual per role and decision documents for every open question. Generated documents (API summary, test report, translations) cannot drift. Weaknesses found and fixed or listed:

| # | Finding | Action |
|---|---|---|
| Doc-1 | After v4.17, five documents still described the removed category and Hub-proposal options of the `.st` import (09, 10, 23, 06, 13) | **corrected** |
| Doc-2 | Operation counts quoted in two older paragraphs (00, 13) | **corrected** |
| Doc-3 | `25-hc-integration-concept.md` still presents *proposal 1 / proposal 2* as open; the decision (Hub range, later systematic move) is now in 03 FR-048s and idea I-75 | add a banner "decided in v4.17" at the top of 25 |
| Doc-4 | Installation, backup and restore are documented well (14, §4a, §6, §7) — but there was no consolidated **runbook**: routine checklists, upgrade *and rollback*, what to do when the audit chain does not verify, key custody, the mapping administration, the first corpus import | **written** as document 28 (I-67); it points to 14 and 11 instead of copying them |
| Doc-5 | No **administrator guide for the mapping** (who staffs the three roles, how to prepare a workbook, what to do when a request goes stale, how to load the seed on an upgrade) | **written** as section 8 of document 28; section 14.2 of the manual remains the user view |
| Doc-6 | No **API client guide** (examples in curl/Python for the tokens, the change feed, the webhooks, the mapping export) | one page with copy-paste examples |
| Doc-7 | No one-page **quick reference per role** | generate from the manual (the PDF builder exists): six cards |
| Doc-8 | No **data protection and records** statement (which personal data: names, e-mails, action log; retention; who may see the audit log; deletion of accounts with history is *erasure in place*) | a short document for the data-protection officer and the works council; the facts are in 11 and 12 |
| Doc-9 | No **glossary of the domain for newcomers** beyond 19 (what a logical node is, what *legacy*, *Hub*, *Main*, *StCd* mean) | extend 19 with the IEC 61400-25 reference and a picture of the numbering |
| Doc-10 | The decision log (D-01 … D-08) stops at v4.7; decisions of v4.9 – v4.18 are in chapters | one table of decisions with date, decider, rationale — it is what an auditor asks for first |
| Doc-11 | Document 22 (software description) quotes counts that a test checks, but not the integration points (OneTool shell, Windows gateway, webhooks) in one picture | add the context diagram of part 6.2 |
| Doc-12 | Long, dense paragraphs in 03 and 06 (one requirement per paragraph of 150+ words) | split by sentence into sub-requirements the next time a requirement changes; no mass rewrite |

---

## 9. Approval and introduction in the organisation

### 9.1 Who has to say yes

| Stakeholder | Interest | What they approve | Needed by |
|---|---|---|---|
| **Sponsor** (head of Controls Engineering) | Money, priority, the MasterDB end date | The mandate, the pilot, the cut-over plan | G0 |
| **StCd Owner** (business owner of the library) | The numbers, the content | The mapping baseline, the roles, the deputies | G0 |
| **Software Owner / Administrator** (technical owner) | Operation, security, upgrades | Architecture, runbook, backup and recovery | G1 |
| **Chief Engineer** | Release quality | The release process and the rule of three approvals | G1 |
| **IT security / information security** | Network, accounts, data | Hosting, accounts (AD), hardening, penetration test, no-cloud exceptions | G1 |
| **IT infrastructure** | Server, backup, certificates | A server, the Confluence integration endpoint | G1 |
| **Quality / compliance** | Change control, records, standards | That the workflow and the audit log are the change-control record; retention | G1 |
| **Service / TCC / Sales / Customer documentation** | Receivers of the released content | The audiences, languages and the form of publication | G2 |
| **Data protection officer and employee representation** | Names and actions are recorded | Purpose, retention, who sees the audit log (employee-representation co-determination typically applies to a system that records user behaviour — **confirm with HR/legal for each country**) | G1 |
| **Software/controls team that owns the generator** | The generator keeps working | The interface (part 7, WP 4) | G2 |

### 9.2 Gates

| Gate | Question | Evidence |
|---|---|---|
| **G0 Mandate** | Do we want this, and who owns it? | This document, the cost estimate, the named owner and deputies |
| **G1 Readiness** | Is it safe and supportable? | Security review, penetration test, backup/restore drill, the runbook, data-protection and employee-representation statement, licence and SBOM list (the dependencies are pinned and pip-audited), a hosting decision |
| **G2 Pilot** | Does it work for real people on real data? | One functional group, 4 – 6 weeks, named users in every role, the corpus run (T-01), the parallel run against the MasterDB, 20 acceptance cases from the user manual, a defect list |
| **G3 Go-live** | Is the pilot result good enough to widen? | Exit criteria of 7.2, KPIs below, training completed, support roster, rollback plan |
| **G4 Cut-over per group** | Is this group's source of truth the tool? | Reconciliation empty, generator output identical, sign-off by the Chief Engineer |
| **G5 Decommission** | Is the MasterDB read-only and archived? | Archive stored, readers migrated, retention decided |

### 9.3 Introducing it to the cross-functional teams

| Audience | Message | Format | Material (exists) |
|---|---|---|---|
| Management | Why: one governed source, traceable approvals, fewer escalations; cost and risk; the end date of the MasterDB | 30 minutes, the management deck | *Design Showcase — Management* (11 slides) |
| Controls engineers (authors) | How you work now: import, mapping, drafts, change sets | 90-minute hands-on in the demo environment | *Design Showcase — Team* (24 slides), the manual, the demo database |
| Reviewers, Chief Engineer, Administrators | The three decisions, the sample inspection, step-up, the mapping approvals | 45 minutes with the test accounts | manual chapters on review and approval, section 14.2 |
| Service, TCC, Sales | What you will receive, in which language and audience; how to give feedback | 30 minutes + a read-only demo | audience publication and the offline lookup |
| Quality / security / data protection | The controls, the evidence | Review pack | documents 11, 12, 20, 24 |
| Everybody | Where to ask | One page, a mailbox, weekly office hour in the first 8 weeks | — |

**Practices that make adoption stick:** a *champion* per team (one hour a week for the first month); an environment for training that cannot hurt (a copy with sandbox codes — the sandbox exists); the first real work is always something people already must do (importing their group, fixing blocked programs); every complaint becomes a visible entry in the improvement list with an owner; a monthly *release of the tool* with a two-line change summary (the release notes engine writes it).

### 9.4 Roles in the organisation (who plays what in the tool)

| Tool role | Typical person | Deputy rule |
|---|---|---|
| StCd Owner | Head of the status-code team | Named deputy; the deputy is *given* the role for a period, recorded |
| Chief Engineer | Chief engineer controls | Named deputy |
| Administrator | Two people minimum (the Software Owner and a second) | The second Administrator is the deputy and the second approver |
| Reviewer / Engineer | Controls, SCADA, safety, power-electronics engineers per domain | Domain tags decide who can sign off a domain |
| Viewer | Service, Sales, TCC, customer documentation | — |

### 9.5 KPIs (the tool already measures most of them)

| KPI | Target for the pilot |
|---|---|
| Time from Draft to Released, median | ≤ 10 working days (SLA engine) |
| Rate of codes with a remedy text | up by 20 points in the pilot group |
| Programs blocked by the mapping in the corpus run, after the first week | ≤ 5 % |
| Reviewers' requests waiting longer than the SLA | < 10 % |
| Active users per role in the pilot | ≥ 80 % of the named users each week |
| MasterDB reads after cut-over of a group | zero for that group |
| Defects found in the controller from catalogue content, after release | zero |

### 9.6 Risks

| Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|
| The three approval roles are not staffed or are absent | medium | work stops | Deputies (D-3); SLA alerts; the approver page (G-1) |
| Key-person dependency on the Software Owner | high | support gap | Runbook, second Administrator, code ownership by two developers, the documentation set |
| Real programs differ from the fixtures | high | pilot delay | Corpus run first (T-01) |
| MasterDB internals unknown | medium | parity gaps | WP 1 before any promise of a date |
| Confluence is Cloud | unknown | legal review | Decide in step 1 (part 6.3) |
| Adoption is slow because of another password, or leavers keep access | medium | low use, audit finding | Windows sign-in through the gateway for the pilot (exists); group provisioning (I-47) afterwards |
| Single-writer database under peak | low | slow imports | T-07, worker process (I-44) |
| Scope creep from "mind-blowing" ideas | high | no delivery | Pilot first; every move of part 5 enters as an idea with a gate |
| Employee-representation or data-protection objection late | medium | delay | Involve at G0, not G3 |

### 9.7 A 90-day plan

| Weeks | Work | Gate |
|---|---|---|
| 1 – 2 | Mandate; name owners and deputies; decide Confluence type; request MasterDB schema and SharePoint export; rotate the passwords of F-6; corpus run on the 1,200 files | G0 |
| 3 – 4 | Browser suite and Windows installer test; penetration test booked; backup restore drill on the target server; AD provider scoped | G1 prep |
| 5 – 6 | Security and data-protection review; second Administrator trained; runbook written; pilot group chosen and data imported | **G1** |
| 7 – 12 | Pilot on one group with real users; parallel run against the MasterDB; weekly defect triage; Confluence outbox and release pages (steps 1 – 3) | **G2** at week 12 |
| 13 + | Decision on go-live; plan the next groups; start N-1 (parameter registry) design | G3 |

---

## 10. Decisions needed from the business

1. Approve the pilot on one functional group (suggestion WCNV).
2. Name the **deputies** of the StCd Owner, the Chief Engineer and the second Administrator, and decide whether a deputy may approve mapping requests (BR-027 says no today).
3. **Confluence: Data Center or Cloud?** And may the tool publish *Released* content there?
4. Release the **MasterDB** schema and access to read it, and name the people who know it.
5. Release the **SharePoint** documentation for inventory (an export is enough).
6. **Sign-in:** the Windows gateway for the pilot (it exists; IT must provide the proxy) and, afterwards, group-to-role provisioning from the directory (extends I-47): priority and owner.
7. **Data protection and employee representation**: who is asked, and when.
8. The **type** of the four unresolved Rotor rows (12515 – 12518) and the TCC level `Covert` of 12 Hub rows (a lookup value to add or a source to correct).
9. A rule for **sample inspection of mapping requests** above how many rows (proposal: 25).
10. Whether the **parameter registry** (N-1) is in scope, and who owns parameters.
11. The retention period of the audit log and of the archived MasterDB.
12. Which of the proposals in the appendix enter the backlog and in which order.

---

## Appendix — proposed backlog entries (continuing `21-improvement-ideas.md`)

| ID | Idea | Priority | Effort | Epic |
|---|---|---|---|---|
| I-66 | Cache the translation inventory (Translations page) — ✅ delivered in v4.18.1: 6 s → 0.5 s | 🟢 LOW | S | EPIC-22 |
| I-67 | Operations runbook — ✅ delivered in v4.18.1 as document 28 (routine, upgrade and rollback, chain failure, keys, accounts, mapping, corpus run); key *rotation* tooling is I-48 | 🔴 HIGH | S | EPIC-25 |
| I-68 | Corpus run: report on a folder of real programs — ✅ tool delivered in v4.18.1 (`flask corpus-report`, TC-083); the run on the real files and the anonymised baseline are open | 🔴 HIGH | S | EPIC-14 |
| I-69 | Browser (end-to-end) test suite with axe-core and screenshots | 🔴 HIGH | M | EPIC-13 |
| I-70 | Deputies for the approval roles; recorded, dated, mapping-aware | 🔴 HIGH | M | EPIC-12 |
| I-71 | Mapping and catalogue drift report; propagate a mapping change to existing codes as a change set | 🟠 MEDIUM | M | EPIC-14 |
| I-72 | Sample inspection for large mapping requests | 🟠 MEDIUM | S | EPIC-04 |
| I-73 | Access levels in the mapping by lookup code, not label | 🟠 MEDIUM | S | EPIC-14 |
| I-74 | Approver page and e-mail digest | 🟠 MEDIUM | M | EPIC-19 |
| I-76 | Integration outbox and worker; Confluence publisher (release pages, group tables) | 🟠 MEDIUM | M | new EPIC-28 |
| I-77 | Documentation links and a live code card for Confluence | 🟢 LOW | S | EPIC-28 |
| I-78 | MasterDB parity matrix, extract and reconciliation loop; SharePoint inventory | 🔴 HIGH | M | new EPIC-29 |
| I-79 | Generator round trip: export in the generator's format, program writer, build drift check | 🟠 MEDIUM | L | EPIC-14 |
| I-80 | Parameter registry and parameter releases | 🟠 MEDIUM | L | new EPIC-30 |
| I-81 | IEC 61400-25 logical node and data object per code, exported (after the match is confirmed) | 🟢 LOW | S | EPIC-18 |
| I-82 | Field intelligence: occurrence views, co-occurrence graph, regression per release | 🟠 MEDIUM | M | EPIC-23 |
| I-83 | Local, human-in-the-loop authoring assistance | 🟢 LOW | M | EPIC-02 |
| I-84 | Load test of 20 users and the imports; Windows installer test; DAST baseline | 🟠 MEDIUM | M | EPIC-13 |
| I-85 | Storing the German program name as a field of the imported revision | 🟢 LOW | S | EPIC-14 |
| I-86 | Grid edit of the mapping; "select all N matching"; row history and comments | 🟠 MEDIUM | M | EPIC-14 |
