-- ============================================================================
-- CSCM Tool — SQLite Physical Schema (MVP) — v4
-- Referenced by: docs/07-database-design.md, docs/06-data-dictionary.md
-- Target: SQLite 3.35+ (requires partial index / generated column support)
-- v3 changes (2026-09-17), grounded in a real export of the live status code
-- library (897 rows, 9 sheets) and the legacy tool's screenshot:
--   - Functional Subgroup renamed with real values and made MANDATORY
--     (was nullable in v2); Administrator can add new subgroups later
--   - status_category simplified to ERROR/WARNING/INFO
--   - available_group is a plain integer code, not a lettered enum
--   - alarm is a boolean, not a 4-value behaviour enum
--   - set_delay/reset_delay are free-text-with-unit, not integer seconds
--   - reset/brake/yaw/converter "program" fields are numeric passthroughs,
--     not governed enums; manual and automatic reset are separate fields
--   - access_rights_id (single enum) replaced by 8 independent
--     audience-access lookups (development/sales/tcc/service/turbine
--     operator package/grid operator/service partner/customer)
--   - new fields: up_down_counter, trigger_snapshot,
--     loadless_spinning_permitted, number_of_times_repeated,
--     repeated_over_the_course, status_code_for_repeated_error (opaque,
--     NOT a foreign key), logical_node/node_value (derived/read-only),
--     legacy_reference_number
--   - new import_job table (CSV/XLSX library import -> Draft Change
--     Requests, full governance still applies)
--   - export_job.export_type gains XLSX
--   - software_version re-added as a nullable field on status_code_revision
--     (was dropped without confirmation in an earlier pass -- open item,
--     may belong on `release` instead; see docs/06-data-dictionary.md)
--   - lookup_functional_system_group.code is NO LONGER unique on its own:
--     the Hub Controller library (range 11000-13999) reuses WTUR and WROT
--     for two new, numerically distinct groups; uniqueness moved to
--     (code, range_start). Three new groups added: WTUR (11000-11999,
--     Hub Control System), WROT (12000-12999, Hub Rotor & Pitch), WPPD
--     (13000-13999, Wind Farm) -- 11 new subgroups under them
--   - trg_prevent_group_overlap added, mirroring the existing subgroup
--     overlap trigger one level up -- Administrators can add whole new
--     Functional System Groups into the confirmed free ranges (10000-10999,
--     14000-14999, 15000-15999, 16000-16999) without a schema change
-- v4 changes (2026-10-22, improvement pack I-01..I-36, docs/21-improvement-ideas.md):
--   - status_code_revision: row_version/updated_at (optimistic concurrency, I-01);
--     remedy_text/affected_component/related_status_codes/standard_references (I-14);
--     applies_from/to_version_id (I-07); planned_effective/deprecation_date (I-27)
--   - lookup_controller_software_version, release_target_version (I-07);
--     lookup_language, revision_translation (I-15)
--   - lookup_*_access.audience_visible (I-03); lookup_functional_system_group.
--     controller_type MAIN|HUB and hub_mc_mapping (I-36)
--   - export_profile (I-02); export_job gains sha256/size/profile/audience/manifest
--     columns and wider type/scope CHECKs (I-06, I-24); import_job progress/mode (I-05, I-32)
--   - change_set (+ change_request.change_set_id, I-11); cr_attachment (I-13);
--     delegation (I-16); field_comment, review_checklist_item,
--     cr_checklist_confirmation (I-23); saved_search (I-26); notification (I-08);
--     login_attempt (I-20); app_setting; occurrence_import/code_occurrence (I-28);
--     api_token, webhook, webhook_delivery (I-29); user.ui_language (I-22)
--   - audit_log_entry.prev_hash/entry_hash: tamper-evident hash chain (I-18)
--   - the optional FTS5 search index lives in schema-fts5.sql (I-31)
-- v4.1 changes (2026-10-23, derived from 14 generated StCd_*.st programs: Main Controller
-- 1000-1010 and Hub Controller 14000/14005/14025, cross-checked against the status code workbooks;
-- docs/06-data-dictionary.md sections 1, 2c, 2d, 2f, 9d.9):
--   - status_code.prg_idx: the PrgIdx_GUi block identification, entered manually, 1..65535 (UINT),
--     unique among non-sandbox codes, frozen once a revision was released
--   - status_code_revision: 13 further Main Controller subsystem programs, 3 Hub Controller
--     programs (pitch error/warning, rotor brake), 5 Hub operation flags and the operating-mode
--     mask / task frequency / availability-calculation / zero-load parameters (all optional)
--   - lookup_user_group_slot + status_code_revision_user_group: the 16 numeric user-group slots of
--     the controller (slots 1..8 = the eight audiences) with a read and a write level per revision;
--     lookup_*_access.default_read_level / default_write_level
--   - trg_prevent_prg_idx_change_after_release, trg_require_prg_idx_for_review (inert until
--     app_setting 'status_code.require_prg_idx' = '1')
-- v4.2 changes (2026-10-23, status code import from the generated StCd_*.st programs,
-- docs/03-srs.md section 1.16, docs/06-data-dictionary.md section 5a):
--   - status_code.reserved_identifier: the number an imported program already carries; the
--     identifier issued at Submit for Review must be exactly this one, no other code may take it
--     (unique among non-sandbox codes; two triggers guard the reservation)
--   - import_job.source_format gains 'ST' and import_job.change_set_id links the batch change set
--   - import_source_item: one row per imported program (file, SHA-256, parsed attributes as JSON)
-- v4.3 changes (2026-10-23, roles and languages):
--   - role 'STCD_OWNER' (id 6): owner of the status code library; may change the role of a user
--     between VIEWER, ENGINEER and REVIEWER only, never creates users (docs/11-security-architecture.md
--     section 3, docs/03-srs.md FR-156, BR-024)
--   - lookup_language: French, Hindi and Georgian added; v4.4 adds Arabic (written right to left); every
--     name reads <country letters> <name> <flag emoji>; user.ui_language accepts the six codes
-- v4.17 changes: the legacy -> new status code mapping kept in the database and changed only with the three
--     approvals of the StCd Owner, the Chief Engineer and an Administrator (status_code_mapping, mapping_change,
--     mapping_change_item, mapping_approval)
-- v4.13 changes: the sample inspection of a bulk decision (bulk_sample, bulk_sample_item)
-- v4.9.2 changes: status_code.deleted_at (a withdrawn code is erased in place, never removed; the delete
--     trigger is strict again)
-- v4.9 changes: the technical nomenclature (terminology_term, terminology_translation); user.deleted_at (a
--     deleted account with history is erased, not removed: BR-025); status_code.withdrawn_at (a code whose
--     change request was withdrawn can be deleted by an Administrator: BR-026)
-- v4.7 changes (2026-10-24): trg_user_email_immutable (the e-mail address of a user is fixed); the tables of the
--     in-application translation review (language_reviewer, translation_review, translation_review_item,
--     translation_override)
-- v4.6 changes (2026-10-23): Spanish, Italian and Danish; Georgian moves to the end of the language list
-- v4.5 changes (2026-10-23): ten more languages (Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu, Kannada, Odia,
--     Malayalam, Punjabi); user.ui_language is a two-letter code (the CHECK no longer lists them, so the next
--     language needs no table rebuild)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Reference / lookup tables
-- ----------------------------------------------------------------------------

CREATE TABLE role (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,      -- ADMINISTRATOR | STCD_OWNER | ENGINEER | REVIEWER | CHIEF_ENGINEER | VIEWER
    label       TEXT NOT NULL
);
INSERT INTO role (id, code, label) VALUES
    (1, 'ADMINISTRATOR', 'Administrator (Product Owner Controls Software)'),
    (2, 'ENGINEER', 'Engineer'),
    (3, 'REVIEWER', 'Reviewer (Sub-PO for Status Codes)'),
    (4, 'CHIEF_ENGINEER', 'Chief Engineer'),
    (5, 'VIEWER', 'Viewer'),
    (6, 'STCD_OWNER', 'StCd Owner (Owner of the Status Code Library)');   -- v4.3

CREATE TABLE lookup_engineering_domain (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO lookup_engineering_domain (code, label, sort_order) VALUES
    ('CONTROLS','Controls Engineering',1), ('ELECTRICAL','Electrical Engineering',2),
    ('MECHANICAL','Mechanical Engineering',3), ('GRID','Grid / Power Systems Engineering',4),
    ('SAFETY','Functional Safety Engineering',5);

-- NOTE (2026-09-17): `code` is intentionally NOT unique on its own. The Hub
-- Controller status code library (range 11000-13999) reuses the WTUR and
-- WROT prefixes for its own, numerically distinct groups (confirmed by the
-- business: same thematic prefix, different status code range) alongside a
-- new WPPD prefix for Wind Farm. Uniqueness is therefore on (code,
-- range_start), not code alone — always resolve a group by its numeric
-- range, never by prefix alone, in application code.
CREATE TABLE lookup_functional_system_group (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL, label TEXT NOT NULL,
    range_start INTEGER NOT NULL, range_end INTEGER NOT NULL,
    description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
    controller_type TEXT NOT NULL DEFAULT 'MAIN' CHECK (controller_type IN ('MAIN','HUB')),   -- I-36
    UNIQUE (code, range_start),
    CHECK (range_end > range_start)
);
INSERT INTO lookup_functional_system_group (code, label, range_start, range_end, sort_order) VALUES
    ('WCNV','Converter & Grid Interface',1000,1999,1),
    ('WGEN','Generator System',2000,2999,2),
    ('WNAC','Meteorology & Nacelle Environment',3000,3999,3),
    ('WROT','Rotor & Pitch System',4000,4999,4),
    ('WTOW','Tower & Structure',5000,5999,5),
    ('WTRF','Transformer & MV System',6000,6999,6),
    ('WTRM','Drivetrain & Gearbox',7000,7999,7),
    ('WYAW','Yaw System',8000,8999,8),
    ('WTUR','Turbine Control & Operation',9000,9999,9),
    -- Hub Controller groups (new 2026-09-17, source: "HC Status Code Number.xlsx")
    ('WTUR','Hub Controller Control System',11000,11999,10),
    ('WROT','Hub Controller Rotor & Pitch',12000,12999,11),
    ('WPPD','Wind Farm / Plant Dispatch',13000,13999,12);
UPDATE lookup_functional_system_group SET controller_type = 'HUB' WHERE range_start >= 11000;

-- Real subgroup taxonomy, corrected 2026-09-17 from the authoritative
-- row-level export (docs/06-data-dictionary.md §9a). Every hundred-block
-- (or, within WTUR's 9900-9999 span, ten-block) not listed is deliberately
-- reserved capacity for subgroups added later via lookup_functional_subgroup
-- inserts validated for non-overlap (§9a.1) -- never a schema migration.
CREATE TABLE lookup_functional_subgroup (
    id INTEGER PRIMARY KEY,
    functional_system_group_id INTEGER NOT NULL REFERENCES lookup_functional_system_group(id),
    code TEXT NOT NULL, label TEXT NOT NULL,
    sub_range_start INTEGER NOT NULL, sub_range_end INTEGER NOT NULL,
    description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (functional_system_group_id, code),
    CHECK (sub_range_end > sub_range_start)
);
-- group_range_start disambiguates WTUR/WROT, which each now identify two
-- different groups (Main Controller and Hub Controller) — always join on
-- (code, range_start) together, never on code alone (see the note above
-- lookup_functional_system_group).
INSERT INTO lookup_functional_subgroup (functional_system_group_id, code, label, sub_range_start, sub_range_end, sort_order)
WITH v(group_code, group_range_start, code, label, sub_range_start, sub_range_end, sort_order) AS (
    VALUES
    ('WCNV',1000,'010xx','Converter',1000,1199,1),
    ('WCNV',1000,'012xx','Grid',1200,1299,2),
    ('WGEN',2000,'020xx','Generator',2000,2199,1),
    ('WGEN',2000,'022xx','Protection',2200,2299,2),
    ('WNAC',3000,'030xx','Meteorology',3000,3199,1),
    ('WNAC',3000,'032xx','Nacelle',3200,3299,2),
    ('WROT',4000,'040xx','Rotor',4000,4199,1),
    ('WROT',4000,'042xx','Hot Air De-icing',4200,4299,2),
    ('WROT',4000,'043xx','Lighting',4300,4399,3),
    ('WROT',4000,'044xx','Blade Sensors',4400,4499,4),
    ('WTOW',5000,'050xx','Tower',5000,5199,1),
    ('WTRF',6000,'060xx','Switches',6000,6199,1),
    ('WTRF',6000,'062xx','Transformer',6200,6299,2),
    ('WTRM',7000,'070xx','Gearbox',7000,7199,1),
    ('WTRM',7000,'072xx','Drive train',7200,7299,2),
    ('WTRM',7000,'073xx','Hydraulics',7300,7399,3),
    ('WTRM',7000,'074xx','Brake',7400,7499,4),
    ('WYAW',8000,'080xx','Yaw',8000,8199,1),
    ('WTUR',9000,'090xx','System',9000,9199,1),
    ('WTUR',9000,'092xx','Control System',9200,9299,2),
    ('WTUR',9000,'093xx','Safety',9300,9399,3),
    ('WTUR',9000,'0990x','External',9900,9929,4),
    ('WTUR',9000,'0993x','Farm',9930,9959,5),
    ('WTUR',9000,'0996x','Feedback Control',9960,9969,6),
    ('WTUR',9000,'0997x','Interface',9970,9979,7),
    ('WTUR',9000,'0998x','Power Management',9980,9989,8),
    ('WTUR',9000,'0999x','UPS',9990,9999,9),
    -- Hub Controller subgroups (new 2026-09-17, source: "HC Status Code Number.xlsx"). Bands are
    -- aligned to the hundreds digit like the Main groups (docs/05-governance-handbook.md section 2;
    -- aligned 2026-10-23, migration a1d4f6b8c203): '123xx' owns 12300-12399. A band shorter than a
    -- hundred is named by its first ten with one digit in place of the second x ('1110x' = 11100-11149,
    -- '1115x' = 11150-11199; renamed from '11-1xxA'/'11-1xxB' by migration f6c8e0a2b459).
    ('WTUR',11000,'110xx','Control System',11000,11099,1),
    ('WTUR',11000,'1110x','Field Bus',11100,11149,2),
    ('WTUR',11000,'1115x','System',11150,11199,3),
    ('WROT',12000,'1200x','Blade',12000,12049,1),
    ('WROT',12000,'1205x','Batteries',12050,12199,2),
    ('WROT',12000,'1220x','Pitch',12200,12249,3),
    ('WROT',12000,'1225x','Pitch Control',12250,12299,4),
    ('WROT',12000,'123xx','Pitch Drivers',12300,12399,5),
    ('WROT',12000,'124xx','Pitch Converter',12400,12499,6),
    ('WROT',12000,'125xx','Rotor',12500,12599,7),
    ('WPPD',13000,'130xx','Wind Farm',13000,13099,1)
)
SELECT g.id, v.code, v.label, v.sub_range_start, v.sub_range_end, v.sort_order
FROM v JOIN lookup_functional_system_group g
  ON g.code = v.group_code AND g.range_start = v.group_range_start;

CREATE TABLE lookup_turbine_platform (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO lookup_turbine_platform (code, label, sort_order) VALUES
    ('2XM','2XM Platform',1), ('3XM','3XM Platform',2), ('4XM','4XM Platform',3);

-- Available Group: numeric codes only, labels TBD pending Controls
-- Engineering confirmation (docs/06-data-dictionary.md §9c). Soft reference
-- set for validation, not a hard-enforced enum, since new codes may appear.
CREATE TABLE lookup_available_group (
    id INTEGER PRIMARY KEY, code INTEGER NOT NULL UNIQUE, label TEXT,
    description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO lookup_available_group (code, sort_order)
WITH v(value) AS (
    VALUES (1),(2),(4),(5),(6),(9),(11),(12),(13),(14),(15),(16),(18),
           (20),(21),(22),(23),(24),(25),(27),(28),(30),(32)
)
SELECT value, ROW_NUMBER() OVER (ORDER BY value) FROM v;

-- Eight independent audience/access lookups, real observed values
-- (docs/06-data-dictionary.md §2d, §9d). Casing/typo variants from the raw
-- export ("See Only" vs "See only", "ProfessionaProfessional") normalized.
CREATE TABLE lookup_development_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_development_access (code, label, sort_order) VALUES
    ('SCADA_USER','SCADA User',1), ('DEPARTMENT','Department',2), ('OPERATION_CONTROL','Operation Control',3), ('SEE_ONLY','See only',4);

CREATE TABLE lookup_sales_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_sales_access (code, label, sort_order) VALUES
    ('SALES','Sales',1), ('COVERT','Covert',2), ('SEE_ONLY','See only',3);

CREATE TABLE lookup_tcc_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_tcc_access (code, label, sort_order) VALUES
    ('TELENOTDIENST','Telenotdienst',1), ('TELENOTDIENST_READ','Telenotdienst-read',2), ('PMS_DISPATCHER','PMS Dispatcher',3), ('SEE_ONLY','See only',4);

CREATE TABLE lookup_service_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_service_access (code, label, sort_order) VALUES
    ('COMMISSIONING','Commissioning',1), ('SERVICE_AND_MAINTENANCE','Service and Maintenance',2), ('SEE_ONLY','See only',3);

CREATE TABLE lookup_top_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_top_access (code, label, sort_order) VALUES
    ('PREVENTIVE_MAINTENANCE','Preventive Maintenance',1), ('TROUBLESHOOTING','Troubleshooting',2),
    ('TROUBLESHOOTING_ADVANCED','Troubleshooting Advanced',3), ('COVERT','Covert',4), ('SEE_ONLY','See only',5);

CREATE TABLE lookup_grid_operator_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_grid_operator_access (code, label, sort_order) VALUES
    ('COVERT','Covert',1), ('SEE_ONLY','See only',2);

CREATE TABLE lookup_service_partner_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_service_partner_access (code, label, sort_order) VALUES
    ('SERVICE_PARTNER','Service Partner',1), ('EXT_SERVICE_PROVIDER','Ext. Service Provider',2),
    ('CUSTOMER_AFTER_WARRANTY_PROFESSIONAL','Customer after warranty Professional',3),
    ('CUSTOMER_AFTER_WARRANTY_ADVANCED','Customer after warranty Advanced',4),
    ('COVERT','Covert',5), ('SEE_ONLY','See only',6);

CREATE TABLE lookup_customer_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, audience_visible INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1)),
    default_read_level INTEGER CHECK (default_read_level IS NULL OR default_read_level BETWEEN 0 AND 255),
    default_write_level INTEGER CHECK (default_write_level IS NULL OR default_write_level BETWEEN 0 AND 255));
INSERT INTO lookup_customer_access (code, label, sort_order) VALUES
    ('STANDARD','Standard',1), ('ADVANCED','Advanced',2), ('PROFESSIONAL','Professional',3),
    ('PREMIUM','Premium',4), ('COVERT','Covert',5), ('SEE_ONLY','See only',6);

-- I-03 / decision D-02: 'Covert' is treated as "not visible to that audience"
-- (fail-closed) until the business confirms otherwise; the flag is data that
-- an Administrator can flip per value in Lookup Administration.
UPDATE lookup_development_access      SET audience_visible = 0 WHERE code = 'COVERT';
UPDATE lookup_sales_access            SET audience_visible = 0 WHERE code = 'COVERT';
UPDATE lookup_tcc_access              SET audience_visible = 0 WHERE code = 'COVERT';
UPDATE lookup_service_access          SET audience_visible = 0 WHERE code = 'COVERT';
UPDATE lookup_top_access              SET audience_visible = 0 WHERE code = 'COVERT';
UPDATE lookup_grid_operator_access    SET audience_visible = 0 WHERE code = 'COVERT';
UPDATE lookup_service_partner_access  SET audience_visible = 0 WHERE code = 'COVERT';
UPDATE lookup_customer_access         SET audience_visible = 0 WHERE code = 'COVERT';

-- v4.1: numeric user-group levels (UserGroupReadArBy / UserGroupWriteArBy, BYTE) that the controller
-- uses for each named access value. Seeded only where the generated programs showed one value for
-- every code that carries the named access value. 'Service and Maintenance' (10 or 20) and
-- 'Telenotdienst' (10 or 20) differ from code to code, so they stay NULL: the level is then
-- entered per revision in status_code_revision_user_group (docs/06-data-dictionary.md section 2d).
UPDATE lookup_development_access      SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_development_access      SET default_read_level = 1,  default_write_level = 20 WHERE code = 'OPERATION_CONTROL';
UPDATE lookup_sales_access            SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_tcc_access              SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_service_access          SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_top_access              SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_top_access              SET default_read_level = 1,  default_write_level = 10 WHERE code = 'PREVENTIVE_MAINTENANCE';
UPDATE lookup_top_access              SET default_read_level = 1,  default_write_level = 15 WHERE code = 'TROUBLESHOOTING';
UPDATE lookup_grid_operator_access    SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_service_partner_access  SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_service_partner_access  SET default_read_level = 1,  default_write_level = 15 WHERE code = 'EXT_SERVICE_PROVIDER';
UPDATE lookup_service_partner_access  SET default_read_level = 1,  default_write_level = 10 WHERE code = 'CUSTOMER_AFTER_WARRANTY_ADVANCED';
UPDATE lookup_customer_access         SET default_read_level = 1,  default_write_level = 50 WHERE code = 'SEE_ONLY';
UPDATE lookup_sales_access            SET default_read_level = 50, default_write_level = 50 WHERE code = 'COVERT';
UPDATE lookup_top_access              SET default_read_level = 50, default_write_level = 50 WHERE code = 'COVERT';
UPDATE lookup_grid_operator_access    SET default_read_level = 50, default_write_level = 50 WHERE code = 'COVERT';
UPDATE lookup_service_partner_access  SET default_read_level = 50, default_write_level = 50 WHERE code = 'COVERT';
UPDATE lookup_customer_access         SET default_read_level = 50, default_write_level = 50 WHERE code = 'COVERT';

-- v4.1: the 16 user-group slots of the controller (UserGroupReadArBy/WriteArBy[Idx, slot]).
-- Slots 1..8 are the eight audiences in the order of the export columns; this was verified on 14
-- programs (a 'Covert' value is read level 50 in exactly the slot of its audience). Slot 13 is
-- never written by the generator; slots 0, 9..12, 14, 15 were 50/50 in every sample (slot 9 reads
-- 1 on Main and 50 on Hub Controller codes) and stay unassigned until Controls Engineering names them.
CREATE TABLE lookup_user_group_slot (
    id INTEGER PRIMARY KEY,
    slot INTEGER NOT NULL UNIQUE CHECK (slot BETWEEN 0 AND 15),
    audience_code TEXT UNIQUE CHECK (audience_code IS NULL OR audience_code IN
        ('DEVELOPMENT','SALES','TCC','SERVICE','TURBINE_OPERATOR_PACKAGE','GRID_OPERATOR','SERVICE_PARTNER','CUSTOMER')),
    label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO lookup_user_group_slot (slot, audience_code, label, is_active, sort_order) VALUES
    (0,NULL,'Slot 0 (unassigned)',0,0),
    (1,'DEVELOPMENT','Development',1,1), (2,'SALES','Sales',1,2), (3,'TCC','TCC',1,3),
    (4,'SERVICE','Service',1,4), (5,'TURBINE_OPERATOR_PACKAGE','Turbine Operator Package',1,5),
    (6,'GRID_OPERATOR','Grid Operator',1,6), (7,'SERVICE_PARTNER','Service Partner',1,7),
    (8,'CUSTOMER','Customer',1,8),
    (9,NULL,'Slot 9 (unassigned)',0,9), (10,NULL,'Slot 10 (unassigned)',0,10),
    (11,NULL,'Slot 11 (unassigned)',0,11), (12,NULL,'Slot 12 (unassigned)',0,12),
    (13,NULL,'Slot 13 (never written by the generator)',0,13), (14,NULL,'Slot 14 (unassigned)',0,14),
    (15,NULL,'Slot 15 (unassigned)',0,15);

-- I-07 / decision D-01: controller software versions, ordered by sort_order.
-- A revision declares the version range it applies to; a Release targets one or more.
CREATE TABLE lookup_controller_software_version (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);

-- I-15 / decision D-03: content languages. Exactly one language is the source
-- language of the catalogue (the text stored on status_code_revision).
CREATE TABLE lookup_language (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    description TEXT, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
    is_source INTEGER NOT NULL DEFAULT 0 CHECK (is_source IN (0,1))
);
INSERT INTO lookup_language (code, label, sort_order, is_source) VALUES
    ('en','GB English 🇬🇧',1,1), ('de','DE Deutsch 🇩🇪',2,0), ('fr','FR Français 🇫🇷',3,0),
    ('hi','IN हिन्दी (Hindi) 🇮🇳',4,0), ('ar','SA العربية (Arabic) 🇸🇦',6,0), ('bn','IN বাংলা (Bengali) 🇮🇳',7,0),
    ('mr','IN मराठी (Marathi) 🇮🇳',8,0), ('te','IN తెలుగు (Telugu) 🇮🇳',9,0), ('ta','IN தமிழ் (Tamil) 🇮🇳',10,0),
    ('gu','IN ગુજરાતી (Gujarati) 🇮🇳',11,0), ('ur','PK اردو (Urdu) 🇵🇰',12,0), ('kn','IN ಕನ್ನಡ (Kannada) 🇮🇳',13,0),
    ('or','IN ଓଡ଼ିଆ (Odia) 🇮🇳',14,0), ('ml','IN മലയാളം (Malayalam) 🇮🇳',15,0), ('pa','IN ਪੰਜਾਬੀ (Punjabi) 🇮🇳',16,0),
    ('es','ES Español 🇪🇸',17,0), ('it','IT Italiano 🇮🇹',18,0), ('da','DK Dansk 🇩🇰',19,0),
    ('ka','GE ქართული (Georgian) 🇬🇪',20,0);   -- v4.3-v4.6: country letters left, flag right; Georgian last

-- ----------------------------------------------------------------------------
-- Identity / access
-- ----------------------------------------------------------------------------

CREATE TABLE user (
    id                  INTEGER PRIMARY KEY,
    username            TEXT NOT NULL UNIQUE,
    email               TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    full_name           TEXT NOT NULL,
    role_id             INTEGER NOT NULL REFERENCES role(id),
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_login_at       TEXT,
    failed_login_count  INTEGER NOT NULL DEFAULT 0,
    locked_until        TEXT,
    ui_language         TEXT NOT NULL DEFAULT 'en' CHECK (length(ui_language) = 2 AND ui_language = lower(ui_language)),   -- I-22; the application decides which codes exist (v4.5)
    deleted_at          TEXT   -- v4.9: set when an Administrator deletes an account that has history; name, address and password are erased, the row stays so that nothing it did loses its author
);

-- 11-security-architecture.md §4: a new password may not repeat any of the last 5
-- passwords. Holds the hashes of previous passwords (never plaintext).
CREATE TABLE user_password_history (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES user(id),
    password_hash   TEXT NOT NULL,
    retired_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX ix_pwhist_user ON user_password_history (user_id, id);

CREATE TABLE user_engineering_domain (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user(id),
    engineering_domain_id INTEGER NOT NULL REFERENCES lookup_engineering_domain(id),
    UNIQUE (user_id, engineering_domain_id)
);

-- ----------------------------------------------------------------------------
-- Core governed entities
-- ----------------------------------------------------------------------------

CREATE TABLE status_code (
    id                                  INTEGER PRIMARY KEY,
    status_code_identifier              TEXT UNIQUE,   -- NULL until Draft->Review; StCd-XXXXX or StCd-TXXXXX
    functional_system_group_id          INTEGER NOT NULL REFERENCES lookup_functional_system_group(id),
    functional_subgroup_id              INTEGER NOT NULL REFERENCES lookup_functional_subgroup(id),  -- mandatory (v3)
    is_sandbox                          INTEGER NOT NULL DEFAULT 0 CHECK (is_sandbox IN (0,1)),
    platform_variant_of_status_code_id  INTEGER REFERENCES status_code(id),
    legacy_reference_number             TEXT,
    -- v4.1: PrgIdx_GUi, the block identification the generated program writes to the controller's
    -- global on entry. Entered by hand (the tool never allocates it), UINT range, audited.
    -- NULL only while the code is a Draft or not yet imported; required from Review on
    -- (docs/06-data-dictionary.md section 1).
    prg_idx                             INTEGER CHECK (prg_idx IS NULL OR prg_idx BETWEEN 1 AND 65535),
    -- v4.2: the number a generated StCd_<n>.st program already carries. Submit for Review issues
    -- exactly this identifier (no sequence allocation, no Administrator override), and the number
    -- allocator skips it. NULL for every code that is not imported from a program.
    reserved_identifier                 TEXT CHECK (reserved_identifier IS NULL
                                                    OR reserved_identifier GLOB 'StCd-[0-9][0-9][0-9][0-9][0-9]'),
    owner_id                            INTEGER NOT NULL REFERENCES user(id),
    created_at                          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    -- v4.9: set when the last revision of the code was withdrawn (the code is an empty shell); only such a code can be deleted
    withdrawn_at                        TEXT,
    -- v4.9.2: set when an Administrator deletes a withdrawn code. The row stays (so no id is ever
    -- reused and every audit entry keeps pointing at one code) but gives up its identifier, reserved
    -- number, legacy number and PrgIdx_GUi, so the same program or row can be imported again.
    deleted_at                          TEXT,
    CHECK (status_code_identifier IS NULL
           OR status_code_identifier GLOB 'StCd-[0-9][0-9][0-9][0-9][0-9]'
           OR status_code_identifier GLOB 'StCd-T[0-9][0-9][0-9][0-9][0-9]')
);

-- v4.1: one PrgIdx_GUi per block; sandbox codes are exempt so test codes never block a real value.
CREATE UNIQUE INDEX ux_status_code_prg_idx ON status_code (prg_idx) WHERE prg_idx IS NOT NULL AND is_sandbox = 0;

-- v4.2: a number can be reserved by one code only.
CREATE UNIQUE INDEX ux_status_code_reserved_identifier ON status_code (reserved_identifier) WHERE reserved_identifier IS NOT NULL;

CREATE TABLE status_code_revision (
    id                              INTEGER PRIMARY KEY,
    status_code_id                  INTEGER NOT NULL REFERENCES status_code(id),
    revision_number                 INTEGER NOT NULL,
    is_current                      INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0,1)),

    title                           TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    description                     TEXT NOT NULL CHECK (length(description) BETWEEN 10 AND 4000),
    software_version                TEXT,   -- nullable; may belong on `release` instead — see docs/06-data-dictionary.md open item
    status_category                 TEXT NOT NULL CHECK (status_category IN ('ERROR','WARNING','INFO')),
    available_group                 INTEGER NOT NULL,
    alarm_flag                      INTEGER NOT NULL DEFAULT 0 CHECK (alarm_flag IN (0,1)),
    set_delay                       TEXT NOT NULL,
    reset_delay                     TEXT NOT NULL,
    up_down_counter                 INTEGER NOT NULL DEFAULT 0 CHECK (up_down_counter IN (0,1)),
    trigger_snapshot                INTEGER NOT NULL DEFAULT 0 CHECK (trigger_snapshot IN (0,1)),
    loadless_spinning_permitted     INTEGER NOT NULL DEFAULT 0 CHECK (loadless_spinning_permitted IN (0,1)),

    number_of_times_repeated        INTEGER CHECK (number_of_times_repeated IS NULL OR number_of_times_repeated >= 1),
    repeated_over_the_course        TEXT,
    status_code_for_repeated_error  INTEGER,   -- opaque reference, NOT a FK (docs/06-data-dictionary.md §2b)

    yaw_program                          INTEGER NOT NULL DEFAULT 0,
    manual_reset_program                 INTEGER NOT NULL DEFAULT 0,
    auto_reset_program                   INTEGER NOT NULL DEFAULT 0,
    converter_reactive_power_program     INTEGER NOT NULL DEFAULT 0,
    brake_program                        INTEGER NOT NULL DEFAULT 0,
    umrichterprogramm_gsc                INTEGER NOT NULL DEFAULT 0,
    umrichterprogramm_msc                INTEGER NOT NULL DEFAULT 0,
    yaw_bearing_lubrication_program      INTEGER NOT NULL DEFAULT 0,

    -- v4.1 Main Controller subsystem programs (4XM 'Naming Conventions' sheet / generated
    -- *PrgArUs arrays). 0 = the code does not act on that subsystem. Hub Controller codes keep 0.
    converter_reset_program              INTEGER NOT NULL DEFAULT 0,   -- ConvRstLev     ResetConverterPrgArUs
    hydraulic_pump_program               INTEGER NOT NULL DEFAULT 0,   -- HyPmpLev       HydraulicPrgArUs
    gearbox_oil_pump_program             INTEGER NOT NULL DEFAULT 0,   -- GbxOilPmpLev   GearOilPumpPrgArUs
    gearbox_oil_fan_program              INTEGER NOT NULL DEFAULT 0,   -- GbxOilFanLev   GearOilCoolingPrgArUs
    gearbox_oil_heating_program          INTEGER NOT NULL DEFAULT 0,   -- GbxOilHtLev    GearHeatingPrgArUs
    generator_fan_program                INTEGER NOT NULL DEFAULT 0,   -- GnFanLev       GenFanPrgArUs
    generator_heating_program            INTEGER NOT NULL DEFAULT 0,   -- GnHtLev        GenHeatingPrgArUs
    generator_bearing_lubrication_program INTEGER NOT NULL DEFAULT 0,  -- GnBrgLuLev     GenoLubPrgArUs
    rotor_bearing_lubrication_program    INTEGER NOT NULL DEFAULT 0,   -- RotBrgLuLev    RotBearLubPrgArUs
    anemometer_heating_program           INTEGER NOT NULL DEFAULT 0,   -- AneHtLev       VaneAneHeatPrgArUs
    medium_voltage_cb_program            INTEGER NOT NULL DEFAULT 0,   -- MedCBLev       MeanVoltageCBPrgArUs ('Mean' reads as a mistranslation of Mittelspannung)
    tower_fan_program                    INTEGER NOT NULL DEFAULT 0,   -- TowFanLev      TowerFanPrgArUs
    transformer_oil_pump_program         INTEGER NOT NULL DEFAULT 0,   -- TrfOilPmpLev   TrafoPumpPrgArUs
    zero_load_operation                  INTEGER CHECK (zero_load_operation IS NULL OR zero_load_operation IN (0,1)),   -- ZeroLoadOperation_ArBo; Main only, NULL = not captured

    -- v4.1 Hub Controller programs and operation flags. brake_program is the Hub 'Stop Program'
    -- (same BrakePrgArUs array); ROTOR_BREAK in the Hub service export is rotor_brake_program.
    pitch_error_program                  INTEGER NOT NULL DEFAULT 0,   -- Pitch Error Program    PtErrOpPrgArUs
    pitch_warning_program                INTEGER NOT NULL DEFAULT 0,   -- Pitch Warning Program  PtWarnOpPrgArUs
    rotor_brake_program                  INTEGER NOT NULL DEFAULT 0,   -- ROTOR_BREAK            RotorBrakePrgArUs
    stop_program_40_flag                 INTEGER CHECK (stop_program_40_flag IS NULL OR stop_program_40_flag IN (0,1)),
    stop_program_80_flag                 INTEGER CHECK (stop_program_80_flag IS NULL OR stop_program_80_flag IN (0,1)),
    manual_operation_flag                INTEGER CHECK (manual_operation_flag IS NULL OR manual_operation_flag IN (0,1)),
    automatic_operation_flag             INTEGER CHECK (automatic_operation_flag IS NULL OR automatic_operation_flag IN (0,1)),
    vane_position_flag                   INTEGER CHECK (vane_position_flag IS NULL OR vane_position_flag IN (0,1)),

    -- v4.1 parameters both controllers carry in the generated program but no workbook exports.
    -- NULL = not captured yet.
    operating_mode_mask                  INTEGER CHECK (operating_mode_mask IS NULL OR operating_mode_mask BETWEEN 0 AND 1048575),   -- OpModeArDw: 20 bits Main, 6 bits Hub
    task_call_frequency                  INTEGER CHECK (task_call_frequency IS NULL OR task_call_frequency >= 1),                  -- TaskCallFrequencyArBy (1, 10 or 100 so far)
    availability_calc                    INTEGER CHECK (availability_calc IS NULL OR availability_calc IN (0,1)),                  -- AvailabilityCalcArBo

    development_access              INTEGER REFERENCES lookup_development_access(id),
    sales_access                    INTEGER REFERENCES lookup_sales_access(id),
    tcc_access                      INTEGER REFERENCES lookup_tcc_access(id),
    service_access                  INTEGER REFERENCES lookup_service_access(id),
    turbine_operator_package_access INTEGER REFERENCES lookup_top_access(id),
    grid_operator_access            INTEGER REFERENCES lookup_grid_operator_access(id),
    service_partner_access          INTEGER REFERENCES lookup_service_partner_access(id),
    customer_access                 INTEGER REFERENCES lookup_customer_access(id),

    -- logical_node / node_value are derived (docs/06-data-dictionary.md §2e);
    -- NOT stored as independent columns to guarantee they can never drift
    -- from the parent status_code's functional_system_group_id. Exposed via
    -- a read-only view / computed API field instead — see 07-database-design.md.

    owner_id                        INTEGER NOT NULL REFERENCES user(id),
    lifecycle_status                TEXT NOT NULL DEFAULT 'DRAFT'
                                     CHECK (lifecycle_status IN ('DRAFT','REVIEW','PENDING_APPROVAL','APPROVED','RELEASED','DEPRECATED','ARCHIVED')),
    created_by                      INTEGER NOT NULL REFERENCES user(id),
    created_at                      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    reviewer_signoff_by             INTEGER REFERENCES user(id),
    reviewer_signoff_at             TEXT,
    admin_signoff_by                INTEGER REFERENCES user(id),
    admin_signoff_at                TEXT,
    chief_engineer_approved_by      INTEGER REFERENCES user(id),
    chief_engineer_approval_date    TEXT,
    effective_date                  TEXT,
    deprecated_reason               TEXT,
    superseded_by_status_code_id    INTEGER REFERENCES status_code(id),

    -- I-01 optimistic concurrency: row_version increments on every Draft edit.
    row_version                     INTEGER NOT NULL DEFAULT 1,
    updated_at                      TEXT,
    -- I-14 troubleshooting content (all optional)
    remedy_text                     TEXT CHECK (remedy_text IS NULL OR length(remedy_text) <= 4000),
    affected_component              TEXT CHECK (affected_component IS NULL OR length(affected_component) <= 200),
    related_status_codes            TEXT CHECK (related_status_codes IS NULL OR length(related_status_codes) <= 500),
    standard_references             TEXT CHECK (standard_references IS NULL OR length(standard_references) <= 1000),
    -- I-07 applicability (from/to inclusive; NULL = open-ended)
    applies_from_version_id         INTEGER REFERENCES lookup_controller_software_version(id),
    applies_to_version_id           INTEGER REFERENCES lookup_controller_software_version(id),
    -- I-27 planned dates (ISO yyyy-mm-dd); informative, never change the lifecycle by themselves
    planned_effective_date          TEXT,
    planned_deprecation_date        TEXT,
    UNIQUE (status_code_id, revision_number),
    CHECK (reviewer_signoff_by IS NULL OR reviewer_signoff_by <> created_by),
    CHECK (admin_signoff_by IS NULL OR admin_signoff_by <> created_by),
    CHECK (chief_engineer_approved_by IS NULL OR (
        chief_engineer_approved_by <> created_by
        AND chief_engineer_approved_by <> reviewer_signoff_by
        AND chief_engineer_approved_by <> admin_signoff_by
    ))
);

CREATE UNIQUE INDEX ux_revision_current_per_code
    ON status_code_revision (status_code_id) WHERE is_current = 1;
CREATE INDEX ix_revision_status_code ON status_code_revision (status_code_id);
CREATE INDEX ix_revision_lifecycle ON status_code_revision (lifecycle_status);
CREATE INDEX ix_revision_owner ON status_code_revision (owner_id);
CREATE INDEX ix_revision_category ON status_code_revision (status_category);
CREATE UNIQUE INDEX ux_one_open_cr_per_code
    ON status_code_revision (status_code_id) WHERE lifecycle_status IN ('DRAFT','REVIEW','PENDING_APPROVAL');

CREATE TABLE status_code_revision_platform (
    id INTEGER PRIMARY KEY,
    status_code_revision_id INTEGER NOT NULL REFERENCES status_code_revision(id),
    turbine_platform_id INTEGER NOT NULL REFERENCES lookup_turbine_platform(id),
    UNIQUE (status_code_revision_id, turbine_platform_id)
);

-- v4.1: the numeric user-group levels of one revision, one row per slot (UserGroupReadArBy /
-- UserGroupWriteArBy are BYTE arrays). Slots 1..8 mirror the eight audience fields above.
CREATE TABLE status_code_revision_user_group (
    id INTEGER PRIMARY KEY,
    status_code_revision_id INTEGER NOT NULL REFERENCES status_code_revision(id),
    user_group_slot_id INTEGER NOT NULL REFERENCES lookup_user_group_slot(id),
    read_level INTEGER NOT NULL CHECK (read_level BETWEEN 0 AND 255),
    write_level INTEGER NOT NULL CHECK (write_level BETWEEN 0 AND 255),
    UNIQUE (status_code_revision_id, user_group_slot_id)
);

-- Import (v3) — CSV/XLSX library import, still subject to full governance
-- (docs/06-data-dictionary.md §5, 05-governance-handbook.md §6b). Created
-- before change_request so the FK below resolves at CREATE TABLE time.
CREATE TABLE import_job (
    id                      INTEGER PRIMARY KEY,
    requested_by            INTEGER NOT NULL REFERENCES user(id),
    source_format           TEXT NOT NULL CHECK (source_format IN ('CSV','XLSX','ST')),   -- 'ST' = v4.2, generated StCd programs
    source_file_reference   TEXT NOT NULL,
    row_count               INTEGER NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','VALIDATING','COMPLETE','FAILED')),
    created_count           INTEGER NOT NULL DEFAULT 0,
    error_count             INTEGER NOT NULL DEFAULT 0,
    error_report_reference  TEXT,
    created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at            TEXT,
    processed_count         INTEGER NOT NULL DEFAULT 0,   -- I-32 progress (rows handled so far)
    warning_count           INTEGER NOT NULL DEFAULT 0,   -- I-12 duplicate / I-04 reference warnings
    import_mode             TEXT NOT NULL DEFAULT 'CREATE' CHECK (import_mode IN ('CREATE','UPDATE')),   -- I-05
    error_report_xlsx_reference TEXT,
    change_set_id           INTEGER REFERENCES change_set(id)   -- v4.2: the batch change set of an ST import
);

-- v4.2: provenance of every status code created from a generated StCd_<n>.st program. The parsed
-- attributes stay as JSON, including those the catalogue has no column for yet (user-group levels,
-- the per-subsystem programs), so nothing the file said is lost and a later re-import can show what
-- changed. The file itself is kept under instance/imports/<job>/ and identified by its SHA-256.
CREATE TABLE import_source_item (
    id              INTEGER PRIMARY KEY,
    import_job_id   INTEGER NOT NULL REFERENCES import_job(id),
    status_code_id  INTEGER NOT NULL REFERENCES status_code(id),
    source_file     TEXT NOT NULL,
    source_sha256   TEXT NOT NULL CHECK (length(source_sha256) = 64),
    program_number  INTEGER NOT NULL CHECK (program_number >= 0),   -- StCd_<n> as written in the file
    controller      TEXT NOT NULL CHECK (controller IN ('MC','HC')),
    source_line     INTEGER NOT NULL DEFAULT 0,
    parsed_json     TEXT NOT NULL,
    UNIQUE (import_job_id, source_file, program_number)
);
CREATE INDEX ix_import_source_item_status_code ON import_source_item (status_code_id);

-- I-11: a change set groups the CRs that ship with one controller software
-- release. Presentation and queueing only: every CR keeps its own three decisions.
CREATE TABLE change_set (
    id                          INTEGER PRIMARY KEY,
    name                        TEXT NOT NULL UNIQUE,
    description                 TEXT,
    target_software_version_id  INTEGER REFERENCES lookup_controller_software_version(id),
    status                      TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CLOSED')),
    created_by                  INTEGER NOT NULL REFERENCES user(id),
    created_at                  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    closed_at                   TEXT
);

CREATE TABLE change_request (
    id                          INTEGER PRIMARY KEY,
    status_code_revision_id     INTEGER NOT NULL UNIQUE REFERENCES status_code_revision(id),
    cr_type                     TEXT NOT NULL CHECK (cr_type IN ('NEW','REVISION','DEPRECATION','IMPORT')),
    requested_by                INTEGER NOT NULL REFERENCES user(id),
    justification               TEXT,
    import_job_id                INTEGER REFERENCES import_job(id),
    state                       TEXT NOT NULL DEFAULT 'DRAFT'
                                 CHECK (state IN ('DRAFT','REVIEW','PENDING_APPROVAL','APPROVED','REJECTED','WITHDRAWN')),
    submitted_at                TEXT,
    chief_engineer_decided_at   TEXT,
    chief_engineer_decided_by   INTEGER REFERENCES user(id),
    assigned_reviewer_id        INTEGER REFERENCES user(id),   -- FR-039: optional Reviewer assignment, Administrator-managed
    change_set_id               INTEGER REFERENCES change_set(id),   -- I-11
    CHECK (chief_engineer_decided_by IS NULL OR chief_engineer_decided_by <> requested_by)
);
CREATE INDEX ix_cr_state ON change_request (state);
CREATE INDEX ix_cr_requested_by ON change_request (requested_by);

CREATE TABLE review_comment (
    id                  INTEGER PRIMARY KEY,
    change_request_id   INTEGER NOT NULL REFERENCES change_request(id),
    author_id           INTEGER NOT NULL REFERENCES user(id),
    comment_text        TEXT NOT NULL CHECK (length(comment_text) BETWEEN 1 AND 4000),
    decision            TEXT CHECK (decision IN (
                             'REVIEWER_APPROVE','REVIEWER_REJECT',
                             'ADMIN_APPROVE','ADMIN_REJECT',
                             'CHIEF_ENGINEER_APPROVE','CHIEF_ENGINEER_REJECT')),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX ix_comment_cr ON review_comment (change_request_id);

CREATE TABLE domain_signoff (
    id                          INTEGER PRIMARY KEY,
    change_request_id           INTEGER NOT NULL REFERENCES change_request(id),
    engineering_domain_id       INTEGER NOT NULL REFERENCES lookup_engineering_domain(id),
    signed_off_by                INTEGER NOT NULL REFERENCES user(id),
    signed_off_at                TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (change_request_id, engineering_domain_id)
);

-- FR-028: the originating Engineer's explicit request for a domain sign-off,
-- optionally directed at one named Engineer holding that domain. Surfaces on
-- the target's Dashboard / My Change Requests (10-ui-ux-specification.md §6).
CREATE TABLE domain_signoff_request (
    id                          INTEGER PRIMARY KEY,
    change_request_id           INTEGER NOT NULL REFERENCES change_request(id),
    engineering_domain_id       INTEGER NOT NULL REFERENCES lookup_engineering_domain(id),
    requested_by                INTEGER NOT NULL REFERENCES user(id),
    target_user_id              INTEGER REFERENCES user(id),
    created_at                  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (change_request_id, engineering_domain_id)
);
CREATE INDEX ix_dsr_target ON domain_signoff_request (target_user_id);

CREATE TABLE release (
    id                  INTEGER PRIMARY KEY,
    name                TEXT NOT NULL,
    version_label       TEXT NOT NULL UNIQUE,
    description         TEXT,
    scope_filter        TEXT NOT NULL DEFAULT '{}',
    status              TEXT NOT NULL DEFAULT 'BUILDING' CHECK (status IN ('BUILDING','PUBLISHED')),
    created_by          INTEGER NOT NULL REFERENCES user(id),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    published_by        INTEGER REFERENCES user(id),
    published_at        TEXT
);

CREATE TABLE release_item (
    id                          INTEGER PRIMARY KEY,
    release_id                  INTEGER NOT NULL REFERENCES release(id),
    status_code_revision_id     INTEGER NOT NULL UNIQUE REFERENCES status_code_revision(id)
);
CREATE INDEX ix_release_item_release ON release_item (release_id);

-- ----------------------------------------------------------------------------
-- Audit & export
-- ----------------------------------------------------------------------------

CREATE TABLE audit_log_entry (
    id              INTEGER PRIMARY KEY,
    entity_type     TEXT NOT NULL,
    entity_id       INTEGER NOT NULL,
    action          TEXT NOT NULL,
    actor_id        INTEGER REFERENCES user(id),
    occurred_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    before_value    TEXT,
    after_value     TEXT,
    ip_address      TEXT,
    request_id      TEXT NOT NULL,
    prev_hash       TEXT,   -- I-18: entry_hash of the preceding row ('GENESIS' for the first)
    entry_hash      TEXT    -- I-18: SHA-256 (or HMAC-SHA-256 with AUDIT_HMAC_KEY) over this row + prev_hash
);
CREATE INDEX ix_audit_entity ON audit_log_entry (entity_type, entity_id);
CREATE INDEX ix_audit_actor ON audit_log_entry (actor_id);
CREATE INDEX ix_audit_occurred ON audit_log_entry (occurred_at);

CREATE TABLE export_job (
    id                  INTEGER PRIMARY KEY,
    requested_by        INTEGER NOT NULL REFERENCES user(id),
    export_type         TEXT NOT NULL CHECK (export_type IN ('CSV','JSON','XLSX','PDF','SQLITE_BACKUP','HTML','MD','ZIP')),
    export_scope_type   TEXT NOT NULL DEFAULT 'CATALOGUE' CHECK (export_scope_type IN ('CATALOGUE','FULL_DATABASE','RELEASE_NOTES','OFFLINE_BUNDLE')),
    scope               TEXT NOT NULL DEFAULT '{}',
    release_id          INTEGER REFERENCES release(id),
    status              TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','COMPLETE','FAILED')),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at        TEXT,
    file_reference      TEXT,
    -- I-06 integrity: what exactly left the system
    sha256              TEXT,
    size_bytes          INTEGER,
    row_count           INTEGER,
    profile_code        TEXT,
    audience            TEXT,
    language_code       TEXT,
    software_version_code TEXT,
    manifest            TEXT
);
CREATE INDEX ix_export_job_sha256 ON export_job (sha256);


-- ----------------------------------------------------------------------------
-- v4 additions (improvement pack, docs/21-improvement-ideas.md)
-- ----------------------------------------------------------------------------

-- I-07: the controller software versions a Release is published for.
CREATE TABLE release_target_version (
    id                  INTEGER PRIMARY KEY,
    release_id          INTEGER NOT NULL REFERENCES release(id),
    software_version_id INTEGER NOT NULL REFERENCES lookup_controller_software_version(id),
    UNIQUE (release_id, software_version_id)
);

-- I-02 / I-03: export profiles are Administrator-managed data, not code.
-- `columns` is a JSON array of {"field": <export column>, "label": <header>}.
CREATE TABLE export_profile (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    description     TEXT,
    columns         TEXT NOT NULL,
    language_code   TEXT,                       -- NULL = the catalogue's source language
    audience        TEXT,                       -- default audience filter (I-03), NULL = none
    title_page      INTEGER NOT NULL DEFAULT 1 CHECK (title_page IN (0,1)),
    pdf_orientation TEXT NOT NULL DEFAULT 'L' CHECK (pdf_orientation IN ('L','P')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_by      INTEGER REFERENCES user(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
INSERT INTO export_profile (code, name, description, columns, audience, pdf_orientation, sort_order) VALUES
    ('SERVICE_MANUAL', 'Service manual',
     'Identifier, title, description, category, delays and remedy text for Technical Publications.',
     '[{"field":"status_code_identifier","label":"Status code"},{"field":"title","label":"Title"},{"field":"description","label":"Description"},{"field":"status_category","label":"Category"},{"field":"set_delay","label":"Set delay"},{"field":"reset_delay","label":"Reset delay"},{"field":"remedy_text","label":"Remedy"}]',
     NULL, 'L', 1),
    ('SCADA_TAGS', 'SCADA tag list',
     'Identifier, logical node, category and alarm flag for SCADA tag import.',
     '[{"field":"status_code_identifier","label":"Status code"},{"field":"logical_node","label":"Node"},{"field":"node_value","label":"Node value"},{"field":"title","label":"Tag text"},{"field":"status_category","label":"Category"},{"field":"alarm_flag","label":"Alarm"}]',
     NULL, 'L', 2),
    ('CUSTOMER_LIST', 'Customer list',
     'Customer-facing list; only codes the Customer audience may see (I-03).',
     '[{"field":"status_code_identifier","label":"Status code"},{"field":"title","label":"Title"},{"field":"description","label":"Description"},{"field":"status_category","label":"Category"},{"field":"remedy_text","label":"Remedy"}]',
     'customer', 'P', 3);

-- I-13: evidence on a change request (files live outside the web root; only metadata here).
CREATE TABLE cr_attachment (
    id                  INTEGER PRIMARY KEY,
    change_request_id   INTEGER NOT NULL REFERENCES change_request(id),
    filename            TEXT NOT NULL,
    content_type        TEXT NOT NULL,
    size_bytes          INTEGER NOT NULL CHECK (size_bytes >= 0),
    sha256              TEXT NOT NULL,
    storage_path        TEXT NOT NULL,
    description         TEXT,
    uploaded_by         INTEGER NOT NULL REFERENCES user(id),
    uploaded_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX ix_cr_attachment_cr ON cr_attachment (change_request_id);

-- I-15: translations of a revision's text. No row = MISSING. Approval is a light
-- review by someone other than the translator, not the three-decision cycle.
CREATE TABLE revision_translation (
    id                      INTEGER PRIMARY KEY,
    status_code_revision_id INTEGER NOT NULL REFERENCES status_code_revision(id),
    language_id             INTEGER NOT NULL REFERENCES lookup_language(id),
    title                   TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    description             TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 4000),
    remedy_text             TEXT CHECK (remedy_text IS NULL OR length(remedy_text) <= 4000),
    translation_status      TEXT NOT NULL DEFAULT 'DRAFT' CHECK (translation_status IN ('DRAFT','APPROVED')),
    translated_by           INTEGER NOT NULL REFERENCES user(id),
    translated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    approved_by             INTEGER REFERENCES user(id),
    approved_at             TEXT,
    UNIQUE (status_code_revision_id, language_id),
    CHECK (approved_by IS NULL OR approved_by <> translated_by)
);

-- I-16: delegation / out-of-office cover for the decision roles.
CREATE TABLE delegation (
    id              INTEGER PRIMARY KEY,
    delegator_id    INTEGER NOT NULL REFERENCES user(id),
    delegate_id     INTEGER NOT NULL REFERENCES user(id),
    role_code       TEXT NOT NULL CHECK (role_code IN ('REVIEWER','ADMINISTRATOR','CHIEF_ENGINEER')),
    valid_from      TEXT NOT NULL,
    valid_to        TEXT NOT NULL,
    created_by      INTEGER NOT NULL REFERENCES user(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    revoked_at      TEXT,
    CHECK (delegator_id <> delegate_id),
    CHECK (valid_to >= valid_from)
);
CREATE INDEX ix_delegation_delegate ON delegation (delegate_id);

-- I-23: field-level review comments and per-group review checklists.
CREATE TABLE field_comment (
    id                  INTEGER PRIMARY KEY,
    change_request_id   INTEGER NOT NULL REFERENCES change_request(id),
    field_name          TEXT NOT NULL,
    author_id           INTEGER NOT NULL REFERENCES user(id),
    comment_text        TEXT NOT NULL CHECK (length(comment_text) BETWEEN 1 AND 2000),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    resolved_by         INTEGER REFERENCES user(id),
    resolved_at         TEXT
);
CREATE INDEX ix_field_comment_cr ON field_comment (change_request_id);

CREATE TABLE review_checklist_item (
    id                          INTEGER PRIMARY KEY,
    functional_system_group_id  INTEGER REFERENCES lookup_functional_system_group(id),   -- NULL = every group
    text                        TEXT NOT NULL CHECK (length(text) BETWEEN 3 AND 300),
    is_active                   INTEGER NOT NULL DEFAULT 1,
    sort_order                  INTEGER NOT NULL DEFAULT 0,
    created_at                  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE cr_checklist_confirmation (
    id                  INTEGER PRIMARY KEY,
    change_request_id   INTEGER NOT NULL REFERENCES change_request(id),
    checklist_item_id   INTEGER NOT NULL REFERENCES review_checklist_item(id),
    item_text           TEXT NOT NULL,   -- snapshot: the wording confirmed at sign-off
    confirmed_by        INTEGER NOT NULL REFERENCES user(id),
    confirmed_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (change_request_id, checklist_item_id)
);

-- I-26: saved searches (definition = JSON of the list filters and visible columns).
CREATE TABLE saved_search (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES user(id),
    name        TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
    definition  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (user_id, name)
);

-- I-08: in-app notices (optionally also mailed through the organisation's own SMTP relay).
CREATE TABLE notification (
    id                  INTEGER PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES user(id),
    kind                TEXT NOT NULL,
    message             TEXT NOT NULL,
    link                TEXT,
    change_request_id   INTEGER REFERENCES change_request(id),
    dedupe_key          TEXT UNIQUE,
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    read_at             TEXT,
    emailed_at          TEXT
);
CREATE INDEX ix_notification_user ON notification (user_id, read_at);

-- I-20: login rate-limit counters live in the database so they survive a restart
-- and are shared by every worker process. attempted_at is epoch seconds.
CREATE TABLE login_attempt (
    id            INTEGER PRIMARY KEY,
    scope         TEXT NOT NULL CHECK (scope IN ('IP','USER')),
    key           TEXT NOT NULL,
    attempted_at  REAL NOT NULL
);
CREATE INDEX ix_login_attempt ON login_attempt (scope, key, attempted_at);

-- Administrator-managed settings (SLA thresholds, reviewer auto-assignment, ...).
CREATE TABLE app_setting (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_by  INTEGER REFERENCES user(id),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- I-28: occurrence counts imported from SCADA/CMS (anonymised, per period).
CREATE TABLE occurrence_import (
    id              INTEGER PRIMARY KEY,
    source_label    TEXT NOT NULL,
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    imported_by     INTEGER NOT NULL REFERENCES user(id),
    imported_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    row_count       INTEGER NOT NULL DEFAULT 0,
    unmatched_count INTEGER NOT NULL DEFAULT 0,
    CHECK (period_end >= period_start)
);
CREATE TABLE code_occurrence (
    id                    INTEGER PRIMARY KEY,
    occurrence_import_id  INTEGER NOT NULL REFERENCES occurrence_import(id),
    status_code_id        INTEGER NOT NULL REFERENCES status_code(id),
    occurrences           INTEGER NOT NULL CHECK (occurrences >= 0),
    UNIQUE (occurrence_import_id, status_code_id)
);

-- I-29: scoped, hashed, expiring API tokens; webhooks for internal consumers.
CREATE TABLE api_token (
    id            INTEGER PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES user(id),
    name          TEXT NOT NULL,
    token_prefix  TEXT NOT NULL,
    token_hash    TEXT NOT NULL UNIQUE,
    scopes        TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    last_used_at  TEXT,
    revoked_at    TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE webhook (
    id               INTEGER PRIMARY KEY,
    name             TEXT NOT NULL,
    url              TEXT NOT NULL,
    secret           TEXT NOT NULL,
    events           TEXT NOT NULL DEFAULT 'release.published',
    is_active        INTEGER NOT NULL DEFAULT 1,
    created_by       INTEGER NOT NULL REFERENCES user(id),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_delivery_at TEXT,
    last_status      TEXT
);
CREATE TABLE webhook_delivery (
    id            INTEGER PRIMARY KEY,
    webhook_id    INTEGER NOT NULL REFERENCES webhook(id),
    event         TEXT NOT NULL,
    payload       TEXT NOT NULL,
    http_status   INTEGER,
    ok            INTEGER NOT NULL DEFAULT 0 CHECK (ok IN (0,1)),
    error         TEXT,
    delivered_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- I-36: which Main Controller code replaces which Hub Controller code.
CREATE TABLE hub_mc_mapping (
    id                  INTEGER PRIMARY KEY,
    hub_status_code_id  INTEGER NOT NULL UNIQUE REFERENCES status_code(id),
    mc_status_code_id   INTEGER NOT NULL REFERENCES status_code(id),
    created_by          INTEGER NOT NULL REFERENCES user(id),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (hub_status_code_id <> mc_status_code_id)
);

-- ----------------------------------------------------------------------------
-- Triggers: prevent write access to immutable states / restricted operations
-- at the database layer (defense in depth — service layer is the primary
-- enforcement point; see docs/07-database-design.md §5)
-- ----------------------------------------------------------------------------

CREATE TRIGGER trg_prevent_edit_locked_revision
BEFORE UPDATE OF title, description, status_category, available_group, alarm_flag,
    set_delay, reset_delay, brake_program, manual_reset_program, auto_reset_program,
    development_access, sales_access, tcc_access, service_access,
    turbine_operator_package_access, grid_operator_access, service_partner_access, customer_access,
    remedy_text, affected_component, related_status_codes, standard_references,
    applies_from_version_id, applies_to_version_id,
    converter_reset_program, hydraulic_pump_program, gearbox_oil_pump_program, gearbox_oil_fan_program,
    gearbox_oil_heating_program, generator_fan_program, generator_heating_program,
    generator_bearing_lubrication_program, rotor_bearing_lubrication_program, anemometer_heating_program,
    medium_voltage_cb_program, tower_fan_program, transformer_oil_pump_program, zero_load_operation,
    pitch_error_program, pitch_warning_program, rotor_brake_program,
    stop_program_40_flag, stop_program_80_flag, manual_operation_flag, automatic_operation_flag,
    vane_position_flag, operating_mode_mask, task_call_frequency, availability_calc
ON status_code_revision
WHEN OLD.lifecycle_status IN ('APPROVED','RELEASED','ARCHIVED')
BEGIN
    SELECT RAISE(ABORT, 'Cannot edit a revision in APPROVED, RELEASED or ARCHIVED state');
END;

CREATE TRIGGER trg_prevent_release_item_delete
BEFORE DELETE ON release_item
WHEN (SELECT status FROM release WHERE id = OLD.release_id) = 'PUBLISHED'
BEGIN
    SELECT RAISE(ABORT, 'Cannot remove items from a published Release');
END;

CREATE TRIGGER trg_prevent_sandbox_release
BEFORE INSERT ON release_item
WHEN (
    SELECT sc.is_sandbox FROM status_code_revision scr
    JOIN status_code sc ON sc.id = scr.status_code_id
    WHERE scr.id = NEW.status_code_revision_id
) = 1
BEGIN
    SELECT RAISE(ABORT, 'Sandbox status codes can never be added to a Release');
END;

-- FR-072/FR-073: the audit trail is append-only at the database layer.
CREATE TRIGGER trg_audit_no_update
BEFORE UPDATE ON audit_log_entry
BEGIN
    SELECT RAISE(ABORT, 'audit_log_entry is append-only');
END;

CREATE TRIGGER trg_audit_no_delete
BEFORE DELETE ON audit_log_entry
BEGIN
    SELECT RAISE(ABORT, 'audit_log_entry is append-only');
END;

CREATE TRIGGER trg_prevent_nonsandbox_delete
BEFORE DELETE ON status_code
WHEN OLD.is_sandbox = 0
BEGIN
    SELECT RAISE(ABORT, 'Only sandbox (is_sandbox=1) status codes may be deleted');
END;

-- New subgroup non-overlap check (docs/06-data-dictionary.md §9a.1): the
-- service layer is the primary enforcement point (it can produce a helpful
-- 409 with the conflicting subgroup's name); this trigger is the database-
-- layer backstop.
CREATE TRIGGER trg_prevent_subgroup_overlap
BEFORE INSERT ON lookup_functional_subgroup
WHEN EXISTS (
    SELECT 1 FROM lookup_functional_subgroup existing
    WHERE existing.functional_system_group_id = NEW.functional_system_group_id
      AND NEW.sub_range_start <= existing.sub_range_end
      AND NEW.sub_range_end >= existing.sub_range_start
)
BEGIN
    SELECT RAISE(ABORT, 'New subgroup sub-range overlaps an existing subgroup in this Functional System Group');
END;

-- New group-level non-overlap check (new 2026-09-17): an Administrator may
-- assign a brand-new Functional System Group into any free range (e.g.
-- 10000-10999, 14000-14999, 15000-15999, 16000-16999 -- docs/05-governance-
-- handbook.md §2). Mirrors trg_prevent_subgroup_overlap one level up.
CREATE TRIGGER trg_prevent_group_overlap
BEFORE INSERT ON lookup_functional_system_group
WHEN EXISTS (
    SELECT 1 FROM lookup_functional_system_group existing
    WHERE NEW.range_start <= existing.range_end
      AND NEW.range_end >= existing.range_start
)
BEGIN
    SELECT RAISE(ABORT, 'New Functional System Group range overlaps an existing group');
END;

-- v4.1: PrgIdx_GUi identifies the block in controller diagnostics, so once a revision of the code
-- has been released the number is frozen. Setting it for the first time (NULL -> value, e.g. the
-- back-fill of the legacy library) is always allowed.
CREATE TRIGGER trg_prevent_prg_idx_change_after_release
BEFORE UPDATE OF prg_idx ON status_code
WHEN OLD.prg_idx IS NOT NULL AND NEW.prg_idx IS NOT OLD.prg_idx
 AND EXISTS (SELECT 1 FROM status_code_revision r
             WHERE r.status_code_id = OLD.id AND r.lifecycle_status IN ('RELEASED','DEPRECATED','ARCHIVED'))
BEGIN
    SELECT RAISE(ABORT, 'prg_idx cannot be changed once the status code has been released');
END;

-- v4.1: database backstop for "PrgIdx_GUi is mandatory". The service layer is the primary
-- enforcement point. The trigger stays inert until app_setting 'status_code.require_prg_idx' is '1',
-- which should happen once the legacy library carries its values and the application collects the field.
CREATE TRIGGER trg_require_prg_idx_for_review
BEFORE UPDATE OF lifecycle_status ON status_code_revision
WHEN NEW.lifecycle_status IN ('REVIEW','PENDING_APPROVAL','APPROVED','RELEASED')
 AND OLD.lifecycle_status IS NOT NEW.lifecycle_status
 AND COALESCE((SELECT value FROM app_setting WHERE key = 'status_code.require_prg_idx'), '0') = '1'
 AND (SELECT is_sandbox FROM status_code WHERE id = NEW.status_code_id) = 0
 AND (SELECT prg_idx FROM status_code WHERE id = NEW.status_code_id) IS NULL
BEGIN
    SELECT RAISE(ABORT, 'A status code needs its PrgIdx_GUi before it can leave Draft');
END;

-- v4.2: an imported code can only ever be issued the number its program carries. The service layer
-- does the same check first; this is the database backstop for any other writer.
CREATE TRIGGER trg_identifier_matches_reservation
BEFORE UPDATE OF status_code_identifier ON status_code
WHEN NEW.status_code_identifier IS NOT NULL
 AND OLD.status_code_identifier IS NULL
 AND NEW.reserved_identifier IS NOT NULL
 AND NEW.status_code_identifier <> NEW.reserved_identifier
BEGIN
    SELECT RAISE(ABORT, 'The identifier of an imported code must be the number it reserved');
END;

-- v4.2: a reservation can neither be taken from an identifier already issued to another code nor
-- be made for one.
CREATE TRIGGER trg_reservation_not_issued_elsewhere
BEFORE INSERT ON status_code
WHEN NEW.reserved_identifier IS NOT NULL
 AND EXISTS (SELECT 1 FROM status_code o WHERE o.status_code_identifier = NEW.reserved_identifier)
BEGIN
    SELECT RAISE(ABORT, 'The reserved identifier is already issued to another status code');
END;

-- v4.2: and no other code can be issued a number that an imported code has reserved.
CREATE TRIGGER trg_identifier_not_reserved_elsewhere
BEFORE UPDATE OF status_code_identifier ON status_code
WHEN NEW.status_code_identifier IS NOT NULL
 AND OLD.status_code_identifier IS NULL
 AND EXISTS (SELECT 1 FROM status_code o
             WHERE o.reserved_identifier = NEW.status_code_identifier AND o.id <> NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'The identifier is reserved by another imported status code');
END;

-- v4.7: the e-mail address identifies the person - also for the Windows sign-in that will replace
-- the password in a deployment - so it is fixed once the account exists. A typing error is corrected
-- by deleting the unused account and creating it again, or by deactivating it (docs/03-srs.md FR-162).
CREATE TRIGGER trg_user_email_immutable
BEFORE UPDATE OF email ON user
WHEN NEW.email <> OLD.email AND NEW.deleted_at IS NULL   -- v4.9: deleting an account erases its address
BEGIN
    SELECT RAISE(ABORT, 'The e-mail address of a user cannot be changed');
END;

-- ----------------------------------------------------------------------------
-- v4.7: translation review in the application (docs/26-translations.md, docs/03-srs.md FR-164).
-- Native speakers check the interface translations in the browser; an Administrator or StCd Owner
-- assigns them to a language and decides on their proposals; an accepted proposal becomes an
-- override that the application shows at once, without a new release.
-- ----------------------------------------------------------------------------

-- Who may review which language. Any account can be assigned (an external native speaker gets a
-- Viewer account and sees only this section).
CREATE TABLE language_reviewer (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES user(id),
    language_code   TEXT NOT NULL REFERENCES lookup_language(code),
    assigned_by     INTEGER NOT NULL REFERENCES user(id),
    assigned_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (user_id, language_code)
);

-- One review of one language by one reviewer. `fingerprint` is the catalogue (shipped text plus
-- overrides) the review started from; when it differs from the catalogue later, the review shows as
-- "changed since".
CREATE TABLE translation_review (
    id              INTEGER PRIMARY KEY,
    language_code   TEXT NOT NULL REFERENCES lookup_language(code),
    reviewer_id     INTEGER NOT NULL REFERENCES user(id),
    status          TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','COMPLETED')),
    started_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at    TEXT,
    fingerprint     TEXT NOT NULL,
    string_count    INTEGER NOT NULL CHECK (string_count >= 0)
);
CREATE UNIQUE INDEX ux_translation_review_open ON translation_review (language_code, reviewer_id) WHERE status = 'OPEN';

-- The answers: one row per string the reviewer has answered. A proposal with no current text is a
-- translation for a string that was missing.
CREATE TABLE translation_review_item (
    id              INTEGER PRIMARY KEY,
    review_id       INTEGER NOT NULL REFERENCES translation_review(id),
    string_id       TEXT NOT NULL,
    english         TEXT NOT NULL,
    current_text    TEXT,
    verdict         TEXT CHECK (verdict IN ('OK','CHANGE','UNCLEAR')),
    proposal        TEXT CHECK (proposal IS NULL OR length(proposal) <= 1000),
    comment         TEXT CHECK (comment IS NULL OR length(comment) <= 1000),
    decision        TEXT NOT NULL DEFAULT 'PENDING' CHECK (decision IN ('PENDING','ACCEPTED','REJECTED','NOTED')),
    decided_by      INTEGER REFERENCES user(id),
    decided_at      TEXT,
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (review_id, string_id),
    CHECK (verdict <> 'CHANGE' OR (proposal IS NOT NULL AND length(trim(proposal)) > 0))
);

-- An accepted proposal: the text the application shows for a string of a language instead of the
-- shipped one. Removing the row brings the shipped text back.
CREATE TABLE translation_override (
    id              INTEGER PRIMARY KEY,
    language_code   TEXT NOT NULL REFERENCES lookup_language(code),
    string_id       TEXT NOT NULL,
    english         TEXT NOT NULL,
    text            TEXT NOT NULL CHECK (length(text) BETWEEN 1 AND 1000),
    review_item_id  INTEGER REFERENCES translation_review_item(id),
    created_by      INTEGER NOT NULL REFERENCES user(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (language_code, string_id)
);


-- ----------------------------------------------------------------------------
-- Technical nomenclature (v4.8, FR-166): the terms of the controller and of the workflow with their
-- translations, kept apart from the interface translations (translation_*). A translation is
-- proposed (DRAFT) by one person and approved by another (APPROVED); a term marked keep_english is
-- never translated.
-- ----------------------------------------------------------------------------
CREATE TABLE terminology_term (
    id              INTEGER PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE CHECK (length(code) BETWEEN 2 AND 80),
    category        TEXT NOT NULL CHECK (category IN ('PRODUCT','DATA','STATE','PROCESS','ROLE','AUDIENCE','KEEP')),
    english         TEXT NOT NULL CHECK (length(trim(english)) BETWEEN 1 AND 200),
    definition      TEXT NOT NULL DEFAULT '' CHECK (length(definition) <= 1000),
    keep_english    INTEGER NOT NULL DEFAULT 0 CHECK (keep_english IN (0,1)),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_by      INTEGER REFERENCES user(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE terminology_translation (
    id              INTEGER PRIMARY KEY,
    term_id         INTEGER NOT NULL REFERENCES terminology_term(id),
    language_code   TEXT NOT NULL REFERENCES lookup_language(code),
    text            TEXT NOT NULL CHECK (length(trim(text)) BETWEEN 1 AND 200),
    status          TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','APPROVED')),
    note            TEXT CHECK (note IS NULL OR length(note) <= 500),
    proposed_by     INTEGER REFERENCES user(id),
    proposed_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    approved_by     INTEGER REFERENCES user(id),
    approved_at     TEXT,
    UNIQUE (term_id, language_code),
    CHECK ((status = 'APPROVED') = (approved_at IS NOT NULL))
);


-- v4.13: the sample inspection of a bulk decision (FR-180): which codes of a batch were drawn, who looked
CREATE TABLE bulk_sample (
    id                  INTEGER PRIMARY KEY,
    change_set_id       INTEGER NOT NULL REFERENCES change_set(id),
    step                TEXT NOT NULL CHECK (step IN ('domain','reviewer','admin','chief-engineer')),
    domain_code         TEXT CHECK (domain_code IS NULL OR length(domain_code) BETWEEN 1 AND 40),
    drawn_by            INTEGER NOT NULL REFERENCES user(id),
    drawn_at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    seed                TEXT NOT NULL,
    population          INTEGER NOT NULL CHECK (population >= 1),
    population_hash     TEXT NOT NULL,
    rate_percent        INTEGER NOT NULL CHECK (rate_percent BETWEEN 1 AND 100),
    status              TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','PASSED','FAILED','USED','VOID')),
    used_at             TEXT,
    CHECK ((step = 'domain') = (domain_code IS NOT NULL)),
    CHECK ((status = 'USED') = (used_at IS NOT NULL))
);

CREATE TABLE bulk_sample_item (
    id                  INTEGER PRIMARY KEY,
    sample_id           INTEGER NOT NULL REFERENCES bulk_sample(id),
    change_request_id   INTEGER NOT NULL REFERENCES change_request(id),
    verdict             TEXT CHECK (verdict IN ('OK','DEFECT')),
    note                TEXT CHECK (note IS NULL OR length(note) <= 1000),
    checked_at          TEXT,
    UNIQUE (sample_id, change_request_id),
    CHECK ((verdict IS NULL) = (checked_at IS NULL))
);

CREATE INDEX ix_bulk_sample_set ON bulk_sample (change_set_id, step, status);


-- v4.17: the legacy -> new status code mapping (FR-191..FR-198). It holds only what the generated .st programs do not
-- carry: the English title, the type, the up/down counter, the named access levels, cause and directive and the
-- legacy -> new pair itself. The initial content is the workbook seed_data/legacy_mapping.xlsx (flask mapping-seed);
-- every later change is a mapping_change with the three approvals of mapping_approval.
CREATE TABLE status_code_mapping (
    id                  INTEGER PRIMARY KEY,
    family              TEXT NOT NULL CHECK (family IN ('MC','HC')),
    legacy_number       INTEGER CHECK (legacy_number IS NULL OR legacy_number >= 0),
    new_number          INTEGER NOT NULL CHECK (new_number BETWEEN 1 AND 99999),
    description         TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 120),
    functional_group    TEXT CHECK (functional_group IS NULL OR length(functional_group) <= 80),
    logical_node        TEXT CHECK (logical_node IS NULL OR length(logical_node) <= 12),
    status_type         TEXT CHECK (status_type IS NULL OR status_type IN ('ERROR','WARNING','INFO')),
    up_down_counter     INTEGER CHECK (up_down_counter IS NULL OR up_down_counter IN (0,1)),
    parameter_set_delay   TEXT CHECK (parameter_set_delay IS NULL OR length(parameter_set_delay) <= 40),
    parameter_reset_delay TEXT CHECK (parameter_reset_delay IS NULL OR length(parameter_reset_delay) <= 40),
    development_access  TEXT,
    sales_access        TEXT,
    tcc_access          TEXT,
    service_access      TEXT,
    turbine_operator_package_access TEXT,
    grid_operator_access TEXT,
    service_partner_access TEXT,
    customer_access     TEXT,
    cause               TEXT CHECK (cause IS NULL OR length(cause) <= 4000),
    directive           TEXT CHECK (directive IS NULL OR length(directive) <= 4000),
    note                TEXT CHECK (note IS NULL OR length(note) <= 2000),
    status              TEXT NOT NULL DEFAULT 'PROPOSED' CHECK (status IN ('PROPOSED','FROM_PROGRAM','APPROVED','ISSUED','REJECTED')),
    source              TEXT CHECK (source IS NULL OR length(source) <= 200),
    version             INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (new_number),
    UNIQUE (family, legacy_number)
);

-- one request to change the mapping: one or several rows, decided as a whole by the three roles
CREATE TABLE mapping_change (
    id                  INTEGER PRIMARY KEY,
    title               TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 120),
    reason              TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 2000),
    origin              TEXT NOT NULL DEFAULT 'FORM' CHECK (origin IN ('FORM','WORKBOOK','SELECTION')),
    requested_by        INTEGER NOT NULL REFERENCES user(id),
    requested_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    state               TEXT NOT NULL DEFAULT 'OPEN' CHECK (state IN ('OPEN','APPLIED','REJECTED','WITHDRAWN')),
    closed_at           TEXT,
    CHECK ((state = 'OPEN') = (closed_at IS NULL))
);

CREATE TABLE mapping_change_item (
    id                  INTEGER PRIMARY KEY,
    change_id           INTEGER NOT NULL REFERENCES mapping_change(id),
    mapping_id          INTEGER REFERENCES status_code_mapping(id),
    action              TEXT NOT NULL CHECK (action IN ('ADD','CHANGE','CONFIRM','REJECT')),
    base_version        INTEGER,
    before_json         TEXT,
    after_json          TEXT NOT NULL,
    CHECK ((action = 'ADD') = (mapping_id IS NULL)),
    CHECK ((action = 'ADD') = (base_version IS NULL))
);

-- the three approvals: StCd Owner, Chief Engineer and one Administrator, each a different person who is not
-- the requester; one rejection closes the request
CREATE TABLE mapping_approval (
    id                  INTEGER PRIMARY KEY,
    change_id           INTEGER NOT NULL REFERENCES mapping_change(id),
    role_code           TEXT NOT NULL CHECK (role_code IN ('STCD_OWNER','CHIEF_ENGINEER','ADMINISTRATOR')),
    user_id             INTEGER NOT NULL REFERENCES user(id),
    decision            TEXT NOT NULL CHECK (decision IN ('APPROVE','REJECT')),
    comment             TEXT CHECK (comment IS NULL OR length(comment) <= 1000),
    decided_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    UNIQUE (change_id, role_code),
    UNIQUE (change_id, user_id)
);

CREATE INDEX ix_mapping_item_change ON mapping_change_item (change_id);
CREATE INDEX ix_mapping_item_row ON mapping_change_item (mapping_id);
CREATE INDEX ix_mapping_change_state ON mapping_change (state);
CREATE INDEX ix_mapping_status ON status_code_mapping (family, status);
