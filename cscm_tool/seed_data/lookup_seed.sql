-- ============================================================================
-- Lookup seed data — extracted verbatim from docs/artifacts/schema.sql.
-- This file is a reference/reuse copy (e.g. for test fixtures that only need
-- to reseed lookups against an already-migrated schema); the initial Alembic
-- migration (migrations/versions/9dc07a07a48b_*.py) applies schema.sql itself
-- and is the actual source of truth. Keep this file in sync with schema.sql's
-- INSERT statements in the same PR (docs/15-development-standards.md §5).
-- Includes the PLACEHOLDER Functional Subgroup taxonomy — see
-- docs/06-data-dictionary.md §9a; replacing it is a data change, not schema.
-- ============================================================================

INSERT INTO role (id, code, label) VALUES
    (1, 'ADMINISTRATOR', 'Administrator (Product Owner Controls Software)'),
    (2, 'ENGINEER', 'Engineer'),
    (3, 'REVIEWER', 'Reviewer (Sub-PO for Status Codes)'),
    (4, 'CHIEF_ENGINEER', 'Chief Engineer'),
    (5, 'VIEWER', 'Viewer');

INSERT INTO lookup_engineering_domain (code, label, sort_order) VALUES
    ('CONTROLS','Controls Engineering',1), ('ELECTRICAL','Electrical Engineering',2),
    ('MECHANICAL','Mechanical Engineering',3), ('GRID','Grid / Power Systems Engineering',4),
    ('SAFETY','Functional Safety Engineering',5);

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
INSERT INTO lookup_functional_subgroup (functional_system_group_id, code, label, sub_range_start, sub_range_end, sort_order)
SELECT g.id, g.code || '-1', 'Subgroup 1 (TBD)', g.range_start, g.range_start + (g.range_end - g.range_start) / 3, 1
FROM lookup_functional_system_group g;
INSERT INTO lookup_functional_subgroup (functional_system_group_id, code, label, sub_range_start, sub_range_end, sort_order)
SELECT g.id, g.code || '-2', 'Subgroup 2 (TBD)', g.range_start + (g.range_end - g.range_start) / 3 + 1, g.range_start + 2 * (g.range_end - g.range_start) / 3, 2
FROM lookup_functional_system_group g;
INSERT INTO lookup_functional_subgroup (functional_system_group_id, code, label, sub_range_start, sub_range_end, sort_order)
SELECT g.id, g.code || '-3', 'Subgroup 3 (TBD)', g.range_start + 2 * (g.range_end - g.range_start) / 3 + 1, g.range_end, 3
FROM lookup_functional_system_group g;

INSERT INTO lookup_turbine_platform (code, label, sort_order) VALUES
    ('2XM','2XM Platform',1), ('3XM','3XM Platform',2), ('4XM','4XM Platform',3);

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
