# 25. Concept — Integrating Hub Controller Codes into the 4xxx / 9xxx Scheme

> **Decided on 2026-10-27 (v4.17):** the Hub codes keep the Hub range of the **mapping** (five digits, 11000 and up; the *proposal 1* of this document). Moving them into the Main scheme (*proposal 2*, below) stays a possible later step, to be made as one systematic request approved by the StCd Owner, the Chief Engineer and an Administrator (idea I-75, `03-srs.md` FR-048s, FR-194). The text below is kept as the reasoning behind that choice.

**Status:** proposal for decision (2026-10-22). Nothing in this document is implemented. Supporting data: [artifacts/hc-numbering-proposal.xlsx](artifacts/hc-numbering-proposal.xlsx) — old number, proposal 1 (5-digit), proposal 2 (this concept) for every Hub Controller code, plus the proposed bands and the existing Main Controller bands.

**Inputs:** `HC Status Code Number.xlsx` (268 HC codes: 51 WTUR, 216 WROT, 1 WPPD), the current Main Controller (MC) taxonomy, assumption A-008 (`03-srs.md`: if the Hub Controller is removed from the hardware setup, its codes are defined anew on the MC side), and the decisions of 2026-10-22: MC identifiers are four digits; WPPD is obsolete (hidden).

**Relationship to what v4 implemented (2026-10-23).** v4 (decision D-06, FR-147) put a `controller_type` flag `MAIN` | `HUB` on the **Functional System Group** — the three existing Hub groups are `HUB` — and built *Hub → Main consolidation* (Main Controller drafts created from Hub codes, a mapping report, bulk deprecation of replaced Hub codes) for assumption A-008. This concept proposes something different and **still unimplemented**: no separate Hub groups at all, with the flag on the **subgroup** inside the existing groups. If this concept is adopted, the group-level flag and the consolidation screens become obsolete for the migration they serve, and these items need a decision: (a) move `controller_type` to `lookup_functional_subgroup` and drop it from the group (a migration with a data copy: every subgroup of a former Hub group becomes `HUB`); (b) keep both and let the subgroup value override the group value; (c) keep v4 as it is and use this concept's numbering only as the target for the Main drafts that *Create MC draft* produces. Option (c) needs no schema change and is the least risky; options (a) and (b) change `schema.sql`, the data dictionary and the consolidation service.

## 1. Idea in one sentence
**Hub Controller functions live inside the Main Controller groups they belong to** — WROT-HC inside group WROT (4000–4999), WTUR-HC inside group WTUR (9000–9999) — each as its own *HC subgroup* in a reserved block, flagged `controller = HUB`, so every status code is a plain four-digit `StCd-NNNN` and the separate five-digit Hub groups disappear.

## 2. Proposed bands (revised 2026-10-22)
Both HC blocks start at the **500 range** of their group. Order and block sizes follow the HC export (50-number blocks, as in the source); *HC Pitch Converter* gets an extra 50.

| Group | HC subgroup | Band | Codes now | Spare |
|---|---|---|---|---|
| WTUR | HC Control System | 9500–9599 | 36 | 64 |
| WTUR | HC Field Bus | 9600–9649 | 8 | 42 |
| WTUR | HC System | 9650–9699 | 7 | 43 |
| WROT | HC Blades | 4500–4549 | 25 | 25 |
| WROT | HC Batteries | 4550–4649 | 51 | 49 |
| WROT | HC Pitch | 4650–4699 | 35 | 15 |
| WROT | HC Pitch Control | 4700–4749 | 9 | 41 |
| WROT | HC Pitch Drives | 4750–4799 | 33 | 17 |
| WROT | HC Pitch Converter | 4800–4899 | 45 | 55 |
| WROT | HC Rotor | 4900–4949 | 18 (14 + 4 added since the export) | 32 |

* **WTUR:** 9500–9699 (200 slots) for 51 codes. MC headroom left in WTUR: 9400–9499 and 9700–9899.
* **WROT:** 4500–4949 (450 slots) for 216 codes. MC headroom left in WROT: only 4950–4999 (the existing MC subgroups end at 4499).
* The new number of each existing code is `band start + (proposal-1 number − block start)`, i.e. the order of the HC export is kept. The four codes without a number in the file (old 14321–14324) are placed at the end of the Rotor block as exported (4914–4917) — they describe the pitch ultracapacitor and fit *HC Pitch Converter* better; see §6.
* **Tightest bands:** HC Pitch (15 spare) and HC Pitch Drives (17 spare).

## 3. What changes in the tool

| Area | Change |
|---|---|
| Taxonomy | Remove the three Hub groups (WTUR 11000–11999, WROT 12000–12999, WPPD — hidden today). Add the ten HC subgroups above under the *existing* groups WTUR (id 9) and WROT (id 4). The "reused prefix, resolve by range" special case disappears. |
| New attribute | `lookup_functional_subgroup.controller_type` = `MAIN` \| `HUB` (default `MAIN`). Enables "HC only" filters and exports, a visible HC badge, and bulk deprecation later. |
| Identifier | Always `StCd-NNNN` (1000–9999); sandbox stays `StCd-T#####`. Needs the database check constraint on `status_code_identifier` to allow four digits (table rebuild in a migration) and the numbering/validation code and documents to drop the leading zero. Existing development codes are renumbered by the migration. |
| Names | HC subgroups are labelled "HC …" because three names collide with MC subgroups (Control System, Rotor, System). |
| Legacy numbers | The old HC numbers (35 of them are four-digit and overlap MC numbers; 7 are below 1000, one is `0`) go into `legacy_reference_number`, which is not unique. |
| Load | Import the 267 codes through the existing library import as Drafts (full governance still applies), using the mapping sheet. |
| Importer *(v4.2)* | Hub Controller programs (`StCd_<legacy>.st`) can be imported directly: the legacy number in the file is translated to the new one through the Hub rows of the mapping (v4.17, kept in the database and changed only with three approvals, 03-srs.md FR-191 … FR-198; the new numbers are in the Hub range), the legacy number is kept as `legacy_reference_number`, and the Draft reserves the new number (03-srs.md FR-048s, 06-data-dictionary.md §5a). |

## 4. When the Hub Controller is removed (assumption A-008)
1. Deactivate the ten HC subgroups (a lookup change; data is kept, numbers are never reused).
2. The functions that move to the MC side are **defined as new MC codes** in the ordinary MC subgroups (4000–4499 / 9000–9399, or the free MC headroom 4950–4999 / 9400–9499 / 9700–9899), using the "create MC draft from HC code" action planned as I-36, which copies the descriptive fields and records the HC number as the legacy reference.
3. The retired HC bands (4500–4949, 9500–9699) simply stay retired — no renumbering of anything.

## 5. Compared with the alternative (5-digit HC numbers, column B of the export)

| | This concept (4xxx / 9xxx) | 5-digit HC numbers (11001–13001) |
|---|---|---|
| Identifier | One format, four digits | Two formats: four digits MC, five digits HC |
| MC vs HC at a glance | Only via subgroup / HC badge | By the number's length |
| Taxonomy | Simpler: no Hub groups, no repeated prefixes | Today's 12 groups incl. repeated WTUR/WROT prefixes |
| MC growth room | Reduced: WROT keeps only 4950–4999 free | Untouched |
| HC removal | Deactivate subgroups; retired numbers stay inside MC space | Deactivate the Hub groups; MC space untouched |
| Change effort now | Higher: taxonomy + `controller_type` + identifier migration + renumber | Lower: only the identifier format (MC four digits) |

**Trade-off to decide:** the concept buys a single identifier format and a simpler taxonomy at the price of consuming most of the free capacity in WROT/WTUR and losing the digit-count distinction. Because HC codes are expected to be redefined on the MC side anyway, consuming MC number space for codes with a limited lifetime is the main argument *against* it.

## 6. Open decisions
1. Approve the concept, or keep the five-digit Hub numbers (then only the MC four-digit change is built).
2. Band sizes — whether to widen *HC Pitch* and *HC Pitch Drives* (15 and 17 spare) as well; WROT would then have no MC headroom left at all.
3. Where the 4 post-export codes (UCAP capacity low axis 1–3, Pitch system hardware mismatch) go: the export lists them under Rotor, but they belong functionally to the pitch system — moving them to *HC Pitch Converter* would use 4 of its 55 spare numbers.
4. Whether the digit-length rule "MC = 4, HC = 5" is a business requirement in itself (e.g. for manuals or field staff). If it is, this concept cannot be used.
