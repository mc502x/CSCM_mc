-- ============================================================================
-- CSCM Tool — SQLite Physical Schema (MVP) — v3
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
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Reference / lookup tables
-- ----------------------------------------------------------------------------

CREATE TABLE role (
    id          INTEGER PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,      -- ADMINISTRATOR | ENGINEER | REVIEWER | CHIEF_ENGINEER | VIEWER
    label       TEXT NOT NULL
);
INSERT INTO role (id, code, label) VALUES
    (1, 'ADMINISTRATOR', 'Administrator (Product Owner Controls Software)'),
    (2, 'ENGINEER', 'Engineer'),
    (3, 'REVIEWER', 'Reviewer (Sub-PO for Status Codes)'),
    (4, 'CHIEF_ENGINEER', 'Chief Engineer'),
    (5, 'VIEWER', 'Viewer');

CREATE TABLE lookup_engineering_domain (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
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
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
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
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
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
    ('WCNV',1000,'010xx','Converter',1000,1099,1),
    ('WCNV',1000,'012xx','Grid',1200,1299,2),
    ('WGEN',2000,'020xx','Generator',2000,2099,1),
    ('WGEN',2000,'022xx','Protection',2200,2299,2),
    ('WNAC',3000,'030xx','Meteorology',3000,3099,1),
    ('WNAC',3000,'032xx','Nacelle',3200,3299,2),
    ('WROT',4000,'040xx','Rotor',4000,4099,1),
    ('WROT',4000,'042xx','Hot Air De-icing',4200,4299,2),
    ('WROT',4000,'043xx','Lighting',4300,4399,3),
    ('WROT',4000,'044xx','Blade Sensors',4400,4499,4),
    ('WTOW',5000,'050xx','Tower',5000,5099,1),
    ('WTRF',6000,'060xx','Switches',6000,6099,1),
    ('WTRF',6000,'062xx','Transformer',6200,6299,2),
    ('WTRM',7000,'070xx','Gearbox',7000,7099,1),
    ('WTRM',7000,'072xx','Drive train',7200,7299,2),
    ('WTRM',7000,'073xx','Hydraulics',7300,7399,3),
    ('WTRM',7000,'074xx','Brake',7400,7499,4),
    ('WYAW',8000,'080xx','Yaw',8000,8099,1),
    ('WTUR',9000,'090xx','System',9000,9099,1),
    ('WTUR',9000,'092xx','Control System',9200,9299,2),
    ('WTUR',9000,'093xx','Safety',9300,9399,3),
    ('WTUR',9000,'099xx-a','External',9900,9929,4),
    ('WTUR',9000,'099xx-b','Farm',9930,9959,5),
    ('WTUR',9000,'099xx-c','Feedback Control',9960,9969,6),
    ('WTUR',9000,'099xx-d','Interface',9970,9979,7),
    ('WTUR',9000,'099xx-e','Power Management',9980,9989,8),
    ('WTUR',9000,'099xx-f','UPS',9990,9999,9),
    -- Hub Controller subgroups (new 2026-09-17, source: "HC Status Code Number.xlsx")
    ('WTUR',11000,'11-0xx','Control System',11000,11100,1),
    ('WTUR',11000,'11-1xxA','Field Bus',11101,11150,2),
    ('WTUR',11000,'11-1xxB','System',11151,11200,3),
    ('WROT',12000,'12-0xx','Blade',12001,12050,1),
    ('WROT',12000,'12-0xxB','Batteries',12051,12200,2),
    ('WROT',12000,'12-2xx','Pitch',12201,12250,3),
    ('WROT',12000,'12-2xxB','Pitch Control',12251,12300,4),
    ('WROT',12000,'12-3xx','Pitch Drivers',12301,12400,5),
    ('WROT',12000,'12-4xx','Pitch Converter',12401,12500,6),
    ('WROT',12000,'12-5xx','Rotor',12501,12600,7),
    ('WPPD',13000,'13-0xx','Wind Farm',13001,13100,1)
)
SELECT g.id, v.code, v.label, v.sub_range_start, v.sub_range_end, v.sort_order
FROM v JOIN lookup_functional_system_group g
  ON g.code = v.group_code AND g.range_start = v.group_range_start;

CREATE TABLE lookup_turbine_platform (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO lookup_turbine_platform (code, label, sort_order) VALUES
    ('2XM','2XM Platform',1), ('3XM','3XM Platform',2), ('4XM','4XM Platform',3);

-- Available Group: numeric codes only, labels TBD pending Controls
-- Engineering confirmation (docs/06-data-dictionary.md §9c). Soft reference
-- set for validation, not a hard-enforced enum, since new codes may appear.
CREATE TABLE lookup_available_group (
    id INTEGER PRIMARY KEY, code INTEGER NOT NULL UNIQUE, label TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
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
CREATE TABLE lookup_development_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_development_access (code, label, sort_order) VALUES
    ('SCADA_USER','SCADA User',1), ('DEPARTMENT','Department',2), ('OPERATION_CONTROL','Operation Control',3), ('SEE_ONLY','See only',4);

CREATE TABLE lookup_sales_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_sales_access (code, label, sort_order) VALUES
    ('SALES','Sales',1), ('COVERT','Covert',2), ('SEE_ONLY','See only',3);

CREATE TABLE lookup_tcc_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_tcc_access (code, label, sort_order) VALUES
    ('TELENOTDIENST','Telenotdienst',1), ('TELENOTDIENST_READ','Telenotdienst-read',2), ('PMS_DISPATCHER','PMS Dispatcher',3), ('SEE_ONLY','See only',4);

CREATE TABLE lookup_service_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_service_access (code, label, sort_order) VALUES
    ('COMMISSIONING','Commissioning',1), ('SERVICE_AND_MAINTENANCE','Service and Maintenance',2), ('SEE_ONLY','See only',3);

CREATE TABLE lookup_top_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_top_access (code, label, sort_order) VALUES
    ('PREVENTIVE_MAINTENANCE','Preventive Maintenance',1), ('TROUBLESHOOTING','Troubleshooting',2),
    ('TROUBLESHOOTING_ADVANCED','Troubleshooting Advanced',3), ('COVERT','Covert',4), ('SEE_ONLY','See only',5);

CREATE TABLE lookup_grid_operator_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_grid_operator_access (code, label, sort_order) VALUES
    ('COVERT','Covert',1), ('SEE_ONLY','See only',2);

CREATE TABLE lookup_service_partner_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_service_partner_access (code, label, sort_order) VALUES
    ('SERVICE_PARTNER','Service Partner',1), ('EXT_SERVICE_PROVIDER','Ext. Service Provider',2),
    ('CUSTOMER_AFTER_WARRANTY_PROFESSIONAL','Customer after warranty Professional',3),
    ('CUSTOMER_AFTER_WARRANTY_ADVANCED','Customer after warranty Advanced',4),
    ('COVERT','Covert',5), ('SEE_ONLY','See only',6);

CREATE TABLE lookup_customer_access (id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0);
INSERT INTO lookup_customer_access (code, label, sort_order) VALUES
    ('STANDARD','Standard',1), ('ADVANCED','Advanced',2), ('PROFESSIONAL','Professional',3),
    ('PREMIUM','Premium',4), ('COVERT','Covert',5), ('SEE_ONLY','See only',6);

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
    locked_until        TEXT
);

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
    owner_id                            INTEGER NOT NULL REFERENCES user(id),
    created_at                          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    CHECK (status_code_identifier IS NULL
           OR status_code_identifier GLOB 'StCd-[0-9][0-9][0-9][0-9][0-9]'
           OR status_code_identifier GLOB 'StCd-T[0-9][0-9][0-9][0-9][0-9]')
);

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

-- Import (v3) — CSV/XLSX library import, still subject to full governance
-- (docs/06-data-dictionary.md §5, 05-governance-handbook.md §6b). Created
-- before change_request so the FK below resolves at CREATE TABLE time.
CREATE TABLE import_job (
    id                      INTEGER PRIMARY KEY,
    requested_by            INTEGER NOT NULL REFERENCES user(id),
    source_format           TEXT NOT NULL CHECK (source_format IN ('CSV','XLSX')),
    source_file_reference   TEXT NOT NULL,
    row_count               INTEGER NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','VALIDATING','COMPLETE','FAILED')),
    created_count           INTEGER NOT NULL DEFAULT 0,
    error_count             INTEGER NOT NULL DEFAULT 0,
    error_report_reference  TEXT,
    created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at            TEXT
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
    request_id      TEXT NOT NULL
);
CREATE INDEX ix_audit_entity ON audit_log_entry (entity_type, entity_id);
CREATE INDEX ix_audit_actor ON audit_log_entry (actor_id);
CREATE INDEX ix_audit_occurred ON audit_log_entry (occurred_at);

CREATE TABLE export_job (
    id                  INTEGER PRIMARY KEY,
    requested_by        INTEGER NOT NULL REFERENCES user(id),
    export_type         TEXT NOT NULL CHECK (export_type IN ('CSV','JSON','XLSX','PDF','SQLITE_BACKUP')),
    export_scope_type   TEXT NOT NULL DEFAULT 'CATALOGUE' CHECK (export_scope_type IN ('CATALOGUE','FULL_DATABASE')),
    scope               TEXT NOT NULL DEFAULT '{}',
    release_id          INTEGER REFERENCES release(id),
    status              TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','COMPLETE','FAILED')),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at        TEXT,
    file_reference      TEXT
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
    turbine_operator_package_access, grid_operator_access, service_partner_access, customer_access
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
