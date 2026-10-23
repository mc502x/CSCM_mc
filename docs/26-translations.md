# 26. Translations — Concept, Review Guide and Catalogue

> **v4.7 (2026-10-24).** This file is the one place for everything about the translations of the web application: how they are organised, how a native speaker checks them, how the status code manuals reach every designated language, and — in section 9, generated from the code — every translation the application contains. Scope of what is translated at all: [10-ui-ux-specification.md](10-ui-ux-specification.md) §10a. The requirements are FR-161 and FR-164 ([03-srs.md](03-srs.md) §1.17); the generator is `scripts/gen_translations_doc.py`.

## 1. Purpose and what is in this file

Nineteen languages are offered (English is the source). German is complete; the others cover the most visible text. Nobody who builds the tool can judge whether a Georgian or Odia sentence is right, so the translations have to be **checkable by a native speaker without knowing anything about the software**. The review is therefore done **in the application itself**, in its own section *Translations* (screens S42 to S44): the reviewer sees one row per string with its context and answers in one word, an Administrator or StCd Owner decides on the proposals, and an accepted proposal is shown at once. The review is recorded and tied to the exact version that was reviewed. A spreadsheet is available for reviewers who prefer to work offline.

| Part | Where it lives | Who changes it |
|---|---|---|
| Concept and review guide | sections 1–8 of this file (hand-written) | the maintainer |
| The catalogue of all translations | section 9 of this file (**generated**, do not edit by hand) | `python scripts/gen_translations_doc.py --write` |
| The review (assignments, answers, proposals, decisions) | the application, section *Translations*; tables `language_reviewer`, `translation_review`, `translation_review_item`, `translation_override` | the reviewers and the Administrator or StCd Owner |
| One review sheet per language | XLSX, downloaded in the review screen or generated with the script (section 3.2); the offline way, uploaded again | nobody, it is an output |
| The shipped translations | `app/i18n_de.py`, `app/i18n_extra.py`, `app/i18n_ar.py`, `app/i18n_in.py`, `app/i18n_eu.py` | the maintainer; accepted overrides are moved in here at a release (section 3.4) |

## 2. The four layers of translated text

A translation is not one thing. Four kinds of text are translated in different ways and are checked in different ways.

| Layer | What it is | Source of truth | Languages today | Checked by |
|---|---|---|---|---|
| **A. Interface text** | navigation, buttons, labels, hints, role names | the catalogues (section 9) | 19 (German complete, the others the main strings) | a native speaker, with the sheet of section 3 |
| **B. Status code content** | title, description and remedy text of every status code revision | the database, `revision_translation` (FR-110) | any active language of the language lookup; German seeded | a native speaker who knows the domain, with approval by a second person (BR-018) |
| **C. Manual and export text** | the words around the content of an exported manual: column headings, title page, footers, banners | the exporters (English only today, inventory in section 5) | English only | a native speaker, with the same sheet as layer A once the text is in a catalogue |
| **D. Help and documentation** | the in-application help, the user manual | help texts in the code; `23-user-manual.md` | help in German; manual in English | a native speaker, only after A to C |

What is **never** translated — identifiers, numbers, stored codes such as `DRAFT` or `ERROR`, audit entries, API field names, names of people — is fixed in [10-ui-ux-specification.md](10-ui-ux-specification.md) §10a and applies to all four layers.

## 3. The concept: how a native speaker checks a language

### 3.1 Principles

1. **One row, one decision.** Every string has a stable id (`S` plus six characters, derived from the English text, so it survives re-ordering), the screens that show it, the English source and the current translation. The reviewer answers per row.
2. **Context is part of the row.** The *Screens* column names the pages that use the string, so a one-word button is not translated in a vacuum.
3. **The reviewer needs no tools.** A browser and an account are enough (an external native speaker gets a Viewer account that sees only this section); the same rows are also in this file and in an ordinary spreadsheet for anybody who prefers to read or to work offline.
4. **Answers are three words.** `OK`, `CHANGE` (with a proposal) or `UNCLEAR` (with a comment). Everything else is free text.
5. **A review is tied to a version.** The review stores the fingerprint of the text the reviewer saw; the overview shows when later changes make a review out of date.
6. **Missing is as visible as wrong.** A second view lists every string that still has no translation, so a reviewer can fill gaps in the same sitting.
7. **Nobody decides on their own proposal.** The reviewer proposes, an Administrator or StCd Owner decides, and a decision is final (the same segregation as BR-018 for status code translations).

### 3.2 The reviewer's kit

| Item | How to get it |
|---|---|
| The review screen (S43) | sidebar *Translations* → the language → *Check translations* (rows with a translation) or *Missing translations*; filter by screen, search text or answer; 40 rows per page; *Mark the rest of this page OK* |
| The language's section in this file | section 9, one table per language, grouped by screen |
| The review sheet (XLSX) of one language | *Download the sheet* in the review screen, or `python scripts/gen_translations_doc.py --xlsx ar -o out/` (or `--xlsx all`); tabs **Review** (current translations, verdict list, proposal and comment columns), **Missing** (strings without translation) and **Checklist**; the completed sheet is uploaded in the same screen |
| Right-to-left languages | Arabic and Urdu are shown and set up right to left in the translation and proposal cells, in the screen and in the sheet |
| A look at the real screens | the application in the language to check (language menu, top bar) |

### 3.3 The checklist

The reviewer looks at every row for these seven things (the same list is in *What to check* of the review screen and on the third tab of each sheet).

| Check | The question |
|---|---|
| Meaning | Does the translation say what the English says, no more and no less? |
| Terminology | Are the fixed terms the same everywhere (Status Code, Draft, Release, Reviewer)? Terms that stay in English are in section 4.3. |
| Fit | Is it short enough for a button, a column heading or a menu entry? |
| Register | Is the form of address right for a technical tool: formal, neutral, no slang? |
| Placeholders | Are markers such as `%(n)s` kept exactly, in a sensible place? |
| Script and direction | Right script; digits and identifiers left in Latin; correct right to left? |
| Spelling and punctuation | Spelling, accents, quotation marks, final full stop. |

### 3.4 From assignment to a shown translation

1. An **Administrator or StCd Owner assigns** one or more reviewers to the language (*Translations* → *Decisions and reviewers*). Any active account can be assigned; the assignment is audited (`LANGUAGE_REVIEWER_ASSIGN`, `LANGUAGE_REVIEWER_REMOVE`).
2. The reviewer opens *Translations*, which lists only the languages they are assigned to, and works through the rows: **OK**, **CHANGE** with a proposal, or **UNCLEAR** with a comment. Answers are saved page by page and can be continued any time; a sheet filled in offline is uploaded and read into the same answers.
3. The reviewer **completes the review** when every translated string has a verdict. The completion is recorded with the date and the fingerprint of the version the review was started on (`TRANSLATION_REVIEW_COMPLETE`).  Proposals for missing translations are possible on the way but are not a condition for completing it.
4. An Administrator or StCd Owner who is **not** the proposer opens *Decisions and reviewers* and **accepts** (optionally correcting the text), **rejects** or **notes** each open item (`TRANSLATION_PROPOSAL_DECIDE`). Only a proposed change can be accepted; an UNCLEAR item is noted or dismissed. A decision is final.
5. An accepted change becomes an **override** and is **shown at once** in the application, for that language only, with no release and no restart. An override can be removed again, which brings the shipped text back (`TRANSLATION_OVERRIDE_REMOVE`).
6. At the next release the maintainer moves the overrides into the catalogue file of the language and regenerates this file; the override then equals the shipped text and is removed.
7. The next visit of an assigned reviewer starts a new review; section 3.5 tells the state of the language.

### 3.5 Review states

The overview (S42) shows one state per language.

| State | Meaning | What it should mean for use (recommended, section 8) |
|---|---|---|
| not reviewed | nobody who speaks the language has completed a review of it | the language is marked as a beta in the language menu; not offered to customers |
| in progress | a review is open | as above |
| reviewed | a native speaker completed a review of exactly this version | offered without marking |
| changed since the review | the text was edited (for example by an accepted proposal) after the review | stays offered; a short follow-up review of the changed strings is scheduled |

### 3.6 Who reviews

A native speaker of the language who has used the product or knows its field (controller software, wind turbines). Two people are required where a mistake could mislead an operator: layer B (status code content) always, layer A only for the strings that appear in warnings and confirmations. For the Indian languages one reviewer per language is needed even where languages seem close (Hindi and Marathi share a script, not their wording).

### 3.7 When

Before a language is shown to anybody who relies on it, and then at every release for the strings that changed since the last review. Because the review stores the fingerprint of a whole language, a change is detected for the language, and a follow-up review is a new review of the whole language (section 8, item 5).

## 4. Status code manuals in all designated languages

### 4.1 What "designated" means

The *designated languages* are the active entries of the language lookup (`lookup_language`, Administration → Lookups): today the nineteen languages of section 9. Deactivating a language in the lookup removes it from the translation screens and the export options; it does not delete translations. English is the source of every status code.

### 4.2 What exists today

| Step | Today |
|---|---|
| A translation of title, description and remedy text per language | `revision_translation` with the states MISSING, DRAFT, APPROVED (FR-110); saved only against an Approved or Released revision; approved by a Reviewer or Administrator who is not the translator (BR-018) |
| Carry-over to the next revision | as DRAFT, on request |
| Worklist | the codes still without an approved translation in a language (FR-111) |
| An export in a language | CSV, JSON, XLSX and PDF of a Release or of all Released codes, in the language, using approved translations only; a code without one shows the English text and is marked (`content_language`), or the export is *strict* and refuses (FR-111) |
| Audience, profile, software version | independent of the language (FR-100 … FR-107) |

### 4.3 Terminology shared by the interface and the content

A manual is only trustworthy if the same term is used in the interface, in the status code texts and in the manual. One list per language, kept next to the catalogue and handed to every reviewer, fixes the terms. The first column says what is **never** translated.

| Term | Rule |
|---|---|
| `StCd`, `StCd-01000`, `PrgIdx_GUi`, `2XM` / `3XM` / `4XM`, `MC`, `HC`, group and subgroup codes (`010xx`, `1110x`) | never translated; Latin letters and digits in every language |
| Status Code, Draft, Review, Approved, Released, Deprecated, Archived | one fixed translation per language, used in the interface and in the manual headings; the English code stays in data and exports |
| Main Controller, Hub Controller | the descriptive name is translated per language (German: Hauptsteuerung, Nabensteuerung); the abbreviations `MC` and `HC` stay |
| Alarm, Set delay, Reset delay, Snapshot, Availability group | one fixed translation per language; the first time a manual uses the term the English word may follow in brackets |
| Product and standard names, units (`ms`, `s`, `min`) | never translated |

The list is a table of about thirty terms per language, reviewed together with the interface (open item 3).

### 4.4 What is missing for "every manual in every language"

| Gap | Concept |
|---|---|
| **Coverage is only visible per language, not per release.** | A matrix *codes × languages* for a Release (counts and percentages) on the Release page and in the export manifest, and a readiness rule: a language is **ready** for a Release when every Released code in it has an APPROVED translation. A manual in a language that is not ready is still possible but carries a visible banner and the per-row marker of FR-111. |
| **Anybody with the role Reviewer may approve a translation, whatever the language.** In nineteen languages nobody can judge them all. | Language competence on the user (*can approve Georgian*, …). A translation is approved only by a user with that competence who is not the translator (BR-018 extended). Without competence a user can still translate and see the worklist. |
| **Translating hundreds of codes one by one in a form does not scale.** | The same round trip as for the interface (section 3): export a *content sheet* per language (identifier, English title, description, remedy text, empty target columns, only codes without approved translation), the translator fills it, the import stores every row as a DRAFT translation, approval stays a separate step. Machine suggestions may fill the sheet but are marked and never approved automatically. |
| **One export per language is a manual job.** | *Export all languages*: one request builds one file per ready language and a manifest of the coverage, as a ZIP, with the same SHA-256 manifest as a single export (FR-103). |
| **The words around the content are English** (headings, title page, footers, banner). | Move the text of section 5 into a catalogue (layer C), translate it into all languages with the same sheet as layer A, and let the exporters read it. |
| **The PDF cannot print Hindi, Arabic, Georgian, Bengali and the other scripts.** *Solved in v4.7 (FR-165, I-37).* | A Noto font per script with HarfBuzz shaping (Devanagari for Hindi and Marathi, Bengali, Telugu, Tamil, Gujarati, Kannada, Odia, Malayalam, Gurmukhi for Punjabi, Naskh Arabic, Nastaliq Urdu, Georgian) and right-to-left layout for Arabic and Urdu, bundled with the application (`app/export/fonts/`). The PDF is therefore offered for every language. |
| **Nobody checks the finished manual.** | A *spot-check sample* per language: the first twenty codes of the Release exported in the language, with the interface text and the manual text, handed to the reviewer of that language together with the sheet. |

### 4.5 The check of a manual in one language

1. The Release is published; the coverage matrix shows the language as ready (or the banner says what is missing).
2. The manual is exported in the language (CSV, JSON, XLSX, DOCX and, since v4.7, PDF in every script).
3. The reviewer of the language reads the spot-check sample against the English original: title and description make sense to an operator, the fixed terms of section 4.3 are used, units and identifiers are untouched.
4. The result is noted on the Release (reviewer, date, language); the export manifest carries the language and its coverage.

## 5. Text outside the interface catalogue (layer C)

This is the English text of the exporters today. It is not in a catalogue, so it cannot be translated or reviewed yet; the list is the starting inventory for moving it.

| Where | English text |
|---|---|
| PDF default columns (`app/export/pdf_exporter.py`) | Status code, Group, Subgroup, Title, Description, Category, Alarm, Set delay, Reset delay, Platforms, State |
| Title page lines (`app/services/export_service.py`) | Release, Version, Effective date, Generated (UTC), Generated by, Records, Profile, Audience, Language, Software version; the values *not yet published*, *all*, *default*, *source* |
| Title page heading and footer | Status code catalogue; CSCM Tool |
| Working-set banner | Not for distribution - unapproved data |
| XLSX sheet name | Status Codes |
| Column headings of CSV, JSON and XLSX | the export field names (`status_code_identifier`, `title`, …) — **these stay English by design** (API contract); an export profile may give each column a label, and that label is translatable |

## 6. Roles and responsibilities

| Role | Task |
|---|---|
| Maintainer | keeps the catalogues, regenerates this file, moves accepted overrides into the catalogues at a release |
| Administrator, StCd Owner | assign the reviewers of each language and decide on their proposals (never on their own) |
| Language reviewer (native speaker) | reviews one language in the *Translations* section or on the sheet; for layer B also approves translations (competence, section 4.4) |
| Reviewer / Administrator of the tool | approves status code translations as today (BR-018) until language competence exists |
| StCd Owner | decides which languages are *designated* (active) and when a language leaves beta |

## 7. Quality gates

| Gate | Checked by |
|---|---|
| Every string a template wraps in `_()` has a German entry | `tests/system/test_i18n.py` |
| The catalogues have the same keys, keep their placeholders and translate only strings that exist | `tests/integration/test_roles_and_languages.py` |
| This file is exactly what the generator produces from the code | `tests/system/test_translations_doc.py` |
| The review sheet of every language is complete (all strings, the missing tab, the checklist) | `tests/system/test_translations_doc.py` |
| Access (assigned reviewers only, managers assign and decide), validations (a change needs a proposal, placeholders kept, 1000 characters), completion rule, sheet upload, no self-decision, accepted override shown at once and removable, audit entries | `tests/integration/test_translation_review.py` |

## 8. Decisions and open items

| # | Item | Why | Priority |
|---|---|---|---|
| 1 | Mark languages that are not reviewed as beta in the language menu, behind a setting, and hide them from customers | people must know that the text is unchecked | high |
| 2 | Find the native-speaker reviewers: one per language, 19 in all (18 besides English) | nothing in this concept works without them | high |
| 3 | Write the terminology list of section 4.3 for every language | one vocabulary for interface, content and manual | high |
| 4 | Language competence on the user and the approval rule of section 4.4 | otherwise nobody can responsibly approve Georgian or Odia | high |
| 5 | A follow-up review that lists only the strings that changed since the last completed one (today the review is per language and the state compares fingerprints) | a release must not trigger a full review | medium |
| 6 | Content sheets: export and import of status code translations per language (section 4.4) | hundreds of codes cannot be translated in a form | high |
| 7 | Coverage matrix and readiness rule per Release; banner on a manual that is not ready | a manual must say what it is | high |
| 8 | Move the layer C text of section 5 into a catalogue and translate it | a translated manual is otherwise half English | medium |
| 9 | *Export all languages* as a ZIP with a coverage manifest | one click instead of nineteen | medium |
| 10 | ~~Unicode fonts and shaping in the PDF, right-to-left layout (I-37)~~ **done (v4.7, FR-165)**; open: bold type, a taller line for Nastaliq | the PDF now prints every script | done |
| 11 | Translate the in-application help and, last, the user manual (layer D) | after layers A to C are stable | low |

Items 1 to 11 are not built. What is built is the catalogue file, the generator, the review sheets, the in-application review with assignments, decisions and overrides (FR-164) and the checks of section 7 (FR-161).

## 9. Catalogue (generated)

<!-- translations:start -->

The interface has **772 strings** (every text a template wraps in `_()`, the role names and the help texts). English is the source; the other languages are listed below. A string without a translation is shown in English.

### 9.1 Coverage

| Language | Code | Direction | Translated | Share | Fingerprint |
|---|---|---|---|---|---|
| GB English 🇬🇧 | `en` | ltr | source | — | — |
| DE Deutsch 🇩🇪 (German) | `de` | ltr | 772 | 100 % | `6fcd677930b4` |
| FR Français 🇫🇷 (French) | `fr` | ltr | 102 | 13 % | `760d28968299` |
| IN हिन्दी 🇮🇳 (Hindi) | `hi` | ltr | 102 | 13 % | `00a0b8dcf5ee` |
| SA العربية 🇸🇦 (Arabic) | `ar` | rtl | 102 | 13 % | `612cb7a89a0b` |
| IN বাংলা 🇮🇳 (Bengali) | `bn` | ltr | 59 | 7 % | `0f967d85b744` |
| IN मराठी 🇮🇳 (Marathi) | `mr` | ltr | 59 | 7 % | `c54092982a23` |
| IN తెలుగు 🇮🇳 (Telugu) | `te` | ltr | 59 | 7 % | `16c8381ac6ee` |
| IN தமிழ் 🇮🇳 (Tamil) | `ta` | ltr | 59 | 7 % | `f7a4b418e729` |
| IN ગુજરાતી 🇮🇳 (Gujarati) | `gu` | ltr | 59 | 7 % | `bbc408b180b1` |
| PK اردو 🇵🇰 (Urdu) | `ur` | rtl | 59 | 7 % | `24ffd1a29475` |
| IN ಕನ್ನಡ 🇮🇳 (Kannada) | `kn` | ltr | 59 | 7 % | `4036883b296f` |
| IN ଓଡ଼ିଆ 🇮🇳 (Odia) | `or` | ltr | 59 | 7 % | `ed08c27723a5` |
| IN മലയാളം 🇮🇳 (Malayalam) | `ml` | ltr | 59 | 7 % | `b9c6260dc8c4` |
| IN ਪੰਜਾਬੀ 🇮🇳 (Punjabi) | `pa` | ltr | 59 | 7 % | `6f0886431813` |
| ES Español 🇪🇸 (Spanish) | `es` | ltr | 102 | 13 % | `e0615d690954` |
| IT Italiano 🇮🇹 (Italian) | `it` | ltr | 102 | 13 % | `3f5a6f857fad` |
| DK Dansk 🇩🇰 (Danish) | `da` | ltr | 102 | 13 % | `b19eca0f8590` |
| GE ქართული 🇬🇪 (Georgian) | `ka` | ltr | 102 | 13 % | `1058d64a65c8` |

The fingerprint is a short hash of the language's catalogue as shipped in the code (string ids and translations). Whether a language has been reviewed, by whom and when, and which proposals were accepted since, is kept in the application (Translations in the sidebar), not in this file.

### 9.2 DE Deutsch 🇩🇪 — German

772 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `S79ba5e` | _macros | After | Nachher |
| `S9eb13d` | _macros | amber after | gelb nach |
| `S74f396` | _macros | Before | Vorher |
| `S228d5f` | _macros, stalled, success_metrics | business days | Werktagen |
| `S141763` | _macros | Confirm with your password | Mit Ihrem Passwort bestätigen |
| `S3c3638` | _macros | d | T |
| `Sc326a4` | _macros, detail, form | Field | Feld |
| `S0a0f8a` | _macros | Field differences | Feldunterschiede |
| `Sbc9819` | _macros | Next | Weiter |
| `S27cea7` | _macros | No field differences. | Keine Feldunterschiede. |
| `S464e43` | _macros | on track | im Plan |
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | überfällig |
| `S600584` | _macros | Pages | Seiten |
| `S810099` | _macros | Please check | Bitte prüfen |
| `S50f942` | _macros | Previous | Zurück |
| `S83fd6e` | _macros, stalled | red after | rot nach |
| `S57e8a7` | _macros, success_metrics | slow | langsam |
| `S15198e` | _macros | Waiting since | Wartet seit |
| `Sad60c5` | _role | level | Stufe |
| `Se32707` | account_settings | Account Settings | Kontoeinstellungen |
| `Sd9e420` | account_settings | At least 12 characters. | Mindestens 12 Zeichen. |
| `S49289d` | account_settings | Change Password | Passwort ändern |
| `S19dff4` | account_settings | Current password | Aktuelles Passwort |
| `S0d01e2` | account_settings | E-mail | E-Mail |
| `Sc469c3` | account_settings | fixed: it identifies you, also for the Windows sign-in | fest: sie identifiziert Sie, auch für die Windows-Anmeldung |
| `S9407e9` | account_settings | Interface language | Sprache der Oberfläche |
| `S89b86a` | account_settings, base, detail | Language | Sprache |
| `Sd850ee` | account_settings | New password | Neues Passwort |
| `Saf5a10` | account_settings | Save language | Sprache speichern |
| `S84c290` | account_settings | Username | Benutzername |
| `S23b0c3` | account_settings | You sign in with Windows; your password is managed there. | Sie melden sich mit Windows an; Ihr Passwort wird dort verwaltet. |
| `S4ab291` | account_settings | Your account | Ihr Konto |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | Administrator |
| `Sc452ad` | approval_queue, base | Approval Queue | Genehmigungs-Warteschlange |
| `S5fda23` | approval_queue, detail, mine | Author | Autor |
| `S003e61` | approval_queue | Change requests waiting for approval | Änderungsanträge, die auf Genehmigung warten |
| `Sa26b9b` | approval_queue | Decide | Entscheiden |
| `S1ffae6` | approval_queue | Functional Group | Funktionsgruppe |
| `S06b6ac` | approval_queue, builder, detail | Identifier | Kennung |
| `S8e70d2` | approval_queue | Nothing is awaiting your approval. | Nichts wartet auf Ihre Genehmigung. |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | Prüfer |
| `S768e0c` | approval_queue, builder, detail | Title | Titel |
| `S33d306` | approval_queue, detail, mine | Waiting | Wartezeit |
| `S85dfa3` | base | Account | Konto |
| `Sb8be3d` | base | Administration | Administration |
| `S28dd75` | base | Audit Log | Audit-Protokoll |
| `Sa28e96` | base, catalogue_health | Catalogue Health | Katalog-Gesundheit |
| `S162a45` | base, list | Change Sets | Änderungspakete |
| `S532c86` | base | covering | vertritt |
| `Sd87f47` | base, dashboard | Dashboard | Übersicht |
| `S710ea3` | base, delegations | Delegation | Vertretung |
| `See833c` | base, export_center | Export Center | Export-Center |
| `S6f6f72` | base, export_profiles | Export Profiles | Export-Profile |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | Flotten-Rückmeldung |
| `Sc47ae1` | base, help | Help | Hilfe |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | Hub-Konsolidierung |
| `S8ac724` | base, new | Import from .st files | Aus .st-Dateien importieren |
| `S1ed126` | base | Insight | Auswertungen |
| `Sa7881c` | base, integrations | Integrations | Integrationen |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | Alt-Neu-Zuordnung |
| `S3c1c8a` | base, new, st_new | Library Import | Bibliotheks-Import |
| `S6e78c9` | base | Log out | Abmelden |
| `S3871af` | base | Lookups | Auswahllisten |
| `Sefd197` | base | Main navigation | Hauptnavigation |
| `S617eec` | base, mine | My Change Requests | Meine Änderungsanträge |
| `Sdbb388` | base | New Sandbox Code | Neuer Sandbox-Code |
| `Sd85719` | base, form, list | New Status Code | Neuer Statuscode |
| `Se94865` | base, dashboard, notifications | Notices | Hinweise |
| `Sa1fdaa` | base, operations | Operations | Betrieb |
| `S8fa41d` | base, dashboard, list | Releases | Releases |
| `Sf490d7` | base, review_checklist | Review Checklist | Prüf-Checkliste |
| `S437a0d` | base, review_queue | Review Queue | Prüf-Warteschlange |
| `Sc7f73b` | base, settings | Settings | Einstellungen |
| `Sbe504f` | base | Skip to main content | Zum Hauptinhalt springen |
| `Sa42252` | base, stalled | Stalled Requests | Hängende Anträge |
| `S7f5583` | base, list | Status Codes | Statuscodes |
| `Sa4a761` | base, success_metrics | Success Metrics | Erfolgskennzahlen |
| `S8ad830` | base, detail, overview | Translations | Übersetzungen |
| `S1b9aeb` | base, dashboard | unread | ungelesen |
| `S57f2b1` | base | Users | Benutzer |
| `Sd7a484` | base | Workflow | Ablauf |
| `S5a4692` | base | You are covering for a colleague | Sie vertreten eine Kollegin / einen Kollegen |
| `S8e9c15` | builder | Candidate revisions | Kandidaten-Revisionen |
| `Sdf2aa0` | builder | Functional Group / Subgroup | Funktionsgruppe / Untergruppe |
| `S11c54a` | builder | Include | Aufnehmen |
| `S12b701` | builder | No Approved candidates match this Release's scope. | Keine freigegebenen Kandidaten passen zum Umfang dieses Releases. |
| `S1359d4` | builder | Planned effective | Geplant gültig ab |
| `Sf6fea0` | builder | Planned in the future: | In der Zukunft geplant: |
| `S565640` | builder | Publish | Veröffentlichen |
| `S5659c7` | builder | Publish Release | Release veröffentlichen |
| `Se2bd5e` | builder | Publish this Release? This cannot be undone. | Dieses Release veröffentlichen? Das kann nicht rückgängig gemacht werden. |
| `Sec31cb` | builder | Publishing transitions every included revision from Approved to Released and locks this Release permanently. | Das Veröffentlichen überführt jede enthaltene Revision von Freigegeben nach Veröffentlicht und sperrt dieses Release dauerhaft. |
| `Sb1fe0b` | builder | Release Builder | Release-Assistent |
| `S5997c5` | builder | Save Candidate Set | Kandidatenauswahl speichern |
| `Scc8a3c` | builder | Save targets | Ziele speichern |
| `S85e466` | builder | Select the Approved, non-sandbox revisions to include, then Save. Publishing is immutable — a correction requires a new Release. | Wählen Sie die freigegebenen Revisionen (ohne Sandbox) aus und speichern Sie. Eine Veröffentlichung ist unveränderlich – eine Korrektur erfordert ein neues Release. |
| `Sd64b6e` | builder, detail | Target software versions | Ziel-Software-Versionen |
| `S6ba0fc` | builder | View Release | Release ansehen |
| `S16b287` | builder | You can still publish; this is a warning only. | Sie können trotzdem veröffentlichen; dies ist nur eine Warnung. |
| `S754eae` | catalogue_health | approved or released codes checked | freigegebene oder veröffentlichte Codes geprüft |
| `Scaf0f4` | catalogue_health | Capacity per subgroup | Kapazität je Untergruppe |
| `S25d185` | catalogue_health | Catalogue health | Katalog-Gesundheit |
| `S199993` | catalogue_health, fleet_feedback | Codes | Codes |
| `S5548ae` | catalogue_health | days | Tage |
| `S34730e` | catalogue_health | Deprecations | Außerbetriebnahmen |
| `S19582d` | catalogue_health | Effective dates | Geplante Gültigkeitsdaten |
| `Seb01bf` | catalogue_health | Examples | Beispiele |
| `S4105cf` | catalogue_health | exhausted | erschöpft |
| `S57e8be` | catalogue_health | Finding | Befund |
| `S1150a1` | catalogue_health | Gaps | Lücken |
| `S171a06` | catalogue_health | Group | Gruppe |
| `Sb4aadc` | catalogue_health, legacy_mapping | Hub Controller | Nabensteuerung |
| `S8ae1c3` | catalogue_health | Left | Übrig |
| `S12c0f1` | catalogue_health | left | übrig |
| `Sa7b60b` | catalogue_health | Left % | Übrig % |
| `S36a883` | catalogue_health | low | knapp |
| `S1b123c` | catalogue_health, legacy_mapping, st_new | Main Controller | Hauptsteuerung |
| `S92185d` | catalogue_health | Missing | Fehlt |
| `S57282a` | catalogue_health | Missing expected data | Fehlende erwartete Daten |
| `Sb8e95b` | catalogue_health | None found. | Nichts gefunden. |
| `S9a9707` | catalogue_health, software_versions | None. | Keine. |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | Noch nicht vergeben |
| `S58c916` | catalogue_health | Number-range capacity | Kapazität der Nummernbereiche |
| `S7b4cb2` | catalogue_health | Numbers are never reused, so a gap is lost capacity - listed for information. | Nummern werden nie wiederverwendet, eine Lücke ist also verlorene Kapazität – zur Information aufgeführt. |
| `S7a85f4` | catalogue_health | ok | in Ordnung |
| `S73b158` | catalogue_health | Planned in the next | Geplant in den nächsten |
| `Sfe5310` | catalogue_health | Probable inconsistencies | Wahrscheinliche Unstimmigkeiten |
| `Sa16c5b` | catalogue_health | Range | Bereich |
| `Sbae7d5` | catalogue_health, detail, list | Status | Status |
| `Sfe07e9` | catalogue_health | Subgroup | Untergruppe |
| `S75a804` | catalogue_health | subgroup(s) are running out of numbers: | Untergruppe(n) gehen die Nummern aus: |
| `S5fec4f` | catalogue_health | Unused numbers inside a band | Ungenutzte Nummern innerhalb eines Bereichs |
| `S02c0e4` | catalogue_health | Used | Belegt |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | Warten auf Freigabe durch den Administrator |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | Warten auf Genehmigung durch den Chefingenieur |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | Warten auf fachübergreifende Freigabe |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | Warten auf Freigabe durch den Prüfer |
| `S452d9f` | dashboard | Browse published and in-progress releases | Veröffentlichte und laufende Releases ansehen |
| `Scf72d4` | dashboard | Browse Status Codes | Statuscodes durchsuchen |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | Meine Entwürfe, die auf eine fachliche Freigabe warten |
| `Se0688f` | dashboard | My Open Change Requests | Meine offenen Änderungsanträge |
| `Sf949fb` | dashboard | Number ranges running out | Nummernbereiche gehen zur Neige |
| `S6605c0` | dashboard | Search and filter all governed status codes | Alle verwalteten Statuscodes suchen und filtern |
| `S916385` | dashboard | Stalled requests | Hängende Anträge |
| `S9661c6` | delegations | Active and planned delegations | Aktive und geplante Vertretungen |
| `Se58311` | delegations | Covered by | Vertreten durch |
| `S10b47f` | delegations | Covering colleague | Vertretende Kollegin / vertretender Kollege |
| `Sf90e46` | delegations | Create delegation | Vertretung anlegen |
| `Sc25e7c` | delegations | Delegation and out-of-office cover | Vertretung und Abwesenheitsregelung |
| `S114c56` | delegations | Delegations | Vertretungen |
| `S3f6605` | delegations, software_versions | From | Von |
| `Sea62b4` | delegations | Name a colleague who may take your decisions while you are away. They act as themselves: the audit trail shows both of you, and the segregation-of-duties rules apply to them personally. Only the decision actions are covered - nothing else you can do. | Benennen Sie eine Kollegin oder einen Kollegen, die/der Ihre Entscheidungen während Ihrer Abwesenheit trifft. Sie handeln als sie selbst: Das Audit-Protokoll zeigt Sie beide, und die Funktionstrennung gilt für sie persönlich. Abgedeckt sind nur die Entscheidungen – sonst nichts von dem, was Sie dürfen. |
| `S7d97d2` | delegations | New delegation | Neue Vertretung |
| `S30d2d7` | delegations | No delegations. | Keine Vertretungen. |
| `S0be720` | delegations, integrations | Revoke | Widerrufen |
| `Sc3f104` | delegations | Role | Rolle |
| `Sd5dcf0` | delegations | Until (inclusive) | Bis (einschließlich) |
| `Sa4aefa` | delegations | Valid | Gültig |
| `Sc3cd63` | detail | Actions | Aktionen |
| `S61cc55` | detail, review_checklist | Add | Hinzufügen |
| `S12cc59` | detail | Add a comment (no decision) | Kommentar hinzufügen (ohne Entscheidung) |
| `Sd89450` | detail | Add Comment | Kommentar hinzufügen |
| `Scfa1b6` | detail | Add field comment | Feldkommentar hinzufügen |
| `Sbb965e` | detail | Add one of your change requests | Einen Ihrer Änderungsanträge hinzufügen |
| `S9a693b` | detail | Add to change set | Zum Änderungspaket hinzufügen |
| `S7bbd6d` | detail | Administrator sign-off | Freigabe durch den Administrator |
| `S212856` | detail | advanced, controller firmware programs | erweitert, Firmware-Programme der Steuerung |
| `Sfbde82` | detail | Affected component | Betroffene Komponente |
| `S25f8c5` | detail, form | Alarm | Alarm |
| `Sd87c44` | detail, hub_consolidation | all | alle |
| `S484388` | detail, export_center | all columns | alle Spalten |
| `S432284` | detail | All required sign-offs are in, but this is still a Draft — the Reviewer and Administrator only see it after you choose Submit for Review below. | Alle erforderlichen Freigaben liegen vor, aber der Antrag ist noch ein Entwurf – Prüfer und Administrator sehen ihn erst, wenn Sie unten "Zur Prüfung einreichen" wählen. |
| `Sb99a01` | detail | Applies to software versions | Gilt für Software-Versionen |
| `S7b2c7f` | detail | Approve | Genehmigen |
| `Sde38bf` | detail | Approve selected | Ausgewählte genehmigen |
| `Scf2999` | detail | Approving confirms these values; any change you make here is applied and audited. Rejecting ignores them. | Mit der Genehmigung bestätigen Sie diese Werte; jede Änderung hier wird übernommen und protokolliert. Bei einer Ablehnung werden sie ignoriert. |
| `Sf7f2d5` | detail | Archive (requires 180-day retention elapsed) | Archivieren (erst nach 180 Tagen Aufbewahrung) |
| `S5d71d2` | detail | Assign least-loaded Reviewer | Prüfer mit der geringsten Last zuweisen |
| `Se29915` | detail | Assign Reviewer | Prüfer zuweisen |
| `Sd371ec` | detail, stalled | Assigned Reviewer | Zugewiesener Prüfer |
| `S1afff0` | detail | Attach | Anhängen |
| `Sb5d75a` | detail | Attach test report, simulation, design note or safety assessment | Prüfbericht, Simulation, Konstruktionsnotiz oder Sicherheitsbewertung anhängen |
| `S51d993` | detail, export_center | Audience | Zielgruppe |
| `S134651` | detail, form | Audience Access | Zielgruppen-Zugriff |
| `Sd71897` | detail, form | Available Group | Verfügbarkeitsgruppe |
| `Scfadbd` | detail | By | Von |
| `S9c8393` | detail | Change Request | Änderungsantrag |
| `S4572f4` | detail | Change request | Änderungsantrag |
| `S3295be` | detail | Change requests in this set | Änderungsanträge in diesem Paket |
| `S4d8006` | detail | Change set | Änderungspaket |
| `S8aa57d` | detail | Changes | Änderungen |
| `Sbd95c0` | detail | Checklist confirmed at sign-off | Bei der Freigabe bestätigte Checkliste |
| `S074d62` | detail, role badge | Chief Engineer | Chefingenieur |
| `S03695d` | detail | Chief Engineer decision | Entscheidung des Chefingenieurs |
| `Sf0a89f` | detail | Close change set | Änderungspaket schließen |
| `S7c0c39` | detail | Close this change set? | Dieses Änderungspaket schließen? |
| `Sadac69` | detail, export_profiles, fleet_feedback | Code | Code |
| `S153d7a` | detail | Comment | Kommentar |
| `S611578` | detail | Comment (required for rejection) | Kommentar (bei Ablehnung erforderlich) |
| `Sc38432` | detail | Comment on this field | Kommentar zu diesem Feld |
| `Sfce06e` | detail | Comments | Kommentare |
| `S8d105c` | detail, reconciliation | Compare | Vergleichen |
| `Sc9a03b` | detail | Compare Revisions | Revisionen vergleichen |
| `S1798b3` | detail | Completed | Abgeschlossen |
| `S7671b5` | detail | Confirm or override Audience Access | Zielgruppen-Zugriff bestätigen oder überschreiben |
| `S3998a7` | detail | Copies the descriptive fields into a new Draft in a Main Controller group (a new number is allocated at submit; this code's identifier is kept as the legacy reference). | Kopiert die beschreibenden Felder in einen neuen Entwurf in einer Hauptsteuerungs-Gruppe (die neue Nummer wird beim Einreichen vergeben; die Kennung dieses Codes bleibt als Altreferenz erhalten). |
| `S54b051` | detail | Copy this code for another turbine platform. The copy is a new Draft that links back here and goes through the normal review. | Diesen Code für eine andere Anlagenplattform kopieren. Die Kopie ist ein neuer Entwurf, verweist hierher zurück und durchläuft die normale Prüfung. |
| `Seb54e4` | detail | Create Main Controller draft from this Hub code | Hauptsteuerungs-Entwurf aus diesem Hub-Code anlegen |
| `See8775` | detail | Create MC draft | MC-Entwurf anlegen |
| `S3c58c3` | detail | Create variant | Variante anlegen |
| `S3a9b50` | detail | Create variant for | Variante anlegen für |
| `Saccf40` | detail | Created | Erstellt |
| `Seb6e02` | detail | Created or revised | Angelegt oder überarbeitet |
| `Sab92d0` | detail | Cross-Domain Sign-Off | Fachübergreifende Freigabe |
| `S4fc0e2` | detail, operations | Current | Aktuell |
| `S405ab5` | detail | current | aktuell |
| `Scb307e` | detail | Decide the selected requests in one sitting | Die ausgewählten Anträge in einem Durchgang entscheiden |
| `S319493` | detail | Decided by | Entschieden von |
| `S7f59a1` | detail | Decision | Entscheidung |
| `Sc51568` | detail | Decisions & Comments | Entscheidungen & Kommentare |
| `Sa9ec7c` | detail | Delete Permanently | Endgültig löschen |
| `S7d1c7a` | detail | Delete Release | Release löschen |
| `Sa2f8f5` | detail | Delete this unpublished Release? | Dieses unveröffentlichte Release löschen? |
| `S524e17` | detail | Deprecate | Außer Betrieb nehmen |
| `S3c1c0d` | detail | deprecation | Außerbetriebnahme |
| `S07bca2` | detail | Deprecation / Archival | Außerbetriebnahme / Archivierung |
| `Sdee63d` | detail | Deprecation Reason | Grund der Außerbetriebnahme |
| `S2e1371` | detail | Deprecation reason | Grund der Außerbetriebnahme |
| `S55f8eb` | detail, form, new | Description | Beschreibung |
| `S388de6` | detail, export_profiles, new | Description (optional) | Beschreibung (optional) |
| `S552a2b` | detail | Documented reason | Dokumentierter Grund |
| `S9b1091` | detail | Domain | Fachbereich |
| `S056839` | detail | Download Error Report | Fehlerbericht herunterladen |
| `S23d33e` | detail | Draft | Entwurf |
| `S3c7a50` | detail | Edit Candidates | Kandidaten bearbeiten |
| `S64d64e` | detail, form | Edit Draft | Entwurf bearbeiten |
| `Sda2252` | detail | effective | gültig ab |
| `S120d93` | detail | Effective Date | Gültig ab |
| `Sd24ec2` | detail | Every comment and decision on every change request of this status code, oldest first. Comments of withdrawn requests are kept in the Audit Log (action WITHDRAW). | Jeder Kommentar und jede Entscheidung zu allen Änderungsanträgen dieses Statuscodes, älteste zuerst. Kommentare zurückgezogener Anträge bleiben im Audit-Protokoll (Aktion WITHDRAW). |
| `S873802` | detail | Every item must be confirmed to approve; rejecting needs no confirmation. | Zur Genehmigung muss jeder Punkt bestätigt werden; für eine Ablehnung ist keine Bestätigung nötig. |
| `S2bac4d` | detail | Every request is still decided on its own: it gets its own check that you did not write or already sign it, its own comment and its own audit entry. Requests you may not decide are reported and skipped. | Jeder Antrag wird weiterhin einzeln entschieden: eigene Prüfung, dass Sie ihn nicht verfasst oder schon freigegeben haben, eigener Kommentar, eigener Audit-Eintrag. Anträge, die Sie nicht entscheiden dürfen, werden gemeldet und übersprungen. |
| `Sa49a78` | detail, export_center | everyone | alle |
| `S7ea014` | detail | Evidence | Nachweise |
| `Sf3e4fa` | detail, export_center | Export | Exportieren |
| `S5755f9` | detail | Export CSV | CSV exportieren |
| `Sbc3990` | detail | Export JSON | JSON exportieren |
| `S3dd7d5` | detail | Export PDF | PDF exportieren |
| `S93f3f8` | detail | Export XLSX | XLSX exportieren |
| `S32aa79` | detail | Exports of this Release | Exporte dieses Releases |
| `S09fef5` | detail | Failed | Fehlgeschlagen |
| `Sdd7b7e` | detail | failed validation | mit Prüffehlern |
| `Sd106a6` | detail | Field comments | Feldkommentare |
| `S2c3caf` | detail, export_verify, operations | File | Datei |
| `Se0996a` | detail, form | first | erste |
| `S041a5d` | detail, export_center | Format | Format |
| `S9e3c65` | detail | From revision | Von Revision |
| `S2fa1f7` | detail, form, list | Functional Subgroup | Funktionsuntergruppe |
| `S90ccd6` | detail | History | Verlauf |
| `Sfec8b7` | detail | Hub Controller group | Hub-Controller-Gruppe |
| `S3c883f` | detail | I have reviewed these dependants | Ich habe diese abhängigen Codes geprüft |
| `S4bc96f` | detail | Import Job | Import-Auftrag |
| `S50565a` | detail | Import progress | Import-Fortschritt |
| `S4c518c` | detail | Imported rows are ordinary Drafts — they still require Cross-Domain Sign-Off, dual review, and Chief Engineer approval before Release. | Importierte Zeilen sind gewöhnliche Entwürfe – sie benötigen vor der Freigabe weiterhin die fachübergreifende Freigabe, die doppelte Prüfung und die Genehmigung durch den Chefingenieur. |
| `S35abd8` | detail | Informative only: a future effective date makes the release builder warn; nothing changes state on its own. | Nur zur Information: Ein zukünftiges Gültigkeitsdatum lässt den Release-Assistenten warnen; von selbst ändert sich kein Zustand. |
| `S54c522` | detail | Initiate Deprecation | Außerbetriebnahme einleiten |
| `S92d001` | detail | Item Count | Anzahl Einträge |
| `S7d2a7b` | detail | Justification | Begründung |
| `S1481d0` | detail, form | latest | neueste |
| `S693272` | detail | Legacy Reference Number | Alt-Referenznummer |
| `S43d5c5` | detail, form | Loadless Spinning Permitted | Lastfreies Drehen erlaubt |
| `S193786` | detail | Logical Node | Logischer Knoten |
| `S578b78` | detail | Main Controller group | Hauptsteuerungs-Gruppe |
| `Seb9a6d` | detail | Manage translations | Übersetzungen verwalten |
| `Sc5beef` | detail | manifest | Manifest |
| `Sf9896c` | detail, form | Mark resolved | Als erledigt markieren |
| `Sa7b93d` | detail, new, reconciliation | Mode | Modus |
| `S31a335` | detail | new code | neuer Code |
| `S816c52` | detail, export_verify, list | No | Nein |
| `S362336` | detail | No change requests in this set yet. | Noch keine Änderungsanträge in diesem Paket. |
| `S7e1129` | detail | No comments or decisions yet. | Noch keine Kommentare oder Entscheidungen. |
| `S207b24` | detail | No comments yet. | Noch keine Kommentare. |
| `S7cb594` | detail | No deprecation/archival/deletion actions are available for this record's current state. | Für den aktuellen Zustand dieses Eintrags sind keine Außerbetriebnahme-, Archivierungs- oder Löschaktionen verfügbar. |
| `Sf502f2` | detail | No evidence attached. | Keine Nachweise angehängt. |
| `Sec1732` | detail | No field comments. | Keine Feldkommentare. |
| `S4bddd5` | detail | Nobody can review it until it is submitted. | Niemand kann ihn prüfen, bevor er eingereicht ist. |
| `S2d8f60` | detail | node value | Knotenwert |
| `S71f8e7` | detail, form | none | keine |
| `S4467d4` | detail | Not yet published | Noch nicht veröffentlicht |
| `S23402a` | detail | Not yet submitted. | Noch nicht eingereicht. |
| `Scd7430` | detail, form | Number of Times Repeated | Anzahl der Wiederholungen |
| `Sde04fa` | detail, fleet_feedback, success_metrics | of | von |
| `S19f611` | detail | Offline lookup (HTML) | Offline-Nachschlagen (HTML) |
| `S2ff2ae` | detail | Offline lookup + manifest (ZIP) | Offline-Nachschlagen + Manifest (ZIP) |
| `S12aa03` | detail | only translated codes | nur übersetzte Codes |
| `S5fc7e3` | detail | open | offen |
| `Sf61187` | detail | Open New Revision | Neue Revision eröffnen |
| `S578c53` | detail | Opens a Draft that must go through the full dual-review and Chief Engineer approval cycle before it takes effect. | Eröffnet einen Entwurf, der vor dem Wirksamwerden die volle doppelte Prüfung und die Genehmigung durch den Chefingenieur durchlaufen muss. |
| `S36463a` | detail | other code(s) still refer to this one: | weitere(r) Code(s) verweisen noch auf diesen: |
| `S9734ac` | detail | Other codes that refer to this one. Review them before deprecating it. | Andere Codes, die auf diesen verweisen. Prüfen Sie sie, bevor Sie ihn außer Betrieb nehmen. |
| `S780d35` | detail | Override identifier (migration / reservation only) | Kennung überschreiben (nur Migration / Reservierung) |
| `S89ff31` | detail | Owner | Verantwortlich |
| `S2d20ee` | detail | Package overview | Paketübersicht |
| `S96f608` | detail, review_queue | Pending | Ausstehend |
| `Sc983b6` | detail | Pick a profile (columns and labels), an audience, a language or a software version. Every file comes with a manifest of SHA-256 hashes; "bundle" packs both into one ZIP. | Wählen Sie ein Profil (Spalten und Überschriften), eine Zielgruppe, eine Sprache oder eine Software-Version. Jede Datei hat ein Manifest mit SHA-256-Hashes; "Bündel" packt beides in ein ZIP. |
| `S72383d` | detail | Planned dates | Geplante Daten |
| `Sfb14b0` | detail | Planned deprecation date | Geplantes Außerbetriebnahmedatum |
| `S00e733` | detail | Planned effective date | Geplantes Gültigkeitsdatum |
| `Sfc8d58` | detail | Platform variant | Plattform-Variante |
| `Scd8926` | detail | Platform variants | Plattform-Varianten |
| `S141f0c` | detail | Processing in the background... | Verarbeitung im Hintergrund ... |
| `Sff4fc0` | detail, export_center | Profile | Profil |
| `Sa4ab7b` | detail | Program References | Programmverweise |
| `S70cbd1` | detail | Proposed | Vorgeschlagen |
| `S483bf2` | detail, list | Published | Veröffentlicht |
| `Sf5ca9d` | detail | Recorded exports | Aufgezeichnete Exporte |
| `Sa3f757` | detail | Reinstate to Released | Wieder auf Veröffentlicht setzen |
| `S3238ca` | detail | Reinstatement reason | Grund der Wiederinbetriebnahme |
| `S2b03b5` | detail | Reject | Ablehnen |
| `S27fb5c` | detail | Reject selected | Ausgewählte ablehnen |
| `S045c2c` | detail | Related codes | Verwandte Codes |
| `S33a5a7` | detail | Relation | Beziehung |
| `Se1fcfa` | detail | Release notes (CSV) | Release-Notes (CSV) |
| `Sa26c4a` | detail | Release notes (Markdown) | Release-Notes (Markdown) |
| `S9b44a2` | detail | Release notes (PDF) | Release-Notes (PDF) |
| `S3dfa01` | detail | Release notes and offline lookup | Release-Notes und Offline-Nachschlagen |
| `Sdcddb7` | detail | Release notes list what was added, changed (field by field) and deprecated since the previous Release. The offline page is one self-contained HTML file for use at the turbine without a connection. | Die Release-Notes führen auf, was seit dem vorigen Release hinzugefügt, geändert (Feld für Feld) und außer Betrieb genommen wurde. Die Offline-Seite ist eine eigenständige HTML-Datei für den Einsatz an der Anlage ohne Verbindung. |
| `S0544a3` | detail | Reload this page to see the progress. | Laden Sie die Seite neu, um den Fortschritt zu sehen. |
| `S99e347` | detail | Remedy | Abhilfe |
| `Se96390` | detail, list | Remove | Entfernen |
| `S400ad0` | detail | Remove this file? | Diese Datei entfernen? |
| `S51c87d` | detail, form | Repeated Over the Course | Wiederholt im Zeitraum |
| `S4c1aa6` | detail | Repeated-Error Escalation | Eskalation bei wiederholtem Fehler |
| `S4aed03` | detail | Request | Anfragen |
| `Sf3421a` | detail | Request a Sign-Off | Freigabe anfordern |
| `Sc26bf6` | detail | Requested | Angefragt |
| `S619e87` | detail, form | Reset Delay | Rücksetzverzögerung |
| `S026ab2` | detail | resolved | erledigt |
| `S68c61f` | detail | Rev # | Rev.-Nr. |
| `Se4758b` | detail, review_checklist | Review checklist | Prüf-Checkliste |
| `S7bfca8` | detail | Reviewer sign-off | Freigabe durch den Prüfer |
| `S3beb9a` | detail | Revision | Revision |
| `Sa72973` | detail | Revision Fields | Revisionsfelder |
| `Sfc1d6a` | detail | row(s) imported as Drafts | Zeile(n) als Entwürfe importiert |
| `S52d0b3` | detail, reconciliation | Rows | Zeilen |
| `Sda38c6` | detail | Save planned dates | Geplante Daten speichern |
| `S13c61c` | detail | Scope Filter | Umfangsfilter |
| `S859822` | detail, mine | Select | Auswählen |
| `S81448f` | detail, form | select | auswählen |
| `S535bd8` | detail, form | Select a Functional System Group first | Wählen Sie zuerst eine Funktionssystemgruppe |
| `S3871fb` | detail, form | Set Delay | Setzverzögerung |
| `S79075b` | detail | Shaped export | Angepasster Export |
| `S5e5039` | detail | Sign Off This Domain | Diesen Fachbereich freigeben |
| `Sfdef49` | detail | Sign-Off Status | Freigabestatus |
| `S6e3665` | detail, review_queue | Signed | Freigegeben |
| `Sddfd83` | detail | Signed by | Freigegeben von |
| `Sb71523` | detail | Size | Größe |
| `Sff44d2` | detail | Software Version | Software-Version |
| `S169bf7` | detail, software_versions | Software version | Software-Version |
| `S6da13a` | detail, fleet_feedback | Source | Quelle |
| `Sd3c56b` | detail, export_profiles | source language | Quellsprache |
| `Sb3883f` | detail | Standards | Normen |
| `Sfaa9e7` | detail, reconciliation | Started | Gestartet |
| `Sa72502` | detail, hub_consolidation, legacy_mapping | State | Zustand |
| `Se246b6` | detail, form, list | Status Category | Statuskategorie |
| `S779953` | detail, form | Status Code for Repeated Error | Statuscode bei wiederholtem Fehler |
| `S98a377` | detail | Still a Draft. | Noch ein Entwurf. |
| `S123f6c` | detail | Submit for Review | Zur Prüfung einreichen |
| `S3dca68` | detail | Superseded by Status Code id (optional) | Abgelöst durch Statuscode-ID (optional) |
| `S08e643` | detail, list | Target software version | Ziel-Software-Version |
| `S8fc804` | detail | The author has to submit it for review before the Reviewer or Administrator can see it. | Der Autor muss ihn zur Prüfung einreichen, bevor Prüfer oder Administrator ihn sehen können. |
| `S091814` | detail | This change request has reached a terminal decision state | Dieser Änderungsantrag hat einen abschließenden Entscheidungszustand erreicht |
| `S6d5708` | detail | This is the one truly irreversible action in the system. Type the identifier to confirm. | Dies ist die einzige wirklich unumkehrbare Aktion im System. Geben Sie zur Bestätigung die Kennung ein. |
| `Sb55f1f` | detail | To revision | Bis Revision |
| `Seaf576` | detail, form | Trigger Snapshot | Schnappschuss auslösen |
| `S285ec8` | detail, form | Troubleshooting | Fehlersuche |
| `S3deb74` | detail, mine, review_queue | Type | Typ |
| `Sb5e264` | detail | Type the identifier to confirm | Kennung zur Bestätigung eingeben |
| `S391d68` | detail, stalled | unassigned | nicht zugewiesen |
| `S73ec5d` | detail, form | Up/Down Counter | Auf-/Abwärtszähler |
| `S80c494` | detail | Uploaded | Hochgeladen |
| `S45288a` | detail, new | Version Label | Versionsbezeichnung |
| `S4993ae` | detail | View Change Request | Änderungsantrag ansehen |
| `Scde93f` | detail | View Imported Drafts | Importierte Entwürfe ansehen |
| `Sd869da` | detail | View Status Code | Statuscode ansehen |
| `Sbcbc36` | detail | vs. revision | gegenüber Revision |
| `Sa3a4bd` | detail | Waiting for cross-domain sign-off from: | Wartet auf die fachübergreifende Freigabe von: |
| `S1430f9` | detail | Warnings | Warnungen |
| `S51ecc5` | detail | What happens next | Wie es weitergeht |
| `S769bb1` | detail | When | Wann |
| `Sf323c0` | detail | Where used | Verwendung |
| `S7d5316` | detail | Who | Wer |
| `S47e564` | detail | Withdraw | Zurückziehen |
| `S51a998` | detail | Withdraw this change request? | Diesen Änderungsantrag zurückziehen? |
| `S5397e0` | detail, export_verify, list | Yes | Ja |
| `Sc8e4b4` | detail | Your decision step | Ihr Entscheidungsschritt |
| `S20cb4c` | detail, export_center | ZIP with manifest | ZIP mit Manifest |
| `S5d4358` | dry_run | All rows are clean. | Alle Zeilen sind fehlerfrei. |
| `S03510d` | dry_run | Back to import | Zurück zum Import |
| `S11f957` | dry_run | error | Fehler |
| `S2e7908` | dry_run | Every row is valid. Nothing has been created yet. | Jede Zeile ist gültig. Es wurde noch nichts angelegt. |
| `Se28265` | dry_run | Import check | Import-Prüfung |
| `Se78fe7` | dry_run | mode | Modus |
| `S044f10` | dry_run, st_preview | Problems and warnings | Probleme und Warnungen |
| `S5faa59` | dry_run | Result | Ergebnis |
| `Sec0298` | dry_run | Result per row | Ergebnis je Zeile |
| `S9bf7a8` | dry_run | Row | Zeile |
| `S3ff0b0` | dry_run | row(s) have problems. Nothing has been created. | Zeile(n) haben Probleme. Es wurde nichts angelegt. |
| `S6c30d2` | dry_run | rows | Zeilen |
| `S8012ff` | dry_run | unchanged | unverändert |
| `S83d655` | dry_run, st_preview | warning(s) | Warnung(en) |
| `S9ddad9` | dry_run | would be created | würden angelegt |
| `S0a18cf` | dry_run | would be revised | würden überarbeitet |
| `S66d6c2` | export_center | All Released Status Codes | Alle freigegebenen Statuscodes |
| `S5ff781` | export_center | Check that a file you received is exactly what this system produced (and, with its MANIFEST.json, that nothing was changed). | Prüfen Sie, ob eine erhaltene Datei genau das ist, was dieses System erzeugt hat (und mit der MANIFEST.json, dass nichts verändert wurde). |
| `S9468a1` | export_center | Download Full Database Backup | Vollständige Datenbanksicherung herunterladen |
| `Scc432e` | export_center | Every current status code in any lifecycle state, including unapproved Drafts. Every row and the file name carry a "Not for distribution — unapproved data" notice. | Jeder aktuelle Statuscode in jedem Lebenszyklus-Zustand, auch nicht freigegebene Entwürfe. Jede Zeile und der Dateiname tragen den Vermerk "Nicht zur Weitergabe – nicht freigegebene Daten". |
| `S53af3d` | export_center | Exported file | Exportierte Datei |
| `S3cd0e5` | export_center | Full-Database Export | Export der gesamten Datenbank |
| `Sc6ff17` | export_center | MANIFEST.json (optional) | MANIFEST.json (optional) |
| `S1b874a` | export_center | No published Releases yet. | Noch keine veröffentlichten Releases. |
| `S5af0a0` | export_center | Not for distribution | Nicht zur Weitergabe |
| `Sd3dfb5` | export_center | Published releases | Veröffentlichte Releases |
| `Se77605` | export_center | Published Releases only. Pick a Release to export its Released contents; the Release page offers profiles, audiences, languages, release notes and the offline lookup page. | Nur veröffentlichte Releases. Wählen Sie ein Release, um seine freigegebenen Inhalte zu exportieren; die Release-Seite bietet Profile, Zielgruppen, Sprachen, Release-Notes und die Offline-Nachschlageseite. |
| `Se25b5d` | export_center | Raw SQLite backup of the complete governed dataset. Handle per data-at-rest access-control requirements — this file carries the same sensitivity as the live database. | Rohe SQLite-Sicherung des gesamten verwalteten Datenbestands. Behandeln Sie sie nach den Vorgaben zur Zugriffskontrolle ruhender Daten – diese Datei ist so schutzbedürftig wie die Produktivdatenbank. |
| `Sd41f56` | export_center | Release | Release |
| `S3a7272` | export_center | Release Export | Release-Export |
| `S94bc64` | export_center | The current set of every Released status code, independent of any single Release. | Die aktuelle Menge aller veröffentlichten Statuscodes, unabhängig von einem einzelnen Release. |
| `Sdda6ac` | export_center | Verify | Prüfen |
| `S22b05e` | export_center | Verify a file | Eine Datei prüfen |
| `S2da600` | export_center, list | Version | Version |
| `S57dda3` | export_center | Working-Set Export | Arbeitsstand-Export |
| `Sbdcc6f` | export_profiles | A profile fixes the columns, their order and header labels, and optionally a default audience and language. Profiles are data: change them here, no deployment needed. | Ein Profil legt Spalten, Reihenfolge und Spaltenüberschriften fest, optional auch eine Standard-Zielgruppe und -Sprache. Profile sind Daten: Änderungen hier, ohne Neuauslieferung. |
| `Sa733b8` | export_profiles, review_checklist | Active | Aktiv |
| `S94ea8c` | export_profiles | Available fields | Verfügbare Felder |
| `Sf27073` | export_profiles | Columns (one per line: field \| header label) | Spalten (je Zeile: Feld \| Überschrift) |
| `S96b8ee` | export_profiles | Create profile | Profil anlegen |
| `Sa8ec52` | export_profiles | Default audience | Standard-Zielgruppe |
| `Sf7e949` | export_profiles | Export profiles | Export-Profile |
| `Sd436a3` | export_profiles | inactive | inaktiv |
| `S0a2f2c` | export_profiles | landscape | Querformat |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | Name |
| `Sca36da` | export_profiles | New profile | Neues Profil |
| `S8af321` | export_profiles | PDF orientation | PDF-Ausrichtung |
| `Sbb23e2` | export_profiles | PDF title page | PDF-Titelseite |
| `S25c604` | export_profiles | portrait | Hochformat |
| `Sf597c0` | export_profiles | Save profile | Profil speichern |
| `Sc0f94f` | export_verify | Back to Export Center | Zurück zum Export-Center |
| `S517134` | export_verify | export | Export |
| `S9ab178` | export_verify | it was changed after export, or it came from somewhere else | sie wurde nach dem Export verändert oder stammt von anderswo |
| `Sdde41f` | export_verify | Listed in manifest | Im Manifest aufgeführt |
| `S45ea95` | export_verify | Manifest signature | Manifest-Signatur |
| `S08f84b` | export_verify | No record of this exact file | Keine Aufzeichnung zu genau dieser Datei |
| `S357953` | export_verify | NOT OK | NICHT IN ORDNUNG |
| `S9ce3bd` | export_verify | OK | In Ordnung |
| `S8a5285` | export_verify | Overall | Gesamt |
| `Sd2bc4a` | export_verify | Produced by this system | Von diesem System erzeugt |
| `S112d15` | export_verify | Verify an export | Einen Export prüfen |
| `S7763b6` | export_verify | Verify an exported file | Eine exportierte Datei prüfen |
| `S32ac07` | fleet_feedback | File (.csv/.xlsx with status_code_identifier, occurrences) | Datei (.csv/.xlsx mit status_code_identifier, occurrences) |
| `S625adf` | fleet_feedback | Fleet feedback | Flotten-Rückmeldung |
| `Sd6fbc9` | fleet_feedback, st_preview | Import | Importieren |
| `S59f4f3` | fleet_feedback | Import occurrence counts | Häufigkeitszahlen importieren |
| `Sfbee55` | fleet_feedback | live codes | aktive Codes |
| `S040779` | fleet_feedback | MISSING | FEHLT |
| `S3da032` | fleet_feedback | Most frequent | Am häufigsten |
| `S7c1caf` | fleet_feedback | Never fired | Nie aufgetreten |
| `S02bd56` | fleet_feedback | No candidates (or no data imported yet). | Keine Kandidaten (oder noch keine Daten importiert). |
| `S3b0b47` | fleet_feedback, success_metrics | No data yet. | Noch keine Daten. |
| `Sd5ab17` | fleet_feedback | Occurrence counts per status code, aggregated and anonymised, imported from the internal monitoring side. They show which codes never fire (candidates for deprecation) and which fire most (candidates for better remedy text). | Häufigkeitszahlen je Statuscode, aggregiert und anonymisiert, aus der internen Überwachung importiert. Sie zeigen, welche Codes nie auftreten (Kandidaten zur Außerbetriebnahme) und welche am häufigsten (Kandidaten für bessere Abhilfetexte). |
| `Sf52555` | fleet_feedback | Occurrences | Auftreten |
| `S170a28` | fleet_feedback | Period | Zeitraum |
| `Sde2f48` | fleet_feedback | Period end | Zeitraum-Ende |
| `Se1f35c` | fleet_feedback | Period start | Zeitraum-Beginn |
| `Sc62d67` | fleet_feedback | period(s) | Zeitraum/-räume |
| `Sbdf5fd` | fleet_feedback | Remedy text | Abhilfetext |
| `S9851cb` | fleet_feedback | Unmatched rows | Nicht zugeordnete Zeilen |
| `Sfb360f` | fleet_feedback | yes | ja |
| `Sba3640` | form | A number with a unit: ms, s, min, h, or d (e.g. "10ms", "2min"). | Eine Zahl mit Einheit: ms, s, min, h oder d (z. B. "10ms", "2min"). |
| `Sf094b9` | form | Affected component (optional) | Betroffene Komponente (optional) |
| `S407cf2` | form | Applies from software version (optional) | Gilt ab Software-Version (optional) |
| `Sa30242` | form | Applies up to software version (optional) | Gilt bis Software-Version (optional) |
| `S77dfd2` | form, st_preview | Cancel | Abbrechen |
| `S94c2a3` | form | Classification | Klassifizierung |
| `S7c9afd` | form | Classification only — a Sandbox code's identifier is still drawn from the isolated StCd-T##### band, never from this group's numeric range. | Nur Klassifizierung – die Kennung eines Sandbox-Codes stammt weiterhin aus dem getrennten Bereich StCd-T#####, nie aus dem Nummernbereich dieser Gruppe. |
| `S9611fe` | form | Create Sandbox Code | Sandbox-Code anlegen |
| `Sced1ce` | form, list | Functional System Group | Funktionssystemgruppe |
| `Sdb0f93` | form | Immutable once allocated (BR-001). | Nach der Vergabe unveränderlich (BR-001). |
| `Sd7635c` | form | Legacy Reference Number (optional) | Alt-Referenznummer (optional) |
| `S2d3840` | form | New Sandbox Status Code | Neuer Sandbox-Statuscode |
| `S8f9967` | form | Not yet assigned — fixed on Submit for Review | Noch nicht vergeben – wird beim Einreichen zur Prüfung festgelegt |
| `S82890d` | form | Open review comments | Offene Prüfkommentare |
| `S611331` | form | Planned deprecation date (optional) | Geplantes Außerbetriebnahmedatum (optional) |
| `S75ee24` | form | Planned effective date (optional) | Geplantes Gültigkeitsdatum (optional) |
| `S39c8c4` | form | Program References — Advanced, controller firmware programs | Programmverweise – erweitert, Firmware-Programme der Steuerung |
| `S05c31a` | form | Proposed — confirmed by Administrator at review | Vorgeschlagen – vom Administrator bei der Prüfung bestätigt |
| `S298d36` | form | Reference number in the separate escalation code pool — not a CSCM Tool status code. | Referenznummer im getrennten Eskalations-Codepool – kein Statuscode des CSCM-Tools. |
| `S9e0128` | form | Related codes (optional) | Verwandte Codes (optional) |
| `S86971e` | form, translations | Remedy / recommended action (optional) | Abhilfe / empfohlene Maßnahme (optional) |
| `S2202ce` | form | Repeated-Error Escalation (optional) | Eskalation bei wiederholtem Fehler (optional) |
| `S4b9d6e` | form | Reviewer comment | Kommentar des Prüfers |
| `S028f6d` | form | Sandbox status code — never numbered from a real range, never released, deletable. | Sandbox-Statuscode – nie aus einem echten Bereich nummeriert, nie veröffentlicht, löschbar. |
| `Sc03132` | form | Save as Draft | Als Entwurf speichern |
| `Scc1316` | form | Save Draft | Entwurf speichern |
| `S6a6d41` | form | Saving again keeps your entries and replaces the stored values. | Erneutes Speichern behält Ihre Eingaben und ersetzt die gespeicherten Werte. |
| `S932745` | form | Software Version (optional) | Software-Version (optional) |
| `S4b57f3` | form | Standard references (optional) | Normverweise (optional) |
| `S82b5dd` | form | Status & Timing | Status & Zeitverhalten |
| `S613b74` | form | Status Code Identifier | Statuscode-Kennung |
| `S5b05b1` | form | Stored now | Jetzt gespeichert |
| `S9a1b35` | form | The pre-migration status code number, if any — for traceability only, never the governed StCd identifier. | Die Statuscode-Nummer vor der Migration, falls vorhanden – nur zur Nachvollziehbarkeit, nie die verwaltete StCd-Kennung. |
| `Sa6dac4` | form | Turbine Platform (at least one required before Submit for Review) | Anlagenplattform (mindestens eine vor dem Einreichen zur Prüfung) |
| `Sed412e` | form | What service staff should do. Feeds the service manual. | Was das Servicepersonal tun soll. Speist das Service-Handbuch. |
| `Sb1d254` | form | Your entries compared with the stored values | Ihre Eingaben im Vergleich zu den gespeicherten Werten |
| `S0b6c72` | form | Your entry | Ihre Eingabe |
| `Sc54d33` | help | Lifecycle states | Lebenszyklus-Zustände |
| `S367f8a` | help | Quick start for the other roles | Schnellstart für die anderen Rollen |
| `S9de664` | help | Quick start for your role | Schnellstart für Ihre Rolle |
| `S47dcc2` | help | Roles | Rollen |
| `Sa55a27` | help | Terms | Begriffe |
| `S689b33` | help | The full manual is docs/23-user-manual.md in the project folder; the glossary below is the same one the tooltips use. | Das vollständige Handbuch ist docs/23-user-manual.md im Projektordner; das Glossar unten ist dasselbe, das die Tooltips verwenden. |
| `S439914` | help | What happens next on a change request | Wie es bei einem Änderungsantrag weitergeht |
| `Sb08e6c` | help and messages | A Reviewer and an Administrator each sign off (in any order). If either rejects, it goes back to the author. | Ein Prüfer und ein Administrator geben jeweils frei (in beliebiger Reihenfolge). Lehnt einer ab, geht der Antrag zurück an den Autor. |
| `S2f1bed` | help and messages | An Administrator includes the revision in a Release and publishes it; then it is Released. | Ein Administrator nimmt die Revision in ein Release auf und veröffentlicht es; dann ist sie veröffentlicht. |
| `Sce489f` | help and messages | The author gets any required cross-domain sign-offs, then submits the change request for review. | Der Autor holt die erforderlichen fachübergreifenden Freigaben ein und reicht den Änderungsantrag dann zur Prüfung ein. |
| `S1cdbdd` | help and messages | The Chief Engineer approves or rejects. Approval makes the revision Approved (or Deprecated for a deprecation request). | Der Chefingenieur genehmigt oder lehnt ab. Die Genehmigung macht die Revision freigegeben (bei einem Außerbetriebnahme-Antrag: außer Betrieb). |
| `Secfb3f` | hub_consolidation | Deprecate replaced Hub codes | Ersetzte Hub-Codes außer Betrieb nehmen |
| `S0e7766` | hub_consolidation | draft | Entwurf |
| `S4e7cfe` | hub_consolidation | Every Hub code is deprecated - the group can be deactivated under Lookups. | Alle Hub-Codes sind außer Betrieb genommen – die Gruppe kann unter Auswahllisten deaktiviert werden. |
| `Sb17ab7` | hub_consolidation | Hub code | Hub-Code |
| `S036d00` | hub_consolidation | Hub codes and their replacements | Hub-Codes und ihre Ersatz-Codes |
| `Sc50c53` | hub_consolidation | Hub Controller to Main Controller consolidation | Konsolidierung Hub-Controller zu Hauptsteuerung |
| `Scd189f` | hub_consolidation | Hub group | Hub-Gruppe |
| `Sa5262b` | hub_consolidation | If the Hub Controller leaves the hardware setup, its codes are defined anew on the Main Controller side. Create an MC draft from an HC code on its detail page (Actions); this report shows how far each has come. Nothing is renumbered. | Entfällt der Hub-Controller aus dem Hardware-Aufbau, werden seine Codes auf der Hauptsteuerungs-Seite neu definiert. Legen Sie auf der Detailseite eines HC-Codes (Aktionen) einen MC-Entwurf an; dieser Bericht zeigt, wie weit jeder ist. Es wird nichts umnummeriert. |
| `Sdd6555` | hub_consolidation, legacy_mapping, st_preview | Legacy no. | Alt-Nr. |
| `S845a2b` | hub_consolidation | No Hub Controller codes yet. | Noch keine Hub-Controller-Codes. |
| `S138665` | hub_consolidation | Open deprecation requests | Außerbetriebnahme-Anträge eröffnen |
| `Sc8df93` | hub_consolidation | Open deprecation requests for all replaced Hub codes of this group? | Außerbetriebnahme-Anträge für alle ersetzten Hub-Codes dieser Gruppe eröffnen? |
| `S533e22` | hub_consolidation | Opens a deprecation request for every Released Hub code of the group whose Main Controller replacement is Released. Each request still needs review and approval. | Eröffnet für jeden freigegebenen Hub-Code der Gruppe, dessen Hauptsteuerungs-Ersatz freigegeben ist, einen Außerbetriebnahme-Antrag. Jeder Antrag braucht weiterhin Prüfung und Genehmigung. |
| `Sc385e3` | hub_consolidation | Replacement | Ersatz |
| `S29e740` | integrations | Add webhook | Webhook hinzufügen |
| `Sc82c65` | integrations | API tokens | API-Token |
| `S5a3538` | integrations | Copy the signing secret now - it is shown only once: | Kopieren Sie das Signatur-Geheimnis jetzt – es wird nur einmal angezeigt: |
| `S05b81a` | integrations | Copy the token now - it is shown only once: | Kopieren Sie das Token jetzt – es wird nur einmal angezeigt: |
| `S4b3c8e` | integrations | Create token | Token erstellen |
| `Sc5497b` | integrations | Events | Ereignisse |
| `Sa99be3` | integrations | Expires | Läuft ab |
| `Sba2a88` | integrations | Internal network only. Tokens can only read; webhooks can only reach private addresses. | Nur internes Netz. Token können nur lesen; Webhooks erreichen nur private Adressen. |
| `S1ed342` | integrations | Last delivery | Letzte Zustellung |
| `Sf1109d` | integrations | Last used | Zuletzt verwendet |
| `S6ad77d` | integrations | No tokens. | Keine Token. |
| `S082244` | integrations | No webhooks. | Keine Webhooks. |
| `S781961` | integrations | Pause | Pausieren |
| `S90eceb` | integrations | Prefix | Präfix |
| `Sb3bd0b` | integrations | Resume | Fortsetzen |
| `S8375cd` | integrations | revoked | widerrufen |
| `Sc23540` | integrations | Scopes | Geltungsbereiche |
| `Sb3138e` | integrations | Sent on release publish as JSON with the header X-CSCM-Signature: sha256=<HMAC of the body with the secret>. | Wird bei der Release-Veröffentlichung als JSON gesendet, mit dem Header X-CSCM-Signature: sha256=<HMAC des Inhalts mit dem Geheimnis>. |
| `S511ee2` | integrations | Valid for (days, max 365) | Gültig für (Tage, max. 365) |
| `Sfdfe2d` | integrations | Webhooks | Webhooks |
| `Sf9d469` | legacy_mapping | All controllers | Alle Steuerungen |
| `Se61c2f` | legacy_mapping | Any number state | Jeder Nummernstatus |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | Steuerung |
| `Sd7decf` | legacy_mapping, list | Filter | Filtern |
| `S7c4f77` | legacy_mapping | issued | vergeben |
| `S81f567` | legacy_mapping | Legacy number to new identifier | Altnummer zu neuer Kennung |
| `S64b267` | legacy_mapping | legacy number, identifier or name | Altnummer, Kennung oder Name |
| `S60fe6c` | legacy_mapping | new codes without a legacy number (n/a) | neue Codes ohne Altnummer (entfällt) |
| `Sf26140` | legacy_mapping, st_preview | New identifier | Neue Kennung |
| `Sf573c8` | legacy_mapping | no number yet | noch keine Nummer |
| `S7877c5` | legacy_mapping | No status code carries a legacy number yet. | Noch kein Statuscode trägt eine Altnummer. |
| `Sb7baa1` | legacy_mapping | Number | Nummer |
| `Sc3fed1` | legacy_mapping | reserved | reserviert |
| `Sbce064` | legacy_mapping, list | Search | Suche |
| `Sf57807` | legacy_mapping | Which new status code replaces which legacy number. The mapping runs from legacy to new only: the new library holds more codes than the old one, so a code without a legacy number is normal and there is no way back. | Welcher neue Statuscode welche Altnummer ersetzt. Die Zuordnung gilt nur von alt nach neu: Die neue Bibliothek enthält mehr Codes als die alte, ein Code ohne Altnummer ist also normal und einen Rückweg gibt es nicht. |
| `S8b0b7c` | legacy_mapping | with a legacy number | mit Altnummer |
| `Seba07b` | list | A change set groups the change requests that ship with one controller software release, so reviewers see the whole package. Each request is still decided on its own. | Ein Änderungspaket fasst die Änderungsanträge zusammen, die mit einem Steuerungs-Software-Release ausgeliefert werden, damit Prüfer das ganze Paket sehen. Jeder Antrag wird weiterhin einzeln entschieden. |
| `Sc5fe02` | list | any | beliebig |
| `Sef5415` | list | Apply columns | Spalten übernehmen |
| `S9e895f` | list | Change sets | Änderungspakete |
| `Scf723c` | list | Columns | Spalten |
| `S759686` | list | Filter status codes | Statuscodes filtern |
| `Sfd327d` | list | Identifier, title, description | Kennung, Titel, Beschreibung |
| `S44d25b` | list | Items | Einträge |
| `S033df3` | list | Lifecycle | Lebenszyklus |
| `Sb4cad6` | list | Link to this view | Link zu dieser Ansicht |
| `Se248d5` | list, new | New change set | Neues Änderungspaket |
| `Se75aa1` | list, new | New Release | Neues Release |
| `Se5076c` | list | No change sets yet. | Noch keine Änderungspakete. |
| `Sd32c03` | list | No releases yet. | Noch keine Releases. |
| `Sc3af43` | list | No saved searches yet. | Noch keine gespeicherten Suchen. |
| `S0cb400` | list | No status codes match these filters. | Keine Statuscodes entsprechen diesen Filtern. |
| `Sf7194e` | list | Requests | Anträge |
| `S37a530` | list | result | Ergebnis |
| `Scdf7e9` | list | results | Ergebnisse |
| `S4f581e` | list | Sandbox only | Nur Sandbox |
| `S1db747` | list | Save search | Suche speichern |
| `Sff86e9` | list | Save the current filters as | Aktuelle Filter speichern als |
| `Sed1d84` | list | Saved searches | Gespeicherte Suchen |
| `S20bff1` | list | Status codes | Statuscodes |
| `Se90eb0` | list | Turbine Platform | Anlagenplattform |
| `S86b1e7` | list | Typos are tolerated: "convertor" still finds "converter". | Tippfehler werden toleriert: "convertor" findet weiterhin "converter". |
| `Sf7c400` | login | Log in | Anmelden |
| `S175835` | login | or | oder |
| `S8be3c9` | login | Password | Passwort |
| `Sd876ad` | login, login_windows | Sign in with Windows | Mit Windows anmelden |
| `Sc5a911` | login | simulated | simuliert |
| `S2c7ab3` | login | Username or email | Benutzername oder E-Mail |
| `S78c92f` | login_windows | Back to the log-in page | Zurück zur Anmeldeseite |
| `S7b6084` | login_windows | In a deployment the browser hands over your Windows identity and you are signed in without this page. Here, type the identity the Windows gateway would have supplied. | Im Betrieb übergibt der Browser Ihre Windows-Identität und Sie werden ohne diese Seite angemeldet. Geben Sie hier die Identität ein, die das Windows-Gateway geliefert hätte. |
| `Sb6fcd9` | login_windows | No Windows identity reached the application. Open it through the organisation address, from a computer signed in to the company network. | Es kam keine Windows-Identität bei der Anwendung an. Öffnen Sie sie über die Adresse der Organisation, von einem im Firmennetz angemeldeten Rechner. |
| `S991f8c` | login_windows | Sign in as this Windows user | Als dieser Windows-Benutzer anmelden |
| `S985cf9` | login_windows | Simulation. | Simulation. |
| `S969b52` | login_windows | The e-mail address of the account is the user principal name; a name with a Windows domain in front needs WINDOWS_AUTH_EMAIL_DOMAIN or a matching user name. | Die E-Mail-Adresse des Kontos ist der Benutzerprinzipalname; ein Name mit vorangestellter Windows-Domäne braucht WINDOWS_AUTH_EMAIL_DOMAIN oder einen passenden Benutzernamen. |
| `S438073` | login_windows | Windows identity | Windows-Identität |
| `S913aff` | mine | Select all | Alle auswählen |
| `S2e0035` | mine | Submitted | Eingereicht |
| `Sa03f8a` | mine | Withdraw selected | Ausgewählte zurückziehen |
| `Sa0d9d0` | mine | Withdraw the ticked change requests? A withdrawn Draft is deleted; its number is only kept if it was already issued. | Die angekreuzten Änderungsanträge zurückziehen? Ein zurückgezogener Entwurf wird gelöscht; seine Nummer bleibt nur erhalten, wenn sie schon vergeben war. |
| `Sdf42bb` | new, review_checklist | all groups | alle Gruppen |
| `S382b49` | new | Controller software versions this Release is for (optional) | Steuerungs-Software-Versionen, für die dieses Release gilt (optional) |
| `Sec0c4b` | new | Create change set | Änderungspaket anlegen |
| `Sbbc876` | new | Create new codes | Neue Codes anlegen |
| `Sbe8337` | new | Create Release | Release anlegen |
| `Sae0114` | new | Every row that passes validation becomes an ordinary Draft, subject to the full Cross-Domain Sign-Off, dual-review, and Chief Engineer approval cycle before it can be Released — import is a faster data-entry path, never a governance bypass. | Jede Zeile, die die Prüfung besteht, wird ein gewöhnlicher Entwurf und durchläuft vor der Freigabe die volle fachübergreifende Freigabe, die doppelte Prüfung und die Genehmigung durch den Chefingenieur – der Import ist ein schnellerer Eingabeweg, nie eine Umgehung der Governance. |
| `Sec1717` | new | File (.csv or .xlsx) | Datei (.csv oder .xlsx) |
| `Sac7f67` | new | headers only | nur Kopfzeile |
| `S801c9a` | new, reconciliation | Migration progress | Migrationsfortschritt |
| `S154964` | new | Scope: Functional System Group (optional) | Umfang: Funktionssystemgruppe (optional) |
| `Sd22e9f` | new | Start from the template: | Beginnen Sie mit der Vorlage: |
| `Sfda98f` | new | Target software version (optional) | Ziel-Software-Version (optional) |
| `S7d2a95` | new | Update: revise codes already imported (matched on the legacy number) | Aktualisieren: bereits importierte Codes überarbeiten (Zuordnung über die Altnummer) |
| `S5b23cf` | new | Upload a CSV or XLSX file — one row per status code, column headers matching the field names used elsewhere in CSCM Tool (Functional System Group/Subgroup and the audience-access fields by their code, e.g. "WCNV", "Converter", "SCADA User"). | Laden Sie eine CSV- oder XLSX-Datei hoch – eine Zeile je Statuscode, Spaltenüberschriften wie die Feldnamen im CSCM-Tool (Funktionssystemgruppe/-untergruppe und die Zielgruppen-Zugriffsfelder über ihren Code, z. B. "WCNV", "Converter", "SCADA User"). |
| `Sf738c6` | new | Upload and Import | Hochladen und importieren |
| `Sfc039f` | new | Validate only (creates nothing) | Nur prüfen (legt nichts an) |
| `Se90e89` | new | When set, only codes that apply to one of these versions are offered as candidates. | Wenn gesetzt, werden nur Codes als Kandidaten angeboten, die für eine dieser Versionen gelten. |
| `S141dbd` | new | with instructions and lookup codes | mit Anleitung und Auswahlcodes |
| `S1b8316` | notifications | Mark all as read | Alle als gelesen markieren |
| `Sc1ee86` | notifications | Mark as read | Als gelesen markieren |
| `Scf9b77` | notifications | Open | Öffnen |
| `Sa94065` | notifications | You have no notices. | Sie haben keine Hinweise. |
| `Sf03c0a` | operations | ago | her |
| `Sd005ac` | operations | Audit log integrity | Integrität des Audit-Protokolls |
| `S530cc2` | operations | Backups | Datensicherungen |
| `S41ba99` | operations | Database schema | Datenbankschema |
| `Sc2e311` | operations | entries | Einträge |
| `Sefd55c` | operations | Every audit entry carries a hash of its predecessor; a removed, reordered or edited entry breaks the chain. | Jeder Audit-Eintrag enthält den Hash seines Vorgängers; ein entfernter, umsortierter oder geänderter Eintrag unterbricht die Kette. |
| `S6ac87f` | operations, reconciliation | Expected | Erwartet |
| `S9eac73` | operations | first bad entry | erster fehlerhafter Eintrag |
| `S7a2ec1` | operations | generations kept | Generationen aufbewahrt |
| `S333c63` | operations | Last run | Letzter Lauf |
| `S3f0b1a` | operations | Last verified | Zuletzt geprüft |
| `Se51105` | operations | Last verified backup | Letzte geprüfte Sicherung |
| `Sa62a99` | operations | No backup directory is configured (BACKUP_DIR). Schedule `flask backup-db` as described in the deployment guide. | Es ist kein Sicherungsverzeichnis konfiguriert (BACKUP_DIR). Planen Sie `flask backup-db` wie im Bereitstellungshandbuch beschrieben ein. |
| `S1fcf54` | operations | OUTDATED - run flask db upgrade | VERALTET – flask db upgrade ausführen |
| `S9e0005` | operations | The audit chain is BROKEN | Die Audit-Kette ist UNTERBROCHEN |
| `S8bdea8` | operations | The audit chain is intact | Die Audit-Kette ist intakt |
| `S95389d` | operations | up to date | aktuell |
| `Sdbf641` | operations | Verify now | Jetzt prüfen |
| `S1a4626` | reconciliation | ...or just the expected number of rows | ...oder nur die erwartete Zeilenzahl |
| `Sf0a8d6` | reconciliation | Compare with the legacy master list | Mit der Alt-Stammliste vergleichen |
| `S805e86` | reconciliation | Errors | Fehler |
| `S434eb2` | reconciliation | Imported | Importiert |
| `Sa671a4` | reconciliation | imported | importiert |
| `Sda104a` | reconciliation | Imported (legacy numbers on file) | Importiert (Altnummern vorhanden) |
| `S82ba98` | reconciliation | Legacy library migration progress | Fortschritt der Migration der Alt-Bibliothek |
| `S48926c` | reconciliation | Master list (.csv/.xlsx with a legacy_reference_number column) | Stammliste (.csv/.xlsx mit Spalte legacy_reference_number) |
| `S17fc39` | reconciliation | Missing legacy numbers | Fehlende Altnummern |
| `Sca5d2f` | reconciliation | Recent import jobs | Letzte Import-Aufträge |
| `S4f437c` | reconciliation | Still missing | Noch fehlend |
| `S92ef08` | review_checklist | Activate | Aktivieren |
| `Sfc1290` | review_checklist | Add an item | Punkt hinzufügen |
| `S0c9d31` | review_checklist | Applies to | Gilt für |
| `Sd9053c` | review_checklist | Checklist items | Checklistenpunkte |
| `Sd65ded` | review_checklist | Deactivate | Deaktivieren |
| `Secdda5` | review_checklist | Item | Punkt |
| `S4b4bb9` | review_checklist | Items a Reviewer must confirm before approving. An item applies to one Functional System Group or to all. With no items nothing is required. | Punkte, die ein Prüfer vor der Genehmigung bestätigen muss. Ein Punkt gilt für eine Funktionssystemgruppe oder für alle. Ohne Punkte ist nichts erforderlich. |
| `S1c1f74` | review_checklist | No checklist items configured. | Keine Checklistenpunkte konfiguriert. |
| `Sc3328c` | review_checklist | Text | Text |
| `Se24e82` | review_queue | Assigned | Zugewiesen |
| `S2ef718` | review_queue | Change requests waiting for review | Änderungsanträge, die auf Prüfung warten |
| `Sb23ab5` | review_queue | Nothing is awaiting Review sign-off. | Nichts wartet auf eine Prüfungsfreigabe. |
| `Se29a79` | review_queue, success_metrics | Review | Prüfen |
| `S05fc94` | role badge | Engineer | Ingenieur |
| `S3c0e8a` | role badge | StCd Owner | StCd-Eigner |
| `Sdbad9f` | role badge | Viewer | Betrachter |
| `S7505d6` | settings | default | Standard |
| `S913aba` | settings | Save settings | Einstellungen speichern |
| `Sb68734` | software_versions | Added | Hinzugefügt |
| `S172415` | software_versions | added | hinzugefügt |
| `Scb5424` | software_versions | Changed | Geändert |
| `S37c6c5` | software_versions, st_preview | changed | geändert |
| `S37d298` | software_versions | codes apply to | Codes gelten für |
| `Sac0d4a` | software_versions | Compare with (what changed) | Vergleichen mit (was sich geändert hat) |
| `S874581` | software_versions | field(s) | Feld(er) |
| `Sb5e77c` | software_versions | Removed | Entfernt |
| `S69992f` | software_versions | removed | entfernt |
| `Sd97d1e` | software_versions | Show | Anzeigen |
| `S42ea2e` | software_versions | Software Versions | Software-Versionen |
| `Sae79ea` | software_versions | To | Bis |
| `S3bd89c` | software_versions | Which codes exist in which software version | Welche Codes in welcher Software-Version existieren |
| `Sb149ca` | st_new | Detect: a number from 10000 up is a Hub Controller program | Erkennen: Eine Nummer ab 10000 ist ein Programm der Nabensteuerung |
| `S7d06d0` | st_new | Every imported program becomes an ordinary Draft with the number it carries reserved. It still needs Cross-Domain Sign-Off, dual review and Chief Engineer approval before Release, and all Drafts of one import share a change set. | Jedes importierte Programm wird ein gewöhnlicher Entwurf, dessen Nummer reserviert ist. Er braucht vor der Veröffentlichung weiterhin die fachübergreifende Freigabe, die doppelte Prüfung und die Genehmigung des Chefingenieurs; alle Entwürfe eines Imports gehören zu einem Änderungspaket. |
| `S3b9e43` | st_new | Hub Controller (legacy numbers, mapped to the new ones) | Nabensteuerung (Altnummern, auf die neuen abgebildet) |
| `Sd7333f` | st_new | Import status codes from .st files | Statuscodes aus .st-Dateien importieren |
| `S6640a6` | st_new | New number of Hub Controller programs | Neue Nummer der Programme der Nabensteuerung |
| `Sc0eff1` | st_new | Or a whole folder | Oder ein ganzer Ordner |
| `S94ddc1` | st_new | Program files (.st) or a ZIP | Programmdateien (.st) oder ein ZIP |
| `Sd99e2a` | st_new | Proposal 1: five-digit numbers (11000 and up) | Vorschlag 1: fünfstellige Nummern (ab 11000) |
| `S2744b0` | st_new | Proposal 2: inside the Main Controller scheme | Vorschlag 2: innerhalb des Schemas der Hauptsteuerung |
| `S67640d` | st_new | Read files and preview | Dateien lesen und Vorschau anzeigen |
| `S234237` | st_new | Status category of the new codes | Statuskategorie der neuen Codes |
| `Sde7a5b` | st_new | The program files do not carry a category; you can change it in each Draft. | Die Programmdateien enthalten keine Kategorie; Sie können sie in jedem Entwurf ändern. |
| `S8f4c21` | st_new | Turbine platforms | Turbinenplattformen |
| `S9ad4d4` | st_new | Upload the generated StCd_<n>.st programs — several files at once, a whole folder, or one ZIP. Nothing is created yet: the next page lists every program so you can tick the ones to import. | Laden Sie die erzeugten StCd_<n>.st-Programme hoch — mehrere Dateien auf einmal, einen ganzen Ordner oder ein ZIP. Es wird noch nichts angelegt: Die nächste Seite listet jedes Programm auf, damit Sie die zu importierenden ankreuzen können. |
| `S2693e5` | st_preview | All Drafts of this import join one change set, so they can be reviewed and decided together. | Alle Entwürfe dieses Imports kommen in ein Änderungspaket, damit sie gemeinsam geprüft und entschieden werden können. |
| `Scbc694` | st_preview | already in the catalogue | bereits im Katalog |
| `Sdf88b8` | st_preview | blocked | gesperrt |
| `S6f7703` | st_preview | Changed and withdrawn programs are not ticked: tick the ones you want to update, revise or restore. | Geänderte und zurückgezogene Programme sind nicht angekreuzt: Kreuzen Sie die an, die aktualisiert, überarbeitet oder wiederhergestellt werden sollen. |
| `S78bb8b` | st_preview | Create Drafts for the ticked programs | Entwürfe für die angekreuzten Programme anlegen |
| `S441564` | st_preview | differs in | weicht ab in |
| `S4bc4cc` | st_preview | file(s) | Datei(en) |
| `S962725` | st_preview | Filter the list | Liste filtern |
| `S8cd536` | st_preview | Group / Subgroup | Gruppe / Untergruppe |
| `S47e0b6` | st_preview | Name of the change set (optional) | Name des Änderungspakets (optional) |
| `S32f96c` | st_preview | No programs found. | Keine Programme gefunden. |
| `S8e20aa` | st_preview | number, name, file ... | Nummer, Name, Datei ... |
| `Sf71701` | st_preview | opens a new Draft on the same number | legt einen neuen Entwurf auf derselben Nummer an |
| `Sffc13f` | st_preview | opens a new revision | legt eine neue Revision an |
| `S6daf16` | st_preview | Preview: status codes from .st files | Vorschau: Statuscodes aus .st-Dateien |
| `S15a21a` | st_preview | program(s) | Programm(e) |
| `Se58289` | st_preview | Programs found in the uploaded files | In den hochgeladenen Dateien gefundene Programme |
| `S75c053` | st_preview | ready | bereit |
| `S0723bf` | st_preview | Select all programs that are ready | Alle bereiten Programme auswählen |
| `S1a767a` | st_preview | updates the open Draft | aktualisiert den offenen Entwurf |
| `S02499f` | st_preview | withdrawn | zurückgezogen |
| `Sf0c3cf` | st_preview | without a legacy number | ohne Altnummer |
| `S8e9c89` | stalled | approval: amber after | Genehmigung: gelb nach |
| `S244492` | stalled | Assign | Zuweisen |
| `Sfd77f5` | stalled | Change thresholds | Schwellwerte ändern |
| `Sc5e8fc` | stalled | Nothing is stalled. | Nichts hängt. |
| `S448e3d` | stalled | Open reviews | Offene Prüfungen |
| `S55843f` | stalled | Reassign | Neu zuweisen |
| `S950eaf` | stalled | Requests waiting longer than the configured thresholds. Review: amber after | Anträge, die länger als die eingestellten Schwellwerte warten. Prüfung: gelb nach |
| `S0bc91e` | stalled | Reviewer workload | Auslastung der Prüfer |
| `Sc0d28c` | stalled | Reviewers who are out of office (they have delegated) are left out. | Prüfer, die abwesend sind (sie haben eine Vertretung eingerichtet), sind nicht aufgeführt. |
| `Sca6d0e` | stalled | Stage | Stufe |
| `Sb1bafe` | stalled | Stalled change requests | Hängende Änderungsanträge |
| `Sff9f1f` | success_metrics | Age | Alter |
| `S8cc047` | success_metrics | Approval | Genehmigung |
| `S273d62` | success_metrics | Audit trail completeness of Released codes | Vollständigkeit der Nachvollziehbarkeit freigegebener Codes |
| `Sc1d0d9` | success_metrics | Codes without an active owner | Codes ohne aktiven Eigentümer |
| `S8666fb` | success_metrics | Cross-domain sign-off (all time) | Fachübergreifende Freigabe (gesamt) |
| `S2d6dbc` | success_metrics | Cross-domain sign-off (last 90 days) | Fachübergreifende Freigabe (letzte 90 Tage) |
| `Sd028de` | success_metrics | Incomplete, e.g. | Unvollständig, z. B. |
| `S9418f1` | success_metrics | median of | Median aus |
| `Sceafa9` | success_metrics | met | erreicht |
| `S0fa9cd` | success_metrics | No Released codes yet. | Noch keine freigegebenen Codes. |
| `Sa8c86d` | success_metrics | NOT met | NICHT erreicht |
| `Sc011aa` | success_metrics | Released revisions have the full trail: submit, both review sign-offs, approval and publish. | Veröffentlichte Revisionen haben die vollständige Spur: Einreichen, beide Prüfungsfreigaben, Genehmigung und Veröffentlichung. |
| `S9ddbd3` | success_metrics | Submission to approval (all time) | Einreichung bis Genehmigung (gesamt) |
| `S1c0f84` | success_metrics | Submission to approval (last 90 days) | Einreichung bis Genehmigung (letzte 90 Tage) |
| `Se08405` | success_metrics | Success metrics | Erfolgskennzahlen |
| `S0e8a3a` | success_metrics | target | Ziel |
| `S05975b` | success_metrics | The targets the business case promises, measured from the timestamps the tool already keeps. Business days are Monday to Friday. | Die Ziele, die der Business Case verspricht, gemessen an den Zeitstempeln, die das Tool ohnehin führt. Werktage sind Montag bis Freitag. |
| `Saa2ee9` | success_metrics | Waiting for a decision | Wartet auf eine Entscheidung |
| `S0240d7` | translations | A code can be translated once its source text is Approved. | Ein Code kann übersetzt werden, sobald sein Quelltext freigegeben ist. |
| `S737d81` | translations | A translation is saved as a draft and approved by someone else - a light review, not the three-decision cycle. Exports in a language use approved translations only. | Eine Übersetzung wird als Entwurf gespeichert und von einer anderen Person freigegeben – eine leichte Prüfung, nicht der Drei-Entscheidungen-Ablauf. Exporte in einer Sprache verwenden nur freigegebene Übersetzungen. |
| `Sa0452c` | translations | Approve translation | Übersetzung freigeben |
| `Sb52b36` | translations | Back | Zurück |
| `S2fd88e` | translations | Copy from previous revision | Aus vorheriger Revision kopieren |
| `Se522f0` | translations | Save draft translation | Entwurfs-Übersetzung speichern |
| `Scb0b87` | translations | source language text of revision | Quellsprachen-Text der Revision |

### 9.3 FR Français 🇫🇷 — French

102 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | en retard |
| `Sad60c5` | _role | level | niveau |
| `S89b86a` | account_settings, base, detail | Language | Langue |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | Administrateur |
| `Sc452ad` | approval_queue, base | Approval Queue | File d'approbation |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | Relecteur |
| `S85dfa3` | base | Account | Compte |
| `Sb8be3d` | base | Administration | Administration |
| `S28dd75` | base | Audit Log | Journal d'audit |
| `Sa28e96` | base, catalogue_health | Catalogue Health | Santé du catalogue |
| `S162a45` | base, list | Change Sets | Lots de modifications |
| `S532c86` | base | covering | remplacement |
| `Sd87f47` | base, dashboard | Dashboard | Tableau de bord |
| `S710ea3` | base, delegations | Delegation | Délégation |
| `See833c` | base, export_center | Export Center | Centre d'export |
| `S6f6f72` | base, export_profiles | Export Profiles | Profils d'export |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | Retour du parc |
| `Sc47ae1` | base, help | Help | Aide |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | Consolidation des Hub |
| `S8ac724` | base, new | Import from .st files | Importer depuis des fichiers .st |
| `S1ed126` | base | Insight | Analyses |
| `Sa7881c` | base, integrations | Integrations | Intégrations |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | Correspondance ancien-nouveau |
| `S3c1c8a` | base, new, st_new | Library Import | Import de la bibliothèque |
| `S6e78c9` | base | Log out | Se déconnecter |
| `S3871af` | base | Lookups | Listes de valeurs |
| `Sefd197` | base | Main navigation | Navigation principale |
| `S617eec` | base, mine | My Change Requests | Mes demandes de modification |
| `Sdbb388` | base | New Sandbox Code | Nouveau code de test |
| `Sd85719` | base, form, list | New Status Code | Nouveau code de statut |
| `Se94865` | base, dashboard, notifications | Notices | Notifications |
| `Sa1fdaa` | base, operations | Operations | Exploitation |
| `S8fa41d` | base, dashboard, list | Releases | Versions publiées |
| `Sf490d7` | base, review_checklist | Review Checklist | Liste de contrôle de relecture |
| `S437a0d` | base, review_queue | Review Queue | File de relecture |
| `Sc7f73b` | base, settings | Settings | Paramètres |
| `Sbe504f` | base | Skip to main content | Aller au contenu principal |
| `Sa42252` | base, stalled | Stalled Requests | Demandes en attente |
| `S7f5583` | base, list | Status Codes | Codes de statut |
| `Sa4a761` | base, success_metrics | Success Metrics | Indicateurs de succès |
| `S1b9aeb` | base, dashboard | unread | non lues |
| `S57f2b1` | base | Users | Utilisateurs |
| `Sd7a484` | base | Workflow | Flux de travail |
| `S5a4692` | base | You are covering for a colleague | Vous remplacez un collègue |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | Pas encore attribué |
| `Sbae7d5` | catalogue_health, detail, list | Status | Statut |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | En attente de la validation de l'administrateur |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | En attente de l'approbation de l'ingénieur en chef |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | En attente de validation inter-domaines |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | En attente de la validation du relecteur |
| `S452d9f` | dashboard | Browse published and in-progress releases | Parcourir les versions publiées et en cours |
| `Scf72d4` | dashboard | Browse Status Codes | Parcourir les codes de statut |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | Mes brouillons bloqués par une validation de domaine |
| `Se0688f` | dashboard | My Open Change Requests | Mes demandes de modification ouvertes |
| `Sf949fb` | dashboard | Number ranges running out | Plages de numéros bientôt épuisées |
| `S6605c0` | dashboard | Search and filter all governed status codes | Rechercher et filtrer tous les codes de statut gouvernés |
| `S916385` | dashboard | Stalled requests | Demandes en attente |
| `S074d62` | detail, role badge | Chief Engineer | Ingénieur en chef |
| `S2fa1f7` | detail, form, list | Functional Subgroup | Sous-groupe fonctionnel |
| `S816c52` | detail, export_verify, list | No | Non |
| `S483bf2` | detail, list | Published | Publié |
| `Se96390` | detail, list | Remove | Supprimer |
| `Se246b6` | detail, form, list | Status Category | Catégorie de statut |
| `S08e643` | detail, list | Target software version | Version logicielle cible |
| `S5397e0` | detail, export_verify, list | Yes | Oui |
| `S2da600` | export_center, list | Version | Version |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | Nom |
| `Sced1ce` | form, list | Functional System Group | Groupe fonctionnel |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | Contrôleur |
| `Sd7decf` | legacy_mapping, list | Filter | Filtrer |
| `Sb7baa1` | legacy_mapping | Number | Numéro |
| `Sbce064` | legacy_mapping, list | Search | Rechercher |
| `Sc5fe02` | list | any | tous |
| `Sef5415` | list | Apply columns | Appliquer les colonnes |
| `S9e895f` | list | Change sets | Lots de modifications |
| `Scf723c` | list | Columns | Colonnes |
| `S759686` | list | Filter status codes | Filtrer les codes de statut |
| `Sfd327d` | list | Identifier, title, description | Identifiant, titre, description |
| `S44d25b` | list | Items | Éléments |
| `S033df3` | list | Lifecycle | Cycle de vie |
| `Sb4cad6` | list | Link to this view | Lien vers cette vue |
| `Se248d5` | list, new | New change set | Nouveau lot de modifications |
| `Se75aa1` | list, new | New Release | Nouvelle version |
| `Se5076c` | list | No change sets yet. | Aucun lot de modifications pour l'instant. |
| `Sd32c03` | list | No releases yet. | Aucune version pour l'instant. |
| `Sc3af43` | list | No saved searches yet. | Aucune recherche enregistrée. |
| `S0cb400` | list | No status codes match these filters. | Aucun code de statut ne correspond à ces filtres. |
| `Sf7194e` | list | Requests | Demandes |
| `S37a530` | list | result | résultat |
| `Scdf7e9` | list | results | résultats |
| `S4f581e` | list | Sandbox only | Test uniquement |
| `S1db747` | list | Save search | Enregistrer la recherche |
| `Sff86e9` | list | Save the current filters as | Enregistrer les filtres actuels sous |
| `Sed1d84` | list | Saved searches | Recherches enregistrées |
| `S20bff1` | list | Status codes | Codes de statut |
| `Se90eb0` | list | Turbine Platform | Plateforme d'éolienne |
| `Sf7c400` | login | Log in | Se connecter |
| `S8be3c9` | login | Password | Mot de passe |
| `S2c7ab3` | login | Username or email | Nom d'utilisateur ou e-mail |
| `S05fc94` | role badge | Engineer | Ingénieur |
| `S3c0e8a` | role badge | StCd Owner | Responsable StCd |
| `Sdbad9f` | role badge | Viewer | Lecteur |

### 9.4 IN हिन्दी 🇮🇳 — Hindi

102 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | विलंबित |
| `Sad60c5` | _role | level | स्तर |
| `S89b86a` | account_settings, base, detail | Language | भाषा |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | प्रशासक |
| `Sc452ad` | approval_queue, base | Approval Queue | अनुमोदन कतार |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | समीक्षक |
| `S85dfa3` | base | Account | खाता |
| `Sb8be3d` | base | Administration | प्रशासन |
| `S28dd75` | base | Audit Log | ऑडिट लॉग |
| `Sa28e96` | base, catalogue_health | Catalogue Health | कैटलॉग स्वास्थ्य |
| `S162a45` | base, list | Change Sets | परिवर्तन समूह |
| `S532c86` | base | covering | प्रतिस्थापन |
| `Sd87f47` | base, dashboard | Dashboard | डैशबोर्ड |
| `S710ea3` | base, delegations | Delegation | प्रत्यायोजन |
| `See833c` | base, export_center | Export Center | निर्यात केंद्र |
| `S6f6f72` | base, export_profiles | Export Profiles | निर्यात प्रोफ़ाइल |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | बेड़े की प्रतिक्रिया |
| `Sc47ae1` | base, help | Help | सहायता |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | हब समेकन |
| `S8ac724` | base, new | Import from .st files | .st फ़ाइलों से आयात करें |
| `S1ed126` | base | Insight | विश्लेषण |
| `Sa7881c` | base, integrations | Integrations | एकीकरण |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | पुराने-नए की मैपिंग |
| `S3c1c8a` | base, new, st_new | Library Import | लाइब्रेरी आयात |
| `S6e78c9` | base | Log out | लॉग आउट |
| `S3871af` | base | Lookups | संदर्भ सूचियाँ |
| `Sefd197` | base | Main navigation | मुख्य नेविगेशन |
| `S617eec` | base, mine | My Change Requests | मेरे परिवर्तन अनुरोध |
| `Sdbb388` | base | New Sandbox Code | नया सैंडबॉक्स कोड |
| `Sd85719` | base, form, list | New Status Code | नया स्थिति कोड |
| `Se94865` | base, dashboard, notifications | Notices | सूचनाएँ |
| `Sa1fdaa` | base, operations | Operations | संचालन |
| `S8fa41d` | base, dashboard, list | Releases | रिलीज़ |
| `Sf490d7` | base, review_checklist | Review Checklist | समीक्षा चेकलिस्ट |
| `S437a0d` | base, review_queue | Review Queue | समीक्षा कतार |
| `Sc7f73b` | base, settings | Settings | सेटिंग्स |
| `Sbe504f` | base | Skip to main content | मुख्य सामग्री पर जाएँ |
| `Sa42252` | base, stalled | Stalled Requests | रुके हुए अनुरोध |
| `S7f5583` | base, list | Status Codes | स्थिति कोड |
| `Sa4a761` | base, success_metrics | Success Metrics | सफलता मापदंड |
| `S1b9aeb` | base, dashboard | unread | अपठित |
| `S57f2b1` | base | Users | उपयोगकर्ता |
| `Sd7a484` | base | Workflow | कार्यप्रवाह |
| `S5a4692` | base | You are covering for a colleague | आप एक सहकर्मी की जगह काम कर रहे हैं |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | अभी निर्धारित नहीं |
| `Sbae7d5` | catalogue_health, detail, list | Status | स्थिति |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | प्रशासक की स्वीकृति की प्रतीक्षा में |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | मुख्य अभियंता के अनुमोदन की प्रतीक्षा में |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | क्रॉस-डोमेन स्वीकृति की प्रतीक्षा में |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | समीक्षक की स्वीकृति की प्रतीक्षा में |
| `S452d9f` | dashboard | Browse published and in-progress releases | प्रकाशित और जारी रिलीज़ देखें |
| `Scf72d4` | dashboard | Browse Status Codes | स्थिति कोड देखें |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | डोमेन स्वीकृति पर रुके मेरे ड्राफ़्ट अनुरोध |
| `Se0688f` | dashboard | My Open Change Requests | मेरे खुले परिवर्तन अनुरोध |
| `Sf949fb` | dashboard | Number ranges running out | समाप्त होती संख्या सीमाएँ |
| `S6605c0` | dashboard | Search and filter all governed status codes | सभी नियंत्रित स्थिति कोड खोजें और फ़िल्टर करें |
| `S916385` | dashboard | Stalled requests | रुके हुए अनुरोध |
| `S074d62` | detail, role badge | Chief Engineer | मुख्य अभियंता |
| `S2fa1f7` | detail, form, list | Functional Subgroup | कार्यात्मक उप-समूह |
| `S816c52` | detail, export_verify, list | No | नहीं |
| `S483bf2` | detail, list | Published | प्रकाशित |
| `Se96390` | detail, list | Remove | हटाएँ |
| `Se246b6` | detail, form, list | Status Category | स्थिति श्रेणी |
| `S08e643` | detail, list | Target software version | लक्षित सॉफ़्टवेयर संस्करण |
| `S5397e0` | detail, export_verify, list | Yes | हाँ |
| `S2da600` | export_center, list | Version | संस्करण |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | नाम |
| `Sced1ce` | form, list | Functional System Group | कार्यात्मक प्रणाली समूह |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | नियंत्रक |
| `Sd7decf` | legacy_mapping, list | Filter | फ़िल्टर करें |
| `Sb7baa1` | legacy_mapping | Number | संख्या |
| `Sbce064` | legacy_mapping, list | Search | खोजें |
| `Sc5fe02` | list | any | कोई भी |
| `Sef5415` | list | Apply columns | स्तंभ लागू करें |
| `S9e895f` | list | Change sets | परिवर्तन समूह |
| `Scf723c` | list | Columns | स्तंभ |
| `S759686` | list | Filter status codes | स्थिति कोड फ़िल्टर करें |
| `Sfd327d` | list | Identifier, title, description | पहचानकर्ता, शीर्षक, विवरण |
| `S44d25b` | list | Items | आइटम |
| `S033df3` | list | Lifecycle | जीवनचक्र |
| `Sb4cad6` | list | Link to this view | इस दृश्य का लिंक |
| `Se248d5` | list, new | New change set | नया परिवर्तन समूह |
| `Se75aa1` | list, new | New Release | नई रिलीज़ |
| `Se5076c` | list | No change sets yet. | अभी कोई परिवर्तन समूह नहीं। |
| `Sd32c03` | list | No releases yet. | अभी कोई रिलीज़ नहीं। |
| `Sc3af43` | list | No saved searches yet. | अभी कोई सहेजी गई खोज नहीं। |
| `S0cb400` | list | No status codes match these filters. | इन फ़िल्टरों से कोई स्थिति कोड मेल नहीं खाता। |
| `Sf7194e` | list | Requests | अनुरोध |
| `S37a530` | list | result | परिणाम |
| `Scdf7e9` | list | results | परिणाम |
| `S4f581e` | list | Sandbox only | केवल सैंडबॉक्स |
| `S1db747` | list | Save search | खोज सहेजें |
| `Sff86e9` | list | Save the current filters as | वर्तमान फ़िल्टर इस नाम से सहेजें |
| `Sed1d84` | list | Saved searches | सहेजी गई खोजें |
| `S20bff1` | list | Status codes | स्थिति कोड |
| `Se90eb0` | list | Turbine Platform | टर्बाइन प्लेटफ़ॉर्म |
| `Sf7c400` | login | Log in | लॉग इन करें |
| `S8be3c9` | login | Password | पासवर्ड |
| `S2c7ab3` | login | Username or email | उपयोगकर्ता नाम या ईमेल |
| `S05fc94` | role badge | Engineer | अभियंता |
| `S3c0e8a` | role badge | StCd Owner | StCd स्वामी |
| `Sdbad9f` | role badge | Viewer | दर्शक |

### 9.5 SA العربية 🇸🇦 — Arabic

102 of 772 strings translated; direction right to left.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | متأخر |
| `Sad60c5` | _role | level | المستوى |
| `S89b86a` | account_settings, base, detail | Language | اللغة |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | المسؤول |
| `Sc452ad` | approval_queue, base | Approval Queue | قائمة الموافقة |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | المراجع |
| `S85dfa3` | base | Account | الحساب |
| `Sb8be3d` | base | Administration | الإدارة |
| `S28dd75` | base | Audit Log | سجل التدقيق |
| `Sa28e96` | base, catalogue_health | Catalogue Health | سلامة الكتالوج |
| `S162a45` | base, list | Change Sets | مجموعات التغيير |
| `S532c86` | base | covering | نيابة |
| `Sd87f47` | base, dashboard | Dashboard | لوحة المعلومات |
| `S710ea3` | base, delegations | Delegation | التفويض |
| `See833c` | base, export_center | Export Center | مركز التصدير |
| `S6f6f72` | base, export_profiles | Export Profiles | ملفات التصدير |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ملاحظات الأسطول |
| `Sc47ae1` | base, help | Help | المساعدة |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | توحيد وحدات Hub |
| `S8ac724` | base, new | Import from .st files | الاستيراد من ملفات .st |
| `S1ed126` | base | Insight | التحليلات |
| `Sa7881c` | base, integrations | Integrations | التكاملات |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | ربط القديم بالجديد |
| `S3c1c8a` | base, new, st_new | Library Import | استيراد المكتبة |
| `S6e78c9` | base | Log out | تسجيل الخروج |
| `S3871af` | base | Lookups | القوائم المرجعية |
| `Sefd197` | base | Main navigation | التنقل الرئيسي |
| `S617eec` | base, mine | My Change Requests | طلبات التغيير الخاصة بي |
| `Sdbb388` | base | New Sandbox Code | رمز تجريبي جديد |
| `Sd85719` | base, form, list | New Status Code | رمز حالة جديد |
| `Se94865` | base, dashboard, notifications | Notices | الإشعارات |
| `Sa1fdaa` | base, operations | Operations | العمليات |
| `S8fa41d` | base, dashboard, list | Releases | الإصدارات |
| `Sf490d7` | base, review_checklist | Review Checklist | قائمة التحقق للمراجعة |
| `S437a0d` | base, review_queue | Review Queue | قائمة المراجعة |
| `Sc7f73b` | base, settings | Settings | الإعدادات |
| `Sbe504f` | base | Skip to main content | انتقل إلى المحتوى الرئيسي |
| `Sa42252` | base, stalled | Stalled Requests | الطلبات المتوقفة |
| `S7f5583` | base, list | Status Codes | رموز الحالة |
| `Sa4a761` | base, success_metrics | Success Metrics | مقاييس النجاح |
| `S1b9aeb` | base, dashboard | unread | غير مقروءة |
| `S57f2b1` | base | Users | المستخدمون |
| `Sd7a484` | base | Workflow | سير العمل |
| `S5a4692` | base | You are covering for a colleague | أنت تنوب عن زميل |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | لم يُعيَّن بعد |
| `Sbae7d5` | catalogue_health, detail, list | Status | الحالة |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | بانتظار موافقة المسؤول |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | بانتظار اعتماد كبير المهندسين |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | بانتظار الموافقة المشتركة بين المجالات |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | بانتظار موافقة المراجع |
| `S452d9f` | dashboard | Browse published and in-progress releases | تصفح الإصدارات المنشورة والجارية |
| `Scf72d4` | dashboard | Browse Status Codes | تصفح رموز الحالة |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | مسوداتي المتوقفة بانتظار موافقة مجال |
| `Se0688f` | dashboard | My Open Change Requests | طلبات التغيير المفتوحة الخاصة بي |
| `Sf949fb` | dashboard | Number ranges running out | نطاقات الأرقام على وشك النفاد |
| `S6605c0` | dashboard | Search and filter all governed status codes | البحث في جميع رموز الحالة الخاضعة للحوكمة وتصفيتها |
| `S916385` | dashboard | Stalled requests | الطلبات المتوقفة |
| `S074d62` | detail, role badge | Chief Engineer | كبير المهندسين |
| `S2fa1f7` | detail, form, list | Functional Subgroup | المجموعة الفرعية الوظيفية |
| `S816c52` | detail, export_verify, list | No | لا |
| `S483bf2` | detail, list | Published | منشور |
| `Se96390` | detail, list | Remove | إزالة |
| `Se246b6` | detail, form, list | Status Category | فئة الحالة |
| `S08e643` | detail, list | Target software version | إصدار البرنامج المستهدف |
| `S5397e0` | detail, export_verify, list | Yes | نعم |
| `S2da600` | export_center, list | Version | الإصدار |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | الاسم |
| `Sced1ce` | form, list | Functional System Group | مجموعة النظام الوظيفي |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | وحدة التحكم |
| `Sd7decf` | legacy_mapping, list | Filter | تصفية |
| `Sb7baa1` | legacy_mapping | Number | الرقم |
| `Sbce064` | legacy_mapping, list | Search | بحث |
| `Sc5fe02` | list | any | أي |
| `Sef5415` | list | Apply columns | تطبيق الأعمدة |
| `S9e895f` | list | Change sets | مجموعات التغيير |
| `Scf723c` | list | Columns | الأعمدة |
| `S759686` | list | Filter status codes | تصفية رموز الحالة |
| `Sfd327d` | list | Identifier, title, description | المعرّف أو العنوان أو الوصف |
| `S44d25b` | list | Items | العناصر |
| `S033df3` | list | Lifecycle | دورة الحياة |
| `Sb4cad6` | list | Link to this view | رابط لهذا العرض |
| `Se248d5` | list, new | New change set | مجموعة تغيير جديدة |
| `Se75aa1` | list, new | New Release | إصدار جديد |
| `Se5076c` | list | No change sets yet. | لا توجد مجموعات تغيير بعد. |
| `Sd32c03` | list | No releases yet. | لا توجد إصدارات بعد. |
| `Sc3af43` | list | No saved searches yet. | لا توجد عمليات بحث محفوظة. |
| `S0cb400` | list | No status codes match these filters. | لا توجد رموز حالة تطابق عوامل التصفية هذه. |
| `Sf7194e` | list | Requests | الطلبات |
| `S37a530` | list | result | نتيجة |
| `Scdf7e9` | list | results | نتائج |
| `S4f581e` | list | Sandbox only | التجريبية فقط |
| `S1db747` | list | Save search | حفظ البحث |
| `Sff86e9` | list | Save the current filters as | حفظ عوامل التصفية الحالية باسم |
| `Sed1d84` | list | Saved searches | عمليات البحث المحفوظة |
| `S20bff1` | list | Status codes | رموز الحالة |
| `Se90eb0` | list | Turbine Platform | منصة التوربين |
| `Sf7c400` | login | Log in | تسجيل الدخول |
| `S8be3c9` | login | Password | كلمة المرور |
| `S2c7ab3` | login | Username or email | اسم المستخدم أو البريد الإلكتروني |
| `S05fc94` | role badge | Engineer | مهندس |
| `S3c0e8a` | role badge | StCd Owner | مالك StCd |
| `Sdbad9f` | role badge | Viewer | مشاهد |

### 9.6 IN বাংলা 🇮🇳 — Bengali

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | স্তর |
| `S89b86a` | account_settings, base, detail | Language | ভাষা |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | প্রশাসক |
| `Sc452ad` | approval_queue, base | Approval Queue | অনুমোদন সারি |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | পর্যালোচক |
| `S85dfa3` | base | Account | অ্যাকাউন্ট |
| `Sb8be3d` | base | Administration | প্রশাসন |
| `S28dd75` | base | Audit Log | অডিট লগ |
| `Sa28e96` | base, catalogue_health | Catalogue Health | ক্যাটালগের স্বাস্থ্য |
| `S162a45` | base, list | Change Sets | পরিবর্তন সেট |
| `S532c86` | base | covering | প্রতিনিধি |
| `Sd87f47` | base, dashboard | Dashboard | ড্যাশবোর্ড |
| `S710ea3` | base, delegations | Delegation | প্রতিনিধিত্ব |
| `See833c` | base, export_center | Export Center | রপ্তানি কেন্দ্র |
| `S6f6f72` | base, export_profiles | Export Profiles | রপ্তানি প্রোফাইল |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ফ্লিট ফিডব্যাক |
| `Sc47ae1` | base, help | Help | সহায়তা |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | হাব একত্রীকরণ |
| `S8ac724` | base, new | Import from .st files | .st ফাইল থেকে আমদানি |
| `S1ed126` | base | Insight | বিশ্লেষণ |
| `Sa7881c` | base, integrations | Integrations | ইন্টিগ্রেশন |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | পুরোনো-নতুন ম্যাপিং |
| `S3c1c8a` | base, new, st_new | Library Import | লাইব্রেরি আমদানি |
| `S6e78c9` | base | Log out | লগ আউট |
| `S3871af` | base | Lookups | তালিকা |
| `Sefd197` | base | Main navigation | প্রধান নেভিগেশন |
| `S617eec` | base, mine | My Change Requests | আমার পরিবর্তনের অনুরোধ |
| `Sdbb388` | base | New Sandbox Code | নতুন স্যান্ডবক্স কোড |
| `Sd85719` | base, form, list | New Status Code | নতুন স্ট্যাটাস কোড |
| `Se94865` | base, dashboard, notifications | Notices | বিজ্ঞপ্তি |
| `Sa1fdaa` | base, operations | Operations | অপারেশন |
| `S8fa41d` | base, dashboard, list | Releases | রিলিজ |
| `Sf490d7` | base, review_checklist | Review Checklist | পর্যালোচনা চেকলিস্ট |
| `S437a0d` | base, review_queue | Review Queue | পর্যালোচনা সারি |
| `Sc7f73b` | base, settings | Settings | সেটিংস |
| `Sbe504f` | base | Skip to main content | মূল বিষয়বস্তুতে যান |
| `Sa42252` | base, stalled | Stalled Requests | আটকে থাকা অনুরোধ |
| `S7f5583` | base, list | Status Codes | স্ট্যাটাস কোড |
| `Sa4a761` | base, success_metrics | Success Metrics | সাফল্যের মাপকাঠি |
| `S1b9aeb` | base, dashboard | unread | অপঠিত |
| `S57f2b1` | base | Users | ব্যবহারকারী |
| `Sd7a484` | base | Workflow | কর্মপ্রবাহ |
| `S5a4692` | base | You are covering for a colleague | আপনি একজন সহকর্মীর জায়গায় কাজ করছেন |
| `Sbae7d5` | catalogue_health, detail, list | Status | অবস্থা |
| `S074d62` | detail, role badge | Chief Engineer | প্রধান প্রকৌশলী |
| `S816c52` | detail, export_verify, list | No | না |
| `Se96390` | detail, list | Remove | সরান |
| `S5397e0` | detail, export_verify, list | Yes | হ্যাঁ |
| `S2da600` | export_center, list | Version | সংস্করণ |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | নাম |
| `Sd7decf` | legacy_mapping, list | Filter | ফিল্টার |
| `Sbce064` | legacy_mapping, list | Search | অনুসন্ধান |
| `S20bff1` | list | Status codes | স্ট্যাটাস কোড |
| `Sf7c400` | login | Log in | লগ ইন |
| `S8be3c9` | login | Password | পাসওয়ার্ড |
| `S2c7ab3` | login | Username or email | ব্যবহারকারীর নাম বা ইমেল |
| `S05fc94` | role badge | Engineer | প্রকৌশলী |
| `S3c0e8a` | role badge | StCd Owner | StCd মালিক |
| `Sdbad9f` | role badge | Viewer | দর্শক |

### 9.7 IN मराठी 🇮🇳 — Marathi

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | पातळी |
| `S89b86a` | account_settings, base, detail | Language | भाषा |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | प्रशासक |
| `Sc452ad` | approval_queue, base | Approval Queue | मंजुरी रांग |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | पुनरावलोकक |
| `S85dfa3` | base | Account | खाते |
| `Sb8be3d` | base | Administration | प्रशासन |
| `S28dd75` | base | Audit Log | लेखापरीक्षण नोंद |
| `Sa28e96` | base, catalogue_health | Catalogue Health | कॅटलॉग आरोग्य |
| `S162a45` | base, list | Change Sets | बदल संच |
| `S532c86` | base | covering | बदली |
| `Sd87f47` | base, dashboard | Dashboard | डॅशबोर्ड |
| `S710ea3` | base, delegations | Delegation | प्रतिनिधीत्व |
| `See833c` | base, export_center | Export Center | निर्यात केंद्र |
| `S6f6f72` | base, export_profiles | Export Profiles | निर्यात प्रोफाइल |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | फ्लीट अभिप्राय |
| `Sc47ae1` | base, help | Help | मदत |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | हब एकत्रीकरण |
| `S8ac724` | base, new | Import from .st files | .st फाइलमधून आयात |
| `S1ed126` | base | Insight | विश्लेषण |
| `Sa7881c` | base, integrations | Integrations | एकत्रीकरणे |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | जुने-नवे मॅपिंग |
| `S3c1c8a` | base, new, st_new | Library Import | लायब्ररी आयात |
| `S6e78c9` | base | Log out | लॉग आउट |
| `S3871af` | base | Lookups | संदर्भ याद्या |
| `Sefd197` | base | Main navigation | मुख्य नेव्हिगेशन |
| `S617eec` | base, mine | My Change Requests | माझ्या बदल विनंत्या |
| `Sdbb388` | base | New Sandbox Code | नवीन सँडबॉक्स कोड |
| `Sd85719` | base, form, list | New Status Code | नवीन स्थिती कोड |
| `Se94865` | base, dashboard, notifications | Notices | सूचना |
| `Sa1fdaa` | base, operations | Operations | कार्यवाही |
| `S8fa41d` | base, dashboard, list | Releases | प्रकाशने |
| `Sf490d7` | base, review_checklist | Review Checklist | पुनरावलोकन तपासणी यादी |
| `S437a0d` | base, review_queue | Review Queue | पुनरावलोकन रांग |
| `Sc7f73b` | base, settings | Settings | सेटिंग्ज |
| `Sbe504f` | base | Skip to main content | मुख्य मजकुराकडे जा |
| `Sa42252` | base, stalled | Stalled Requests | रखडलेल्या विनंत्या |
| `S7f5583` | base, list | Status Codes | स्थिती कोड |
| `Sa4a761` | base, success_metrics | Success Metrics | यश मापदंड |
| `S1b9aeb` | base, dashboard | unread | न वाचलेले |
| `S57f2b1` | base | Users | वापरकर्ते |
| `Sd7a484` | base | Workflow | कार्यप्रवाह |
| `S5a4692` | base | You are covering for a colleague | तुम्ही सहकाऱ्याच्या जागी काम करत आहात |
| `Sbae7d5` | catalogue_health, detail, list | Status | स्थिती |
| `S074d62` | detail, role badge | Chief Engineer | मुख्य अभियंता |
| `S816c52` | detail, export_verify, list | No | नाही |
| `Se96390` | detail, list | Remove | काढा |
| `S5397e0` | detail, export_verify, list | Yes | होय |
| `S2da600` | export_center, list | Version | आवृत्ती |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | नाव |
| `Sd7decf` | legacy_mapping, list | Filter | फिल्टर |
| `Sbce064` | legacy_mapping, list | Search | शोध |
| `S20bff1` | list | Status codes | स्थिती कोड |
| `Sf7c400` | login | Log in | लॉग इन |
| `S8be3c9` | login | Password | पासवर्ड |
| `S2c7ab3` | login | Username or email | वापरकर्तानाव किंवा ईमेल |
| `S05fc94` | role badge | Engineer | अभियंता |
| `S3c0e8a` | role badge | StCd Owner | StCd मालक |
| `Sdbad9f` | role badge | Viewer | दर्शक |

### 9.8 IN తెలుగు 🇮🇳 — Telugu

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | స్థాయి |
| `S89b86a` | account_settings, base, detail | Language | భాష |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | నిర్వాహకుడు |
| `Sc452ad` | approval_queue, base | Approval Queue | ఆమోద క్యూ |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | సమీక్షకుడు |
| `S85dfa3` | base | Account | ఖాతా |
| `Sb8be3d` | base | Administration | పరిపాలన |
| `S28dd75` | base | Audit Log | ఆడిట్ లాగ్ |
| `Sa28e96` | base, catalogue_health | Catalogue Health | కేటలాగ్ ఆరోగ్యం |
| `S162a45` | base, list | Change Sets | మార్పు సెట్‌లు |
| `S532c86` | base | covering | బదులుగా |
| `Sd87f47` | base, dashboard | Dashboard | డ్యాష్‌బోర్డ్ |
| `S710ea3` | base, delegations | Delegation | ప్రతినిధి బాధ్యత |
| `See833c` | base, export_center | Export Center | ఎగుమతి కేంద్రం |
| `S6f6f72` | base, export_profiles | Export Profiles | ఎగుమతి ప్రొఫైల్‌లు |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ఫ్లీట్ అభిప్రాయం |
| `Sc47ae1` | base, help | Help | సహాయం |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | హబ్ ఏకీకరణ |
| `S8ac724` | base, new | Import from .st files | .st ఫైళ్ల నుండి దిగుమతి |
| `S1ed126` | base | Insight | విశ్లేషణ |
| `Sa7881c` | base, integrations | Integrations | ఇంటిగ్రేషన్‌లు |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | పాత-కొత్త మ్యాపింగ్ |
| `S3c1c8a` | base, new, st_new | Library Import | లైబ్రరీ దిగుమతి |
| `S6e78c9` | base | Log out | లాగ్ అవుట్ |
| `S3871af` | base | Lookups | లుకప్‌లు |
| `Sefd197` | base | Main navigation | ప్రధాన నావిగేషన్ |
| `S617eec` | base, mine | My Change Requests | నా మార్పు అభ్యర్థనలు |
| `Sdbb388` | base | New Sandbox Code | కొత్త శాండ్‌బాక్స్ కోడ్ |
| `Sd85719` | base, form, list | New Status Code | కొత్త స్థితి కోడ్ |
| `Se94865` | base, dashboard, notifications | Notices | నోటీసులు |
| `Sa1fdaa` | base, operations | Operations | కార్యకలాపాలు |
| `S8fa41d` | base, dashboard, list | Releases | విడుదలలు |
| `Sf490d7` | base, review_checklist | Review Checklist | సమీక్ష చెక్‌లిస్ట్ |
| `S437a0d` | base, review_queue | Review Queue | సమీక్ష క్యూ |
| `Sc7f73b` | base, settings | Settings | సెట్టింగ్‌లు |
| `Sbe504f` | base | Skip to main content | ప్రధాన కంటెంట్‌కు వెళ్లండి |
| `Sa42252` | base, stalled | Stalled Requests | నిలిచిపోయిన అభ్యర్థనలు |
| `S7f5583` | base, list | Status Codes | స్థితి కోడ్‌లు |
| `Sa4a761` | base, success_metrics | Success Metrics | విజయ కొలమానాలు |
| `S1b9aeb` | base, dashboard | unread | చదవనివి |
| `S57f2b1` | base | Users | వినియోగదారులు |
| `Sd7a484` | base | Workflow | వర్క్‌ఫ్లో |
| `S5a4692` | base | You are covering for a colleague | మీరు ఒక సహోద్యోగి స్థానంలో పనిచేస్తున్నారు |
| `Sbae7d5` | catalogue_health, detail, list | Status | స్థితి |
| `S074d62` | detail, role badge | Chief Engineer | చీఫ్ ఇంజనీర్ |
| `S816c52` | detail, export_verify, list | No | కాదు |
| `Se96390` | detail, list | Remove | తొలగించు |
| `S5397e0` | detail, export_verify, list | Yes | అవును |
| `S2da600` | export_center, list | Version | వెర్షన్ |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | పేరు |
| `Sd7decf` | legacy_mapping, list | Filter | ఫిల్టర్ |
| `Sbce064` | legacy_mapping, list | Search | శోధన |
| `S20bff1` | list | Status codes | స్థితి కోడ్‌లు |
| `Sf7c400` | login | Log in | లాగిన్ |
| `S8be3c9` | login | Password | పాస్‌వర్డ్ |
| `S2c7ab3` | login | Username or email | వినియోగదారు పేరు లేదా ఇమెయిల్ |
| `S05fc94` | role badge | Engineer | ఇంజనీర్ |
| `S3c0e8a` | role badge | StCd Owner | StCd యజమాని |
| `Sdbad9f` | role badge | Viewer | వీక్షకుడు |

### 9.9 IN தமிழ் 🇮🇳 — Tamil

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | நிலை |
| `S89b86a` | account_settings, base, detail | Language | மொழி |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | நிர்வாகி |
| `Sc452ad` | approval_queue, base | Approval Queue | ஒப்புதல் வரிசை |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | மதிப்பாய்வாளர் |
| `S85dfa3` | base | Account | கணக்கு |
| `Sb8be3d` | base | Administration | நிர்வாகம் |
| `S28dd75` | base | Audit Log | தணிக்கைப் பதிவு |
| `Sa28e96` | base, catalogue_health | Catalogue Health | பட்டியல் நலம் |
| `S162a45` | base, list | Change Sets | மாற்றத் தொகுப்புகள் |
| `S532c86` | base | covering | மாற்றாக |
| `Sd87f47` | base, dashboard | Dashboard | டாஷ்போர்டு |
| `S710ea3` | base, delegations | Delegation | பிரதிநிதித்துவம் |
| `See833c` | base, export_center | Export Center | ஏற்றுமதி மையம் |
| `S6f6f72` | base, export_profiles | Export Profiles | ஏற்றுமதி சுயவிவரங்கள் |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | கடற்படை கருத்து |
| `Sc47ae1` | base, help | Help | உதவி |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | ஹப் ஒருங்கிணைப்பு |
| `S8ac724` | base, new | Import from .st files | .st கோப்புகளிலிருந்து இறக்குமதி |
| `S1ed126` | base | Insight | நுண்ணறிவு |
| `Sa7881c` | base, integrations | Integrations | ஒருங்கிணைப்புகள் |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | பழைய-புதிய இணைப்பு |
| `S3c1c8a` | base, new, st_new | Library Import | நூலக இறக்குமதி |
| `S6e78c9` | base | Log out | வெளியேறு |
| `S3871af` | base | Lookups | தேடல் பட்டியல்கள் |
| `Sefd197` | base | Main navigation | முதன்மை வழிசெலுத்தல் |
| `S617eec` | base, mine | My Change Requests | எனது மாற்றக் கோரிக்கைகள் |
| `Sdbb388` | base | New Sandbox Code | புதிய சாண்ட்பாக்ஸ் குறியீடு |
| `Sd85719` | base, form, list | New Status Code | புதிய நிலைக் குறியீடு |
| `Se94865` | base, dashboard, notifications | Notices | அறிவிப்புகள் |
| `Sa1fdaa` | base, operations | Operations | செயல்பாடுகள் |
| `S8fa41d` | base, dashboard, list | Releases | வெளியீடுகள் |
| `Sf490d7` | base, review_checklist | Review Checklist | மதிப்பாய்வு சரிபார்ப்புப் பட்டியல் |
| `S437a0d` | base, review_queue | Review Queue | மதிப்பாய்வு வரிசை |
| `Sc7f73b` | base, settings | Settings | அமைப்புகள் |
| `Sbe504f` | base | Skip to main content | முதன்மை உள்ளடக்கத்திற்குச் செல் |
| `Sa42252` | base, stalled | Stalled Requests | நிறுத்தப்பட்ட கோரிக்கைகள் |
| `S7f5583` | base, list | Status Codes | நிலைக் குறியீடுகள் |
| `Sa4a761` | base, success_metrics | Success Metrics | வெற்றி அளவீடுகள் |
| `S1b9aeb` | base, dashboard | unread | படிக்காதவை |
| `S57f2b1` | base | Users | பயனர்கள் |
| `Sd7a484` | base | Workflow | பணிப்பாய்வு |
| `S5a4692` | base | You are covering for a colleague | நீங்கள் ஒரு சக ஊழியருக்குப் பதிலாகச் செயல்படுகிறீர்கள் |
| `Sbae7d5` | catalogue_health, detail, list | Status | நிலை |
| `S074d62` | detail, role badge | Chief Engineer | தலைமைப் பொறியாளர் |
| `S816c52` | detail, export_verify, list | No | இல்லை |
| `Se96390` | detail, list | Remove | அகற்று |
| `S5397e0` | detail, export_verify, list | Yes | ஆம் |
| `S2da600` | export_center, list | Version | பதிப்பு |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | பெயர் |
| `Sd7decf` | legacy_mapping, list | Filter | வடிகட்டு |
| `Sbce064` | legacy_mapping, list | Search | தேடு |
| `S20bff1` | list | Status codes | நிலைக் குறியீடுகள் |
| `Sf7c400` | login | Log in | உள்நுழை |
| `S8be3c9` | login | Password | கடவுச்சொல் |
| `S2c7ab3` | login | Username or email | பயனர்பெயர் அல்லது மின்னஞ்சல் |
| `S05fc94` | role badge | Engineer | பொறியாளர் |
| `S3c0e8a` | role badge | StCd Owner | StCd உரிமையாளர் |
| `Sdbad9f` | role badge | Viewer | பார்வையாளர் |

### 9.10 IN ગુજરાતી 🇮🇳 — Gujarati

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | સ્તર |
| `S89b86a` | account_settings, base, detail | Language | ભાષા |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | સંચાલક |
| `Sc452ad` | approval_queue, base | Approval Queue | મંજૂરી કતાર |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | સમીક્ષક |
| `S85dfa3` | base | Account | ખાતું |
| `Sb8be3d` | base | Administration | વહીવટ |
| `S28dd75` | base | Audit Log | ઓડિટ લોગ |
| `Sa28e96` | base, catalogue_health | Catalogue Health | કેટલોગ આરોગ્ય |
| `S162a45` | base, list | Change Sets | ફેરફાર સમૂહો |
| `S532c86` | base | covering | બદલે |
| `Sd87f47` | base, dashboard | Dashboard | ડેશબોર્ડ |
| `S710ea3` | base, delegations | Delegation | પ્રતિનિધિત્વ |
| `See833c` | base, export_center | Export Center | નિકાસ કેન્દ્ર |
| `S6f6f72` | base, export_profiles | Export Profiles | નિકાસ પ્રોફાઇલ |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ફ્લીટ પ્રતિસાદ |
| `Sc47ae1` | base, help | Help | સહાય |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | હબ એકીકરણ |
| `S8ac724` | base, new | Import from .st files | .st ફાઇલોમાંથી આયાત |
| `S1ed126` | base | Insight | વિશ્લેષણ |
| `Sa7881c` | base, integrations | Integrations | સંકલન |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | જૂનું-નવું મેપિંગ |
| `S3c1c8a` | base, new, st_new | Library Import | લાઇબ્રેરી આયાત |
| `S6e78c9` | base | Log out | લૉગ આઉટ |
| `S3871af` | base | Lookups | સંદર્ભ યાદીઓ |
| `Sefd197` | base | Main navigation | મુખ્ય નેવિગેશન |
| `S617eec` | base, mine | My Change Requests | મારી ફેરફાર વિનંતીઓ |
| `Sdbb388` | base | New Sandbox Code | નવો સેન્ડબોક્સ કોડ |
| `Sd85719` | base, form, list | New Status Code | નવો સ્ટેટસ કોડ |
| `Se94865` | base, dashboard, notifications | Notices | સૂચનાઓ |
| `Sa1fdaa` | base, operations | Operations | કામગીરી |
| `S8fa41d` | base, dashboard, list | Releases | રિલીઝ |
| `Sf490d7` | base, review_checklist | Review Checklist | સમીક્ષા ચેકલિસ્ટ |
| `S437a0d` | base, review_queue | Review Queue | સમીક્ષા કતાર |
| `Sc7f73b` | base, settings | Settings | સેટિંગ્સ |
| `Sbe504f` | base | Skip to main content | મુખ્ય સામગ્રી પર જાઓ |
| `Sa42252` | base, stalled | Stalled Requests | અટકેલી વિનંતીઓ |
| `S7f5583` | base, list | Status Codes | સ્ટેટસ કોડ |
| `Sa4a761` | base, success_metrics | Success Metrics | સફળતા માપદંડ |
| `S1b9aeb` | base, dashboard | unread | વણવાંચેલા |
| `S57f2b1` | base | Users | વપરાશકર્તાઓ |
| `Sd7a484` | base | Workflow | કાર્યપ્રવાહ |
| `S5a4692` | base | You are covering for a colleague | તમે એક સહકર્મીની જગ્યાએ કામ કરી રહ્યા છો |
| `Sbae7d5` | catalogue_health, detail, list | Status | સ્થિતિ |
| `S074d62` | detail, role badge | Chief Engineer | મુખ્ય ઇજનેર |
| `S816c52` | detail, export_verify, list | No | ના |
| `Se96390` | detail, list | Remove | દૂર કરો |
| `S5397e0` | detail, export_verify, list | Yes | હા |
| `S2da600` | export_center, list | Version | આવૃત્તિ |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | નામ |
| `Sd7decf` | legacy_mapping, list | Filter | ફિલ્ટર |
| `Sbce064` | legacy_mapping, list | Search | શોધ |
| `S20bff1` | list | Status codes | સ્ટેટસ કોડ |
| `Sf7c400` | login | Log in | લૉગ ઇન |
| `S8be3c9` | login | Password | પાસવર્ડ |
| `S2c7ab3` | login | Username or email | વપરાશકર્તા નામ અથવા ઇમેઇલ |
| `S05fc94` | role badge | Engineer | ઇજનેર |
| `S3c0e8a` | role badge | StCd Owner | StCd માલિક |
| `Sdbad9f` | role badge | Viewer | દર્શક |

### 9.11 PK اردو 🇵🇰 — Urdu

59 of 772 strings translated; direction right to left.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | سطح |
| `S89b86a` | account_settings, base, detail | Language | زبان |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | منتظم |
| `Sc452ad` | approval_queue, base | Approval Queue | منظوری قطار |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | جائزہ کار |
| `S85dfa3` | base | Account | اکاؤنٹ |
| `Sb8be3d` | base | Administration | انتظامیہ |
| `S28dd75` | base | Audit Log | آڈٹ لاگ |
| `Sa28e96` | base, catalogue_health | Catalogue Health | کیٹلاگ کی صحت |
| `S162a45` | base, list | Change Sets | تبدیلی سیٹس |
| `S532c86` | base | covering | نیابت |
| `Sd87f47` | base, dashboard | Dashboard | ڈیش بورڈ |
| `S710ea3` | base, delegations | Delegation | تفویض |
| `See833c` | base, export_center | Export Center | برآمد مرکز |
| `S6f6f72` | base, export_profiles | Export Profiles | برآمدی پروفائلز |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | فلیٹ فیڈ بیک |
| `Sc47ae1` | base, help | Help | مدد |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | ہب کا انضمام |
| `S8ac724` | base, new | Import from .st files | .st فائلوں سے درآمد |
| `S1ed126` | base | Insight | تجزیہ |
| `Sa7881c` | base, integrations | Integrations | انضمامات |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | پرانے-نئے کی میپنگ |
| `S3c1c8a` | base, new, st_new | Library Import | لائبریری درآمد |
| `S6e78c9` | base | Log out | لاگ آؤٹ |
| `S3871af` | base | Lookups | حوالہ جاتی فہرستیں |
| `Sefd197` | base | Main navigation | مرکزی نیویگیشن |
| `S617eec` | base, mine | My Change Requests | میری تبدیلی کی درخواستیں |
| `Sdbb388` | base | New Sandbox Code | نیا سینڈ باکس کوڈ |
| `Sd85719` | base, form, list | New Status Code | نیا اسٹیٹس کوڈ |
| `Se94865` | base, dashboard, notifications | Notices | اطلاعات |
| `Sa1fdaa` | base, operations | Operations | آپریشنز |
| `S8fa41d` | base, dashboard, list | Releases | ریلیزز |
| `Sf490d7` | base, review_checklist | Review Checklist | جائزہ چیک لسٹ |
| `S437a0d` | base, review_queue | Review Queue | جائزہ قطار |
| `Sc7f73b` | base, settings | Settings | ترتیبات |
| `Sbe504f` | base | Skip to main content | مرکزی مواد پر جائیں |
| `Sa42252` | base, stalled | Stalled Requests | رکی ہوئی درخواستیں |
| `S7f5583` | base, list | Status Codes | اسٹیٹس کوڈز |
| `Sa4a761` | base, success_metrics | Success Metrics | کامیابی کے پیمانے |
| `S1b9aeb` | base, dashboard | unread | غیر پڑھے ہوئے |
| `S57f2b1` | base | Users | صارفین |
| `Sd7a484` | base | Workflow | ورک فلو |
| `S5a4692` | base | You are covering for a colleague | آپ ایک ساتھی کی جگہ کام کر رہے ہیں |
| `Sbae7d5` | catalogue_health, detail, list | Status | حالت |
| `S074d62` | detail, role badge | Chief Engineer | چیف انجینئر |
| `S816c52` | detail, export_verify, list | No | نہیں |
| `Se96390` | detail, list | Remove | ہٹائیں |
| `S5397e0` | detail, export_verify, list | Yes | ہاں |
| `S2da600` | export_center, list | Version | ورژن |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | نام |
| `Sd7decf` | legacy_mapping, list | Filter | فلٹر |
| `Sbce064` | legacy_mapping, list | Search | تلاش |
| `S20bff1` | list | Status codes | اسٹیٹس کوڈز |
| `Sf7c400` | login | Log in | لاگ ان |
| `S8be3c9` | login | Password | پاس ورڈ |
| `S2c7ab3` | login | Username or email | صارف نام یا ای میل |
| `S05fc94` | role badge | Engineer | انجینئر |
| `S3c0e8a` | role badge | StCd Owner | StCd مالک |
| `Sdbad9f` | role badge | Viewer | ناظر |

### 9.12 IN ಕನ್ನಡ 🇮🇳 — Kannada

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | ಮಟ್ಟ |
| `S89b86a` | account_settings, base, detail | Language | ಭಾಷೆ |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | ನಿರ್ವಾಹಕ |
| `Sc452ad` | approval_queue, base | Approval Queue | ಅನುಮೋದನೆ ಸರತಿ |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | ಪರಿಶೀಲಕ |
| `S85dfa3` | base | Account | ಖಾತೆ |
| `Sb8be3d` | base | Administration | ಆಡಳಿತ |
| `S28dd75` | base | Audit Log | ಲೆಕ್ಕಪರಿಶೋಧನಾ ಲಾಗ್ |
| `Sa28e96` | base, catalogue_health | Catalogue Health | ಕ್ಯಾಟಲಾಗ್ ಆರೋಗ್ಯ |
| `S162a45` | base, list | Change Sets | ಬದಲಾವಣೆ ಸೆಟ್‌ಗಳು |
| `S532c86` | base | covering | ಬದಲಿ |
| `Sd87f47` | base, dashboard | Dashboard | ಡ್ಯಾಶ್‌ಬೋರ್ಡ್ |
| `S710ea3` | base, delegations | Delegation | ನಿಯೋಜನೆ |
| `See833c` | base, export_center | Export Center | ರಫ್ತು ಕೇಂದ್ರ |
| `S6f6f72` | base, export_profiles | Export Profiles | ರಫ್ತು ಪ್ರೊಫೈಲ್‌ಗಳು |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ಫ್ಲೀಟ್ ಪ್ರತಿಕ್ರಿಯೆ |
| `Sc47ae1` | base, help | Help | ಸಹಾಯ |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | ಹಬ್ ಏಕೀಕರಣ |
| `S8ac724` | base, new | Import from .st files | .st ಫೈಲ್‌ಗಳಿಂದ ಆಮದು |
| `S1ed126` | base | Insight | ವಿಶ್ಲೇಷಣೆ |
| `Sa7881c` | base, integrations | Integrations | ಇಂಟಿಗ್ರೇಶನ್‌ಗಳು |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | ಹಳೆಯ-ಹೊಸ ಮ್ಯಾಪಿಂಗ್ |
| `S3c1c8a` | base, new, st_new | Library Import | ಲೈಬ್ರರಿ ಆಮದು |
| `S6e78c9` | base | Log out | ಲಾಗ್ ಔಟ್ |
| `S3871af` | base | Lookups | ಉಲ್ಲೇಖ ಪಟ್ಟಿಗಳು |
| `Sefd197` | base | Main navigation | ಮುಖ್ಯ ನ್ಯಾವಿಗೇಶನ್ |
| `S617eec` | base, mine | My Change Requests | ನನ್ನ ಬದಲಾವಣೆ ವಿನಂತಿಗಳು |
| `Sdbb388` | base | New Sandbox Code | ಹೊಸ ಸ್ಯಾಂಡ್‌ಬಾಕ್ಸ್ ಕೋಡ್ |
| `Sd85719` | base, form, list | New Status Code | ಹೊಸ ಸ್ಥಿತಿ ಕೋಡ್ |
| `Se94865` | base, dashboard, notifications | Notices | ಸೂಚನೆಗಳು |
| `Sa1fdaa` | base, operations | Operations | ಕಾರ್ಯಾಚರಣೆಗಳು |
| `S8fa41d` | base, dashboard, list | Releases | ಬಿಡುಗಡೆಗಳು |
| `Sf490d7` | base, review_checklist | Review Checklist | ಪರಿಶೀಲನೆ ಚೆಕ್‌ಲಿಸ್ಟ್ |
| `S437a0d` | base, review_queue | Review Queue | ಪರಿಶೀಲನೆ ಸರತಿ |
| `Sc7f73b` | base, settings | Settings | ಸೆಟ್ಟಿಂಗ್‌ಗಳು |
| `Sbe504f` | base | Skip to main content | ಮುಖ್ಯ ವಿಷಯಕ್ಕೆ ಹೋಗಿ |
| `Sa42252` | base, stalled | Stalled Requests | ನಿಂತುಹೋದ ವಿನಂತಿಗಳು |
| `S7f5583` | base, list | Status Codes | ಸ್ಥಿತಿ ಕೋಡ್‌ಗಳು |
| `Sa4a761` | base, success_metrics | Success Metrics | ಯಶಸ್ಸಿನ ಮಾಪನಗಳು |
| `S1b9aeb` | base, dashboard | unread | ಓದದಿರುವ |
| `S57f2b1` | base | Users | ಬಳಕೆದಾರರು |
| `Sd7a484` | base | Workflow | ವರ್ಕ್‌ಫ್ಲೋ |
| `S5a4692` | base | You are covering for a colleague | ನೀವು ಸಹೋದ್ಯೋಗಿಯ ಬದಲಿಗೆ ಕೆಲಸ ಮಾಡುತ್ತಿದ್ದೀರಿ |
| `Sbae7d5` | catalogue_health, detail, list | Status | ಸ್ಥಿತಿ |
| `S074d62` | detail, role badge | Chief Engineer | ಮುಖ್ಯ ಎಂಜಿನಿಯರ್ |
| `S816c52` | detail, export_verify, list | No | ಇಲ್ಲ |
| `Se96390` | detail, list | Remove | ತೆಗೆದುಹಾಕಿ |
| `S5397e0` | detail, export_verify, list | Yes | ಹೌದು |
| `S2da600` | export_center, list | Version | ಆವೃತ್ತಿ |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | ಹೆಸರು |
| `Sd7decf` | legacy_mapping, list | Filter | ಫಿಲ್ಟರ್ |
| `Sbce064` | legacy_mapping, list | Search | ಹುಡುಕಿ |
| `S20bff1` | list | Status codes | ಸ್ಥಿತಿ ಕೋಡ್‌ಗಳು |
| `Sf7c400` | login | Log in | ಲಾಗ್ ಇನ್ |
| `S8be3c9` | login | Password | ಪಾಸ್‌ವರ್ಡ್ |
| `S2c7ab3` | login | Username or email | ಬಳಕೆದಾರ ಹೆಸರು ಅಥವಾ ಇಮೇಲ್ |
| `S05fc94` | role badge | Engineer | ಎಂಜಿನಿಯರ್ |
| `S3c0e8a` | role badge | StCd Owner | StCd ಮಾಲೀಕ |
| `Sdbad9f` | role badge | Viewer | ವೀಕ್ಷಕ |

### 9.13 IN ଓଡ଼ିଆ 🇮🇳 — Odia

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | ସ୍ତର |
| `S89b86a` | account_settings, base, detail | Language | ଭାଷା |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | ପ୍ରଶାସକ |
| `Sc452ad` | approval_queue, base | Approval Queue | ଅନୁମୋଦନ ଧାଡ଼ି |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | ସମୀକ୍ଷକ |
| `S85dfa3` | base | Account | ଖାତା |
| `Sb8be3d` | base | Administration | ପ୍ରଶାସନ |
| `S28dd75` | base | Audit Log | ଅଡିଟ୍ ଲଗ୍ |
| `Sa28e96` | base, catalogue_health | Catalogue Health | କାଟାଲଗ୍ ସ୍ୱାସ୍ଥ୍ୟ |
| `S162a45` | base, list | Change Sets | ପରିବର୍ତ୍ତନ ସେଟ୍ |
| `S532c86` | base | covering | ବଦଳରେ |
| `Sd87f47` | base, dashboard | Dashboard | ଡ୍ୟାସବୋର୍ଡ |
| `S710ea3` | base, delegations | Delegation | ପ୍ରତିନିଧିତ୍ୱ |
| `See833c` | base, export_center | Export Center | ରପ୍ତାନି କେନ୍ଦ୍ର |
| `S6f6f72` | base, export_profiles | Export Profiles | ରପ୍ତାନି ପ୍ରୋଫାଇଲ୍ |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ଫ୍ଲିଟ୍ ମତାମତ |
| `Sc47ae1` | base, help | Help | ସହାୟତା |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | ହବ୍ ଏକୀକରଣ |
| `S8ac724` | base, new | Import from .st files | .st ଫାଇଲରୁ ଆମଦାନି |
| `S1ed126` | base | Insight | ବିଶ୍ଳେଷଣ |
| `Sa7881c` | base, integrations | Integrations | ଇଣ୍ଟିଗ୍ରେସନ୍ |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | ପୁରୁଣା-ନୂଆ ମ୍ୟାପିଂ |
| `S3c1c8a` | base, new, st_new | Library Import | ଲାଇବ୍ରେରୀ ଆମଦାନି |
| `S6e78c9` | base | Log out | ଲଗ୍ ଆଉଟ୍ |
| `S3871af` | base | Lookups | ସନ୍ଦର୍ଭ ତାଲିକା |
| `Sefd197` | base | Main navigation | ମୁଖ୍ୟ ନାଭିଗେସନ୍ |
| `S617eec` | base, mine | My Change Requests | ମୋ ପରିବର୍ତ୍ତନ ଅନୁରୋଧ |
| `Sdbb388` | base | New Sandbox Code | ନୂଆ ସାଣ୍ଡବକ୍ସ କୋଡ୍ |
| `Sd85719` | base, form, list | New Status Code | ନୂଆ ଅବସ୍ଥା କୋଡ୍ |
| `Se94865` | base, dashboard, notifications | Notices | ବିଜ୍ଞପ୍ତି |
| `Sa1fdaa` | base, operations | Operations | କାର୍ଯ୍ୟ |
| `S8fa41d` | base, dashboard, list | Releases | ପ୍ରକାଶନ |
| `Sf490d7` | base, review_checklist | Review Checklist | ସମୀକ୍ଷା ଚେକଲିଷ୍ଟ |
| `S437a0d` | base, review_queue | Review Queue | ସମୀକ୍ଷା ଧାଡ଼ି |
| `Sc7f73b` | base, settings | Settings | ସେଟିଂସ୍ |
| `Sbe504f` | base | Skip to main content | ମୁଖ୍ୟ ବିଷୟବସ୍ତୁକୁ ଯାଆନ୍ତୁ |
| `Sa42252` | base, stalled | Stalled Requests | ଅଟକି ଯାଇଥିବା ଅନୁରୋଧ |
| `S7f5583` | base, list | Status Codes | ଅବସ୍ଥା କୋଡ୍ |
| `Sa4a761` | base, success_metrics | Success Metrics | ସଫଳତା ମାପକ |
| `S1b9aeb` | base, dashboard | unread | ଅପଠିତ |
| `S57f2b1` | base | Users | ବ୍ୟବହାରକାରୀ |
| `Sd7a484` | base | Workflow | କାର୍ଯ୍ୟପ୍ରବାହ |
| `S5a4692` | base | You are covering for a colleague | ଆପଣ ଜଣେ ସହକର୍ମୀଙ୍କ ବଦଳରେ କାମ କରୁଛନ୍ତି |
| `Sbae7d5` | catalogue_health, detail, list | Status | ଅବସ୍ଥା |
| `S074d62` | detail, role badge | Chief Engineer | ମୁଖ୍ୟ ଇଞ୍ଜିନିୟର |
| `S816c52` | detail, export_verify, list | No | ନା |
| `Se96390` | detail, list | Remove | ହଟାନ୍ତୁ |
| `S5397e0` | detail, export_verify, list | Yes | ହଁ |
| `S2da600` | export_center, list | Version | ସଂସ୍କରଣ |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | ନାମ |
| `Sd7decf` | legacy_mapping, list | Filter | ଫିଲ୍ଟର୍ |
| `Sbce064` | legacy_mapping, list | Search | ସନ୍ଧାନ |
| `S20bff1` | list | Status codes | ଅବସ୍ଥା କୋଡ୍ |
| `Sf7c400` | login | Log in | ଲଗ୍ ଇନ୍ |
| `S8be3c9` | login | Password | ପାସୱାର୍ଡ |
| `S2c7ab3` | login | Username or email | ଉପଯୋଗକର୍ତ୍ତା ନାମ କିମ୍ବା ଇମେଲ୍ |
| `S05fc94` | role badge | Engineer | ଇଞ୍ଜିନିୟର |
| `S3c0e8a` | role badge | StCd Owner | StCd ମାଲିକ |
| `Sdbad9f` | role badge | Viewer | ଦର୍ଶକ |

### 9.14 IN മലയാളം 🇮🇳 — Malayalam

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | നില |
| `S89b86a` | account_settings, base, detail | Language | ഭാഷ |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | അഡ്മിനിസ്ട്രേറ്റർ |
| `Sc452ad` | approval_queue, base | Approval Queue | അംഗീകാര ക്യൂ |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | അവലോകകൻ |
| `S85dfa3` | base | Account | അക്കൗണ്ട് |
| `Sb8be3d` | base | Administration | ഭരണം |
| `S28dd75` | base | Audit Log | ഓഡിറ്റ് ലോഗ് |
| `Sa28e96` | base, catalogue_health | Catalogue Health | കാറ്റലോഗ് ആരോഗ്യം |
| `S162a45` | base, list | Change Sets | മാറ്റ സെറ്റുകൾ |
| `S532c86` | base | covering | പകരം |
| `Sd87f47` | base, dashboard | Dashboard | ഡാഷ്ബോർഡ് |
| `S710ea3` | base, delegations | Delegation | ചുമതല കൈമാറ്റം |
| `See833c` | base, export_center | Export Center | കയറ്റുമതി കേന്ദ്രം |
| `S6f6f72` | base, export_profiles | Export Profiles | കയറ്റുമതി പ്രൊഫൈലുകൾ |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ഫ്ലീറ്റ് പ്രതികരണം |
| `Sc47ae1` | base, help | Help | സഹായം |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | ഹബ് ഏകീകരണം |
| `S8ac724` | base, new | Import from .st files | .st ഫയലുകളിൽ നിന്ന് ഇറക്കുമതി |
| `S1ed126` | base | Insight | വിശകലനം |
| `Sa7881c` | base, integrations | Integrations | സംയോജനങ്ങൾ |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | പഴയത്-പുതിയത് മാപ്പിംഗ് |
| `S3c1c8a` | base, new, st_new | Library Import | ലൈബ്രറി ഇറക്കുമതി |
| `S6e78c9` | base | Log out | ലോഗ് ഔട്ട് |
| `S3871af` | base | Lookups | റഫറൻസ് പട്ടികകൾ |
| `Sefd197` | base | Main navigation | പ്രധാന നാവിഗേഷൻ |
| `S617eec` | base, mine | My Change Requests | എന്റെ മാറ്റ അഭ്യർത്ഥനകൾ |
| `Sdbb388` | base | New Sandbox Code | പുതിയ സാൻഡ്ബോക്സ് കോഡ് |
| `Sd85719` | base, form, list | New Status Code | പുതിയ സ്റ്റാറ്റസ് കോഡ് |
| `Se94865` | base, dashboard, notifications | Notices | അറിയിപ്പുകൾ |
| `Sa1fdaa` | base, operations | Operations | പ്രവർത്തനങ്ങൾ |
| `S8fa41d` | base, dashboard, list | Releases | റിലീസുകൾ |
| `Sf490d7` | base, review_checklist | Review Checklist | അവലോകന ചെക്ക്‌ലിസ്റ്റ് |
| `S437a0d` | base, review_queue | Review Queue | അവലോകന ക്യൂ |
| `Sc7f73b` | base, settings | Settings | ക്രമീകരണങ്ങൾ |
| `Sbe504f` | base | Skip to main content | പ്രധാന ഉള്ളടക്കത്തിലേക്ക് പോകുക |
| `Sa42252` | base, stalled | Stalled Requests | തടസ്സപ്പെട്ട അഭ്യർത്ഥനകൾ |
| `S7f5583` | base, list | Status Codes | സ്റ്റാറ്റസ് കോഡുകൾ |
| `Sa4a761` | base, success_metrics | Success Metrics | വിജയ മാനദണ്ഡങ്ങൾ |
| `S1b9aeb` | base, dashboard | unread | വായിക്കാത്തവ |
| `S57f2b1` | base | Users | ഉപയോക്താക്കൾ |
| `Sd7a484` | base | Workflow | വർക്ക്ഫ്ലോ |
| `S5a4692` | base | You are covering for a colleague | നിങ്ങൾ ഒരു സഹപ്രവർത്തകനു പകരം പ്രവർത്തിക്കുന്നു |
| `Sbae7d5` | catalogue_health, detail, list | Status | നില |
| `S074d62` | detail, role badge | Chief Engineer | ചീഫ് എൻജിനീയർ |
| `S816c52` | detail, export_verify, list | No | ഇല്ല |
| `Se96390` | detail, list | Remove | നീക്കം ചെയ്യുക |
| `S5397e0` | detail, export_verify, list | Yes | അതെ |
| `S2da600` | export_center, list | Version | പതിപ്പ് |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | പേര് |
| `Sd7decf` | legacy_mapping, list | Filter | ഫിൽട്ടർ |
| `Sbce064` | legacy_mapping, list | Search | തിരയുക |
| `S20bff1` | list | Status codes | സ്റ്റാറ്റസ് കോഡുകൾ |
| `Sf7c400` | login | Log in | ലോഗിൻ |
| `S8be3c9` | login | Password | പാസ്‌വേഡ് |
| `S2c7ab3` | login | Username or email | ഉപയോക്തൃനാമം അല്ലെങ്കിൽ ഇമെയിൽ |
| `S05fc94` | role badge | Engineer | എൻജിനീയർ |
| `S3c0e8a` | role badge | StCd Owner | StCd ഉടമ |
| `Sdbad9f` | role badge | Viewer | കാഴ്ചക്കാരൻ |

### 9.15 IN ਪੰਜਾਬੀ 🇮🇳 — Punjabi

59 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sad60c5` | _role | level | ਪੱਧਰ |
| `S89b86a` | account_settings, base, detail | Language | ਭਾਸ਼ਾ |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | ਪ੍ਰਸ਼ਾਸਕ |
| `Sc452ad` | approval_queue, base | Approval Queue | ਮਨਜ਼ੂਰੀ ਕਤਾਰ |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | ਸਮੀਖਿਅਕ |
| `S85dfa3` | base | Account | ਖਾਤਾ |
| `Sb8be3d` | base | Administration | ਪ੍ਰਸ਼ਾਸਨ |
| `S28dd75` | base | Audit Log | ਆਡਿਟ ਲੌਗ |
| `Sa28e96` | base, catalogue_health | Catalogue Health | ਕੈਟਾਲਾਗ ਦੀ ਸਿਹਤ |
| `S162a45` | base, list | Change Sets | ਤਬਦੀਲੀ ਸੈੱਟ |
| `S532c86` | base | covering | ਬਦਲ ਵਜੋਂ |
| `Sd87f47` | base, dashboard | Dashboard | ਡੈਸ਼ਬੋਰਡ |
| `S710ea3` | base, delegations | Delegation | ਸੌਂਪਣਾ |
| `See833c` | base, export_center | Export Center | ਨਿਰਯਾਤ ਕੇਂਦਰ |
| `S6f6f72` | base, export_profiles | Export Profiles | ਨਿਰਯਾਤ ਪ੍ਰੋਫਾਈਲ |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | ਫਲੀਟ ਫੀਡਬੈਕ |
| `Sc47ae1` | base, help | Help | ਮਦਦ |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | ਹੱਬ ਏਕੀਕਰਨ |
| `S8ac724` | base, new | Import from .st files | .st ਫਾਈਲਾਂ ਤੋਂ ਆਯਾਤ |
| `S1ed126` | base | Insight | ਵਿਸ਼ਲੇਸ਼ਣ |
| `Sa7881c` | base, integrations | Integrations | ਏਕੀਕਰਨ |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | ਪੁਰਾਣੇ-ਨਵੇਂ ਦੀ ਮੈਪਿੰਗ |
| `S3c1c8a` | base, new, st_new | Library Import | ਲਾਇਬ੍ਰੇਰੀ ਆਯਾਤ |
| `S6e78c9` | base | Log out | ਲਾਗ ਆਊਟ |
| `S3871af` | base | Lookups | ਹਵਾਲਾ ਸੂਚੀਆਂ |
| `Sefd197` | base | Main navigation | ਮੁੱਖ ਨੈਵੀਗੇਸ਼ਨ |
| `S617eec` | base, mine | My Change Requests | ਮੇਰੀਆਂ ਤਬਦੀਲੀ ਬੇਨਤੀਆਂ |
| `Sdbb388` | base | New Sandbox Code | ਨਵਾਂ ਸੈਂਡਬਾਕਸ ਕੋਡ |
| `Sd85719` | base, form, list | New Status Code | ਨਵਾਂ ਸਥਿਤੀ ਕੋਡ |
| `Se94865` | base, dashboard, notifications | Notices | ਸੂਚਨਾਵਾਂ |
| `Sa1fdaa` | base, operations | Operations | ਕਾਰਵਾਈਆਂ |
| `S8fa41d` | base, dashboard, list | Releases | ਰਿਲੀਜ਼ |
| `Sf490d7` | base, review_checklist | Review Checklist | ਸਮੀਖਿਆ ਚੈੱਕਲਿਸਟ |
| `S437a0d` | base, review_queue | Review Queue | ਸਮੀਖਿਆ ਕਤਾਰ |
| `Sc7f73b` | base, settings | Settings | ਸੈਟਿੰਗਾਂ |
| `Sbe504f` | base | Skip to main content | ਮੁੱਖ ਸਮੱਗਰੀ 'ਤੇ ਜਾਓ |
| `Sa42252` | base, stalled | Stalled Requests | ਰੁਕੀਆਂ ਬੇਨਤੀਆਂ |
| `S7f5583` | base, list | Status Codes | ਸਥਿਤੀ ਕੋਡ |
| `Sa4a761` | base, success_metrics | Success Metrics | ਸਫਲਤਾ ਮਾਪਦੰਡ |
| `S1b9aeb` | base, dashboard | unread | ਨਾ-ਪੜ੍ਹੇ |
| `S57f2b1` | base | Users | ਵਰਤੋਂਕਾਰ |
| `Sd7a484` | base | Workflow | ਕਾਰਜ-ਪ੍ਰਵਾਹ |
| `S5a4692` | base | You are covering for a colleague | ਤੁਸੀਂ ਇੱਕ ਸਾਥੀ ਦੀ ਥਾਂ ਕੰਮ ਕਰ ਰਹੇ ਹੋ |
| `Sbae7d5` | catalogue_health, detail, list | Status | ਸਥਿਤੀ |
| `S074d62` | detail, role badge | Chief Engineer | ਮੁੱਖ ਇੰਜੀਨੀਅਰ |
| `S816c52` | detail, export_verify, list | No | ਨਹੀਂ |
| `Se96390` | detail, list | Remove | ਹਟਾਓ |
| `S5397e0` | detail, export_verify, list | Yes | ਹਾਂ |
| `S2da600` | export_center, list | Version | ਸੰਸਕਰਣ |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | ਨਾਮ |
| `Sd7decf` | legacy_mapping, list | Filter | ਫਿਲਟਰ |
| `Sbce064` | legacy_mapping, list | Search | ਖੋਜ |
| `S20bff1` | list | Status codes | ਸਥਿਤੀ ਕੋਡ |
| `Sf7c400` | login | Log in | ਲਾਗ ਇਨ |
| `S8be3c9` | login | Password | ਪਾਸਵਰਡ |
| `S2c7ab3` | login | Username or email | ਵਰਤੋਂਕਾਰ ਨਾਮ ਜਾਂ ਈਮੇਲ |
| `S05fc94` | role badge | Engineer | ਇੰਜੀਨੀਅਰ |
| `S3c0e8a` | role badge | StCd Owner | StCd ਮਾਲਕ |
| `Sdbad9f` | role badge | Viewer | ਦਰਸ਼ਕ |

### 9.16 ES Español 🇪🇸 — Spanish

102 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | vencidas |
| `Sad60c5` | _role | level | nivel |
| `S89b86a` | account_settings, base, detail | Language | Idioma |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | Administrador |
| `Sc452ad` | approval_queue, base | Approval Queue | Cola de aprobación |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | Revisor |
| `S85dfa3` | base | Account | Cuenta |
| `Sb8be3d` | base | Administration | Administración |
| `S28dd75` | base | Audit Log | Registro de auditoría |
| `Sa28e96` | base, catalogue_health | Catalogue Health | Estado del catálogo |
| `S162a45` | base, list | Change Sets | Conjuntos de cambios |
| `S532c86` | base | covering | sustitución |
| `Sd87f47` | base, dashboard | Dashboard | Panel |
| `S710ea3` | base, delegations | Delegation | Delegación |
| `See833c` | base, export_center | Export Center | Centro de exportación |
| `S6f6f72` | base, export_profiles | Export Profiles | Perfiles de exportación |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | Comentarios de la flota |
| `Sc47ae1` | base, help | Help | Ayuda |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | Consolidación de Hub |
| `S8ac724` | base, new | Import from .st files | Importar desde archivos .st |
| `S1ed126` | base | Insight | Análisis |
| `Sa7881c` | base, integrations | Integrations | Integraciones |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | Correspondencia antiguo-nuevo |
| `S3c1c8a` | base, new, st_new | Library Import | Importar biblioteca |
| `S6e78c9` | base | Log out | Cerrar sesión |
| `S3871af` | base | Lookups | Listas de valores |
| `Sefd197` | base | Main navigation | Navegación principal |
| `S617eec` | base, mine | My Change Requests | Mis solicitudes de cambio |
| `Sdbb388` | base | New Sandbox Code | Nuevo código de pruebas |
| `Sd85719` | base, form, list | New Status Code | Nuevo código de estado |
| `Se94865` | base, dashboard, notifications | Notices | Avisos |
| `Sa1fdaa` | base, operations | Operations | Operaciones |
| `S8fa41d` | base, dashboard, list | Releases | Versiones publicadas |
| `Sf490d7` | base, review_checklist | Review Checklist | Lista de comprobación de revisión |
| `S437a0d` | base, review_queue | Review Queue | Cola de revisión |
| `Sc7f73b` | base, settings | Settings | Ajustes |
| `Sbe504f` | base | Skip to main content | Saltar al contenido principal |
| `Sa42252` | base, stalled | Stalled Requests | Solicitudes detenidas |
| `S7f5583` | base, list | Status Codes | Códigos de estado |
| `Sa4a761` | base, success_metrics | Success Metrics | Indicadores de éxito |
| `S1b9aeb` | base, dashboard | unread | sin leer |
| `S57f2b1` | base | Users | Usuarios |
| `Sd7a484` | base | Workflow | Flujo de trabajo |
| `S5a4692` | base | You are covering for a colleague | Está sustituyendo a un compañero |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | Aún sin asignar |
| `Sbae7d5` | catalogue_health, detail, list | Status | Estado |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | Pendiente de aprobación del administrador |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | Pendiente de aprobación del ingeniero jefe |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | Pendiente de aprobación entre dominios |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | Pendiente de aprobación del revisor |
| `S452d9f` | dashboard | Browse published and in-progress releases | Explorar versiones publicadas y en curso |
| `Scf72d4` | dashboard | Browse Status Codes | Explorar códigos de estado |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | Mis borradores bloqueados por una aprobación de dominio |
| `Se0688f` | dashboard | My Open Change Requests | Mis solicitudes de cambio abiertas |
| `Sf949fb` | dashboard | Number ranges running out | Rangos de números a punto de agotarse |
| `S6605c0` | dashboard | Search and filter all governed status codes | Buscar y filtrar todos los códigos de estado gobernados |
| `S916385` | dashboard | Stalled requests | Solicitudes detenidas |
| `S074d62` | detail, role badge | Chief Engineer | Ingeniero jefe |
| `S2fa1f7` | detail, form, list | Functional Subgroup | Subgrupo funcional |
| `S816c52` | detail, export_verify, list | No | No |
| `S483bf2` | detail, list | Published | Publicado |
| `Se96390` | detail, list | Remove | Quitar |
| `Se246b6` | detail, form, list | Status Category | Categoría de estado |
| `S08e643` | detail, list | Target software version | Versión de software de destino |
| `S5397e0` | detail, export_verify, list | Yes | Sí |
| `S2da600` | export_center, list | Version | Versión |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | Nombre |
| `Sced1ce` | form, list | Functional System Group | Grupo de sistema funcional |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | Controlador |
| `Sd7decf` | legacy_mapping, list | Filter | Filtrar |
| `Sb7baa1` | legacy_mapping | Number | Número |
| `Sbce064` | legacy_mapping, list | Search | Buscar |
| `Sc5fe02` | list | any | cualquiera |
| `Sef5415` | list | Apply columns | Aplicar columnas |
| `S9e895f` | list | Change sets | Conjuntos de cambios |
| `Scf723c` | list | Columns | Columnas |
| `S759686` | list | Filter status codes | Filtrar códigos de estado |
| `Sfd327d` | list | Identifier, title, description | Identificador, título, descripción |
| `S44d25b` | list | Items | Elementos |
| `S033df3` | list | Lifecycle | Ciclo de vida |
| `Sb4cad6` | list | Link to this view | Enlace a esta vista |
| `Se248d5` | list, new | New change set | Nuevo conjunto de cambios |
| `Se75aa1` | list, new | New Release | Nueva versión |
| `Se5076c` | list | No change sets yet. | Todavía no hay conjuntos de cambios. |
| `Sd32c03` | list | No releases yet. | Todavía no hay versiones. |
| `Sc3af43` | list | No saved searches yet. | Todavía no hay búsquedas guardadas. |
| `S0cb400` | list | No status codes match these filters. | Ningún código de estado coincide con estos filtros. |
| `Sf7194e` | list | Requests | Solicitudes |
| `S37a530` | list | result | resultado |
| `Scdf7e9` | list | results | resultados |
| `S4f581e` | list | Sandbox only | Solo pruebas |
| `S1db747` | list | Save search | Guardar búsqueda |
| `Sff86e9` | list | Save the current filters as | Guardar los filtros actuales como |
| `Sed1d84` | list | Saved searches | Búsquedas guardadas |
| `S20bff1` | list | Status codes | Códigos de estado |
| `Se90eb0` | list | Turbine Platform | Plataforma de turbina |
| `Sf7c400` | login | Log in | Iniciar sesión |
| `S8be3c9` | login | Password | Contraseña |
| `S2c7ab3` | login | Username or email | Usuario o correo electrónico |
| `S05fc94` | role badge | Engineer | Ingeniero |
| `S3c0e8a` | role badge | StCd Owner | Propietario de StCd |
| `Sdbad9f` | role badge | Viewer | Lector |

### 9.17 IT Italiano 🇮🇹 — Italian

102 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | in ritardo |
| `Sad60c5` | _role | level | livello |
| `S89b86a` | account_settings, base, detail | Language | Lingua |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | Amministratore |
| `Sc452ad` | approval_queue, base | Approval Queue | Coda di approvazione |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | Revisore |
| `S85dfa3` | base | Account | Account |
| `Sb8be3d` | base | Administration | Amministrazione |
| `S28dd75` | base | Audit Log | Registro di audit |
| `Sa28e96` | base, catalogue_health | Catalogue Health | Stato del catalogo |
| `S162a45` | base, list | Change Sets | Set di modifiche |
| `S532c86` | base | covering | sostituzione |
| `Sd87f47` | base, dashboard | Dashboard | Dashboard |
| `S710ea3` | base, delegations | Delegation | Delega |
| `See833c` | base, export_center | Export Center | Centro esportazioni |
| `S6f6f72` | base, export_profiles | Export Profiles | Profili di esportazione |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | Feedback dalla flotta |
| `Sc47ae1` | base, help | Help | Aiuto |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | Consolidamento Hub |
| `S8ac724` | base, new | Import from .st files | Importa da file .st |
| `S1ed126` | base | Insight | Analisi |
| `Sa7881c` | base, integrations | Integrations | Integrazioni |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | Corrispondenza vecchio-nuovo |
| `S3c1c8a` | base, new, st_new | Library Import | Importazione libreria |
| `S6e78c9` | base | Log out | Esci |
| `S3871af` | base | Lookups | Elenchi di valori |
| `Sefd197` | base | Main navigation | Navigazione principale |
| `S617eec` | base, mine | My Change Requests | Le mie richieste di modifica |
| `Sdbb388` | base | New Sandbox Code | Nuovo codice sandbox |
| `Sd85719` | base, form, list | New Status Code | Nuovo codice di stato |
| `Se94865` | base, dashboard, notifications | Notices | Avvisi |
| `Sa1fdaa` | base, operations | Operations | Operazioni |
| `S8fa41d` | base, dashboard, list | Releases | Rilasci |
| `Sf490d7` | base, review_checklist | Review Checklist | Checklist di revisione |
| `S437a0d` | base, review_queue | Review Queue | Coda di revisione |
| `Sc7f73b` | base, settings | Settings | Impostazioni |
| `Sbe504f` | base | Skip to main content | Vai al contenuto principale |
| `Sa42252` | base, stalled | Stalled Requests | Richieste ferme |
| `S7f5583` | base, list | Status Codes | Codici di stato |
| `Sa4a761` | base, success_metrics | Success Metrics | Indicatori di successo |
| `S1b9aeb` | base, dashboard | unread | non letti |
| `S57f2b1` | base | Users | Utenti |
| `Sd7a484` | base | Workflow | Flusso di lavoro |
| `S5a4692` | base | You are covering for a colleague | Stai sostituendo un collega |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | Non ancora assegnato |
| `Sbae7d5` | catalogue_health, detail, list | Status | Stato |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | In attesa dell'approvazione dell'amministratore |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | In attesa dell'approvazione del capo ingegnere |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | In attesa dell'approvazione interdominio |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | In attesa dell'approvazione del revisore |
| `S452d9f` | dashboard | Browse published and in-progress releases | Sfoglia i rilasci pubblicati e in corso |
| `Scf72d4` | dashboard | Browse Status Codes | Sfoglia i codici di stato |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | Le mie bozze bloccate da un'approvazione di dominio |
| `Se0688f` | dashboard | My Open Change Requests | Le mie richieste di modifica aperte |
| `Sf949fb` | dashboard | Number ranges running out | Intervalli di numeri in esaurimento |
| `S6605c0` | dashboard | Search and filter all governed status codes | Cerca e filtra tutti i codici di stato governati |
| `S916385` | dashboard | Stalled requests | Richieste ferme |
| `S074d62` | detail, role badge | Chief Engineer | Capo ingegnere |
| `S2fa1f7` | detail, form, list | Functional Subgroup | Sottogruppo funzionale |
| `S816c52` | detail, export_verify, list | No | No |
| `S483bf2` | detail, list | Published | Pubblicato |
| `Se96390` | detail, list | Remove | Rimuovi |
| `Se246b6` | detail, form, list | Status Category | Categoria di stato |
| `S08e643` | detail, list | Target software version | Versione software di destinazione |
| `S5397e0` | detail, export_verify, list | Yes | Sì |
| `S2da600` | export_center, list | Version | Versione |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | Nome |
| `Sced1ce` | form, list | Functional System Group | Gruppo di sistema funzionale |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | Controller |
| `Sd7decf` | legacy_mapping, list | Filter | Filtra |
| `Sb7baa1` | legacy_mapping | Number | Numero |
| `Sbce064` | legacy_mapping, list | Search | Cerca |
| `Sc5fe02` | list | any | qualsiasi |
| `Sef5415` | list | Apply columns | Applica colonne |
| `S9e895f` | list | Change sets | Set di modifiche |
| `Scf723c` | list | Columns | Colonne |
| `S759686` | list | Filter status codes | Filtra i codici di stato |
| `Sfd327d` | list | Identifier, title, description | Identificatore, titolo, descrizione |
| `S44d25b` | list | Items | Elementi |
| `S033df3` | list | Lifecycle | Ciclo di vita |
| `Sb4cad6` | list | Link to this view | Link a questa vista |
| `Se248d5` | list, new | New change set | Nuovo set di modifiche |
| `Se75aa1` | list, new | New Release | Nuovo rilascio |
| `Se5076c` | list | No change sets yet. | Nessun set di modifiche per ora. |
| `Sd32c03` | list | No releases yet. | Nessun rilascio per ora. |
| `Sc3af43` | list | No saved searches yet. | Nessuna ricerca salvata per ora. |
| `S0cb400` | list | No status codes match these filters. | Nessun codice di stato corrisponde a questi filtri. |
| `Sf7194e` | list | Requests | Richieste |
| `S37a530` | list | result | risultato |
| `Scdf7e9` | list | results | risultati |
| `S4f581e` | list | Sandbox only | Solo sandbox |
| `S1db747` | list | Save search | Salva ricerca |
| `Sff86e9` | list | Save the current filters as | Salva i filtri attuali come |
| `Sed1d84` | list | Saved searches | Ricerche salvate |
| `S20bff1` | list | Status codes | Codici di stato |
| `Se90eb0` | list | Turbine Platform | Piattaforma della turbina |
| `Sf7c400` | login | Log in | Accedi |
| `S8be3c9` | login | Password | Password |
| `S2c7ab3` | login | Username or email | Nome utente o e-mail |
| `S05fc94` | role badge | Engineer | Ingegnere |
| `S3c0e8a` | role badge | StCd Owner | Responsabile StCd |
| `Sdbad9f` | role badge | Viewer | Osservatore |

### 9.18 DK Dansk 🇩🇰 — Danish

102 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | forsinkede |
| `Sad60c5` | _role | level | niveau |
| `S89b86a` | account_settings, base, detail | Language | Sprog |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | Administrator |
| `Sc452ad` | approval_queue, base | Approval Queue | Godkendelseskø |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | Reviewer |
| `S85dfa3` | base | Account | Konto |
| `Sb8be3d` | base | Administration | Administration |
| `S28dd75` | base | Audit Log | Revisionslog |
| `Sa28e96` | base, catalogue_health | Catalogue Health | Katalogets tilstand |
| `S162a45` | base, list | Change Sets | Ændringssæt |
| `S532c86` | base | covering | vikariat |
| `Sd87f47` | base, dashboard | Dashboard | Overblik |
| `S710ea3` | base, delegations | Delegation | Delegering |
| `See833c` | base, export_center | Export Center | Eksportcenter |
| `S6f6f72` | base, export_profiles | Export Profiles | Eksportprofiler |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | Feedback fra flåden |
| `Sc47ae1` | base, help | Help | Hjælp |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | Hub-konsolidering |
| `S8ac724` | base, new | Import from .st files | Importér fra .st-filer |
| `S1ed126` | base | Insight | Indsigt |
| `Sa7881c` | base, integrations | Integrations | Integrationer |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | Gammel-ny-kobling |
| `S3c1c8a` | base, new, st_new | Library Import | Import af bibliotek |
| `S6e78c9` | base | Log out | Log ud |
| `S3871af` | base | Lookups | Opslagslister |
| `Sefd197` | base | Main navigation | Hovednavigation |
| `S617eec` | base, mine | My Change Requests | Mine ændringsanmodninger |
| `Sdbb388` | base | New Sandbox Code | Ny sandbox-kode |
| `Sd85719` | base, form, list | New Status Code | Ny statuskode |
| `Se94865` | base, dashboard, notifications | Notices | Meddelelser |
| `Sa1fdaa` | base, operations | Operations | Drift |
| `S8fa41d` | base, dashboard, list | Releases | Udgivelser |
| `Sf490d7` | base, review_checklist | Review Checklist | Gennemgangstjekliste |
| `S437a0d` | base, review_queue | Review Queue | Gennemgangskø |
| `Sc7f73b` | base, settings | Settings | Indstillinger |
| `Sbe504f` | base | Skip to main content | Gå til hovedindholdet |
| `Sa42252` | base, stalled | Stalled Requests | Fastlåste anmodninger |
| `S7f5583` | base, list | Status Codes | Statuskoder |
| `Sa4a761` | base, success_metrics | Success Metrics | Succesmålinger |
| `S1b9aeb` | base, dashboard | unread | ulæste |
| `S57f2b1` | base | Users | Brugere |
| `Sd7a484` | base | Workflow | Arbejdsgang |
| `S5a4692` | base | You are covering for a colleague | Du vikarierer for en kollega |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | Endnu ikke tildelt |
| `Sbae7d5` | catalogue_health, detail, list | Status | Status |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | Afventer administratorens godkendelse |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | Afventer chefingeniørens godkendelse |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | Afventer tværfaglig godkendelse |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | Afventer reviewerens godkendelse |
| `S452d9f` | dashboard | Browse published and in-progress releases | Gennemse udgivne og igangværende udgivelser |
| `Scf72d4` | dashboard | Browse Status Codes | Gennemse statuskoder |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | Mine kladder, der venter på en domænegodkendelse |
| `Se0688f` | dashboard | My Open Change Requests | Mine åbne ændringsanmodninger |
| `Sf949fb` | dashboard | Number ranges running out | Nummerintervaller ved at slippe op |
| `S6605c0` | dashboard | Search and filter all governed status codes | Søg i og filtrér alle styrede statuskoder |
| `S916385` | dashboard | Stalled requests | Fastlåste anmodninger |
| `S074d62` | detail, role badge | Chief Engineer | Chefingeniør |
| `S2fa1f7` | detail, form, list | Functional Subgroup | Funktionel undergruppe |
| `S816c52` | detail, export_verify, list | No | Nej |
| `S483bf2` | detail, list | Published | Udgivet |
| `Se96390` | detail, list | Remove | Fjern |
| `Se246b6` | detail, form, list | Status Category | Statuskategori |
| `S08e643` | detail, list | Target software version | Målsoftwareversion |
| `S5397e0` | detail, export_verify, list | Yes | Ja |
| `S2da600` | export_center, list | Version | Version |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | Navn |
| `Sced1ce` | form, list | Functional System Group | Funktionel systemgruppe |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | Controller |
| `Sd7decf` | legacy_mapping, list | Filter | Filtrér |
| `Sb7baa1` | legacy_mapping | Number | Nummer |
| `Sbce064` | legacy_mapping, list | Search | Søg |
| `Sc5fe02` | list | any | alle |
| `Sef5415` | list | Apply columns | Anvend kolonner |
| `S9e895f` | list | Change sets | Ændringssæt |
| `Scf723c` | list | Columns | Kolonner |
| `S759686` | list | Filter status codes | Filtrér statuskoder |
| `Sfd327d` | list | Identifier, title, description | Identifikator, titel, beskrivelse |
| `S44d25b` | list | Items | Elementer |
| `S033df3` | list | Lifecycle | Livscyklus |
| `Sb4cad6` | list | Link to this view | Link til denne visning |
| `Se248d5` | list, new | New change set | Nyt ændringssæt |
| `Se75aa1` | list, new | New Release | Ny udgivelse |
| `Se5076c` | list | No change sets yet. | Ingen ændringssæt endnu. |
| `Sd32c03` | list | No releases yet. | Ingen udgivelser endnu. |
| `Sc3af43` | list | No saved searches yet. | Ingen gemte søgninger endnu. |
| `S0cb400` | list | No status codes match these filters. | Ingen statuskoder matcher disse filtre. |
| `Sf7194e` | list | Requests | Anmodninger |
| `S37a530` | list | result | resultat |
| `Scdf7e9` | list | results | resultater |
| `S4f581e` | list | Sandbox only | Kun sandbox |
| `S1db747` | list | Save search | Gem søgning |
| `Sff86e9` | list | Save the current filters as | Gem de aktuelle filtre som |
| `Sed1d84` | list | Saved searches | Gemte søgninger |
| `S20bff1` | list | Status codes | Statuskoder |
| `Se90eb0` | list | Turbine Platform | Turbineplatform |
| `Sf7c400` | login | Log in | Log ind |
| `S8be3c9` | login | Password | Adgangskode |
| `S2c7ab3` | login | Username or email | Brugernavn eller e-mail |
| `S05fc94` | role badge | Engineer | Ingeniør |
| `S3c0e8a` | role badge | StCd Owner | StCd-ejer |
| `Sdbad9f` | role badge | Viewer | Læser |

### 9.19 GE ქართული 🇬🇪 — Georgian

102 of 772 strings translated; direction left to right.

| Id | Screens | English | Translation |
|---|---|---|---|
| `Sba2fff` | _macros, dashboard, success_metrics | overdue | ვადაგადაცილებული |
| `Sad60c5` | _role | level | დონე |
| `S89b86a` | account_settings, base, detail | Language | ენა |
| `S1eda23` | approval_queue, detail, review_queue | Administrator | ადმინისტრატორი |
| `Sc452ad` | approval_queue, base | Approval Queue | დამტკიცების რიგი |
| `Sa74f16` | approval_queue, detail, review_queue | Reviewer | მიმომხილველი |
| `S85dfa3` | base | Account | ანგარიში |
| `Sb8be3d` | base | Administration | ადმინისტრირება |
| `S28dd75` | base | Audit Log | აუდიტის ჟურნალი |
| `Sa28e96` | base, catalogue_health | Catalogue Health | კატალოგის მდგომარეობა |
| `S162a45` | base, list | Change Sets | ცვლილებების ჯგუფები |
| `S532c86` | base | covering | ჩანაცვლება |
| `Sd87f47` | base, dashboard | Dashboard | მთავარი პანელი |
| `S710ea3` | base, delegations | Delegation | დელეგირება |
| `See833c` | base, export_center | Export Center | ექსპორტის ცენტრი |
| `S6f6f72` | base, export_profiles | Export Profiles | ექსპორტის პროფილები |
| `Scd938f` | base, fleet_feedback | Fleet Feedback | პარკის უკუკავშირი |
| `Sc47ae1` | base, help | Help | დახმარება |
| `S2fa8ef` | base, hub_consolidation | Hub Consolidation | ჰაბის კონსოლიდაცია |
| `S8ac724` | base, new | Import from .st files | იმპორტი .st ფაილებიდან |
| `S1ed126` | base | Insight | ანალიტიკა |
| `Sa7881c` | base, integrations | Integrations | ინტეგრაციები |
| `Sfd5ec0` | base, legacy_mapping, new | Legacy mapping | ძველი-ახალის შესაბამისობა |
| `S3c1c8a` | base, new, st_new | Library Import | ბიბლიოთეკის იმპორტი |
| `S6e78c9` | base | Log out | გასვლა |
| `S3871af` | base | Lookups | საცნობარო სიები |
| `Sefd197` | base | Main navigation | მთავარი ნავიგაცია |
| `S617eec` | base, mine | My Change Requests | ჩემი ცვლილების მოთხოვნები |
| `Sdbb388` | base | New Sandbox Code | ახალი სატესტო კოდი |
| `Sd85719` | base, form, list | New Status Code | ახალი სტატუსის კოდი |
| `Se94865` | base, dashboard, notifications | Notices | შეტყობინებები |
| `Sa1fdaa` | base, operations | Operations | ოპერაციები |
| `S8fa41d` | base, dashboard, list | Releases | რელიზები |
| `Sf490d7` | base, review_checklist | Review Checklist | განხილვის ჩეკლისტი |
| `S437a0d` | base, review_queue | Review Queue | განხილვის რიგი |
| `Sc7f73b` | base, settings | Settings | პარამეტრები |
| `Sbe504f` | base | Skip to main content | ძირითად შინაარსზე გადასვლა |
| `Sa42252` | base, stalled | Stalled Requests | შეჩერებული მოთხოვნები |
| `S7f5583` | base, list | Status Codes | სტატუსის კოდები |
| `Sa4a761` | base, success_metrics | Success Metrics | წარმატების მაჩვენებლები |
| `S1b9aeb` | base, dashboard | unread | წაუკითხავი |
| `S57f2b1` | base | Users | მომხმარებლები |
| `Sd7a484` | base | Workflow | სამუშაო პროცესი |
| `S5a4692` | base | You are covering for a colleague | თქვენ კოლეგას ცვლით |
| `Sc914e0` | catalogue_health, detail, hub_consolidation | Not yet assigned | ჯერ არ არის მინიჭებული |
| `Sbae7d5` | catalogue_health, detail, list | Status | სტატუსი |
| `S66dc40` | dashboard | Awaiting Administrator Sign-Off | ელოდება ადმინისტრატორის დადასტურებას |
| `S33a0d3` | dashboard | Awaiting Chief Engineer Approval | ელოდება მთავარი ინჟინრის დამტკიცებას |
| `S04cc8e` | dashboard | Awaiting Cross-Domain Sign-Off | ელოდება დომენთაშორის დადასტურებას |
| `S52bbc1` | dashboard | Awaiting Reviewer Sign-Off | ელოდება მიმომხილველის დადასტურებას |
| `S452d9f` | dashboard | Browse published and in-progress releases | გამოქვეყნებული და მიმდინარე რელიზების დათვალიერება |
| `Scf72d4` | dashboard | Browse Status Codes | სტატუსის კოდების დათვალიერება |
| `S250750` | dashboard | Draft CRs of mine blocked on a domain sign-off | დომენის დადასტურებაზე შეჩერებული ჩემი დრაფტები |
| `Se0688f` | dashboard | My Open Change Requests | ჩემი ღია ცვლილების მოთხოვნები |
| `Sf949fb` | dashboard | Number ranges running out | ამოწურვადი ნომრების დიაპაზონები |
| `S6605c0` | dashboard | Search and filter all governed status codes | ყველა მართული სტატუსის კოდის ძიება და გაფილტვრა |
| `S916385` | dashboard | Stalled requests | შეჩერებული მოთხოვნები |
| `S074d62` | detail, role badge | Chief Engineer | მთავარი ინჟინერი |
| `S2fa1f7` | detail, form, list | Functional Subgroup | ფუნქციური ქვეჯგუფი |
| `S816c52` | detail, export_verify, list | No | არა |
| `S483bf2` | detail, list | Published | გამოქვეყნებული |
| `Se96390` | detail, list | Remove | წაშლა |
| `Se246b6` | detail, form, list | Status Category | სტატუსის კატეგორია |
| `S08e643` | detail, list | Target software version | სამიზნე პროგრამული ვერსია |
| `S5397e0` | detail, export_verify, list | Yes | დიახ |
| `S2da600` | export_center, list | Version | ვერსია |
| `S709a23` | export_profiles, integrations, legacy_mapping | Name | სახელი |
| `Sced1ce` | form, list | Functional System Group | ფუნქციური სისტემის ჯგუფი |
| `Sa36a5f` | legacy_mapping, st_new, st_preview | Controller | კონტროლერი |
| `Sd7decf` | legacy_mapping, list | Filter | ფილტრი |
| `Sb7baa1` | legacy_mapping | Number | ნომერი |
| `Sbce064` | legacy_mapping, list | Search | ძიება |
| `Sc5fe02` | list | any | ნებისმიერი |
| `Sef5415` | list | Apply columns | სვეტების გამოყენება |
| `S9e895f` | list | Change sets | ცვლილებების ჯგუფები |
| `Scf723c` | list | Columns | სვეტები |
| `S759686` | list | Filter status codes | სტატუსის კოდების გაფილტვრა |
| `Sfd327d` | list | Identifier, title, description | იდენტიფიკატორი, სათაური, აღწერა |
| `S44d25b` | list | Items | ელემენტები |
| `S033df3` | list | Lifecycle | სასიცოცხლო ციკლი |
| `Sb4cad6` | list | Link to this view | ბმული ამ ხედზე |
| `Se248d5` | list, new | New change set | ახალი ცვლილებების ჯგუფი |
| `Se75aa1` | list, new | New Release | ახალი რელიზი |
| `Se5076c` | list | No change sets yet. | ცვლილებების ჯგუფები ჯერ არ არის. |
| `Sd32c03` | list | No releases yet. | რელიზები ჯერ არ არის. |
| `Sc3af43` | list | No saved searches yet. | შენახული ძიებები ჯერ არ არის. |
| `S0cb400` | list | No status codes match these filters. | ამ ფილტრებს არცერთი სტატუსის კოდი არ შეესაბამება. |
| `Sf7194e` | list | Requests | მოთხოვნები |
| `S37a530` | list | result | შედეგი |
| `Scdf7e9` | list | results | შედეგი |
| `S4f581e` | list | Sandbox only | მხოლოდ სატესტო |
| `S1db747` | list | Save search | ძიების შენახვა |
| `Sff86e9` | list | Save the current filters as | მიმდინარე ფილტრების შენახვა სახელით |
| `Sed1d84` | list | Saved searches | შენახული ძიებები |
| `S20bff1` | list | Status codes | სტატუსის კოდები |
| `Se90eb0` | list | Turbine Platform | ტურბინის პლატფორმა |
| `Sf7c400` | login | Log in | შესვლა |
| `S8be3c9` | login | Password | პაროლი |
| `S2c7ab3` | login | Username or email | მომხმარებლის სახელი ან ელფოსტა |
| `S05fc94` | role badge | Engineer | ინჟინერი |
| `S3c0e8a` | role badge | StCd Owner | StCd-ის მფლობელი |
| `Sdbad9f` | role badge | Viewer | მაყურებელი |

### 9.20 Strings with the screens that show them

Every string of the interface with the templates that use it. A native speaker adding a missing translation finds the context here.

| Id | English | Screens | Languages |
|---|---|---|---|
| `S1a4626` | ...or just the expected number of rows | reconciliation | 1 of 18 |
| `Seba07b` | A change set groups the change requests that ship with one controller software release, so reviewers see the whole package. Each request is still decided on its own. | list | 1 of 18 |
| `S0240d7` | A code can be translated once its source text is Approved. | translations | 1 of 18 |
| `Sba3640` | A number with a unit: ms, s, min, h, or d (e.g. "10ms", "2min"). | form | 1 of 18 |
| `Sbdcc6f` | A profile fixes the columns, their order and header labels, and optionally a default audience and language. Profiles are data: change them here, no deployment needed. | export_profiles | 1 of 18 |
| `Sb08e6c` | A Reviewer and an Administrator each sign off (in any order). If either rejects, it goes back to the author. | help and messages | 1 of 18 |
| `S737d81` | A translation is saved as a draft and approved by someone else - a light review, not the three-decision cycle. Exports in a language use approved translations only. | translations | 1 of 18 |
| `S85dfa3` | Account | base | 18 of 18 |
| `Se32707` | Account Settings | account_settings | 1 of 18 |
| `Sc3cd63` | Actions | detail | 1 of 18 |
| `S92ef08` | Activate | review_checklist | 1 of 18 |
| `Sa733b8` | Active | export_profiles, review_checklist | 1 of 18 |
| `S9661c6` | Active and planned delegations | delegations | 1 of 18 |
| `S61cc55` | Add | detail, review_checklist | 1 of 18 |
| `S12cc59` | Add a comment (no decision) | detail | 1 of 18 |
| `Sfc1290` | Add an item | review_checklist | 1 of 18 |
| `Sd89450` | Add Comment | detail | 1 of 18 |
| `Scfa1b6` | Add field comment | detail | 1 of 18 |
| `Sbb965e` | Add one of your change requests | detail | 1 of 18 |
| `S9a693b` | Add to change set | detail | 1 of 18 |
| `S29e740` | Add webhook | integrations | 1 of 18 |
| `S172415` | added | software_versions | 1 of 18 |
| `Sb68734` | Added | software_versions | 1 of 18 |
| `Sb8be3d` | Administration | base | 18 of 18 |
| `S1eda23` | Administrator | approval_queue, detail, review_queue, role badge | 18 of 18 |
| `S7bbd6d` | Administrator sign-off | detail | 1 of 18 |
| `S212856` | advanced, controller firmware programs | detail | 1 of 18 |
| `Sfbde82` | Affected component | detail | 1 of 18 |
| `Sf094b9` | Affected component (optional) | form | 1 of 18 |
| `S79ba5e` | After | _macros | 1 of 18 |
| `Sff9f1f` | Age | success_metrics | 1 of 18 |
| `Sf03c0a` | ago | operations | 1 of 18 |
| `S25f8c5` | Alarm | detail, form | 1 of 18 |
| `Sd87c44` | all | detail, hub_consolidation | 1 of 18 |
| `S484388` | all columns | detail, export_center | 1 of 18 |
| `Sf9d469` | All controllers | legacy_mapping | 1 of 18 |
| `S2693e5` | All Drafts of this import join one change set, so they can be reviewed and decided together. | st_preview | 1 of 18 |
| `Sdf42bb` | all groups | new, review_checklist | 1 of 18 |
| `S66d6c2` | All Released Status Codes | export_center | 1 of 18 |
| `S432284` | All required sign-offs are in, but this is still a Draft — the Reviewer and Administrator only see it after you choose Submit for Review below. | detail | 1 of 18 |
| `S5d4358` | All rows are clean. | dry_run | 1 of 18 |
| `Scbc694` | already in the catalogue | st_preview | 1 of 18 |
| `S9eb13d` | amber after | _macros | 1 of 18 |
| `S2f1bed` | An Administrator includes the revision in a Release and publishes it; then it is Released. | help and messages | 1 of 18 |
| `Sc5fe02` | any | list | 8 of 18 |
| `Se61c2f` | Any number state | legacy_mapping | 1 of 18 |
| `Sc82c65` | API tokens | integrations | 1 of 18 |
| `S407cf2` | Applies from software version (optional) | form | 1 of 18 |
| `S0c9d31` | Applies to | review_checklist | 1 of 18 |
| `Sb99a01` | Applies to software versions | detail | 1 of 18 |
| `Sa30242` | Applies up to software version (optional) | form | 1 of 18 |
| `Sef5415` | Apply columns | list | 8 of 18 |
| `S8cc047` | Approval | success_metrics | 1 of 18 |
| `Sc452ad` | Approval Queue | approval_queue, base | 18 of 18 |
| `S8e9c89` | approval: amber after | stalled | 1 of 18 |
| `S7b2c7f` | Approve | detail | 1 of 18 |
| `Sde38bf` | Approve selected | detail | 1 of 18 |
| `Sa0452c` | Approve translation | translations | 1 of 18 |
| `S754eae` | approved or released codes checked | catalogue_health | 1 of 18 |
| `Scf2999` | Approving confirms these values; any change you make here is applied and audited. Rejecting ignores them. | detail | 1 of 18 |
| `Sf7f2d5` | Archive (requires 180-day retention elapsed) | detail | 1 of 18 |
| `S244492` | Assign | stalled | 1 of 18 |
| `S5d71d2` | Assign least-loaded Reviewer | detail | 1 of 18 |
| `Se29915` | Assign Reviewer | detail | 1 of 18 |
| `Se24e82` | Assigned | review_queue | 1 of 18 |
| `Sd371ec` | Assigned Reviewer | detail, stalled | 1 of 18 |
| `Sd9e420` | At least 12 characters. | account_settings | 1 of 18 |
| `S1afff0` | Attach | detail | 1 of 18 |
| `Sb5d75a` | Attach test report, simulation, design note or safety assessment | detail | 1 of 18 |
| `S51d993` | Audience | detail, export_center | 1 of 18 |
| `S134651` | Audience Access | detail, form | 1 of 18 |
| `S28dd75` | Audit Log | base | 18 of 18 |
| `Sd005ac` | Audit log integrity | operations | 1 of 18 |
| `S273d62` | Audit trail completeness of Released codes | success_metrics | 1 of 18 |
| `S5fda23` | Author | approval_queue, detail, mine, review_queue | 1 of 18 |
| `S94ea8c` | Available fields | export_profiles | 1 of 18 |
| `Sd71897` | Available Group | detail, form | 1 of 18 |
| `S66dc40` | Awaiting Administrator Sign-Off | dashboard | 8 of 18 |
| `S33a0d3` | Awaiting Chief Engineer Approval | dashboard | 8 of 18 |
| `S04cc8e` | Awaiting Cross-Domain Sign-Off | dashboard | 8 of 18 |
| `S52bbc1` | Awaiting Reviewer Sign-Off | dashboard | 8 of 18 |
| `Sb52b36` | Back | translations | 1 of 18 |
| `Sc0f94f` | Back to Export Center | export_verify | 1 of 18 |
| `S03510d` | Back to import | dry_run | 1 of 18 |
| `S78c92f` | Back to the log-in page | login_windows | 1 of 18 |
| `S530cc2` | Backups | operations | 1 of 18 |
| `S74f396` | Before | _macros | 1 of 18 |
| `Sdf88b8` | blocked | st_preview | 1 of 18 |
| `S452d9f` | Browse published and in-progress releases | dashboard | 8 of 18 |
| `Scf72d4` | Browse Status Codes | dashboard | 8 of 18 |
| `S228d5f` | business days | _macros, stalled, success_metrics | 1 of 18 |
| `Scfadbd` | By | detail | 1 of 18 |
| `S77dfd2` | Cancel | form, st_preview | 1 of 18 |
| `S8e9c15` | Candidate revisions | builder | 1 of 18 |
| `Scaf0f4` | Capacity per subgroup | catalogue_health | 1 of 18 |
| `Sa28e96` | Catalogue Health | base, catalogue_health | 18 of 18 |
| `S25d185` | Catalogue health | catalogue_health | 1 of 18 |
| `S49289d` | Change Password | account_settings | 1 of 18 |
| `S9c8393` | Change Request | detail | 1 of 18 |
| `S4572f4` | Change request | detail | 1 of 18 |
| `S3295be` | Change requests in this set | detail | 1 of 18 |
| `S003e61` | Change requests waiting for approval | approval_queue | 1 of 18 |
| `S2ef718` | Change requests waiting for review | review_queue | 1 of 18 |
| `S4d8006` | Change set | detail | 1 of 18 |
| `S162a45` | Change Sets | base, list | 18 of 18 |
| `S9e895f` | Change sets | list | 8 of 18 |
| `Sfd77f5` | Change thresholds | stalled | 1 of 18 |
| `S37c6c5` | changed | software_versions, st_preview | 1 of 18 |
| `Scb5424` | Changed | software_versions | 1 of 18 |
| `S6f7703` | Changed and withdrawn programs are not ticked: tick the ones you want to update, revise or restore. | st_preview | 1 of 18 |
| `S8aa57d` | Changes | detail | 1 of 18 |
| `S5ff781` | Check that a file you received is exactly what this system produced (and, with its MANIFEST.json, that nothing was changed). | export_center | 1 of 18 |
| `Sbd95c0` | Checklist confirmed at sign-off | detail | 1 of 18 |
| `Sd9053c` | Checklist items | review_checklist | 1 of 18 |
| `S074d62` | Chief Engineer | detail, role badge | 18 of 18 |
| `S03695d` | Chief Engineer decision | detail | 1 of 18 |
| `S94c2a3` | Classification | form | 1 of 18 |
| `S7c9afd` | Classification only — a Sandbox code's identifier is still drawn from the isolated StCd-T##### band, never from this group's numeric range. | form | 1 of 18 |
| `Sf0a89f` | Close change set | detail | 1 of 18 |
| `S7c0c39` | Close this change set? | detail | 1 of 18 |
| `Sadac69` | Code | detail, export_profiles, fleet_feedback, software_versions | 1 of 18 |
| `S199993` | Codes | catalogue_health, fleet_feedback | 1 of 18 |
| `S37d298` | codes apply to | software_versions | 1 of 18 |
| `Sc1d0d9` | Codes without an active owner | success_metrics | 1 of 18 |
| `Scf723c` | Columns | list | 8 of 18 |
| `Sf27073` | Columns (one per line: field \| header label) | export_profiles | 1 of 18 |
| `S153d7a` | Comment | detail | 1 of 18 |
| `S611578` | Comment (required for rejection) | detail | 1 of 18 |
| `Sc38432` | Comment on this field | detail | 1 of 18 |
| `Sfce06e` | Comments | detail | 1 of 18 |
| `S8d105c` | Compare | detail, reconciliation | 1 of 18 |
| `Sc9a03b` | Compare Revisions | detail | 1 of 18 |
| `Sac0d4a` | Compare with (what changed) | software_versions | 1 of 18 |
| `Sf0a8d6` | Compare with the legacy master list | reconciliation | 1 of 18 |
| `S1798b3` | Completed | detail | 1 of 18 |
| `S7671b5` | Confirm or override Audience Access | detail | 1 of 18 |
| `S141763` | Confirm with your password | _macros | 1 of 18 |
| `Sa36a5f` | Controller | legacy_mapping, st_new, st_preview | 8 of 18 |
| `S382b49` | Controller software versions this Release is for (optional) | new | 1 of 18 |
| `S3998a7` | Copies the descriptive fields into a new Draft in a Main Controller group (a new number is allocated at submit; this code's identifier is kept as the legacy reference). | detail | 1 of 18 |
| `S2fd88e` | Copy from previous revision | translations | 1 of 18 |
| `S5a3538` | Copy the signing secret now - it is shown only once: | integrations | 1 of 18 |
| `S05b81a` | Copy the token now - it is shown only once: | integrations | 1 of 18 |
| `S54b051` | Copy this code for another turbine platform. The copy is a new Draft that links back here and goes through the normal review. | detail | 1 of 18 |
| `Se58311` | Covered by | delegations | 1 of 18 |
| `S532c86` | covering | base | 18 of 18 |
| `S10b47f` | Covering colleague | delegations | 1 of 18 |
| `Sec0c4b` | Create change set | new | 1 of 18 |
| `Sf90e46` | Create delegation | delegations | 1 of 18 |
| `S78bb8b` | Create Drafts for the ticked programs | st_preview | 1 of 18 |
| `Seb54e4` | Create Main Controller draft from this Hub code | detail | 1 of 18 |
| `See8775` | Create MC draft | detail | 1 of 18 |
| `Sbbc876` | Create new codes | new | 1 of 18 |
| `S96b8ee` | Create profile | export_profiles | 1 of 18 |
| `Sbe8337` | Create Release | new | 1 of 18 |
| `S9611fe` | Create Sandbox Code | form | 1 of 18 |
| `S4b3c8e` | Create token | integrations | 1 of 18 |
| `S3c58c3` | Create variant | detail | 1 of 18 |
| `S3a9b50` | Create variant for | detail | 1 of 18 |
| `Saccf40` | Created | detail | 1 of 18 |
| `Seb6e02` | Created or revised | detail | 1 of 18 |
| `Sab92d0` | Cross-Domain Sign-Off | detail | 1 of 18 |
| `S8666fb` | Cross-domain sign-off (all time) | success_metrics | 1 of 18 |
| `S2d6dbc` | Cross-domain sign-off (last 90 days) | success_metrics | 1 of 18 |
| `S4fc0e2` | Current | detail, operations | 1 of 18 |
| `S405ab5` | current | detail | 1 of 18 |
| `S19dff4` | Current password | account_settings | 1 of 18 |
| `S3c3638` | d | _macros | 1 of 18 |
| `Sd87f47` | Dashboard | base, dashboard | 18 of 18 |
| `S41ba99` | Database schema | operations | 1 of 18 |
| `S5548ae` | days | catalogue_health | 1 of 18 |
| `Sd65ded` | Deactivate | review_checklist | 1 of 18 |
| `Sa26b9b` | Decide | approval_queue | 1 of 18 |
| `Scb307e` | Decide the selected requests in one sitting | detail | 1 of 18 |
| `S319493` | Decided by | detail | 1 of 18 |
| `S7f59a1` | Decision | detail | 1 of 18 |
| `Sc51568` | Decisions & Comments | detail | 1 of 18 |
| `S7505d6` | default | settings | 1 of 18 |
| `Sa8ec52` | Default audience | export_profiles | 1 of 18 |
| `S710ea3` | Delegation | base, delegations | 18 of 18 |
| `Sc25e7c` | Delegation and out-of-office cover | delegations | 1 of 18 |
| `S114c56` | Delegations | delegations | 1 of 18 |
| `Sa9ec7c` | Delete Permanently | detail | 1 of 18 |
| `S7d1c7a` | Delete Release | detail | 1 of 18 |
| `Sa2f8f5` | Delete this unpublished Release? | detail | 1 of 18 |
| `S524e17` | Deprecate | detail | 1 of 18 |
| `Secfb3f` | Deprecate replaced Hub codes | hub_consolidation | 1 of 18 |
| `S3c1c0d` | deprecation | detail | 1 of 18 |
| `S07bca2` | Deprecation / Archival | detail | 1 of 18 |
| `Sdee63d` | Deprecation Reason | detail | 1 of 18 |
| `S2e1371` | Deprecation reason | detail | 1 of 18 |
| `S34730e` | Deprecations | catalogue_health | 1 of 18 |
| `S55f8eb` | Description | detail, form, new, translations | 1 of 18 |
| `S388de6` | Description (optional) | detail, export_profiles, new | 1 of 18 |
| `Sb149ca` | Detect: a number from 10000 up is a Hub Controller program | st_new | 1 of 18 |
| `S441564` | differs in | st_preview | 1 of 18 |
| `S552a2b` | Documented reason | detail | 1 of 18 |
| `S9b1091` | Domain | detail | 1 of 18 |
| `S056839` | Download Error Report | detail | 1 of 18 |
| `S9468a1` | Download Full Database Backup | export_center | 1 of 18 |
| `S0e7766` | draft | hub_consolidation | 1 of 18 |
| `S23d33e` | Draft | detail | 1 of 18 |
| `S250750` | Draft CRs of mine blocked on a domain sign-off | dashboard | 8 of 18 |
| `S0d01e2` | E-mail | account_settings | 1 of 18 |
| `S3c7a50` | Edit Candidates | detail | 1 of 18 |
| `S64d64e` | Edit Draft | detail, form | 1 of 18 |
| `Sda2252` | effective | detail | 1 of 18 |
| `S120d93` | Effective Date | detail | 1 of 18 |
| `S19582d` | Effective dates | catalogue_health | 1 of 18 |
| `S05fc94` | Engineer | role badge | 18 of 18 |
| `Sc2e311` | entries | operations | 1 of 18 |
| `S11f957` | error | dry_run | 1 of 18 |
| `S805e86` | Errors | reconciliation | 1 of 18 |
| `Sc5497b` | Events | integrations | 1 of 18 |
| `Sefd55c` | Every audit entry carries a hash of its predecessor; a removed, reordered or edited entry breaks the chain. | operations | 1 of 18 |
| `Sd24ec2` | Every comment and decision on every change request of this status code, oldest first. Comments of withdrawn requests are kept in the Audit Log (action WITHDRAW). | detail | 1 of 18 |
| `Scc432e` | Every current status code in any lifecycle state, including unapproved Drafts. Every row and the file name carry a "Not for distribution — unapproved data" notice. | export_center | 1 of 18 |
| `S4e7cfe` | Every Hub code is deprecated - the group can be deactivated under Lookups. | hub_consolidation | 1 of 18 |
| `S7d06d0` | Every imported program becomes an ordinary Draft with the number it carries reserved. It still needs Cross-Domain Sign-Off, dual review and Chief Engineer approval before Release, and all Drafts of one import share a change set. | st_new | 1 of 18 |
| `S873802` | Every item must be confirmed to approve; rejecting needs no confirmation. | detail | 1 of 18 |
| `S2bac4d` | Every request is still decided on its own: it gets its own check that you did not write or already sign it, its own comment and its own audit entry. Requests you may not decide are reported and skipped. | detail | 1 of 18 |
| `S2e7908` | Every row is valid. Nothing has been created yet. | dry_run | 1 of 18 |
| `Sae0114` | Every row that passes validation becomes an ordinary Draft, subject to the full Cross-Domain Sign-Off, dual-review, and Chief Engineer approval cycle before it can be Released — import is a faster data-entry path, never a governance bypass. | new | 1 of 18 |
| `Sa49a78` | everyone | detail, export_center | 1 of 18 |
| `S7ea014` | Evidence | detail | 1 of 18 |
| `Seb01bf` | Examples | catalogue_health | 1 of 18 |
| `S4105cf` | exhausted | catalogue_health | 1 of 18 |
| `S6ac87f` | Expected | operations, reconciliation | 1 of 18 |
| `Sa99be3` | Expires | integrations | 1 of 18 |
| `Sf3e4fa` | Export | detail, export_center | 1 of 18 |
| `S517134` | export | export_verify | 1 of 18 |
| `See833c` | Export Center | base, export_center | 18 of 18 |
| `S5755f9` | Export CSV | detail | 1 of 18 |
| `Sbc3990` | Export JSON | detail | 1 of 18 |
| `S3dd7d5` | Export PDF | detail | 1 of 18 |
| `S6f6f72` | Export Profiles | base, export_profiles | 18 of 18 |
| `Sf7e949` | Export profiles | export_profiles | 1 of 18 |
| `S93f3f8` | Export XLSX | detail | 1 of 18 |
| `S53af3d` | Exported file | export_center | 1 of 18 |
| `S32aa79` | Exports of this Release | detail | 1 of 18 |
| `S09fef5` | Failed | detail | 1 of 18 |
| `Sdd7b7e` | failed validation | detail | 1 of 18 |
| `Sc326a4` | Field | _macros, detail, form | 1 of 18 |
| `Sd106a6` | Field comments | detail | 1 of 18 |
| `S0a0f8a` | Field differences | _macros | 1 of 18 |
| `S874581` | field(s) | software_versions | 1 of 18 |
| `S2c3caf` | File | detail, export_verify, operations | 1 of 18 |
| `Sec1717` | File (.csv or .xlsx) | new | 1 of 18 |
| `S32ac07` | File (.csv/.xlsx with status_code_identifier, occurrences) | fleet_feedback | 1 of 18 |
| `S4bc4cc` | file(s) | st_preview | 1 of 18 |
| `Sd7decf` | Filter | legacy_mapping, list | 18 of 18 |
| `S759686` | Filter status codes | list | 8 of 18 |
| `S962725` | Filter the list | st_preview | 1 of 18 |
| `S57e8be` | Finding | catalogue_health | 1 of 18 |
| `Se0996a` | first | detail, form | 1 of 18 |
| `S9eac73` | first bad entry | operations | 1 of 18 |
| `Sc469c3` | fixed: it identifies you, also for the Windows sign-in | account_settings | 1 of 18 |
| `Scd938f` | Fleet Feedback | base, fleet_feedback | 18 of 18 |
| `S625adf` | Fleet feedback | fleet_feedback | 1 of 18 |
| `S041a5d` | Format | detail, export_center | 1 of 18 |
| `S3f6605` | From | delegations, software_versions | 1 of 18 |
| `S9e3c65` | From revision | detail | 1 of 18 |
| `S3cd0e5` | Full-Database Export | export_center | 1 of 18 |
| `S1ffae6` | Functional Group | approval_queue | 1 of 18 |
| `Sdf2aa0` | Functional Group / Subgroup | builder | 1 of 18 |
| `S2fa1f7` | Functional Subgroup | detail, form, list | 8 of 18 |
| `Sced1ce` | Functional System Group | form, list | 8 of 18 |
| `S1150a1` | Gaps | catalogue_health | 1 of 18 |
| `S7a2ec1` | generations kept | operations | 1 of 18 |
| `S171a06` | Group | catalogue_health | 1 of 18 |
| `S8cd536` | Group / Subgroup | st_preview | 1 of 18 |
| `Sac7f67` | headers only | new | 1 of 18 |
| `Sc47ae1` | Help | base, help | 18 of 18 |
| `S90ccd6` | History | detail | 1 of 18 |
| `Sb17ab7` | Hub code | hub_consolidation | 1 of 18 |
| `S036d00` | Hub codes and their replacements | hub_consolidation | 1 of 18 |
| `S2fa8ef` | Hub Consolidation | base, hub_consolidation | 18 of 18 |
| `Sb4aadc` | Hub Controller | catalogue_health, legacy_mapping | 1 of 18 |
| `S3b9e43` | Hub Controller (legacy numbers, mapped to the new ones) | st_new | 1 of 18 |
| `Sfec8b7` | Hub Controller group | detail | 1 of 18 |
| `Sc50c53` | Hub Controller to Main Controller consolidation | hub_consolidation | 1 of 18 |
| `Scd189f` | Hub group | hub_consolidation | 1 of 18 |
| `S3c883f` | I have reviewed these dependants | detail | 1 of 18 |
| `S06b6ac` | Identifier | approval_queue, builder, detail, mine | 1 of 18 |
| `Sfd327d` | Identifier, title, description | list | 8 of 18 |
| `Sa5262b` | If the Hub Controller leaves the hardware setup, its codes are defined anew on the Main Controller side. Create an MC draft from an HC code on its detail page (Actions); this report shows how far each has come. Nothing is renumbered. | hub_consolidation | 1 of 18 |
| `Sdb0f93` | Immutable once allocated (BR-001). | form | 1 of 18 |
| `Sd6fbc9` | Import | fleet_feedback, st_preview | 1 of 18 |
| `Se28265` | Import check | dry_run | 1 of 18 |
| `S8ac724` | Import from .st files | base, new | 18 of 18 |
| `S4bc96f` | Import Job | detail | 1 of 18 |
| `S59f4f3` | Import occurrence counts | fleet_feedback | 1 of 18 |
| `S50565a` | Import progress | detail | 1 of 18 |
| `Sd7333f` | Import status codes from .st files | st_new | 1 of 18 |
| `Sa671a4` | imported | reconciliation | 1 of 18 |
| `S434eb2` | Imported | reconciliation | 1 of 18 |
| `Sda104a` | Imported (legacy numbers on file) | reconciliation | 1 of 18 |
| `S4c518c` | Imported rows are ordinary Drafts — they still require Cross-Domain Sign-Off, dual review, and Chief Engineer approval before Release. | detail | 1 of 18 |
| `S7b6084` | In a deployment the browser hands over your Windows identity and you are signed in without this page. Here, type the identity the Windows gateway would have supplied. | login_windows | 1 of 18 |
| `Sd436a3` | inactive | export_profiles | 1 of 18 |
| `S11c54a` | Include | builder | 1 of 18 |
| `Sd028de` | Incomplete, e.g. | success_metrics | 1 of 18 |
| `S35abd8` | Informative only: a future effective date makes the release builder warn; nothing changes state on its own. | detail | 1 of 18 |
| `S54c522` | Initiate Deprecation | detail | 1 of 18 |
| `S1ed126` | Insight | base | 18 of 18 |
| `Sa7881c` | Integrations | base, integrations | 18 of 18 |
| `S9407e9` | Interface language | account_settings | 1 of 18 |
| `Sba2a88` | Internal network only. Tokens can only read; webhooks can only reach private addresses. | integrations | 1 of 18 |
| `S7c4f77` | issued | legacy_mapping | 1 of 18 |
| `S9ab178` | it was changed after export, or it came from somewhere else | export_verify | 1 of 18 |
| `Secdda5` | Item | review_checklist | 1 of 18 |
| `S92d001` | Item Count | detail | 1 of 18 |
| `S44d25b` | Items | list | 8 of 18 |
| `S4b4bb9` | Items a Reviewer must confirm before approving. An item applies to one Functional System Group or to all. With no items nothing is required. | review_checklist | 1 of 18 |
| `S7d2a7b` | Justification | detail | 1 of 18 |
| `S0a2f2c` | landscape | export_profiles | 1 of 18 |
| `S89b86a` | Language | account_settings, base, detail, export_profiles | 18 of 18 |
| `S1ed342` | Last delivery | integrations | 1 of 18 |
| `S333c63` | Last run | operations | 1 of 18 |
| `Sf1109d` | Last used | integrations | 1 of 18 |
| `S3f0b1a` | Last verified | operations | 1 of 18 |
| `Se51105` | Last verified backup | operations | 1 of 18 |
| `S1481d0` | latest | detail, form | 1 of 18 |
| `S12c0f1` | left | catalogue_health | 1 of 18 |
| `S8ae1c3` | Left | catalogue_health | 1 of 18 |
| `Sa7b60b` | Left % | catalogue_health | 1 of 18 |
| `S82ba98` | Legacy library migration progress | reconciliation | 1 of 18 |
| `Sfd5ec0` | Legacy mapping | base, legacy_mapping, new, st_new | 18 of 18 |
| `Sdd6555` | Legacy no. | hub_consolidation, legacy_mapping, st_preview | 1 of 18 |
| `S81f567` | Legacy number to new identifier | legacy_mapping | 1 of 18 |
| `S64b267` | legacy number, identifier or name | legacy_mapping | 1 of 18 |
| `S693272` | Legacy Reference Number | detail | 1 of 18 |
| `Sd7635c` | Legacy Reference Number (optional) | form | 1 of 18 |
| `Sad60c5` | level | _role | 18 of 18 |
| `S3c1c8a` | Library Import | base, new, st_new | 18 of 18 |
| `S033df3` | Lifecycle | list | 8 of 18 |
| `Sc54d33` | Lifecycle states | help | 1 of 18 |
| `Sb4cad6` | Link to this view | list | 8 of 18 |
| `Sdde41f` | Listed in manifest | export_verify | 1 of 18 |
| `Sfbee55` | live codes | fleet_feedback | 1 of 18 |
| `S43d5c5` | Loadless Spinning Permitted | detail, form | 1 of 18 |
| `Sf7c400` | Log in | login | 18 of 18 |
| `S6e78c9` | Log out | base | 18 of 18 |
| `S193786` | Logical Node | detail | 1 of 18 |
| `S3871af` | Lookups | base | 18 of 18 |
| `S36a883` | low | catalogue_health | 1 of 18 |
| `S1b123c` | Main Controller | catalogue_health, legacy_mapping, st_new | 1 of 18 |
| `S578b78` | Main Controller group | detail | 1 of 18 |
| `Sefd197` | Main navigation | base | 18 of 18 |
| `Seb9a6d` | Manage translations | detail | 1 of 18 |
| `Sc5beef` | manifest | detail | 1 of 18 |
| `S45ea95` | Manifest signature | export_verify | 1 of 18 |
| `Sc6ff17` | MANIFEST.json (optional) | export_center | 1 of 18 |
| `S1b8316` | Mark all as read | notifications | 1 of 18 |
| `Sc1ee86` | Mark as read | notifications | 1 of 18 |
| `Sf9896c` | Mark resolved | detail, form | 1 of 18 |
| `S48926c` | Master list (.csv/.xlsx with a legacy_reference_number column) | reconciliation | 1 of 18 |
| `S9418f1` | median of | success_metrics | 1 of 18 |
| `Sceafa9` | met | success_metrics | 1 of 18 |
| `S801c9a` | Migration progress | new, reconciliation | 1 of 18 |
| `S92185d` | Missing | catalogue_health | 1 of 18 |
| `S040779` | MISSING | fleet_feedback | 1 of 18 |
| `S57282a` | Missing expected data | catalogue_health | 1 of 18 |
| `S17fc39` | Missing legacy numbers | reconciliation | 1 of 18 |
| `Sa7b93d` | Mode | detail, new, reconciliation | 1 of 18 |
| `Se78fe7` | mode | dry_run | 1 of 18 |
| `S3da032` | Most frequent | fleet_feedback | 1 of 18 |
| `S617eec` | My Change Requests | base, mine | 18 of 18 |
| `Se0688f` | My Open Change Requests | dashboard | 8 of 18 |
| `S709a23` | Name | export_profiles, integrations, legacy_mapping, list | 18 of 18 |
| `Sea62b4` | Name a colleague who may take your decisions while you are away. They act as themselves: the audit trail shows both of you, and the segregation-of-duties rules apply to them personally. Only the decision actions are covered - nothing else you can do. | delegations | 1 of 18 |
| `S47e0b6` | Name of the change set (optional) | st_preview | 1 of 18 |
| `S7c1caf` | Never fired | fleet_feedback | 1 of 18 |
| `Se248d5` | New change set | list, new | 8 of 18 |
| `S31a335` | new code | detail | 1 of 18 |
| `S60fe6c` | new codes without a legacy number (n/a) | legacy_mapping | 1 of 18 |
| `S7d97d2` | New delegation | delegations | 1 of 18 |
| `Sf26140` | New identifier | legacy_mapping, st_preview | 1 of 18 |
| `S6640a6` | New number of Hub Controller programs | st_new | 1 of 18 |
| `Sd850ee` | New password | account_settings | 1 of 18 |
| `Sca36da` | New profile | export_profiles | 1 of 18 |
| `Se75aa1` | New Release | list, new | 8 of 18 |
| `Sdbb388` | New Sandbox Code | base | 18 of 18 |
| `S2d3840` | New Sandbox Status Code | form | 1 of 18 |
| `Sd85719` | New Status Code | base, form, list | 18 of 18 |
| `Sbc9819` | Next | _macros | 1 of 18 |
| `S816c52` | No | detail, export_verify, list, review_checklist | 18 of 18 |
| `S12b701` | No Approved candidates match this Release's scope. | builder | 1 of 18 |
| `Sa62a99` | No backup directory is configured (BACKUP_DIR). Schedule `flask backup-db` as described in the deployment guide. | operations | 1 of 18 |
| `S02bd56` | No candidates (or no data imported yet). | fleet_feedback | 1 of 18 |
| `S362336` | No change requests in this set yet. | detail | 1 of 18 |
| `Se5076c` | No change sets yet. | list | 8 of 18 |
| `S1c1f74` | No checklist items configured. | review_checklist | 1 of 18 |
| `S7e1129` | No comments or decisions yet. | detail | 1 of 18 |
| `S207b24` | No comments yet. | detail | 1 of 18 |
| `S3b0b47` | No data yet. | fleet_feedback, success_metrics | 1 of 18 |
| `S30d2d7` | No delegations. | delegations | 1 of 18 |
| `S7cb594` | No deprecation/archival/deletion actions are available for this record's current state. | detail | 1 of 18 |
| `Sf502f2` | No evidence attached. | detail | 1 of 18 |
| `Sec1732` | No field comments. | detail | 1 of 18 |
| `S27cea7` | No field differences. | _macros | 1 of 18 |
| `S845a2b` | No Hub Controller codes yet. | hub_consolidation | 1 of 18 |
| `Sf573c8` | no number yet | legacy_mapping | 1 of 18 |
| `S32f96c` | No programs found. | st_preview | 1 of 18 |
| `S1b874a` | No published Releases yet. | export_center | 1 of 18 |
| `S08f84b` | No record of this exact file | export_verify | 1 of 18 |
| `S0fa9cd` | No Released codes yet. | success_metrics | 1 of 18 |
| `Sd32c03` | No releases yet. | list | 8 of 18 |
| `Sc3af43` | No saved searches yet. | list | 8 of 18 |
| `S7877c5` | No status code carries a legacy number yet. | legacy_mapping | 1 of 18 |
| `S0cb400` | No status codes match these filters. | list | 8 of 18 |
| `S6ad77d` | No tokens. | integrations | 1 of 18 |
| `S082244` | No webhooks. | integrations | 1 of 18 |
| `Sb6fcd9` | No Windows identity reached the application. Open it through the organisation address, from a computer signed in to the company network. | login_windows | 1 of 18 |
| `S4bddd5` | Nobody can review it until it is submitted. | detail | 1 of 18 |
| `S2d8f60` | node value | detail | 1 of 18 |
| `S71f8e7` | none | detail, form | 1 of 18 |
| `Sb8e95b` | None found. | catalogue_health | 1 of 18 |
| `S9a9707` | None. | catalogue_health, software_versions | 1 of 18 |
| `S5af0a0` | Not for distribution | export_center | 1 of 18 |
| `Sa8c86d` | NOT met | success_metrics | 1 of 18 |
| `S357953` | NOT OK | export_verify | 1 of 18 |
| `Sc914e0` | Not yet assigned | catalogue_health, detail, hub_consolidation, list | 8 of 18 |
| `S8f9967` | Not yet assigned — fixed on Submit for Review | form | 1 of 18 |
| `S4467d4` | Not yet published | detail | 1 of 18 |
| `S23402a` | Not yet submitted. | detail | 1 of 18 |
| `Sb23ab5` | Nothing is awaiting Review sign-off. | review_queue | 1 of 18 |
| `S8e70d2` | Nothing is awaiting your approval. | approval_queue | 1 of 18 |
| `Sc5e8fc` | Nothing is stalled. | stalled | 1 of 18 |
| `Se94865` | Notices | base, dashboard, notifications | 18 of 18 |
| `Sb7baa1` | Number | legacy_mapping | 8 of 18 |
| `Scd7430` | Number of Times Repeated | detail, form | 1 of 18 |
| `Sf949fb` | Number ranges running out | dashboard | 8 of 18 |
| `S8e20aa` | number, name, file ... | st_preview | 1 of 18 |
| `S58c916` | Number-range capacity | catalogue_health | 1 of 18 |
| `S7b4cb2` | Numbers are never reused, so a gap is lost capacity - listed for information. | catalogue_health | 1 of 18 |
| `Sd5ab17` | Occurrence counts per status code, aggregated and anonymised, imported from the internal monitoring side. They show which codes never fire (candidates for deprecation) and which fire most (candidates for better remedy text). | fleet_feedback | 1 of 18 |
| `Sf52555` | Occurrences | fleet_feedback | 1 of 18 |
| `Sde04fa` | of | detail, fleet_feedback, success_metrics | 1 of 18 |
| `S19f611` | Offline lookup (HTML) | detail | 1 of 18 |
| `S2ff2ae` | Offline lookup + manifest (ZIP) | detail | 1 of 18 |
| `S9ce3bd` | OK | export_verify | 1 of 18 |
| `S7a85f4` | ok | catalogue_health | 1 of 18 |
| `S464e43` | on track | _macros | 1 of 18 |
| `S12aa03` | only translated codes | detail | 1 of 18 |
| `S5fc7e3` | open | detail | 1 of 18 |
| `Scf9b77` | Open | notifications | 1 of 18 |
| `S138665` | Open deprecation requests | hub_consolidation | 1 of 18 |
| `Sc8df93` | Open deprecation requests for all replaced Hub codes of this group? | hub_consolidation | 1 of 18 |
| `Sf61187` | Open New Revision | detail | 1 of 18 |
| `S82890d` | Open review comments | form | 1 of 18 |
| `S448e3d` | Open reviews | stalled | 1 of 18 |
| `S533e22` | Opens a deprecation request for every Released Hub code of the group whose Main Controller replacement is Released. Each request still needs review and approval. | hub_consolidation | 1 of 18 |
| `S578c53` | Opens a Draft that must go through the full dual-review and Chief Engineer approval cycle before it takes effect. | detail | 1 of 18 |
| `Sf71701` | opens a new Draft on the same number | st_preview | 1 of 18 |
| `Sffc13f` | opens a new revision | st_preview | 1 of 18 |
| `Sa1fdaa` | Operations | base, operations | 18 of 18 |
| `S175835` | or | login | 1 of 18 |
| `Sc0eff1` | Or a whole folder | st_new | 1 of 18 |
| `S36463a` | other code(s) still refer to this one: | detail | 1 of 18 |
| `S9734ac` | Other codes that refer to this one. Review them before deprecating it. | detail | 1 of 18 |
| `S1fcf54` | OUTDATED - run flask db upgrade | operations | 1 of 18 |
| `S8a5285` | Overall | export_verify | 1 of 18 |
| `Sba2fff` | overdue | _macros, dashboard, success_metrics | 8 of 18 |
| `S780d35` | Override identifier (migration / reservation only) | detail | 1 of 18 |
| `S89ff31` | Owner | detail | 1 of 18 |
| `S2d20ee` | Package overview | detail | 1 of 18 |
| `S600584` | Pages | _macros | 1 of 18 |
| `S8be3c9` | Password | login | 18 of 18 |
| `S781961` | Pause | integrations | 1 of 18 |
| `S8af321` | PDF orientation | export_profiles | 1 of 18 |
| `Sbb23e2` | PDF title page | export_profiles | 1 of 18 |
| `S96f608` | Pending | detail, review_queue | 1 of 18 |
| `S170a28` | Period | fleet_feedback | 1 of 18 |
| `Sde2f48` | Period end | fleet_feedback | 1 of 18 |
| `Se1f35c` | Period start | fleet_feedback | 1 of 18 |
| `Sc62d67` | period(s) | fleet_feedback | 1 of 18 |
| `Sc983b6` | Pick a profile (columns and labels), an audience, a language or a software version. Every file comes with a manifest of SHA-256 hashes; "bundle" packs both into one ZIP. | detail | 1 of 18 |
| `S72383d` | Planned dates | detail | 1 of 18 |
| `Sfb14b0` | Planned deprecation date | detail | 1 of 18 |
| `S611331` | Planned deprecation date (optional) | form | 1 of 18 |
| `S1359d4` | Planned effective | builder | 1 of 18 |
| `S00e733` | Planned effective date | detail | 1 of 18 |
| `S75ee24` | Planned effective date (optional) | form | 1 of 18 |
| `Sf6fea0` | Planned in the future: | builder | 1 of 18 |
| `S73b158` | Planned in the next | catalogue_health | 1 of 18 |
| `Sfc8d58` | Platform variant | detail | 1 of 18 |
| `Scd8926` | Platform variants | detail | 1 of 18 |
| `S810099` | Please check | _macros | 1 of 18 |
| `S25c604` | portrait | export_profiles | 1 of 18 |
| `S90eceb` | Prefix | integrations | 1 of 18 |
| `S6daf16` | Preview: status codes from .st files | st_preview | 1 of 18 |
| `S50f942` | Previous | _macros | 1 of 18 |
| `Sfe5310` | Probable inconsistencies | catalogue_health | 1 of 18 |
| `S044f10` | Problems and warnings | dry_run, st_preview | 1 of 18 |
| `S141f0c` | Processing in the background... | detail | 1 of 18 |
| `Sd2bc4a` | Produced by this system | export_verify | 1 of 18 |
| `Sff4fc0` | Profile | detail, export_center | 1 of 18 |
| `S94ddc1` | Program files (.st) or a ZIP | st_new | 1 of 18 |
| `Sa4ab7b` | Program References | detail | 1 of 18 |
| `S39c8c4` | Program References — Advanced, controller firmware programs | form | 1 of 18 |
| `S15a21a` | program(s) | st_preview | 1 of 18 |
| `Se58289` | Programs found in the uploaded files | st_preview | 1 of 18 |
| `Sd99e2a` | Proposal 1: five-digit numbers (11000 and up) | st_new | 1 of 18 |
| `S2744b0` | Proposal 2: inside the Main Controller scheme | st_new | 1 of 18 |
| `S70cbd1` | Proposed | detail | 1 of 18 |
| `S05c31a` | Proposed — confirmed by Administrator at review | form | 1 of 18 |
| `S565640` | Publish | builder | 1 of 18 |
| `S5659c7` | Publish Release | builder | 1 of 18 |
| `Se2bd5e` | Publish this Release? This cannot be undone. | builder | 1 of 18 |
| `S483bf2` | Published | detail, list | 8 of 18 |
| `Sd3dfb5` | Published releases | export_center | 1 of 18 |
| `Se77605` | Published Releases only. Pick a Release to export its Released contents; the Release page offers profiles, audiences, languages, release notes and the offline lookup page. | export_center | 1 of 18 |
| `Sec31cb` | Publishing transitions every included revision from Approved to Released and locks this Release permanently. | builder | 1 of 18 |
| `S367f8a` | Quick start for the other roles | help | 1 of 18 |
| `S9de664` | Quick start for your role | help | 1 of 18 |
| `Sa16c5b` | Range | catalogue_health | 1 of 18 |
| `Se25b5d` | Raw SQLite backup of the complete governed dataset. Handle per data-at-rest access-control requirements — this file carries the same sensitivity as the live database. | export_center | 1 of 18 |
| `S67640d` | Read files and preview | st_new | 1 of 18 |
| `S75c053` | ready | st_preview | 1 of 18 |
| `S55843f` | Reassign | stalled | 1 of 18 |
| `Sca5d2f` | Recent import jobs | reconciliation | 1 of 18 |
| `Sf5ca9d` | Recorded exports | detail | 1 of 18 |
| `S83fd6e` | red after | _macros, stalled | 1 of 18 |
| `S298d36` | Reference number in the separate escalation code pool — not a CSCM Tool status code. | form | 1 of 18 |
| `Sa3f757` | Reinstate to Released | detail | 1 of 18 |
| `S3238ca` | Reinstatement reason | detail | 1 of 18 |
| `S2b03b5` | Reject | detail | 1 of 18 |
| `S27fb5c` | Reject selected | detail | 1 of 18 |
| `S045c2c` | Related codes | detail | 1 of 18 |
| `S9e0128` | Related codes (optional) | form | 1 of 18 |
| `S33a5a7` | Relation | detail | 1 of 18 |
| `Sd41f56` | Release | export_center | 1 of 18 |
| `Sb1fe0b` | Release Builder | builder | 1 of 18 |
| `S3a7272` | Release Export | export_center | 1 of 18 |
| `Se1fcfa` | Release notes (CSV) | detail | 1 of 18 |
| `Sa26c4a` | Release notes (Markdown) | detail | 1 of 18 |
| `S9b44a2` | Release notes (PDF) | detail | 1 of 18 |
| `S3dfa01` | Release notes and offline lookup | detail | 1 of 18 |
| `Sdcddb7` | Release notes list what was added, changed (field by field) and deprecated since the previous Release. The offline page is one self-contained HTML file for use at the turbine without a connection. | detail | 1 of 18 |
| `Sc011aa` | Released revisions have the full trail: submit, both review sign-offs, approval and publish. | success_metrics | 1 of 18 |
| `S8fa41d` | Releases | base, dashboard, list | 18 of 18 |
| `S0544a3` | Reload this page to see the progress. | detail | 1 of 18 |
| `S99e347` | Remedy | detail | 1 of 18 |
| `S86971e` | Remedy / recommended action (optional) | form, translations | 1 of 18 |
| `Sbdf5fd` | Remedy text | fleet_feedback | 1 of 18 |
| `Se96390` | Remove | detail, list | 18 of 18 |
| `S400ad0` | Remove this file? | detail | 1 of 18 |
| `S69992f` | removed | software_versions | 1 of 18 |
| `Sb5e77c` | Removed | software_versions | 1 of 18 |
| `S51c87d` | Repeated Over the Course | detail, form | 1 of 18 |
| `S4c1aa6` | Repeated-Error Escalation | detail | 1 of 18 |
| `S2202ce` | Repeated-Error Escalation (optional) | form | 1 of 18 |
| `Sc385e3` | Replacement | hub_consolidation | 1 of 18 |
| `S4aed03` | Request | detail | 1 of 18 |
| `Sf3421a` | Request a Sign-Off | detail | 1 of 18 |
| `Sc26bf6` | Requested | detail | 1 of 18 |
| `Sf7194e` | Requests | list | 8 of 18 |
| `S950eaf` | Requests waiting longer than the configured thresholds. Review: amber after | stalled | 1 of 18 |
| `Sc3fed1` | reserved | legacy_mapping | 1 of 18 |
| `S619e87` | Reset Delay | detail, form | 1 of 18 |
| `S026ab2` | resolved | detail | 1 of 18 |
| `S5faa59` | Result | dry_run | 1 of 18 |
| `S37a530` | result | list | 8 of 18 |
| `Sec0298` | Result per row | dry_run | 1 of 18 |
| `Scdf7e9` | results | list | 8 of 18 |
| `Sb3bd0b` | Resume | integrations | 1 of 18 |
| `S68c61f` | Rev # | detail | 1 of 18 |
| `Se29a79` | Review | review_queue, success_metrics | 1 of 18 |
| `Sf490d7` | Review Checklist | base, review_checklist | 18 of 18 |
| `Se4758b` | Review checklist | detail, review_checklist | 1 of 18 |
| `S437a0d` | Review Queue | base, review_queue | 18 of 18 |
| `Sa74f16` | Reviewer | approval_queue, detail, review_queue, role badge | 18 of 18 |
| `S4b9d6e` | Reviewer comment | form | 1 of 18 |
| `S7bfca8` | Reviewer sign-off | detail | 1 of 18 |
| `S0bc91e` | Reviewer workload | stalled | 1 of 18 |
| `Sc0d28c` | Reviewers who are out of office (they have delegated) are left out. | stalled | 1 of 18 |
| `S3beb9a` | Revision | detail | 1 of 18 |
| `Sa72973` | Revision Fields | detail | 1 of 18 |
| `S0be720` | Revoke | delegations, integrations | 1 of 18 |
| `S8375cd` | revoked | integrations | 1 of 18 |
| `Sc3f104` | Role | delegations | 1 of 18 |
| `S47dcc2` | Roles | help | 1 of 18 |
| `S9bf7a8` | Row | dry_run | 1 of 18 |
| `S3ff0b0` | row(s) have problems. Nothing has been created. | dry_run | 1 of 18 |
| `Sfc1d6a` | row(s) imported as Drafts | detail | 1 of 18 |
| `S52d0b3` | Rows | detail, reconciliation | 1 of 18 |
| `S6c30d2` | rows | dry_run | 1 of 18 |
| `S4f581e` | Sandbox only | list | 8 of 18 |
| `S028f6d` | Sandbox status code — never numbered from a real range, never released, deletable. | form | 1 of 18 |
| `Sc03132` | Save as Draft | form | 1 of 18 |
| `S5997c5` | Save Candidate Set | builder | 1 of 18 |
| `Scc1316` | Save Draft | form | 1 of 18 |
| `Se522f0` | Save draft translation | translations | 1 of 18 |
| `Saf5a10` | Save language | account_settings | 1 of 18 |
| `Sda38c6` | Save planned dates | detail | 1 of 18 |
| `Sf597c0` | Save profile | export_profiles | 1 of 18 |
| `S1db747` | Save search | list | 8 of 18 |
| `S913aba` | Save settings | settings | 1 of 18 |
| `Scc8a3c` | Save targets | builder | 1 of 18 |
| `Sff86e9` | Save the current filters as | list | 8 of 18 |
| `Sed1d84` | Saved searches | list | 8 of 18 |
| `S6a6d41` | Saving again keeps your entries and replaces the stored values. | form | 1 of 18 |
| `S13c61c` | Scope Filter | detail | 1 of 18 |
| `S154964` | Scope: Functional System Group (optional) | new | 1 of 18 |
| `Sc23540` | Scopes | integrations | 1 of 18 |
| `Sbce064` | Search | legacy_mapping, list | 18 of 18 |
| `S6605c0` | Search and filter all governed status codes | dashboard | 8 of 18 |
| `S859822` | Select | detail, mine | 1 of 18 |
| `S81448f` | select | detail, form | 1 of 18 |
| `S535bd8` | Select a Functional System Group first | detail, form | 1 of 18 |
| `S913aff` | Select all | mine | 1 of 18 |
| `S0723bf` | Select all programs that are ready | st_preview | 1 of 18 |
| `S85e466` | Select the Approved, non-sandbox revisions to include, then Save. Publishing is immutable — a correction requires a new Release. | builder | 1 of 18 |
| `Sb3138e` | Sent on release publish as JSON with the header X-CSCM-Signature: sha256=<HMAC of the body with the secret>. | integrations | 1 of 18 |
| `S3871fb` | Set Delay | detail, form | 1 of 18 |
| `Sc7f73b` | Settings | base, settings | 18 of 18 |
| `S79075b` | Shaped export | detail | 1 of 18 |
| `Sd97d1e` | Show | software_versions | 1 of 18 |
| `S991f8c` | Sign in as this Windows user | login_windows | 1 of 18 |
| `Sd876ad` | Sign in with Windows | login, login_windows | 1 of 18 |
| `S5e5039` | Sign Off This Domain | detail | 1 of 18 |
| `Sfdef49` | Sign-Off Status | detail | 1 of 18 |
| `S6e3665` | Signed | detail, review_queue | 1 of 18 |
| `Sddfd83` | Signed by | detail | 1 of 18 |
| `Sc5a911` | simulated | login | 1 of 18 |
| `S985cf9` | Simulation. | login_windows | 1 of 18 |
| `Sb71523` | Size | detail | 1 of 18 |
| `Sbe504f` | Skip to main content | base | 18 of 18 |
| `S57e8a7` | slow | _macros, success_metrics | 1 of 18 |
| `Sff44d2` | Software Version | detail | 1 of 18 |
| `S169bf7` | Software version | detail, software_versions | 1 of 18 |
| `S932745` | Software Version (optional) | form | 1 of 18 |
| `S42ea2e` | Software Versions | software_versions | 1 of 18 |
| `S6da13a` | Source | detail, fleet_feedback | 1 of 18 |
| `Sd3c56b` | source language | detail, export_profiles | 1 of 18 |
| `Scb0b87` | source language text of revision | translations | 1 of 18 |
| `Sca6d0e` | Stage | stalled | 1 of 18 |
| `Sb1bafe` | Stalled change requests | stalled | 1 of 18 |
| `Sa42252` | Stalled Requests | base, stalled | 18 of 18 |
| `S916385` | Stalled requests | dashboard | 8 of 18 |
| `S4b57f3` | Standard references (optional) | form | 1 of 18 |
| `Sb3883f` | Standards | detail | 1 of 18 |
| `Sd22e9f` | Start from the template: | new | 1 of 18 |
| `Sfaa9e7` | Started | detail, reconciliation | 1 of 18 |
| `Sa72502` | State | detail, hub_consolidation, legacy_mapping, mine | 1 of 18 |
| `Sbae7d5` | Status | catalogue_health, detail, list, reconciliation | 18 of 18 |
| `S82b5dd` | Status & Timing | form | 1 of 18 |
| `Se246b6` | Status Category | detail, form, list | 8 of 18 |
| `S234237` | Status category of the new codes | st_new | 1 of 18 |
| `S779953` | Status Code for Repeated Error | detail, form | 1 of 18 |
| `S613b74` | Status Code Identifier | form | 1 of 18 |
| `S7f5583` | Status Codes | base, list | 18 of 18 |
| `S20bff1` | Status codes | list | 18 of 18 |
| `S3c0e8a` | StCd Owner | role badge | 18 of 18 |
| `S98a377` | Still a Draft. | detail | 1 of 18 |
| `S4f437c` | Still missing | reconciliation | 1 of 18 |
| `S5b05b1` | Stored now | form | 1 of 18 |
| `Sfe07e9` | Subgroup | catalogue_health | 1 of 18 |
| `S75a804` | subgroup(s) are running out of numbers: | catalogue_health | 1 of 18 |
| `S9ddbd3` | Submission to approval (all time) | success_metrics | 1 of 18 |
| `S1c0f84` | Submission to approval (last 90 days) | success_metrics | 1 of 18 |
| `S123f6c` | Submit for Review | detail | 1 of 18 |
| `S2e0035` | Submitted | mine | 1 of 18 |
| `Sa4a761` | Success Metrics | base, success_metrics | 18 of 18 |
| `Se08405` | Success metrics | success_metrics | 1 of 18 |
| `S3dca68` | Superseded by Status Code id (optional) | detail | 1 of 18 |
| `S0e8a3a` | target | success_metrics | 1 of 18 |
| `S08e643` | Target software version | detail, list | 8 of 18 |
| `Sfda98f` | Target software version (optional) | new | 1 of 18 |
| `Sd64b6e` | Target software versions | builder, detail | 1 of 18 |
| `Sa55a27` | Terms | help | 1 of 18 |
| `Sc3328c` | Text | review_checklist | 1 of 18 |
| `S9e0005` | The audit chain is BROKEN | operations | 1 of 18 |
| `S8bdea8` | The audit chain is intact | operations | 1 of 18 |
| `Sce489f` | The author gets any required cross-domain sign-offs, then submits the change request for review. | help and messages | 1 of 18 |
| `S8fc804` | The author has to submit it for review before the Reviewer or Administrator can see it. | detail | 1 of 18 |
| `S1cdbdd` | The Chief Engineer approves or rejects. Approval makes the revision Approved (or Deprecated for a deprecation request). | help and messages | 1 of 18 |
| `S94bc64` | The current set of every Released status code, independent of any single Release. | export_center | 1 of 18 |
| `S969b52` | The e-mail address of the account is the user principal name; a name with a Windows domain in front needs WINDOWS_AUTH_EMAIL_DOMAIN or a matching user name. | login_windows | 1 of 18 |
| `S689b33` | The full manual is docs/23-user-manual.md in the project folder; the glossary below is the same one the tooltips use. | help | 1 of 18 |
| `S9a1b35` | The pre-migration status code number, if any — for traceability only, never the governed StCd identifier. | form | 1 of 18 |
| `Sde7a5b` | The program files do not carry a category; you can change it in each Draft. | st_new | 1 of 18 |
| `S05975b` | The targets the business case promises, measured from the timestamps the tool already keeps. Business days are Monday to Friday. | success_metrics | 1 of 18 |
| `S091814` | This change request has reached a terminal decision state | detail | 1 of 18 |
| `S6d5708` | This is the one truly irreversible action in the system. Type the identifier to confirm. | detail | 1 of 18 |
| `S768e0c` | Title | approval_queue, builder, detail, fleet_feedback | 1 of 18 |
| `Sae79ea` | To | software_versions | 1 of 18 |
| `Sb55f1f` | To revision | detail | 1 of 18 |
| `S8ad830` | Translations | base, detail, overview, translations | 1 of 18 |
| `Seaf576` | Trigger Snapshot | detail, form | 1 of 18 |
| `S285ec8` | Troubleshooting | detail, form | 1 of 18 |
| `Se90eb0` | Turbine Platform | list | 8 of 18 |
| `Sa6dac4` | Turbine Platform (at least one required before Submit for Review) | form | 1 of 18 |
| `S8f4c21` | Turbine platforms | st_new | 1 of 18 |
| `S3deb74` | Type | detail, mine, review_queue | 1 of 18 |
| `Sb5e264` | Type the identifier to confirm | detail | 1 of 18 |
| `S86b1e7` | Typos are tolerated: "convertor" still finds "converter". | list | 1 of 18 |
| `S391d68` | unassigned | detail, stalled | 1 of 18 |
| `S8012ff` | unchanged | dry_run | 1 of 18 |
| `S9851cb` | Unmatched rows | fleet_feedback | 1 of 18 |
| `S1b9aeb` | unread | base, dashboard | 18 of 18 |
| `Sd5dcf0` | Until (inclusive) | delegations | 1 of 18 |
| `S5fec4f` | Unused numbers inside a band | catalogue_health | 1 of 18 |
| `S95389d` | up to date | operations | 1 of 18 |
| `S73ec5d` | Up/Down Counter | detail, form | 1 of 18 |
| `S7d2a95` | Update: revise codes already imported (matched on the legacy number) | new | 1 of 18 |
| `S1a767a` | updates the open Draft | st_preview | 1 of 18 |
| `S5b23cf` | Upload a CSV or XLSX file — one row per status code, column headers matching the field names used elsewhere in CSCM Tool (Functional System Group/Subgroup and the audience-access fields by their code, e.g. "WCNV", "Converter", "SCADA User"). | new | 1 of 18 |
| `Sf738c6` | Upload and Import | new | 1 of 18 |
| `S9ad4d4` | Upload the generated StCd_<n>.st programs — several files at once, a whole folder, or one ZIP. Nothing is created yet: the next page lists every program so you can tick the ones to import. | st_new | 1 of 18 |
| `S80c494` | Uploaded | detail | 1 of 18 |
| `S02c0e4` | Used | catalogue_health | 1 of 18 |
| `S84c290` | Username | account_settings | 1 of 18 |
| `S2c7ab3` | Username or email | login | 18 of 18 |
| `S57f2b1` | Users | base | 18 of 18 |
| `Sa4aefa` | Valid | delegations | 1 of 18 |
| `S511ee2` | Valid for (days, max 365) | integrations | 1 of 18 |
| `Sfc039f` | Validate only (creates nothing) | new | 1 of 18 |
| `Sdda6ac` | Verify | export_center | 1 of 18 |
| `S22b05e` | Verify a file | export_center | 1 of 18 |
| `S112d15` | Verify an export | export_verify | 1 of 18 |
| `S7763b6` | Verify an exported file | export_verify | 1 of 18 |
| `Sdbf641` | Verify now | operations | 1 of 18 |
| `S2da600` | Version | export_center, list | 18 of 18 |
| `S45288a` | Version Label | detail, new | 1 of 18 |
| `S4993ae` | View Change Request | detail | 1 of 18 |
| `Scde93f` | View Imported Drafts | detail | 1 of 18 |
| `S6ba0fc` | View Release | builder | 1 of 18 |
| `Sd869da` | View Status Code | detail | 1 of 18 |
| `Sdbad9f` | Viewer | role badge | 18 of 18 |
| `Sbcbc36` | vs. revision | detail | 1 of 18 |
| `S33d306` | Waiting | approval_queue, detail, mine, review_queue | 1 of 18 |
| `Saa2ee9` | Waiting for a decision | success_metrics | 1 of 18 |
| `Sa3a4bd` | Waiting for cross-domain sign-off from: | detail | 1 of 18 |
| `S15198e` | Waiting since | _macros | 1 of 18 |
| `S83d655` | warning(s) | dry_run, st_preview | 1 of 18 |
| `S1430f9` | Warnings | detail | 1 of 18 |
| `Sfdfe2d` | Webhooks | integrations | 1 of 18 |
| `S51ecc5` | What happens next | detail | 1 of 18 |
| `S439914` | What happens next on a change request | help | 1 of 18 |
| `Sed412e` | What service staff should do. Feeds the service manual. | form | 1 of 18 |
| `S769bb1` | When | detail | 1 of 18 |
| `Se90e89` | When set, only codes that apply to one of these versions are offered as candidates. | new | 1 of 18 |
| `Sf323c0` | Where used | detail | 1 of 18 |
| `S3bd89c` | Which codes exist in which software version | software_versions | 1 of 18 |
| `Sf57807` | Which new status code replaces which legacy number. The mapping runs from legacy to new only: the new library holds more codes than the old one, so a code without a legacy number is normal and there is no way back. | legacy_mapping | 1 of 18 |
| `S7d5316` | Who | detail | 1 of 18 |
| `S438073` | Windows identity | login_windows | 1 of 18 |
| `S8b0b7c` | with a legacy number | legacy_mapping | 1 of 18 |
| `S141dbd` | with instructions and lookup codes | new | 1 of 18 |
| `S47e564` | Withdraw | detail | 1 of 18 |
| `Sa03f8a` | Withdraw selected | mine | 1 of 18 |
| `Sa0d9d0` | Withdraw the ticked change requests? A withdrawn Draft is deleted; its number is only kept if it was already issued. | mine | 1 of 18 |
| `S51a998` | Withdraw this change request? | detail | 1 of 18 |
| `S02499f` | withdrawn | st_preview | 1 of 18 |
| `Sf0c3cf` | without a legacy number | st_preview | 1 of 18 |
| `Sd7a484` | Workflow | base | 18 of 18 |
| `S57dda3` | Working-Set Export | export_center | 1 of 18 |
| `S9ddad9` | would be created | dry_run | 1 of 18 |
| `S0a18cf` | would be revised | dry_run | 1 of 18 |
| `S5397e0` | Yes | detail, export_verify, list, review_checklist | 18 of 18 |
| `Sfb360f` | yes | fleet_feedback | 1 of 18 |
| `S5a4692` | You are covering for a colleague | base | 18 of 18 |
| `S16b287` | You can still publish; this is a warning only. | builder | 1 of 18 |
| `Sa94065` | You have no notices. | notifications | 1 of 18 |
| `S23b0c3` | You sign in with Windows; your password is managed there. | account_settings | 1 of 18 |
| `S4ab291` | Your account | account_settings | 1 of 18 |
| `Sc8e4b4` | Your decision step | detail | 1 of 18 |
| `Sb1d254` | Your entries compared with the stored values | form | 1 of 18 |
| `S0b6c72` | Your entry | form | 1 of 18 |
| `S20cb4c` | ZIP with manifest | detail, export_center | 1 of 18 |

<!-- translations:end -->
