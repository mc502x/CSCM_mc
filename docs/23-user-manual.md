# 23. User Manual — CSCM Tool

**Controller Status Code Management Tool** — for the people who create, review, approve, release and look up wind-turbine controller status codes.
This is a separate artefact from the requirements, the [software description](22-software-description.md) and the [test report](24-test-report.md). It describes the application as delivered on 2026-10-23 (version 4; sections and rows added in v4 are marked *(v4)*); where behaviour is not yet available it says so.

---

## Contents
1. [What the tool is for](#1-what-the-tool-is-for)
2. [Getting started](#2-getting-started)
3. [Finding your way around](#3-finding-your-way-around)
4. [Who can do what](#4-who-can-do-what)
5. [Looking up status codes (everyone)](#5-looking-up-status-codes-everyone)
6. [Engineer: creating and submitting a status code](#6-engineer-creating-and-submitting-a-status-code)
7. [Engineer: cross-domain sign-off](#7-engineer-cross-domain-sign-off)
8. [Changing or retiring an existing code](#8-changing-or-retiring-an-existing-code)
9. [Reviewer: reviewing a change request](#9-reviewer-reviewing-a-change-request)
10. [Administrator: sign-off, assignment and special actions](#10-administrator-sign-off-assignment-and-special-actions)
11. [Chief Engineer: final approval](#11-chief-engineer-final-approval)
12. [Administrator: releases](#12-administrator-releases)
13. [Exporting data](#13-exporting-data)
14. [Importing the legacy library](#14-importing-the-legacy-library)
15. [Sandbox (test) codes](#15-sandbox-test-codes)
16. [Administration: users, vocabularies, audit log](#16-administration-users-vocabularies-audit-log)
17. [Your account](#17-your-account)
18. [Rules the tool enforces — and why](#18-rules-the-tool-enforces--and-why)
19. [Troubleshooting](#19-troubleshooting)
20. [Glossary](#20-glossary)
21. [Working with a stalled queue: notices, delegation, change sets](#21-notices-delegation-and-change-sets-v4)
22. [Evidence, field comments and the review checklist](#22-evidence-field-comments-and-the-review-checklist-v4)
23. [Translations and language](#23-translations-and-language-v4)
24. [Publishing: profiles, audiences, manifests, notes, offline page](#24-publishing-profiles-audiences-manifests-notes-offline-page-v4)
25. [Software versions](#25-software-versions-v4)
26. [Insight: health, metrics, fleet feedback, saved searches](#26-insight-health-metrics-fleet-feedback-saved-searches-v4)
27. [Hub Controller to Main Controller consolidation](#27-hub-controller-to-main-controller-consolidation-v4)
28. [Administrator: settings, integrations and operations](#28-administrator-settings-integrations-and-operations-v4)
29. [Help inside the tool](#29-help-inside-the-tool-v4)

---

## 1. What the tool is for
Every status code of the Main and Hub Controllers (faults, warnings, information) lives in this tool and nowhere else as the master. A code is written here, completed by the right specialists, checked by two independent people, approved by the Chief Engineer, and only then **released**. Manuals, specifications and SCADA lists are produced *from* released data.

A code travels through seven states:

| State | Meaning |
|---|---|
| **Draft** | Being written. No identifier yet. Freely editable by its author. |
| **Review** | Submitted. Has its `StCd-XXXXX` number. Waiting for the Reviewer and the Administrator. |
| **Pending Approval** | Both reviews done. Waiting for the Chief Engineer. |
| **Approved** | Chief Engineer agreed. Waiting to be included in a Release. |
| **Released** | Published in a Release. Locked. This is the version the world sees. |
| **Deprecated** | Obsolete; kept for history. |
| **Archived** | Deprecated long enough; read-only. |

## 2. Getting started
1. Open the address your administrator gave you (an internal web address).
2. Sign in with your **username (or e-mail) and password**. This tool has its own login; it does not use your OneTool sign-in. *(v4.7)* Where your organisation has switched on the **Windows sign-in**, you are signed in with your Windows account: open the address from your company computer, or use *Sign in with your Windows account* on the login page; there is no password to type. The account is found by your e-mail address, so an Administrator must have created your account with it; if the page says that no active account matches, ask an Administrator.
3. After **5 wrong passwords** the account is locked for **15 minutes**. After **30 minutes without activity**, or **12 hours** after signing in, you must sign in again.
4. Passwords need at least 12 characters, must not be a common password, and must differ from your last 5 passwords. Change yours under **Account** (§17).
5. A new account starts as a **Viewer**. Ask an Administrator to give you the role you need.

## 3. Finding your way around
* **Top bar:** your name and role (and, *(v4)*, a chip when you are covering for a colleague), the **Notices** bell with the number of unread notices, the **language** switch (nineteen languages from GB English to GE ქართული, each with its country letters and flag; the list scrolls; Georgian is last), **Account**, **Log out**.
* **Menu on the left** (it shows only what your role may use). A **+ New Status Code** button (Engineer, Administrator) sits on top, then *Dashboard*, then groups you can open and close (the groups you closed stay closed): **Catalogue** (*Status Codes*, *Releases*, *Export Center*, *New Sandbox Code* for an Administrator), **Workflow** (*My Change Requests*, *Review Queue*, *Approval Queue*, *Change Sets*, *Delegation*), **Import and Migration** (*Library Import*, *Import from .st files*, *Legacy mapping*, *Hub Consolidation*, *Withdrawn Codes*), **Insight** (*Catalogue Health*, *Stalled Requests*, *Success Metrics*, *Fleet Feedback*), **Languages** (*Terminology*, *Translations*) and **Administration** (*People*: *Users*; *Configuration*: *Lookups*, *Export Profiles*, *Review Checklist*, *Settings*, *Integrations*; *Operations*: *Operations*, *Audit Log*); **Help** is at the bottom. A number next to a link says how many items wait for you (reviews, approvals, stalled requests, withdrawn codes; at *My Change Requests* your own open requests); a closed group still shows the total.
* **Dashboard:** counters for the work waiting for you, with links.
* On narrow windows (below 768 px) the menu is hidden until you press **Menu** in the top bar; **Esc** closes it.

## 4. Who can do what

|                                                                                         | Viewer        | Engineer       | Reviewer | Chief Engineer | Administrator | StCd Owner |
| --------------------------------------------------------------------------------------- | ------------- | -------------- | -------- | -------------- | ------------- | ---------- |
| Search and read Approved / Released / Deprecated / Archived codes                       | ✓             | ✓              | ✓        | ✓              | ✓             | ✓          |
| See Drafts and codes under review                                                       | —             | ✓              | ✓        | ✓              | ✓             | ✓          |
| Create a code, edit own Draft, submit, withdraw                                         | —             | ✓              | —        | —              | ✓             | —          |
| Give a cross-domain sign-off                                                            | —             | ✓ (own domain) | —        | —              | —             | —          |
| Reviewer sign-off                                                                       | —             | —              | ✓        | —              | —             | —          |
| Administrator sign-off (and confirm audience access)                                    | —             | —              | —        | —              | ✓             | —          |
| Chief Engineer approval                                                                 | —             | —              | —        | ✓              | —             | —          |
| Comment on a change request                                                             | —             | —              | ✓        | ✓              | ✓             | —          |
| Assign the Reviewer                                                                     | —             | —              | —        | —              | ✓             | —          |
| Build, publish, delete (unpublished) releases                                           | —             | —              | —        | —              | ✓             | —          |
| Archive / reinstate deprecated codes; sandbox codes                                     | —             | —              | —        | —              | ✓             | —          |
| Library import                                                                          | —             | ✓              | —        | —              | ✓             | —          |
| Export released data                                                                    | ✓             | ✓              | ✓        | ✓              | ✓             | —          |
| Export the unapproved working set                                                       | —             | ✓              | ✓        | ✓              | ✓             | —          |
| Full-database backup (password required)                                                | —             | —              | —        | —              | ✓             | —          |
| Confirm a decision with your password *(v4)*                                            | —             | —              | ✓        | ✓              | ✓             | —          |
| Name a delegate / act as a delegate *(v4)*                                              | —             | —              | ✓        | ✓              | ✓             | —          |
| Attach evidence to own change request *(v4)*                                            | —             | ✓              | —        | —              | ✓             | —          |
| Comment on a field, confirm the review checklist *(v4)*                                 | —             | —              | ✓        | ✓ (comment)    | ✓             | —          |
| Change sets: create / decide *(v4)*                                                     | —             | ✓ / —          | — / ✓    | ✓ / ✓          | ✓ / ✓         | —          |
| Translate / approve a translation *(v4)*                                                | read approved | ✓ / —          | — / ✓    | —              | ✓ / ✓         | —          |
| Publish with audience, language, profile; release notes; offline page *(v4)*            | read          | read           | read     | read           | ✓             | —          |
| Catalogue health                                                                        | —             | —              | ✓        | ✓              | ✓             | —          |
| Success metrics, fleet feedback                                                         | —             | —              | —        | ✓              | ✓             | —          |
| Settings, profiles, checklist, API tokens, webhooks, backups, audit verification *(v4)* | —             | —              | —        | —              | ✓             | —          |
| Users, vocabularies                                                                     | —             | —              | —        | —              | ✓             | —          |
| Audit log                                                                               | —             | —              | scoped   | scoped         | ✓             | —          |
| Create users; change any role                                                           | —             | —              | —        | —              | ✓             | —          |
| Change a role between Viewer, Engineer and Reviewer                                     | —             | —              | —        | —              | ✓             | ✓          |

**Nobody decides their own work.** The author of a change request can never give the Reviewer sign-off, the Administrator sign-off or the Chief Engineer approval on it, and the Chief Engineer also cannot be the person who gave either earlier sign-off (§18).

## 5. Looking up status codes (everyone)
1. Choose **Status Codes**.
2. **Search** by identifier (e.g. `StCd-01042`), words in the title, or words in the description.
3. Narrow with **Functional System Group**, **Lifecycle** and the other filters, then **Filter**. *(v4)* Search is ranked (a word in the title ranks above one in a long description) and forgives small spelling mistakes ("convertor"); click a column heading to sort; use **Columns** to choose what the table shows; **Save search** keeps the filters and columns under a name, and copying the page address shares exactly this view.
4. Open a row to see the detail page with three tabs:
   * **Current** — all fields, grouped (classification, status and timing, repeated-error escalation, program references, audience access). *(v4.9)* Below them: **Further Program References** (the subsystem programs of the controller of the code), **Operation Parameters** (operating-mode mask as a bit string such as `111011`, task call frequency, flags) and **User-Group Levels** (read and write level per slot, as the generated program holds them).
   * **History** — every revision you may see. To compare two, use **Compare Revisions**: pick *From* and *To* and choose **Compare**; changed fields are listed with the old and new value.
   * **Actions** — what you may do with the code (revise, deprecate, create a platform variant (**Create variant**), …).
   *(v4)* The detail page also shows **Where-used** (other codes that refer to this one), the **family** of platform variants, remedy text, affected component, related codes, standards, the software versions the code applies to, planned dates and a link to its **Translations**.
5. Sandbox test codes are hidden unless filtered for explicitly.

*Viewers:* you see only decided data. If someone is working on a new revision of a released code, you keep seeing the released one until the new one is released.

## 6. Engineer: creating and submitting a status code
### 6.1 Create the Draft
1. **New Status Code**.
2. **Classification** — choose the **Functional System Group**, then the **Functional Subgroup** (the list fills in after the group; the subgroup is **mandatory**). Tick at least one **Turbine Platform** (2XM, 3XM, 4XM). Optionally enter the **Legacy Reference Number** from the old tool; it is for traceability only and is never the new identifier.
3. **Description** — **Title** (up to 120 characters) and **Description** (10–4000 characters); they must not be identical.
4. **Status & Timing** — **Status Category** (Error, Warning, Info), **Available Group**, optional **Software Version**, **Set Delay** and **Reset Delay** written as a number and a unit: `10ms`, `2min`, `1.5s`, `*500ms` (units: ms, s, min, h, d), and the checkboxes *Alarm*, *Up/Down counter*, *Trigger snapshot*, *Loadless spinning permitted*.
5. **Repeated-error escalation** (optional) — times repeated (at least 1), the time window (e.g. `1d`) and the escalation code.
6. **Program references** — the eight numeric program numbers.
7. **Audience Access** — one choice for each of Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer. These are **proposals**: they are marked *Proposed* until the Administrator confirms them at review.
8. Under every dropdown a line explains the option you selected. If it says *No description available yet*, the vocabulary has no text yet — ask Controls Engineering or an Administrator.
9. **Save as Draft**.

If something is wrong the page comes back with the error messages **and everything you typed still in place**. Fix the fields and save again.

The Draft shows **Not yet assigned** as its identifier. That is normal: the number is only given at submission.

### 6.2 Keep working
Open the Draft (from **My Change Requests** → *View* → *View Status Code* → **Edit Draft**) and save as often as you like; nothing else happens until you submit. Another person (the Administrator) may also edit your Draft. *(v4)* If someone saved it after you opened it, your save is **refused** with the message that the Draft changed; nothing is overwritten and your entries stay in the form beside the current values — compare, adjust and save again. After saving you may see **warnings** (a reference to an unknown or retired code, a similar title in the same subgroup): they never block, but check them. New optional fields: *remedy text*, *affected component*, *related codes*, *standard references* and the software-version range.

### 6.3 Submit for review
1. Open the change request (**My Change Requests** → *View*).
2. If cross-domain sign-offs are missing (§7), submission is refused with a message naming them.
3. Choose **Submit for Review**. The code receives its `StCd-` number and moves to *Review*. The number never changes afterwards, even if the request is rejected and resubmitted.
4. Changed your mind before a decision? Use **Withdraw** (a Draft, a code in Review, or one waiting for approval can be withdrawn by its author). To withdraw several at once, tick them in **My Change Requests** and press **Withdraw selected**; each is reported, and one that cannot be withdrawn does not stop the others. **What happens to a withdrawn change request:** it is deleted, its content stays in the audit log, and the code stays hidden. If the code never received its identifier, the number an import reserved for it and its legacy number are free again, so the same program can be imported again. If it was already in review, it has its identifier and keeps it (numbers are never reused); import the program file again and choose **restore** to open a new Draft on the same number, or — if the number is to be given up — an Administrator deletes the empty code under **Administration → Withdrawn Codes** (tick it, enter the password, *Delete selected*; the deletion is final and audited), after which the program or row can be imported as a new code.

### 6.4 If it is rejected
A reviewer, the Administrator or the Chief Engineer rejected it with a comment. The code returns to **Draft**, and **all earlier sign-offs are cleared**. Read the comment on the change request page, edit, and submit again.

## 7. Engineer: cross-domain sign-off
Some fields belong to a specialist domain. The timing, repeated-error and program fields belong to **Controls**. If you are not tagged for that domain, a Controls Engineer must confirm them before you can submit.

**Asking for a sign-off (author).** On the change request page, under *Request a Sign-Off*, choose a named Engineer who holds the domain (or *Any … Engineer*) and press **Request**. The request appears on that person's Dashboard and under **My Change Requests → Sign-Off Requests For You**.

**Giving a sign-off (domain Engineer).** Open the request, check the fields, choose your domain and press **Sign Off This Domain**. You can only sign for a domain you are tagged with.

## 8. Changing or retiring an existing code
* **Revise a Released code:** open it → **Actions** → **Open New Revision**. This creates a new Draft copy; the released version stays valid until the new one is released. Only one open revision per code is allowed. It goes through the same review and approval, keeps the same identifier, and needs a new Release.
* **Deprecate a Released code:** **Actions** → *Deprecation reason* (10–2000 characters, mandatory), optionally the replacement code → **Initiate Deprecation**. It opens a change request that needs the full review and approval before it takes effect.
* **Archive / reinstate:** Administrators only (§10).

## 9. Reviewer: reviewing a change request
1. **Review Queue** lists requests in Review (with who is assigned, and whether the Reviewer / Administrator signed already).
2. Open one. Check:
   * **Changes** — what differs from the last decided version, or *(new code)*.
   * **Revision Fields**, the **Sign-Off Status** strip, and the **Cross-Domain Sign-Off** strip.
   * **Comments** from others.
3. Decide: **Approve**, or **Reject** with a mandatory comment explaining what to fix.
4. You cannot decide a request you authored, and if an Administrator assigned the request to another Reviewer, only that Reviewer can decide it.
5. You may add a plain **comment** at any time without deciding. *(v4)* You can also comment on **one field** (§22), you must tick every item of the configured **review checklist** before you approve, and **Approve** / **Reject** asks for **your password** (§21). The queue shows how long each request has waited (amber/red).

**Where comments and decisions are kept.** (1) On the change request page, card **Comments** — author (name and role), decision in words, text and time. (2) On the status code page, tab **Decisions & Comments** — the same for *every* change request of that code, oldest first (not visible to Viewers). (3) In the **Audit Log** (filter by *Action*, e.g. `REVIEWER_SIGNOFF` or `COMMENT`, and by actor) — each entry includes the comment text. If a change request is withdrawn its comments disappear from the pages above, but the `WITHDRAW` audit entry keeps a full copy.

## 10. Administrator: sign-off, assignment and special actions
### 10.1 Administrator sign-off
In the review queue, open the request. Alongside the normal checks you confirm the **Audience Access**:

* The eight dropdowns under *Confirm or override Audience Access* show what the Engineer proposed. **Approve** confirms them as shown; change any dropdown first to override. Overrides are recorded in the audit log. If you **Reject**, the dropdowns are ignored.
* The Reviewer sign-off and yours can come in either order; when the second one is recorded the request moves to *Pending Approval* by itself.

### 10.2 Assigning the Reviewer
On the request page choose a Reviewer under *Assigned Reviewer* and **Assign Reviewer** (or *unassigned*). Possible until the Reviewer has signed. The author cannot be assigned.

### 10.3 Submitting with a manual identifier
For a documented migration or reservation case, an Administrator who authored the Draft can open *Override identifier* on the submit panel, enter an unused `StCd-NNNNN` inside the subgroup's number range and a reason, then **Submit for Review**. The tool refuses malformed numbers, numbers outside the subgroup, numbers already in use, and any override without a reason; every override is audited. It is not available once the code already has a number.

### 10.4 Archiving and reinstating
On a Deprecated code → **Actions**: **Archive** (only after the 180-day retention period; refused before) or **Reinstate to Released** (with a reason, exception path).

### 10.5 Comments
Add a comment to any request with *Add a comment*. It changes nothing but is recorded.

## 11. Chief Engineer: final approval
1. **Approval Queue** lists requests in Pending Approval.
2. Open one, review the changes, comments and sign-offs.
3. **Approve** (for a deprecation request the button reads *Approve (Deprecate)*) or **Reject** with a comment; *(v4)* enter your password to confirm. From **Change Sets** you can work through the requests of one software release in one sitting (§21).
4. You are not offered the buttons if you authored the request or gave either earlier sign-off.

## 12. Administrator: releases
1. **Releases → New Release**: *Name*, *Version Label*, optional *Description*, optional scope (*Functional System Group*). **Create Release**.
2. *(v4)* In the Release Builder, **Target software versions** limits the candidate list to codes that apply to the chosen versions (§25). **Edit Candidates**: the list shows Approved codes within the scope (never sandbox codes). Tick the ones to include → **Save Candidate Set**. Approved codes you leave out stay Approved for a later Release.
3. **Publish** (confirm the dialog; *(v4)* you also enter your password, and codes whose planned effective date is still in the future are listed as warnings — they do not block). All included codes become **Released**, receive the effective date, and the Release is frozen. This cannot be undone and a published Release cannot be changed or deleted. Corrections need a new revision and a new Release.
4. A Release not yet published can be removed with **Delete Release**. *(v4)* A published Release has **Release notes**, **exports with a manifest**, an **offline lookup page** and — if webhooks are configured — notifies them (§24).

## 13. Exporting data
**Export Center** offers, in **CSV, JSON, XLSX and PDF**:

| Export | Who | Content |
|---|---|---|
| **All Released Status Codes** | everyone | the latest Released version of every code (sandbox excluded) |
| **Release Export** | everyone | the contents of one published Release |
| **Working-Set Export** | everyone except Viewers | every current code in any state, including unapproved Drafts. Every row carries *Not for distribution - unapproved data*, and the file name says so too. Never publish it. |
| **Full-Database Backup** | Administrator | complete raw database file. Store it with the same protection as the database itself. |

File names end with the time of generation, e.g. `cscm_released_2026-10-22_11-05.csv`, `cscm_release_v1.0_2026-10-22_11-05.xlsx`, `cscm_working-set_NOT_FOR_DISTRIBUTION_2026-10-22_11-05.csv` (format `YYYY-MM-DD_HH-MM`, UTC).

*(v4.7)* The **PDF prints every language**: Hindi, Marathi, Bengali, Punjabi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam, Georgian, Arabic (right to left) and Urdu as well as the Latin-script languages; the fonts come with the tool. Headings are not set in bold, and a character that none of the fonts has shows as `?`.

*(v4)* Exports can be shaped: choose a **profile** (a fixed column set), an **audience** (only codes that audience may see), a **language** (approved translations), a **software version**, and **bundle** (a ZIP with the data file, `MANIFEST.json` and the release notes); see §24. Full-Database Backup asks for your password. Files are flat tables: one row per status code, every field a column. Values beginning with `=`, `+`, `-` or `@` get a leading apostrophe so that spreadsheet programs do not treat them as formulas. *(v4)* The PDF now wraps long text over several lines (nothing is cut), repeats the header on every page and starts with a title page showing release, version, effective date, filters, row count and a content digest.

## 14. Importing the legacy library
Engineers and Administrators can load many codes at once, but **import is only a faster way to enter Drafts**. Every imported row still goes through cross-domain sign-off, both reviews and the Chief Engineer's approval.

1. Prepare a **.csv** or **.xlsx** (max 20 MB), first row = column names, one row per status code.
2. Required columns: `functional_system_group` (code, e.g. `WCNV`), `functional_subgroup` (code, e.g. `010xx`), `turbine_platforms` (e.g. `3XM;4XM`), `title`, `description`, `status_category`, `available_group`, `set_delay`, `reset_delay`.
   Optional: `functional_system_group_range_start` (needed when a code such as `WTUR` exists twice), `software_version`, `alarm_flag`, `up_down_counter`, `trigger_snapshot`, `loadless_spinning_permitted`, `number_of_times_repeated`, `repeated_over_the_course`, `status_code_for_repeated_error`, the eight program columns (`yaw_program`, `manual_reset_program`, `auto_reset_program`, `converter_reactive_power_program`, `brake_program`, `umrichterprogramm_gsc`, `umrichterprogramm_msc`, `yaw_bearing_lubrication_program`), the eight audience columns (`development_access`, `sales_access`, `tcc_access`, `service_access`, `turbine_operator_package_access`, `grid_operator_access`, `service_partner_access`, `customer_access`) and `legacy_reference_number`.
3. *(v4)* use **Start from the template** (XLSX with instructions and lookup codes, or CSV with headers only) if you start from scratch; the untouched template imports cleanly. Choose the **mode**: *create* (default) or *update* (match rows to codes already imported through `legacy_reference_number`: an open Draft is revised in place, a Released code gets a new revision, an unchanged row is skipped, a missing one is created; a request in review, a Draft of another owner or a change of group or subgroup is reported on that row). Press **Validate only** first: every problem is listed per row and column with the value and how to fix it, and **nothing is created**. Then **Upload and Import**.
4. The result page shows how many rows were read, created, warned and rejected; *(v4)* a large file (over 300 rows) runs in the background and the page shows a progress bar — you may leave and come back. Warnings (for example a similar title already in the subgroup) do not block. **Download Error Report** (CSV or XLSX) lists each rejected problem — row, column, value, problem, how to fix — for each rejected row (row 1 is the header) with the reason; fix those rows and upload them again. A rejected row creates nothing. **View Imported Drafts** opens the new Drafts in *My Change Requests*.

*(v4)* **Migration progress:** *Library Import → Migration progress* shows how many legacy rows are imported, in review, approved, released, retired and — when you give the expected total, or upload the legacy master list — which legacy numbers are still missing.

### 14.1 Importing from the generated `.st` programs *(v4.2)*
The generated controller programs (`StCd_1000.st`, `StCd_14000.st`, …) already hold the status codes, so you can import them directly. As with the spreadsheet import, every program only becomes a **Draft**: it still needs cross-domain sign-off, both reviews and the Chief Engineer's approval.

1. Open **Import from .st files** (sidebar, or the button on *Library Import*). Choose the files — several at once, a whole folder, or one ZIP. Leave *Controller* on *Detect* (a file number from 10000 up is a Hub Controller program) unless a Hub file has a smaller number. For Hub programs pick the new numbering: *Proposal 1* (five-digit, the default) or *Proposal 2* (inside the Main scheme). Choose the **status category** of the new codes (the files do not carry one) and the turbine platforms, then **Read files and preview**.
2. The **preview** creates nothing. Each program is one row: its new identifier, the legacy number (*n/a* when there is none), the controller, the name with file and line, the group and subgroup its number lies in, and the state — *ready*, *already in the catalogue* or *blocked* with the reason (for example a number no subgroup covers, a Hub number missing from the numbering table, a legacy number already used by another code, or the same number twice in the upload). Warnings never block: a delay that is a parameter and not a time (`0ms` is entered), a `PrgIdx_GUi` that is already used (it is not stored), no `PrgIdx_GUi`. Tick the programs you want (the header box selects all ready ones; the filter box narrows the list) and optionally name the change set.
3. **Create Drafts for the ticked programs.** The tool checks them again (somebody may have imported one meanwhile), creates the Drafts and puts all of them into **one change set**, so the batch can be reviewed and decided together (chapter 21). The result page links to the change set; large batches run in the background with a progress bar. Each Draft **reserves the number of its program**: when you submit it for review it receives exactly that identifier, no other number and no override. Open the Draft to correct the category, the description (generated from the file and the set condition) and the audience access, which the file does not supply.

Everything else the program says — the user-group levels and the remaining subsystem programs — is kept with the Draft as its *import source* and is not lost (`GET /status-codes/<id>/import-source`).

**Legacy mapping.** *Legacy mapping* (sidebar) lists which new status code replaces which legacy number, separately for the Main Controller and the Hub Controller, with the state of the number (*issued*, *reserved* by a Draft, *no number yet*), filters and a CSV or XLSX export. It runs from legacy to new only: the new library has more codes than the old one, so a code without a legacy number is normal (*n/a*) and there is no way back from a new number to a legacy one. Viewers do not see it.

## 15. Sandbox (test) codes
Administrators only. **New Sandbox Code** creates a code with a `StCd-T#####` number for training or tests. It is excluded from searches by default, from every export and from every Release. When no longer needed, open it → **Actions** → type the identifier to confirm → **Delete Permanently**. This is the only thing in the tool that can be permanently deleted; the audit log keeps a full copy of what was removed.

## 16. Administration: users, vocabularies, audit log
### 16.1 Users
**Roles and colours.** Every role is a coloured badge; the colour is the level and red is the highest: **Administrator** (red), **StCd Owner** (purple), **Chief Engineer** (amber), **Reviewer** (blue), **Engineer** (green), **Viewer** (grey). The StCd Owner owns the status code library: reads everything and may move people between Viewer, Engineer and Reviewer under *Administration → Users*, but cannot create users, change any other role, edit data or decide. Everything else about a person needs an Administrator.

**Administration → Users.** Every row has **View** (the user's page with profile and what the account has done), **Edit**, **Deactivate / Activate** and **Delete**. *Deactivate* stops the person signing in at once and loses nothing; *Delete* removes an account for good and works only for an account that was never used — as soon as it has a change request, a review, an audit entry or any other record it can only be deactivated, so everything stays attributable. Deleting asks for your password again. The StCd Owner sees the list and the user pages and can only change the role between Viewer, Engineer and Reviewer.

**Administration → Users.** *Create User* (username, e-mail, full name, role — default Viewer, engineering domains, initial password). *(v4.7)* **The e-mail address cannot be changed afterwards** — it is the person's identity (the Windows sign-in finds the account by it), so enter it carefully; a person with a new address gets a new account and the old one is deactivated. For an existing user use *Edit* to change name, role, engineering domains or active state; **Reset Password** forces a new password and signs the person out. *(v4)* Each user also has a language preference (set by the language switch). **Delete** (on the user's page, with your own password) works for every account: one that was never used is removed; one with history is **erased** — name, address and password go, the person leaves every list and can no longer sign in, and what they did stays in the audit log and in the records as *Deleted user*. The audit log is never changed. Their user name and address can be used again. *Deactivate* keeps the name and is the gentler choice. The last active Administrator cannot be deactivated, demoted or deleted, and nobody deletes their own account. Give **Engineers** the domain tags they are qualified for (Controls, Electrical, Mechanical, Grid, Safety) — they decide who can give cross-domain sign-offs.

### 16.2 Lookups (vocabularies)
**Administration → Lookups**: choose a vocabulary (turbine platforms, engineering domains, available groups, the eight audience-access lists, functional groups and subgroups).
* Edit a value's **label**, **description** (shown as inline help to everyone) and active state. Values are deactivated, never deleted.
* **Add** a value to a simple vocabulary.
* **Create a Functional Subgroup:** pick the group, a code, a label and a sub-range of numbers. Ranges may not overlap another subgroup of the same group; the tool names the conflict.
* **Create a Functional System Group:** a code, a label and a range inside free capacity (10000–10999, 14000–14999, 15000–15999, 16000–16999). It may not overlap any existing group.

### 16.3 Audit log
**Audit Log** (Administrators see everything; Reviewers and Chief Engineers a scoped part). Filter by entity type and id, **action** (e.g. `REVIEWER_SIGNOFF`, `COMMENT`, `WITHDRAW`), actor id, and date range. Each line shows who did what and when, with before/after values. Entries cannot be edited or removed by anyone.

## 17. Your account
**Account** → *Change Password* (enter the current and the new password). *(v4)* The same page shows your language preference (English or Deutsch); the language switch in the top bar changes it at any time, and before you sign in it follows your browser. Choose a passphrase of at least 12 characters that you do not use elsewhere. *(v4.7)* Where the Windows sign-in is the only way in, your password is managed in Windows and the page has no password form; your e-mail address is shown but cannot be changed.

## 18. Rules the tool enforces — and why
| Rule | Why |
|---|---|
| The identifier is allocated once, at submission, and never changes | stable references in manuals and software |
| Subgroup is mandatory | every code belongs to exactly one subgroup |
| Author cannot sign off or approve own request; Chief Engineer also cannot be an earlier signer | independent control |
| Rejection needs a comment and clears all sign-offs | the fix is reviewed again from scratch |
| No editing outside Draft; changes are new revisions | released data is reliable |
| One open revision per code | no conflicting parallel edits |
| Released codes are never deleted | history; only deprecation and archiving |
| Sandbox codes can never be released and are the only deletable records | safe testing |
| Audience-access values are authoritative only after Administrator sign-off | access decisions are a governance act |
| A published Release cannot change | what was published is what was published |
| *(v4)* Sign-offs, approvals, publishing and the full backup ask for your password | each is a deliberate act that an unattended screen cannot perform |
| *(v4)* A delegate acts as themselves and only for decisions | covering for a colleague never widens anyone's rights; the audit shows both names |
| *(v4)* A save based on an outdated Draft is refused | nobody silently overwrites someone else's work |
| *(v4)* An audience export shows only what the audience may see; no confirmed value, or `Covert`, means hidden | the safe default is to disclose nothing |
| *(v4)* Audit entries are chained and never deleted | tampering is detectable; history is complete |

## 19. Troubleshooting
| You see | What it means / what to do |
|---|---|
| "Password must differ from your last 5 passwords." | Choose a passphrase you have not used recently. |
| "Invalid username or password." | Check caps lock; after 5 failures wait 15 minutes or ask an Administrator to reset the password. |
| Signed out unexpectedly | 30 minutes idle or 12 hours since sign-in. Sign in again; unsaved form data is not kept across a sign-out. |
| "Cross-Domain Sign-Off still pending for: CONTROLS" | Ask a Controls-tagged Engineer to sign off (§7). |
| "At least one Turbine Platform is required" | Tick a platform and save the Draft, then submit. |
| Set Delay / Reset Delay rejected | Use a number plus a unit, e.g. `10ms`, `2min`. |
| "Title must not equal Description" | Make the description longer and more specific. |
| "Cannot sign off own change request" | By design; another person must do it. |
| "This change request is assigned to a different Reviewer" | The Administrator assigned someone else; ask them to reassign. |
| Cannot find a code that exists | You may be a Viewer and it is not yet Approved/Released; or it is a sandbox code (filter for it). |
| Import rejects a row | Open the error report: it names the row and the problem (unknown group or subgroup code, bad delay, bad category …). |
| "Archive refused – retention period" | 180 days must pass after deprecation. |
| Page says forbidden (403) | Your role may not do that (§4). |
| Too many login attempts (429) | Wait a few minutes; the limit protects accounts. |
| *(v4)* "This Draft was changed by someone else after you opened it" | Your entries are kept below the form; compare with the current values and save again. |
| *(v4)* "Your password is required" / "The password is wrong" | Sign-offs, approvals, publishing and the full backup need your own password; after 5 wrong ones the account locks (15 minutes). |
| *(v4)* A code is missing from an audience or language export | The audience's confirmed value does not make it visible, or no approved translation exists (strict mode); check the access fields and the translation worklist. |
| *(v4)* "Evidence can only be attached while the request is open" / type not allowed | Attach to an open request; allowed: PDF, PNG, JPG, TXT, LOG, MD, CSV, XLSX, DOCX, up to 10 MB, 20 files. |
| *(v4)* Backup shows "stale" or "last attempt failed" | See §28; ask the operator to check the nightly job. |
| *(v4)* Import says nothing was created after "Validate only" | That is what it does; fix the listed problems and import. |
| Anything unexpected | Note the time and what you did; an Administrator can find it in the Audit Log. |

## 20. Glossary
**Audience access** — eight values stating how each audience (Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer) may use a code. **Change request (CR)** — the workflow envelope around one revision. **Cross-domain sign-off** — confirmation by a specialist of fields owned by their domain. **Engineering domain** — Controls, Electrical, Mechanical, Grid, Safety. **Functional System Group / Subgroup** — the classification that also defines the number range, e.g. *WCNV* "Converter & Grid Interface" → subgroup "Converter". **Hub Controller / Main Controller** — the two controller types whose codes are managed. **Identifier** — `StCd-XXXXX`; sandbox codes use `StCd-T#####`. **Legacy reference number** — the number in the old tool. **Release** — a named, versioned, immutable bundle of Approved codes. **Revision** — one version of a code. **Sandbox code** — a test code that never reaches a Release. **Working set** — export of current codes in any state; not for distribution.

## 21. Notices, delegation and change sets *(v4)*

**Notices.** The bell in the top bar counts your unread **notices**: when a request waiting for *your* decision has stayed longer than the amber or red limit, you get one notice per request and day (and an e-mail if your organisation configured one). Open **Notices** to read them; **Mark all as read** clears them. **Stalled Requests** (Administrators) lists everything past its limit, with *Assign least-loaded Reviewer* and a per-request reassignment; the page also shows each Reviewer's open reviews.

**Entering your password.** Reviewer and Administrator sign-off, Chief Engineer approval, publishing and the full backup have a *Your password* field. It is checked every time — a wrong one cancels the action, is audited and counts toward the account lock.

**Delegation (when you are away).** *Delegation* → *Create delegation*: choose a colleague (not a Viewer, not yourself) and the dates. For those dates the colleague may take the *decision actions* of your role — sign off, approve — **as themselves**: they see the queue, a chip in their top bar says whom they cover, the audit trail names both of you, and the usual rules still apply to them personally (they cannot decide something they wrote or already signed; the two Review sign-offs must come from two different people). They cannot administer users or do anything else an Administrator can. You or an Administrator can **Revoke** it at any time; it ends by itself after the last date, or if you are deactivated. While you are away the automatic Reviewer assignment skips you.

**Change sets.** An Engineer, Chief Engineer or Administrator creates a **change set** (a name, optionally a target software version) and adds the open requests that ship together (author or Administrator adds; *Remove* takes one out). The set page shows each request's state and waiting time. A decision maker can tick several requests and press **Approve selected** / **Reject selected**: each request is still decided on its own — its own checks, comment and audit entry; a request you may not decide (for instance one you wrote) is skipped with the reason and the others go through; the password is asked once. An Administrator **closes** the set when the release is done.

## 22. Evidence, field comments and the review checklist *(v4)*

**Evidence.** On your open change request, **Attach**: test reports, simulations, design notes, a safety assessment (PDF, PNG, JPG, TXT, LOG, MD, CSV, XLSX, DOCX; up to 10 MB each, 20 per request; the file must really be what its extension says). Reviewers and the Chief Engineer download it at decision time; it is always downloaded, never shown in the browser. You can remove it only while the request is a Draft.

**Field comments.** In Review or Pending Approval, a Reviewer, Administrator or Chief Engineer can press **Add field comment** next to a field and say what is wrong with that field. The author sees the open comments next to the field when the request is back in Draft and presses **Mark resolved** (the commenter, the author and Administrators can do so).

**Review checklist.** Administrators maintain *Administration → Review Checklist*: sentences such as "delay values checked against the control logic", for one Functional System Group or for all. When you approve as Reviewer you must tick every item that applies; the wording you confirmed is stored with your sign-off. Rejecting does not need the checklist.

## 23. Translations and language *(v4)*

**Interface language.** The switch in the top bar (English, Deutsch, Français, हिन्दी, العربية, then বাংলা, मराठी, తెలుగు, தமிழ், ગુજરાતી, اردو, ಕನ್ನಡ, ଓଡ଼ିଆ, മലയാളം, ਪੰਜਾਬੀ, Español, Italiano, Dansk and last ქართული — the country letters on the left and the flag on the right; Arabic and Urdu switch the page to right-to-left) is remembered for your account. French, Hindi, Arabic, Spanish, Italian, Danish and Georgian cover only the most visible text (navigation, login, dashboard, status code lists and the role names), the ten languages after Arabic only the top bar, the navigation, the login page and the role names, and all show English for the rest; the translations are unreviewed. German covers navigation, dashboard, login, lists, forms, change-request screens and help; some messages produced deep inside the tool and the administration pages stay English. *(v4.9)* Every text of the interface — also the messages that appear after an action and the reasons for a refusal — exists in all languages. The translations are proposals until a native speaker has checked them (next paragraph); a language nobody has reviewed carries a small **beta** mark in the language menu for Engineers, Reviewers, Chief Engineers, Administrators and the StCd Owner; Viewers and the login page offer only the reviewed languages (a Viewer who was assigned a language to review sees that one). An Administrator can switch both off in *Settings*. *(v4.9.2)* The words around an export — the title page, the column headings of the default PDF, the footer and the banner of the working set — follow the language you choose for the export.

**Translating a code.** English is the source. Once a code is Approved or Released, open **Translations** on its page: for each language you see *MISSING*, *DRAFT* or *APPROVED*. An Engineer or Administrator enters title, description and remedy text and saves a **draft**; a Reviewer or Administrator **other than the translator** presses **Approve translation**. Editing an approved translation sends it back to draft. **Copy from previous revision** takes over the translations of the previous revision as drafts. The translation **worklist** lists the codes that still lack an approved translation in a language. Viewers see approved translations only.

**Checking the interface translations (native speakers, *v4.7*).** The sidebar entry **Translations** appears for people who were assigned a language and for Administrators and StCd Owners. Concept and background: [26-translations.md](26-translations.md).

* *Reviewer.* Open **Translations**, choose your language, **Review**. Each row shows the English, the current translation and where it is used. Mark **OK** if it is right, **CHANGE** and write your version in the *Proposal* box, or **UNCLEAR** and say why in the comment. The seven things to look at are under *What to check*; keep markers such as `%(n)s` exactly as they are. **Mark the rest of this page OK** saves time on a clean page; **Save** or **Save and next page** stores your answers, and you can stop and continue later. **Missing translations** lists the strings that have none yet: write a proposal for those you can. If you prefer a spreadsheet, **Download the sheet (XLSX)**, fill the *Verdict*, *Proposal* and *Comment* columns and **Upload** it. When every translated string has a verdict, **Complete the review**.
* *Administrator or StCd Owner.* Open **Translations**, choose a language, **Decisions and reviewers**. *Assign* the native speaker (an external person gets a Viewer account and sees only this section) or *Remove* them. Under *Proposals waiting for a decision* **Accept** (you may correct the text first), **Reject**, or for an unclear string mark it **Noted**. You cannot decide on your own proposal. An accepted proposal is shown in the application at once, for that language; under *Accepted changes* **Remove** brings the shipped text back.

**Technical nomenclature (*v4.9*).** The sidebar entry **Terminology** holds the words of the controller and of the workflow (Status Code, Hub Controller, Set delay, Draft, the roles …) with their translation in every language, apart from the interface translations. Everybody who is signed in can read it. *Overview:* the coverage per language, the terms with category, meaning and the state of each language, a search and a filter by category; an Administrator, StCd Owner or Chief Engineer adds a term (*Add a term*: a code of lower-case letters, digits and hyphens that never changes, the English text, the category and a meaning for a translator who does not know the product) and edits the English text, the meaning or *never translated* (a changed English text reopens the approved translations). *One language:* an Engineer, Reviewer, Administrator, StCd Owner or Chief Engineer writes a translation and saves it as a **draft**; a second person with the right to approve presses **Approve** (or *Approve all drafts of others* for the whole language) — you cannot approve your own proposal. *Send back* needs a note and turns an approved translation into a draft again. *Check against the interface* lists the interface strings that contain a term whose translation does not appear in the translated string: it is a hint, not a verdict, because languages that inflect words change the ending. *Export all (XLSX)* and *(CSV)* give the vocabulary to a native speaker or a translation office. Being the reviewer of an interface language gives no right here.

## 24. Publishing: profiles, audiences, manifests, notes, offline page *(v4)*

* **Profiles.** *Administration → Export Profiles* defines named column sets — *Service manual*, *SCADA tag list* and *Customer list* are provided — with the header labels, an optional default audience and language. Choose one in the export form.
* **Audience.** The eight audiences are Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer. An audience export contains only the codes whose confirmed value for that audience is *visible*, and none of the other audiences' columns; a code without a value, or with `Covert`, is hidden. Administrators decide visibility per value in *Lookups*. The unapproved working set can never be exported for an audience.
* **Manifest and verification.** Every Release export is recorded with its SHA-256 and has a manifest (release, scope, row count, hashes, generator, time, options; signed if the organisation configured a key). With **bundle** you get a ZIP containing the data file, `MANIFEST.json` and the release notes. **Export Center → Verify a file**: upload a file and optionally its manifest to learn whether it is exactly what the tool produced, whether it is listed in the manifest and whether the signature is valid. The same check works without the tool: `flask verify-export <file> <manifest>`.
* **Release notes.** On a published Release: **Release notes** lists the codes *added*, *changed* (field by field, old and new value) and *deprecated* compared with the previous published Release, as Markdown, CSV or PDF.
* **Offline page.** **Offline lookup (HTML)** (or **Offline lookup + manifest (ZIP)**) produces one HTML file with the Release's codes and a search box, to open at the turbine without a network; it respects audience, language and software version.

## 25. Software versions *(v4)*

A code applies to a range of controller software versions: on the form choose *Applies to software versions* **from** and **to** (either may stay open). An Administrator sets the versions a Release targets (§12). **Software Versions** answers two questions: which Released codes apply to version X, and what was added, removed and changed between versions X and Y.

## 26. Insight: health, metrics, fleet feedback, saved searches *(v4)*

* **Catalogue Health** (Administrator, Reviewer, Chief Engineer): how full every subgroup's number band is (alert when little is left; Main Controller rows are blue, Hub Controller rows light blue, each with an *MC* or *HC* chip), codes missing expected data (remedy text, component, version range, audience access), suspicious combinations (an INFO code with an alarm, a repeat count without an escalation code or the reverse, a planned deprecation date that has passed), gaps in a number band, and planned dates coming up. On *New Status Code* a hint shows how many numbers are left in the chosen subgroup.
* **Success Metrics** (Administrator, Chief Engineer): median days from submission to approval (target ≤ 7), median days for a cross-domain sign-off (≤ 3), the share of Released codes with a complete audit trail (100 %), how long open requests have waited, and codes whose owner is no longer an active user.
* **Fleet Feedback** (Administrator, Chief Engineer): upload a CSV or XLSX with `status_code_identifier` and `occurrences` (anonymised, per period) with a source label and the period dates. The report names Released codes that never occurred (candidates for deprecation) and the most frequent ones, flagging those without remedy text.
* **Saved searches** — see §5.

## 27. Hub Controller to Main Controller consolidation *(v4)*

If the Hub Controller leaves the hardware setup, its codes are defined anew on the Main Controller side. **Hub Consolidation** lists every Hub code with the state of its replacement (*open*, *draft*, *live*, *retired*). On an Approved or Released Hub code, an Engineer or Administrator presses **Create MC draft**, chooses a Main Controller group and subgroup, and a new Draft is created with the same descriptive fields; the Hub number is kept as its legacy reference, and the new number is allocated at submission like for any code. It then goes through the whole cycle. When replacements are Released, an Administrator uses **Deprecate replaced Hub codes** for a Hub group: a deprecation request is opened for each replaced code — each still needs review and approval.

## 28. Administrator: settings, integrations and operations *(v4)*

* **Settings:** the amber and red limits for the review and approval stages (business days; amber must not exceed red), automatic assignment of the least-loaded Reviewer at submission, and the number-band alert level. Every change is audited.
* **Integrations:** **API tokens** (name, scope *catalogue:read* and/or *changes:read*, validity up to 365 days): the secret is shown **once** — copy it; a token can only read, with the visibility of a Viewer, and can be **Revoked**. **Webhooks:** a URL on the internal network that receives a signed notice when a Release is published; the page shows each delivery's outcome; a failing webhook never stops a publish; **Pause** / resume as needed. Machine consumers may also poll the **change feed** (`/api/v1/changes`).
* **Operations:** shows the last **verified backup** (file, size, age, result of the integrity, restore and audit-chain checks) and has a **Verify now** button for the audit log (it also runs weekly by schedule). A red result names the first entry that does not fit. The backup and archive commands and the restore drill are in the deployment document (14).

## 29. Help inside the tool *(v4)*

**Help** (sidebar) shows the quick start for your role and the explanations of states, roles and terms. Hover over a state or role name for its explanation; every change request states **what happens next**.
