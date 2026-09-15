-- ============================================================================
-- CSCM Tool — SQLite Physical Schema (MVP) — v2
-- Referenced by: docs/07-database-design.md
-- Target: SQLite 3.35+ (requires partial index / generated column support)
-- v2 changes: Functional System Group/Subgroup numbering replaces Controller
-- Type; StCd-XXXXX identifier allocated at Draft->Review; Turbine Platform
-- multi-select; Engineering Domain + DomainSignoff; dual-review + Chief
-- Engineer approval (5 roles, 7 lifecycle states); sandbox status codes.
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

CREATE TABLE lookup_functional_system_group (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    range_start INTEGER NOT NULL, range_end INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
    CHECK (range_end > range_start)
);
INSERT INTO lookup_functional_system_group (code, label, range_start, range_end, sort_order) VALUES
    ('WCNV','Converter / Grid Interface',1000,1999,1),
    ('WGEN','Generator',2000,2999,2),
    ('WNAC','Meteorology / Environment / Nacelle Monitoring',3000,3999,3),
    ('WROT','Pitch System / Hub',4000,4999,4),
    ('WTOW','Tower / Oscillation Monitoring',5000,5999,5),
    ('WTRF','Transformer / MV Switchgear',6000,6999,6),
    ('WTRM','Drive Train / Gearbox / Hydraulic System / Rotor Brake',7000,7999,7),
    ('WYAW','Yaw System',8000,8999,8),
    ('WTUR','Turbine Control / Safety / Operational States / SCADA',9000,9999,9);

-- PLACEHOLDER subgroup taxonomy — replace with real data from Controls
-- Engineering before go-live (docs/06-data-dictionary.md §9a). Three even
-- sub-bands generated per group; no schema change needed to replace this data.
CREATE TABLE lookup_functional_subgroup (
    id INTEGER PRIMARY KEY,
    functional_system_group_id INTEGER NOT NULL REFERENCES lookup_functional_system_group(id),
    code TEXT NOT NULL, label TEXT NOT NULL,
    sub_range_start INTEGER NOT NULL, sub_range_end INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (functional_system_group_id, code),
    CHECK (sub_range_end > sub_range_start)
);
INSERT INTO lookup_functional_subgroup (functional_system_group_id, code, label, sub_range_start, sub_range_end, sort_order)
SELECT g.id, g.code || '-1', 'Subgroup 1 (TBD)', g.range_start, g.range_start + (g.range_end - g.range_start) / 3, 1
FROM lookup_functional_system_group g;
INSERT INTO lookup_functional_subgroup (functional_system_group_id, code, label, sub_range_start, sub_range_end, sort_order)
SELECT g.id, g.code || '-2', 'Subgroup 2 (TBD)', g.range_start + (g.range_end - g.range_start) / 3 + 1, g.range_start + 2 * (g.range_end - g.range_start) / 3, 2
FROM lookup_functional_system_group g;
INSERT INTO lookup_functional_subgroup (functional_system_group_id, code, label, sub_range_start, sub_range_end, sort_order)
SELECT g.id, g.code || '-3', 'Subgroup 3 (TBD)', g.range_start + 2 * (g.range_end - g.range_start) / 3 + 1, g.range_end, 3
FROM lookup_functional_system_group g;

CREATE TABLE lookup_turbine_platform (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
INSERT INTO lookup_turbine_platform (code, label, sort_order) VALUES
    ('2XM','2XM Platform',1), ('3XM','3XM Platform',2), ('4XM','4XM Platform',3);

CREATE TABLE lookup_status_category (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE lookup_availability_group (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE lookup_brake_program (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE lookup_reset_program (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE lookup_operational_state (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE lookup_access_rights (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE lookup_alarm_behaviour (
    id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, label TEXT NOT NULL, description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0
);

INSERT INTO lookup_status_category (code, label, sort_order) VALUES
    ('FAULT','Fault',1), ('WARNING','Warning',2), ('SAFETY','Safety',3),
    ('OPERATIONAL','Operational',4), ('MAINTENANCE','Maintenance',5), ('INFORMATION','Information',6);
INSERT INTO lookup_availability_group (code, label, sort_order) VALUES
    ('A','Group A - Full Stop',1), ('B','Group B - Partial Derate',2),
    ('C','Group C - Scheduled',3), ('D','Group D - No Impact',4);
INSERT INTO lookup_brake_program (code, label, sort_order) VALUES
    ('BP-NONE','No Brake Action',0), ('BP-1','Soft Aerodynamic Brake',1),
    ('BP-2','Full Aerodynamic Brake',2), ('BP-3','Mechanical Brake Assist',3),
    ('BP-4','Emergency Brake',4);
INSERT INTO lookup_reset_program (code, label, sort_order) VALUES
    ('AUTO','Automatic Reset',1), ('MANUAL','Manual Reset (Local)',2),
    ('REMOTE','Manual Reset (Remote/SCADA)',3), ('SCHEDULED','Scheduled Reset Window',4);
INSERT INTO lookup_operational_state (code, label, sort_order) VALUES
    ('RUNNING','Running',1), ('STOPPED','Stopped',2), ('IDLE','Idle',3),
    ('FAULT','Fault State',4), ('MAINTENANCE','Maintenance Mode',5), ('POWER_CURTAILED','Power Curtailed',6);
INSERT INTO lookup_access_rights (code, label, sort_order) VALUES
    ('SERVICE','Service Technician',1), ('CUSTOMER','Customer-Visible',2),
    ('OEM_ONLY','OEM Engineering Only',3), ('LEVEL_1','Level 1',4),
    ('LEVEL_2','Level 2',5), ('LEVEL_3','Level 3',6), ('LEVEL_4','Level 4',7);
INSERT INTO lookup_alarm_behaviour (code, label, sort_order) VALUES
    ('LATCHING','Latching',1), ('SELF_CLEARING','Self-Clearing',2),
    ('ESCALATING','Escalating',3), ('SILENT','Silent (Log-Only)',4);

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
    functional_subgroup_id              INTEGER REFERENCES lookup_functional_subgroup(id),
    is_sandbox                          INTEGER NOT NULL DEFAULT 0 CHECK (is_sandbox IN (0,1)),
    platform_variant_of_status_code_id  INTEGER REFERENCES status_code(id),
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
    status_category_id              INTEGER NOT NULL REFERENCES lookup_status_category(id),
    availability_group_id           INTEGER NOT NULL REFERENCES lookup_availability_group(id),
    brake_program_id                INTEGER NOT NULL REFERENCES lookup_brake_program(id),
    reset_program_id                INTEGER NOT NULL REFERENCES lookup_reset_program(id),
    software_version                TEXT NOT NULL,
    operational_state_id            INTEGER NOT NULL REFERENCES lookup_operational_state(id),
    access_rights_id                INTEGER NOT NULL REFERENCES lookup_access_rights(id),
    delay_before_alarm_seconds      INTEGER NOT NULL DEFAULT 0 CHECK (delay_before_alarm_seconds BETWEEN 0 AND 3600),
    delay_before_reset_seconds      INTEGER NOT NULL DEFAULT 0 CHECK (delay_before_reset_seconds BETWEEN 0 AND 86400),
    alarm_behaviour_id              INTEGER NOT NULL REFERENCES lookup_alarm_behaviour(id),
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
CREATE INDEX ix_revision_category ON status_code_revision (status_category_id);
CREATE UNIQUE INDEX ux_one_open_cr_per_code
    ON status_code_revision (status_code_id) WHERE lifecycle_status IN ('DRAFT','REVIEW','PENDING_APPROVAL');

CREATE TABLE status_code_revision_platform (
    id INTEGER PRIMARY KEY,
    status_code_revision_id INTEGER NOT NULL REFERENCES status_code_revision(id),
    turbine_platform_id INTEGER NOT NULL REFERENCES lookup_turbine_platform(id),
    UNIQUE (status_code_revision_id, turbine_platform_id)
);

CREATE TABLE change_request (
    id                          INTEGER PRIMARY KEY,
    status_code_revision_id     INTEGER NOT NULL UNIQUE REFERENCES status_code_revision(id),
    cr_type                     TEXT NOT NULL CHECK (cr_type IN ('NEW','REVISION','DEPRECATION')),
    requested_by                INTEGER NOT NULL REFERENCES user(id),
    justification               TEXT,
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
    export_type         TEXT NOT NULL CHECK (export_type IN ('CSV','JSON','PDF','SQLITE_BACKUP')),
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
BEFORE UPDATE OF title, description, status_category_id, availability_group_id,
    brake_program_id, reset_program_id, software_version, operational_state_id,
    access_rights_id, delay_before_alarm_seconds, delay_before_reset_seconds,
    alarm_behaviour_id
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
