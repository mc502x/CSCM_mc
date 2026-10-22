# 23. User Manual — CSCM Tool

**Controller Status Code Management Tool** — for the people who create, review, approve, release and look up wind-turbine controller status codes.
This is a separate artefact from the requirements, the [software description](22-software-description.md) and the [test report](24-test-report.md). It describes the application as delivered on 2026-10-21; where behaviour is not yet available it says so.

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
2. Sign in with your **username (or e-mail) and password**. This tool has its own login; it does not use your OneTool sign-in.
3. After **5 wrong passwords** the account is locked for **15 minutes**. After **30 minutes without activity**, or **12 hours** after signing in, you must sign in again.
4. Passwords need at least 12 characters, must not be a common password, and must differ from your last 5 passwords. Change yours under **Account** (§17).
5. A new account starts as a **Viewer**. Ask an Administrator to give you the role you need.

## 3. Finding your way around
* **Top bar:** your name and role, **Account**, **Log out**.
* **Sidebar** (it shows only what your role may use): *Dashboard*, *Status Codes*, *New Status Code* (Engineer, Administrator), *New Sandbox Code* (Administrator), *Library Import* (Engineer, Administrator); under **Workflow**: *My Change Requests*, *Review Queue*, *Approval Queue*; under **Releases**: *Releases*, *Export Center*; under **Administration**: *Users*, *Lookups*, *Audit Log*.
* **Dashboard:** counters for the work waiting for you, with links.
* On narrow windows the sidebar collapses to save space.

## 4. Who can do what

| | Viewer | Engineer | Reviewer | Chief Engineer | Administrator |
|---|---|---|---|---|---|
| Search and read Approved / Released / Deprecated / Archived codes | ✓ | ✓ | ✓ | ✓ | ✓ |
| See Drafts and codes under review | — | ✓ | ✓ | ✓ | ✓ |
| Create a code, edit own Draft, submit, withdraw | — | ✓ | — | — | ✓ |
| Give a cross-domain sign-off | — | ✓ (own domain) | — | — | — |
| Reviewer sign-off | — | — | ✓ | — | — |
| Administrator sign-off (and confirm audience access) | — | — | — | — | ✓ |
| Chief Engineer approval | — | — | — | ✓ | — |
| Comment on a change request | — | — | ✓ | ✓ | ✓ |
| Assign the Reviewer | — | — | — | — | ✓ |
| Build, publish, delete (unpublished) releases | — | — | — | — | ✓ |
| Archive / reinstate deprecated codes; sandbox codes | — | — | — | — | ✓ |
| Library import | — | ✓ | — | — | ✓ |
| Export released data | ✓ | ✓ | ✓ | ✓ | ✓ |
| Export the unapproved working set | — | ✓ | ✓ | ✓ | ✓ |
| Full-database backup | — | — | — | — | ✓ |
| Users, vocabularies | — | — | — | — | ✓ |
| Audit log | — | — | scoped | scoped | ✓ |

**Nobody decides their own work.** The author of a change request can never give the Reviewer sign-off, the Administrator sign-off or the Chief Engineer approval on it, and the Chief Engineer also cannot be the person who gave either earlier sign-off (§18).

## 5. Looking up status codes (everyone)
1. Choose **Status Codes**.
2. **Search** by identifier (e.g. `StCd-01042`), words in the title, or words in the description.
3. Narrow with **Functional System Group** and **Lifecycle**, then **Filter**.
4. Open a row to see the detail page with three tabs:
   * **Current** — all fields, grouped (classification, status and timing, repeated-error escalation, program references, audience access).
   * **History** — every revision you may see. To compare two, use **Compare Revisions**: pick *From* and *To* and choose **Compare**; changed fields are listed with the old and new value.
   * **Actions** — what you may do with the code (revise, deprecate, …).
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
Open the Draft (from **My Change Requests** → *View* → *View Status Code* → **Edit Draft**) and save as often as you like; nothing else happens until you submit. Another person (the Administrator) may also edit your Draft — check before editing.

### 6.3 Submit for review
1. Open the change request (**My Change Requests** → *View*).
2. If cross-domain sign-offs are missing (§7), submission is refused with a message naming them.
3. Choose **Submit for Review**. The code receives its `StCd-` number and moves to *Review*. The number never changes afterwards, even if the request is rejected and resubmitted.
4. Changed your mind before a decision? Use **Withdraw** (a Draft, a code in Review, or one waiting for approval can be withdrawn by its author).

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
5. You may add a plain **comment** at any time without deciding.

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
3. **Approve** (for a deprecation request the button reads *Approve (Deprecate)*) or **Reject** with a comment.
4. You are not offered the buttons if you authored the request or gave either earlier sign-off.

## 12. Administrator: releases
1. **Releases → New Release**: *Name*, *Version Label*, optional *Description*, optional scope (*Functional System Group*). **Create Release**.
2. **Edit Candidates** (Release Builder): the list shows Approved codes within the scope (never sandbox codes). Tick the ones to include → **Save Candidate Set**. Approved codes you leave out stay Approved for a later Release.
3. **Publish** (confirm the dialog). All included codes become **Released**, receive the effective date, and the Release is frozen. This cannot be undone and a published Release cannot be changed or deleted. Corrections need a new revision and a new Release.
4. A Release not yet published can be removed with **Delete Release**.

## 13. Exporting data
**Export Center** offers, in **CSV, JSON, XLSX and PDF**:

| Export | Who | Content |
|---|---|---|
| **All Released Status Codes** | everyone | the latest Released version of every code (sandbox excluded) |
| **Release Export** | everyone | the contents of one published Release |
| **Working-Set Export** | everyone except Viewers | every current code in any state, including unapproved Drafts. Every row carries *Not for distribution - unapproved data*, and the file name says so too. Never publish it. |
| **Full-Database Backup** | Administrator | complete raw database file. Store it with the same protection as the database itself. |

File names end with the time of generation, e.g. `cscm_released_2026-10-22_11-05.csv`, `cscm_release_v1.0_2026-10-22_11-05.xlsx`, `cscm_working-set_NOT_FOR_DISTRIBUTION_2026-10-22_11-05.csv` (format `YYYY-MM-DD_HH-MM`, UTC).

Files are flat tables: one row per status code, every field a column. Values beginning with `=`, `+`, `-` or `@` get a leading apostrophe so that spreadsheet programs do not treat them as formulas. **Note:** the PDF shortens long cell contents; use CSV or XLSX when you need complete text.

## 14. Importing the legacy library
Engineers and Administrators can load many codes at once, but **import is only a faster way to enter Drafts**. Every imported row still goes through cross-domain sign-off, both reviews and the Chief Engineer's approval.

1. Prepare a **.csv** or **.xlsx** (max 20 MB), first row = column names, one row per status code.
2. Required columns: `functional_system_group` (code, e.g. `WCNV`), `functional_subgroup` (code, e.g. `010xx`), `turbine_platforms` (e.g. `3XM;4XM`), `title`, `description`, `status_category`, `available_group`, `set_delay`, `reset_delay`.
   Optional: `functional_system_group_range_start` (needed when a code such as `WTUR` exists twice), `software_version`, `alarm_flag`, `up_down_counter`, `trigger_snapshot`, `loadless_spinning_permitted`, `number_of_times_repeated`, `repeated_over_the_course`, `status_code_for_repeated_error`, the eight program columns (`yaw_program`, `manual_reset_program`, `auto_reset_program`, `converter_reactive_power_program`, `brake_program`, `umrichterprogramm_gsc`, `umrichterprogramm_msc`, `yaw_bearing_lubrication_program`), the eight audience columns (`development_access`, `sales_access`, `tcc_access`, `service_access`, `turbine_operator_package_access`, `grid_operator_access`, `service_partner_access`, `customer_access`) and `legacy_reference_number`.
3. **Library Import → Upload and Import.**
4. The result page shows how many rows were read, created and rejected. **Download Error Report** lists each rejected row (row 1 is the header) with the reason; fix those rows and upload them again. A rejected row creates nothing. **View Imported Drafts** opens the new Drafts in *My Change Requests*.

## 15. Sandbox (test) codes
Administrators only. **New Sandbox Code** creates a code with a `StCd-T#####` number for training or tests. It is excluded from searches by default, from every export and from every Release. When no longer needed, open it → **Actions** → type the identifier to confirm → **Delete Permanently**. This is the only thing in the tool that can be permanently deleted; the audit log keeps a full copy of what was removed.

## 16. Administration: users, vocabularies, audit log
### 16.1 Users
**Administration → Users.** *Create User* (username, e-mail, full name, role — default Viewer, engineering domains, initial password). For an existing user use *Edit* to change name, role, engineering domains or active state; **Reset Password** forces a new password and signs the person out. The last active Administrator cannot be deactivated or demoted. Give **Engineers** the domain tags they are qualified for (Controls, Electrical, Mechanical, Grid, Safety) — they decide who can give cross-domain sign-offs.

### 16.2 Lookups (vocabularies)
**Administration → Lookups**: choose a vocabulary (turbine platforms, engineering domains, available groups, the eight audience-access lists, functional groups and subgroups).
* Edit a value's **label**, **description** (shown as inline help to everyone) and active state. Values are deactivated, never deleted.
* **Add** a value to a simple vocabulary.
* **Create a Functional Subgroup:** pick the group, a code, a label and a sub-range of numbers. Ranges may not overlap another subgroup of the same group; the tool names the conflict.
* **Create a Functional System Group:** a code, a label and a range inside free capacity (10000–10999, 14000–14999, 15000–15999, 16000–16999). It may not overlap any existing group.

### 16.3 Audit log
**Audit Log** (Administrators see everything; Reviewers and Chief Engineers a scoped part). Filter by entity type and id, **action** (e.g. `REVIEWER_SIGNOFF`, `COMMENT`, `WITHDRAW`), actor id, and date range. Each line shows who did what and when, with before/after values. Entries cannot be edited or removed by anyone.

## 17. Your account
**Account** → *Change Password* (enter the current and the new password). Choose a passphrase of at least 12 characters that you do not use elsewhere.

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
| Anything unexpected | Note the time and what you did; an Administrator can find it in the Audit Log. |

## 20. Glossary
**Audience access** — eight values stating how each audience (Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer) may use a code. **Change request (CR)** — the workflow envelope around one revision. **Cross-domain sign-off** — confirmation by a specialist of fields owned by their domain. **Engineering domain** — Controls, Electrical, Mechanical, Grid, Safety. **Functional System Group / Subgroup** — the classification that also defines the number range, e.g. *WCNV* "Converter & Grid Interface" → subgroup "Converter". **Hub Controller / Main Controller** — the two controller types whose codes are managed. **Identifier** — `StCd-XXXXX`; sandbox codes use `StCd-T#####`. **Legacy reference number** — the number in the old tool. **Release** — a named, versioned, immutable bundle of Approved codes. **Revision** — one version of a code. **Sandbox code** — a test code that never reaches a Release. **Working set** — export of current codes in any state; not for distribution.
