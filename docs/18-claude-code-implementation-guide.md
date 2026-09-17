# 18. Claude Code Implementation Guide — CSCM Tool

This document is the implementation-facing companion to the rest of this package. It assumes the reader (human or Claude Code) has the full documentation set available and translates it into concrete build guidance. It does not restate business rules — it references them by ID.

## 1. Recommended Architecture Patterns

Unchanged in principle from v1 (18-claude-code-implementation-guide.md v1 §1): layered monolith (Presentation → Service → Repository → Data), repository pattern per aggregate root, service layer owning all business rules, Application Factory pattern, DTOs at the service boundary. The v2 model adds no new architectural pattern — it adds more service-layer state machine complexity (7 lifecycle states, three decision points instead of one) and one new cross-cutting concern (Cross-Domain Sign-Off gating), both of which fit cleanly inside the existing service layer.

## 2. Recommended Folder Structure

```
cscm_tool/
├── app/
│   ├── __init__.py                    # create_app() application factory
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── models/
│   │   ├── user.py                    # User, Role, EngineeringDomain, UserEngineeringDomain
│   │   ├── status_code.py             # StatusCode, StatusCodeRevision, StatusCodeRevisionPlatform
│   │   ├── change_request.py          # ChangeRequest, ReviewComment, DomainSignoff
│   │   ├── release.py                 # Release, ReleaseItem
│   │   ├── lookup.py                  # FunctionalSystemGroup, FunctionalSubgroup, TurbinePlatform,
│   │   │                               #   LookupStatusCategory, ... (7 original vocabularies)
│   │   ├── audit.py                   # AuditLogEntry
│   │   └── export_job.py              # ExportJob
│   │
│   ├── repositories/
│   │   ├── base.py
│   │   ├── user_repository.py
│   │   ├── status_code_repository.py  # incl. allocate_next_identifier() — see §6
│   │   ├── change_request_repository.py
│   │   ├── domain_signoff_repository.py
│   │   ├── release_repository.py
│   │   ├── lookup_repository.py
│   │   └── audit_repository.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── status_code_service.py     # create Draft, create sandbox, delete sandbox, edit
│   │   ├── numbering_service.py       # NEW — Functional Group/Subgroup identifier allocation
│   │   ├── domain_signoff_service.py  # NEW — Cross-Domain Sign-Off gating and recording
│   │   ├── change_request_service.py  # submit, reviewer_signoff, admin_signoff,
│   │   │                               #   chief_engineer_decide, withdraw
│   │   ├── release_service.py
│   │   ├── lookup_service.py
│   │   ├── export_service.py          # catalogue + full-database export
│   │   ├── import_service.py          # CSV/XLSX library import -> Draft CRs (new)
│   │   ├── subgroup_admin_service.py  # new-subgroup creation, overlap validation (new)
│   │   ├── audit_service.py
│   │   └── validation.py
│   │
│   ├── auth/
│   │   ├── providers.py               # AuthProvider protocol, SessionPasswordAuthProvider
│   │   │                               #   (future: OnPremActiveDirectoryAuthProvider — never a cloud IdP)
│   │   ├── decorators.py              # @login_required, @require_role(...), @not_author(...)
│   │   └── password.py
│   │
│   ├── api/v1/
│   │   ├── auth_routes.py
│   │   ├── user_routes.py
│   │   ├── status_code_routes.py      # incl. next-available preview, sandbox delete
│   │   ├── revision_routes.py
│   │   ├── change_request_routes.py   # incl. reviewer-signoff, admin-signoff, chief-engineer-decide
│   │   ├── domain_signoff_routes.py
│   │   ├── release_routes.py
│   │   ├── lookup_routes.py
│   │   ├── export_routes.py           # incl. /exports/full-database (Administrator only)
│   │   └── audit_routes.py
│   │
│   ├── ui/
│   │   ├── auth_views.py
│   │   ├── dashboard_views.py
│   │   ├── status_code_views.py       # S3-S7, S5a (sandbox)
│   │   ├── change_request_views.py    # S8-S10, S9a (approval queue), S10a (domain sign-off)
│   │   ├── release_views.py           # S11-S13
│   │   ├── admin_views.py             # S14-S16
│   │   └── export_views.py            # S17
│   │
│   ├── export/
│   │   ├── csv_exporter.py
│   │   ├── json_exporter.py
│   │   ├── xlsx_exporter.py
│   │   ├── pdf_exporter.py
│   │   └── full_database_exporter.py  # SQLite Online Backup API wrapper, Administrator only
│   │
│   ├── templates/
│   ├── static/                        # local-only assets, no CDN references (11-security-architecture.md §12)
│   │   ├── css/onetool-tokens.css     # OneTool design tokens (10-ui-ux-specification.md §0), vendored locally
│   │   └── vendor/manrope, inter, material-symbols/  # self-hosted fonts/icons, per the no-CDN rule
│   └── errors.py
│
├── migrations/
├── tests/{unit,integration,system}/
├── docs/
├── seed_data/lookup_seed.sql          # matches artifacts/schema.sql's seed inserts, incl. the real Functional Subgroup taxonomy
├── requirements.txt
├── pyproject.toml
├── wsgi.py
└── README.md
```

## 3. Flask Blueprint Structure

Unchanged in mechanism from v1 §3. Route handlers stay thin; the new decision endpoints follow the same pattern as the original `decide` example, now split into three distinct, narrowly-scoped handlers rather than one generic one, because each has a different authorization check:

```python
# app/api/v1/change_request_routes.py
from flask import Blueprint, request, jsonify
from app.auth.decorators import login_required, require_role
from app.services.change_request_service import ChangeRequestService

def register(bp: Blueprint):
    @bp.post("/change-requests/<int:cr_id>/reviewer-signoff")
    @login_required
    @require_role("REVIEWER")
    def reviewer_signoff(cr_id: int):
        body = request.get_json()
        result = ChangeRequestService.reviewer_signoff(
            cr_id=cr_id, actor=request.current_user,
            decision=body["decision"], comment=body.get("comment"),
        )
        return jsonify(result.to_dict()), 200

    @bp.post("/change-requests/<int:cr_id>/admin-signoff")
    @login_required
    @require_role("ADMINISTRATOR")
    def admin_signoff(cr_id: int):
        body = request.get_json()
        result = ChangeRequestService.admin_signoff(
            cr_id=cr_id, actor=request.current_user,
            decision=body["decision"], comment=body.get("comment"),
        )
        return jsonify(result.to_dict()), 200

    @bp.post("/change-requests/<int:cr_id>/chief-engineer-decide")
    @login_required
    @require_role("CHIEF_ENGINEER")
    def chief_engineer_decide(cr_id: int):
        body = request.get_json()
        result = ChangeRequestService.chief_engineer_decide(
            cr_id=cr_id, actor=request.current_user,
            decision=body["decision"], comment=body.get("comment"),
        )
        return jsonify(result.to_dict()), 200
```

The segregation-of-duties check (actor ≠ author, and for the Chief Engineer step, actor ≠ either prior sign-off) lives inside each service method, not in the decorator — the decorator only checks role membership, which is static; the author/sign-off comparison needs the specific `ChangeRequest` row (SEC-011).

## 4. Repository Pattern

Unchanged in mechanism from v1 §4 (`BaseRepository` generic CRUD helpers, no business rules in repositories). New repository method of note:

```python
# app/repositories/status_code_repository.py
class StatusCodeRepository(BaseRepository[StatusCode]):
    model = StatusCode

    def allocate_next_identifier(self, functional_system_group_id: int,
                                   functional_subgroup_id: int | None) -> str:
        """Must be called inside a BEGIN IMMEDIATE transaction — see
        docs/07-database-design.md §7a. Returns e.g. 'StCd-01233'."""
        ...

    def allocate_next_sandbox_identifier(self) -> str:
        """Draws from the isolated StCd-T##### counter; never touches the
        real Functional System Group ranges."""
        ...
```

## 5. Service Layer Pattern

The dual-sign-off + Chief Engineer approval logic is the most state-sensitive part of the system; it is written so the "did both sign-offs land" check and the resulting transition are always one atomic operation (07-database-design.md §7b):

```python
# app/services/change_request_service.py
from app.extensions import db
from app.repositories.change_request_repository import ChangeRequestRepository
from app.services.audit_service import AuditService
from app.domain.errors import SegregationOfDutiesViolation

class ChangeRequestService:
    """Implements the dual-review-then-Chief-Engineer-approval workflow.
    See 05-governance-handbook.md §7-8, BR-004/BR-005."""

    @staticmethod
    def admin_signoff(cr_id: int, actor, decision: str, comment: str | None):
        repo = ChangeRequestRepository()
        cr = repo.get(cr_id)
        revision = cr.revision

        if actor.id == cr.requested_by:
            raise SegregationOfDutiesViolation("BR-005: cannot sign off own change request")
        if revision.lifecycle_status != "REVIEW":
            raise InvalidTransition(f"Cannot sign off a revision in state {revision.lifecycle_status}")
        if decision == "REJECT" and not comment:
            raise ValueError("Rejection requires a comment")

        with db.session.begin():
            repo.add_comment(cr, author=actor, text=comment,
                              decision="ADMIN_APPROVE" if decision == "APPROVE" else "ADMIN_REJECT")
            if decision == "REJECT":
                repo.clear_review_signoffs(revision)          # both columns, whichever was set
                revision.lifecycle_status = "DRAFT"
            else:
                revision.admin_signoff_by, revision.admin_signoff_at = actor.id, now()
                # confirm/override any restricted field the Engineer proposed (SEC-013)
                repo.confirm_restricted_fields(revision, actor)
                if revision.reviewer_signoff_by is not None:
                    revision.lifecycle_status = "PENDING_APPROVAL"   # atomic 2nd-signoff transition
            AuditService.log(entity_type="StatusCodeRevision", entity_id=revision.id,
                              action="ADMIN_SIGNOFF", actor=actor,
                              before={"lifecycle_status": "REVIEW"},
                              after={"lifecycle_status": revision.lifecycle_status})
        return cr

    @staticmethod
    def chief_engineer_decide(cr_id: int, actor, decision: str, comment: str | None):
        repo = ChangeRequestRepository()
        cr = repo.get(cr_id)
        revision = cr.revision

        blocked = {cr.requested_by, revision.reviewer_signoff_by, revision.admin_signoff_by}
        if actor.id in blocked:
            raise SegregationOfDutiesViolation("BR-005: segregation of duties across all three decision points")
        if revision.lifecycle_status != "PENDING_APPROVAL":
            raise InvalidTransition(f"Cannot decide a revision in state {revision.lifecycle_status}")
        if decision == "REJECT" and not comment:
            raise ValueError("Rejection requires a comment")

        with db.session.begin():
            repo.add_comment(cr, author=actor, text=comment,
                              decision="CHIEF_ENGINEER_APPROVE" if decision == "APPROVE" else "CHIEF_ENGINEER_REJECT")
            if decision == "APPROVE":
                revision.chief_engineer_approved_by, revision.chief_engineer_approval_date = actor.id, now()
                revision.lifecycle_status = "APPROVED"
            else:
                repo.clear_review_signoffs(revision)
                revision.lifecycle_status = "DRAFT"
            cr.chief_engineer_decided_by, cr.chief_engineer_decided_at = actor.id, now()
            AuditService.log(entity_type="StatusCodeRevision", entity_id=revision.id,
                              action="CHIEF_ENGINEER_APPROVE" if decision == "APPROVE" else "CHIEF_ENGINEER_REJECT",
                              actor=actor, before={"lifecycle_status": "PENDING_APPROVAL"},
                              after={"lifecycle_status": revision.lifecycle_status})
        return cr
```

`reviewer_signoff` is the mirror image of `admin_signoff` (no restricted-field confirmation step). `submit` (Draft→Review) additionally calls `NumberingService.allocate_next_identifier(...)` and `DomainSignoffService.assert_all_required_domains_signed(revision)` before performing its transaction.

## 6. Database Migration Strategy

Unchanged in mechanism from v1 §6 (Alembic baseline from `artifacts/schema.sql`, hand-reviewed autogenerate for `CHECK`/triggers/partial indexes, `PRAGMA foreign_keys = ON` on every connection). New note: the real Functional Subgroup data (06-data-dictionary.md §9a) is seeded by the same baseline migration as every other lookup; any future addition (a new subgroup into a currently-reserved hundred-block, or a whole new Functional System Group into one of the confirmed free ranges — `10000–10999`, `14000–14999`, `15000–15999`, `16000–16999`) is a **data migration** (an `INSERT`/re-seed script), never a schema migration — call this out explicitly in that future migration's docstring so nobody mistakes it for a breaking change.

## 7. Testing Framework

Unchanged in mechanism from v1 §7 (`pytest`, `pytest-cov`, role-scoped authenticated-client fixtures — now five: `engineer_client`, `reviewer_client`, `administrator_client`, `chief_engineer_client`, `viewer_client`, plus fixtures for Engineers tagged with specific Engineering Domains for Cross-Domain Sign-Off tests). `schemathesis` (or equivalent) against `artifacts/openapi.yaml` v3.0.0. `bandit -r app/` and `pip-audit`, plus the new no-cloud-import grep check (13-test-strategy.md §6, TC-029) wired into the same CI stage.

## 8. Suggested Coding Order

Updated sequencing reflecting the new epics (17-implementation-backlog.md dependency graph):

1. `app/config.py`, `app/__init__.py`, `wsgi.py`, health endpoint (US-001, US-002 incl. no-cloud CI check).
2. `app/models/` in full (all v2 tables from `artifacts/schema.sql`), then the baseline Alembic migration incl. seed data (US-003, US-004).
3. Auth: password hashing, `SessionPasswordAuthProvider`, `auth_service`, decorators (US-005–US-008).
4. `user_repository`, `user_service`, minimal user list/create UI+API, **including Engineering Domain tagging** (US-009–US-012) — needed early since Cross-Domain Sign-Off tests require tagged users.
5. `audit_service` as shared infrastructure before any consuming service (unchanged rationale from v1 §8 step 5).
6. `numbering_service` (Functional Group/Subgroup allocation, §5, §6) and `validation.py`, then `status_code_repository`/`status_code_service` for Draft creation (EPIC-02).
7. `domain_signoff_service` and its API/UI (EPIC-03) — build this **before** the submit/review workflow, since Submit-for-Review depends on it, not after.
8. `change_request_repository`, `change_request_service` covering `submit`, `reviewer_signoff`, `admin_signoff`, `chief_engineer_decide`, `withdraw` (EPIC-04) — the most transaction-sensitive service in the system; write the atomic-second-signoff and segregation-of-duties integration tests alongside this code, not after.
9. Search/filter/list on `StatusCodeRepository` plus corresponding UI/API, with the new Functional Group/Subgroup/Platform/sandbox filters (EPIC-05).
10. `release_repository`/`release_service` (candidate resolution now excluding sandbox, atomic publish) plus `export/` (catalogue formats, then `full_database_exporter.py`) (EPIC-06).
11. Sandbox create/delete (EPIC-07) — deliberately sequenced after the main workflow is solid, since it reuses the same state machine and its only new surface area is the isolated numbering band, the delete trigger, and the `SANDBOX_DELETE` snapshot-audit path.
12. Deprecation/archival methods, now routed through the full dual-review-plus-approval cycle when initiated by an Engineer CR (EPIC-08).
13. Remaining lookup administration UI/API for the new vocabularies (EPIC-09).
14. Audit search/reporting UI/API, extended to the Chief Engineer role (EPIC-10's consumer-facing half).
15. Fill in remaining OpenAPI-contract gaps, `schemathesis` conformance (EPIC-11).
16. Security headers, CSRF, `bandit`/`pip-audit`, manual OWASP + no-cloud checklist sign-off (EPIC-12).
17. Performance testing (incl. identifier-allocation contention, TC-025), deployment scripts, backup/restore drill, monitoring (EPIC-13), immediately preceding go-live.
18. `import_service.py` and the Library Import UI/API (EPIC-14), reusing the validation logic already built in step 6 — an import row and a manually typed Draft go through the exact same validators.
19. `subgroup_admin_service.py` and its group-level counterpart (EPIC-16) — straightforward once the lookup administration screens from step 13 exist; the group-level "create a new Functional System Group into a free range" capability (FR-048g/h) is the lowest-priority piece of this epic and can slip past MVP if time is tight.
20. OneTool shell integration and the two explicit UX fixes — no-data-loss-on-failure and inline lookup descriptions (EPIC-15) — applied as a pass across every existing form, not a new module; do this once the forms it touches are stable, to avoid rework.
