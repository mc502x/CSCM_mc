-- ============================================================================
-- CSCM Tool — optional full-text search index (SQLite FTS5) — I-31
-- Applied by migration f8b2d4e6a012 after schema.sql. It is a separate file
-- because it is *derived* data: if the SQLite build has no FTS5 module the
-- migration skips it and catalogue search silently falls back to substring
-- search (LIKE); nothing else depends on it.
--
-- One row per status_code_revision (rowid = revision id), kept in step by
-- triggers. `prefix` indexes make "conv*" style matches fast.
-- ============================================================================

CREATE VIRTUAL TABLE IF NOT EXISTS status_code_fts USING fts5(
    identifier, title, description, remedy_text,
    tokenize = 'unicode61 remove_diacritics 2',
    prefix = '2 3 4'
);

-- Vocabulary of indexed terms; used for typo tolerance ("converte" ~ "converter").
CREATE VIRTUAL TABLE IF NOT EXISTS status_code_fts_vocab USING fts5vocab(status_code_fts, 'row');

CREATE TRIGGER IF NOT EXISTS trg_fts_revision_insert
AFTER INSERT ON status_code_revision
BEGIN
    INSERT INTO status_code_fts (rowid, identifier, title, description, remedy_text)
    VALUES (
        NEW.id,
        COALESCE((SELECT status_code_identifier FROM status_code WHERE id = NEW.status_code_id), ''),
        NEW.title, NEW.description, COALESCE(NEW.remedy_text, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_fts_revision_update
AFTER UPDATE OF title, description, remedy_text ON status_code_revision
BEGIN
    DELETE FROM status_code_fts WHERE rowid = OLD.id;
    INSERT INTO status_code_fts (rowid, identifier, title, description, remedy_text)
    VALUES (
        NEW.id,
        COALESCE((SELECT status_code_identifier FROM status_code WHERE id = NEW.status_code_id), ''),
        NEW.title, NEW.description, COALESCE(NEW.remedy_text, '')
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_fts_revision_delete
AFTER DELETE ON status_code_revision
BEGIN
    DELETE FROM status_code_fts WHERE rowid = OLD.id;
END;

-- The identifier is assigned at Submit for Review, after the revision rows exist.
CREATE TRIGGER IF NOT EXISTS trg_fts_code_identifier
AFTER UPDATE OF status_code_identifier ON status_code
BEGIN
    DELETE FROM status_code_fts
     WHERE rowid IN (SELECT id FROM status_code_revision WHERE status_code_id = NEW.id);
    INSERT INTO status_code_fts (rowid, identifier, title, description, remedy_text)
    SELECT r.id, COALESCE(NEW.status_code_identifier, ''), r.title, r.description,
           COALESCE(r.remedy_text, '')
      FROM status_code_revision r
     WHERE r.status_code_id = NEW.id;
END;
