"""Status Code creation and lifecycle. FR-020-FR-029, FR-053-FR-056, BR-001-BR-003.

Every non-sandbox creation also creates a wrapping ChangeRequest (FR-030);
sandbox creation deliberately does not (docs/08-system-architecture.md §5.4
sequence diagram shows no ChangeRequest in the sandbox create/delete path —
sandbox codes bypass the governance workflow entirely by design)."""

from datetime import UTC, datetime, timedelta

from app.domain.authz import require_roles
from app.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
)
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.change_request import ChangeRequest
from app.models.lookup import (
    LookupCustomerAccess,
    LookupDevelopmentAccess,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupGridOperatorAccess,
    LookupSalesAccess,
    LookupServiceAccess,
    LookupServicePartnerAccess,
    LookupTccAccess,
    LookupTopAccess,
    LookupTurbinePlatform,
)
from app.models.status_code import StatusCode, StatusCodeRevision, StatusCodeRevisionPlatform
from app.repositories.status_code_repository import StatusCodeRepository
from app.services.audit_service import AuditService
from app.services.lookup_service import LookupService
from app.services.numbering_service import NumberingService
from app.services.validation import validate_deprecation_reason, validate_revision_fields
from app.utils import parse_iso, utcnow_iso

VIEWER_VISIBLE_STATES = ("APPROVED", "RELEASED", "DEPRECATED", "ARCHIVED")
MINIMUM_DEPRECATED_RETENTION_DAYS = 180  # BR-006, docs/05-governance-handbook.md §11


class ValidationFailed(DomainError):
    def __init__(self, field_errors: list[dict]):
        super().__init__("Validation failed")
        self.field_errors = field_errors


class StatusCodeService:
    _repo = StatusCodeRepository()

    @staticmethod
    def create_draft(
        data: dict, actor_user, *, import_job_id: int | None = None
    ) -> StatusCodeRevision:
        """FR-020: Engineer or Administrator creates a new Status Code as a
        Draft revision. No identifier is assigned (FR-021); a wrapping
        ChangeRequest is created alongside it (FR-030) — cr_type=IMPORT
        when called from ImportService (FR-048a-c), cr_type=NEW otherwise.
        Either way the CR goes through the identical submit/dual-review/
        Chief-Engineer-approval cycle (05-governance-handbook.md §6b)."""
        require_roles(actor_user, "ADMINISTRATOR", "ENGINEER")
        revision = StatusCodeService._build_revision(
            data, actor_user, is_sandbox=False, status_code_id=None, revision_number=1
        )
        status_code = revision.status_code

        cr = ChangeRequest(
            status_code_revision_id=revision.id,
            cr_type="IMPORT" if import_job_id else "NEW",
            requested_by=actor_user.id,
            justification=data.get("justification"),
            import_job_id=import_job_id,
            state="DRAFT",
        )
        db.session.add(cr)

        AuditService.log(
            "StatusCode",
            status_code.id,
            "CREATE",
            actor=actor_user,
            after=_revision_snapshot(revision),
        )
        db.session.commit()
        return revision

    @staticmethod
    def create_revision(status_code_id: int, data: dict, actor_user) -> StatusCodeRevision:
        """Opens a new Draft revision (copy-on-write) against an existing
        code (FR-025). BR-003: rejected if an open revision already exists."""
        require_roles(actor_user, "ADMINISTRATOR", "ENGINEER")
        status_code = StatusCodeService._repo.get_or_404(status_code_id)
        if StatusCodeService._repo.get_open_revision(status_code_id) is not None:
            raise InvalidTransitionError(
                "An open Draft/Review/PendingApproval revision already exists (BR-003)."
            )

        next_number = max((r.revision_number for r in status_code.revisions), default=0) + 1
        revision = StatusCodeService._build_revision(
            data,
            actor_user,
            is_sandbox=bool(status_code.is_sandbox),
            status_code_id=status_code_id,
            revision_number=next_number,
        )

        cr = ChangeRequest(
            status_code_revision_id=revision.id,
            cr_type="REVISION",
            requested_by=actor_user.id,
            justification=data.get("justification"),
            state="DRAFT",
        )
        db.session.add(cr)

        AuditService.log(
            "StatusCode",
            status_code.id,
            "CREATE",
            actor=actor_user,
            after=_revision_snapshot(revision),
        )
        db.session.commit()
        return revision

    @staticmethod
    def create_deprecation_request(
        status_code_id: int,
        reason: str,
        superseded_by_status_code_id: int | None,
        actor_user,
    ) -> StatusCodeRevision:
        """FR-050/BR-005 (Released -> Deprecated via full cycle,
        docs/05-governance-handbook.md §5): copy-on-write a new Draft
        revision carrying the deprecation reason, wrapped in a
        cr_type=DEPRECATION ChangeRequest. Goes through the same
        submit/dual-review/Chief-Engineer-approval machinery as any other
        CR; ChangeRequestService.chief_engineer_decide routes a DEPRECATION
        CR's approval to DEPRECATED instead of APPROVED."""
        require_roles(actor_user, "ADMINISTRATOR", "ENGINEER")
        status_code = StatusCodeService._repo.get_or_404(status_code_id)
        current = StatusCodeService._repo.get_current_revision(status_code_id)
        if current is None or current.lifecycle_status != "RELEASED":
            raise InvalidTransitionError("Only a Released Status Code can be deprecated.")
        if StatusCodeService._repo.get_open_revision(status_code_id) is not None:
            raise InvalidTransitionError(
                "An open Draft/Review/PendingApproval revision already exists (BR-003)."
            )

        field_errors = validate_deprecation_reason(reason)
        if field_errors:
            raise ValidationFailed(field_errors)
        if superseded_by_status_code_id is not None:
            if superseded_by_status_code_id == status_code_id:
                raise ValidationFailed(
                    [
                        {
                            "field": "superseded_by_status_code_id",
                            "message": "A code cannot supersede itself.",
                        }
                    ]
                )
            if db.session.get(StatusCode, superseded_by_status_code_id) is None:
                raise ValidationFailed(
                    [
                        {
                            "field": "superseded_by_status_code_id",
                            "message": "Referenced Status Code does not exist.",
                        }
                    ]
                )

        current.is_current = 0
        db.session.flush()  # see the matching comment in _build_revision

        now = utcnow_iso()
        next_number = max(r.revision_number for r in status_code.revisions) + 1
        revision = StatusCodeRevision(
            status_code_id=status_code.id,
            revision_number=next_number,
            is_current=1,
            title=current.title,
            description=current.description,
            software_version=current.software_version,
            status_category=current.status_category,
            available_group=current.available_group,
            alarm_flag=current.alarm_flag,
            set_delay=current.set_delay,
            reset_delay=current.reset_delay,
            up_down_counter=current.up_down_counter,
            trigger_snapshot=current.trigger_snapshot,
            loadless_spinning_permitted=current.loadless_spinning_permitted,
            number_of_times_repeated=current.number_of_times_repeated,
            repeated_over_the_course=current.repeated_over_the_course,
            status_code_for_repeated_error=current.status_code_for_repeated_error,
            yaw_program=current.yaw_program,
            manual_reset_program=current.manual_reset_program,
            auto_reset_program=current.auto_reset_program,
            converter_reactive_power_program=current.converter_reactive_power_program,
            brake_program=current.brake_program,
            umrichterprogramm_gsc=current.umrichterprogramm_gsc,
            umrichterprogramm_msc=current.umrichterprogramm_msc,
            yaw_bearing_lubrication_program=current.yaw_bearing_lubrication_program,
            development_access_id=current.development_access_id,
            sales_access_id=current.sales_access_id,
            tcc_access_id=current.tcc_access_id,
            service_access_id=current.service_access_id,
            turbine_operator_package_access_id=current.turbine_operator_package_access_id,
            grid_operator_access_id=current.grid_operator_access_id,
            service_partner_access_id=current.service_partner_access_id,
            customer_access_id=current.customer_access_id,
            owner_id=current.owner_id,
            lifecycle_status="DRAFT",
            created_by=actor_user.id,
            created_at=now,
            deprecated_reason=reason,
            superseded_by_status_code_id=superseded_by_status_code_id,
        )
        db.session.add(revision)
        db.session.flush()
        for platform in current.platforms:
            db.session.add(
                StatusCodeRevisionPlatform(
                    status_code_revision_id=revision.id,
                    turbine_platform_id=platform.turbine_platform_id,
                )
            )

        cr = ChangeRequest(
            status_code_revision_id=revision.id,
            cr_type="DEPRECATION",
            requested_by=actor_user.id,
            justification=reason,
            state="DRAFT",
        )
        db.session.add(cr)

        AuditService.log(
            "StatusCode",
            status_code.id,
            "CREATE",
            actor=actor_user,
            after={"cr_type": "DEPRECATION", "deprecated_reason": reason},
        )
        db.session.commit()
        return revision

    @staticmethod
    def archive(status_code_id: int, actor_user) -> StatusCodeRevision:
        """FR-051/BR-006: Administrator-only, direct action (no CR — not a
        content decision, so it doesn't go through dual review), only once
        the minimum retention period has elapsed since deprecation. There is
        no deprecated_at column (docs/artifacts/schema.sql), so the
        DEPRECATE audit_log_entry is the authoritative timestamp source —
        consistent with the audit trail being the compliance record of
        truth (docs/12-audit-compliance.md §1)."""
        require_roles(actor_user, "ADMINISTRATOR")
        current = StatusCodeService._repo.get_current_revision(status_code_id)
        if current is None or current.lifecycle_status != "DEPRECATED":
            raise InvalidTransitionError("Only a Deprecated Status Code can be archived.")

        deprecated_at = (
            db.session.query(AuditLogEntry)
            .filter(
                AuditLogEntry.entity_type == "StatusCodeRevision",
                AuditLogEntry.entity_id == current.id,
                AuditLogEntry.action == "DEPRECATE",
            )
            .order_by(AuditLogEntry.occurred_at.desc())
            .first()
        )
        if deprecated_at is None:
            raise DomainError("No DEPRECATE audit entry found; cannot verify retention period.")

        elapsed = datetime.now(UTC) - parse_iso(deprecated_at.occurred_at)
        if elapsed < timedelta(days=MINIMUM_DEPRECATED_RETENTION_DAYS):
            raise DomainError(
                f"Minimum {MINIMUM_DEPRECATED_RETENTION_DAYS}-day retention period as "
                f"Deprecated has not elapsed ({elapsed.days} days so far)."
            )

        current.lifecycle_status = "ARCHIVED"
        AuditService.log(
            "StatusCodeRevision",
            current.id,
            "ARCHIVE",
            actor=actor_user,
            after={"retention_days_elapsed": elapsed.days},
        )
        db.session.commit()
        return current

    @staticmethod
    def reinstate(status_code_id: int, reason: str, actor_user) -> StatusCodeRevision:
        """Deprecated -> Released, exceptional (docs/05-governance-handbook.md
        §5): Administrator-only, direct action, mandatory reason."""
        require_roles(actor_user, "ADMINISTRATOR")
        current = StatusCodeService._repo.get_current_revision(status_code_id)
        if current is None or current.lifecycle_status != "DEPRECATED":
            raise InvalidTransitionError("Only a Deprecated Status Code can be reinstated.")

        field_errors = validate_deprecation_reason(reason)
        if field_errors:
            raise ValidationFailed(field_errors)

        current.lifecycle_status = "RELEASED"
        AuditService.log(
            "StatusCodeRevision",
            current.id,
            "REINSTATE",
            actor=actor_user,
            after={"reason": reason},
        )
        db.session.commit()
        return current

    @staticmethod
    def create_sandbox(data: dict, actor_user) -> StatusCodeRevision:
        """FR-053: Administrator-only. Identifier is allocated immediately
        (not deferred to Submit-for-Review) from the isolated StCd-T#####
        band; no ChangeRequest is created."""
        revision = StatusCodeService._build_revision(
            data, actor_user, is_sandbox=True, status_code_id=None, revision_number=1
        )
        status_code = revision.status_code
        status_code.status_code_identifier = NumberingService.allocate_next_sandbox_identifier()

        AuditService.log(
            "StatusCode",
            status_code.id,
            "SANDBOX_CREATE",
            actor=actor_user,
            after={
                **_revision_snapshot(revision),
                "status_code_identifier": status_code.status_code_identifier,
            },
        )
        db.session.commit()
        return revision

    @staticmethod
    def update_draft(revision_id: int, data: dict, actor_user) -> StatusCodeRevision:
        """FR-024/FR-025: unlimited saves while Draft; rejected outside
        Draft (the DB trigger trg_prevent_edit_locked_revision is
        defense-in-depth for the locked states; DRAFT itself needs an
        explicit application-level check since the trigger doesn't cover
        it). Accepts the same field set as creation.

        Note: docs/artifacts/openapi.yaml's StatusCodeRevisionUpdate schema
        lists only `expected_updated_at` for optimistic concurrency, but
        status_code_revision has no updated_at/version column in
        docs/artifacts/schema.sql to back that check — so it is accepted
        (for forward API compatibility) but not currently enforced. Adding
        real optimistic concurrency needs its own schema migration."""
        require_roles(actor_user, "ADMINISTRATOR", "ENGINEER")
        revision = db.session.get(StatusCodeRevision, revision_id)
        if revision is None:
            raise NotFoundError(f"Revision {revision_id} not found")
        if revision.lifecycle_status != "DRAFT":
            raise InvalidTransitionError("Only a Draft revision may be edited in place (FR-025).")
        if revision.created_by != actor_user.id and actor_user.role_code != "ADMINISTRATOR":
            raise SegregationOfDutiesViolation(
                "Only the owning Engineer or an Administrator may edit this Draft."
            )

        field_errors = validate_revision_fields(data)
        if field_errors:
            raise ValidationFailed(field_errors)

        before = _revision_snapshot(revision)
        _apply_revision_fields(revision, data)
        if data.get("turbine_platforms") is not None:
            _set_platforms(revision, data["turbine_platforms"])

        AuditService.log(
            "StatusCodeRevision",
            revision.id,
            "EDIT",
            actor=actor_user,
            before=before,
            after=_revision_snapshot(revision),
        )
        db.session.commit()
        return revision

    @staticmethod
    def get_current_revision(status_code_id: int, actor_user) -> StatusCodeRevision:
        if actor_user.role_code == "VIEWER":
            revision = StatusCodeService._repo.get_latest_revision_in_states(
                status_code_id, VIEWER_VISIBLE_STATES
            )
        else:
            revision = StatusCodeService._repo.get_current_revision(status_code_id)
        if revision is None or not StatusCodeService._is_visible(revision, actor_user):
            raise NotFoundError(f"Status Code {status_code_id} not found")
        return revision

    @staticmethod
    def list_revision_history(status_code_id: int, actor_user) -> list[StatusCodeRevision]:
        status_code = StatusCodeService._repo.get_or_404(status_code_id)
        return [r for r in status_code.revisions if StatusCodeService._is_visible(r, actor_user)]

    @staticmethod
    def search(actor_user, **filters) -> tuple[list[StatusCodeRevision], int]:
        visible_states = VIEWER_VISIBLE_STATES if actor_user.role_code == "VIEWER" else None
        return StatusCodeService._repo.search_current_revisions(
            visible_lifecycle_statuses=visible_states, **filters
        )

    @staticmethod
    def preview_next_identifier(
        functional_system_group_id: int, functional_subgroup_id: int
    ) -> str:
        """FR-021/US-023. v3: Functional Subgroup is mandatory (never
        optional), so both ids are required here, matching
        docs/artifacts/openapi.yaml's now-required `functional_subgroup`
        query parameter on GET /status-codes/next-available."""
        group = LookupService.get_by_id(LookupFunctionalSystemGroup, functional_system_group_id)
        subgroup = LookupService.get_by_id(LookupFunctionalSubgroup, functional_subgroup_id)
        if subgroup.functional_system_group_id != group.id:
            raise ValueError("Subgroup does not belong to the selected Functional System Group.")
        return NumberingService.preview_next_identifier(group.id, subgroup.id)

    @staticmethod
    def delete_sandbox(status_code_id: int, actor_user) -> None:
        """FR-055/FR-056: permanently delete a sandbox code, writing a
        SANDBOX_DELETE audit entry with a full pre-delete snapshot in the
        same transaction. trg_prevent_nonsandbox_delete is defense-in-depth
        if this service-layer check is ever bypassed."""
        require_roles(actor_user, "ADMINISTRATOR")
        status_code = StatusCodeService._repo.get_or_404(status_code_id)
        if not status_code.is_sandbox:
            raise DomainError("Only sandbox status codes may be deleted (FR-055).")

        snapshot = {
            "status_code_identifier": status_code.status_code_identifier,
            "functional_system_group": status_code.functional_system_group.code,
            "revisions": [_revision_snapshot(r) for r in status_code.revisions],
        }
        AuditService.log(
            "StatusCode", status_code.id, "SANDBOX_DELETE", actor=actor_user, before=snapshot
        )
        for revision in list(status_code.revisions):
            db.session.query(StatusCodeRevisionPlatform).filter(
                StatusCodeRevisionPlatform.status_code_revision_id == revision.id
            ).delete()
            db.session.delete(revision)
        db.session.delete(status_code)
        db.session.commit()

    @staticmethod
    def _is_visible(revision: StatusCodeRevision, actor_user) -> bool:
        """BR-009: Draft/Review/PendingApproval data is hidden from Viewers."""
        if actor_user.role_code == "VIEWER":
            return revision.lifecycle_status in VIEWER_VISIBLE_STATES
        return True

    @staticmethod
    def _build_revision(
        data: dict,
        actor_user,
        *,
        is_sandbox: bool,
        status_code_id: int | None,
        revision_number: int,
    ) -> StatusCodeRevision:
        if is_sandbox and actor_user.role_code != "ADMINISTRATOR":
            raise SegregationOfDutiesViolation("Only an Administrator may create a sandbox code.")

        field_errors = validate_revision_fields(data)
        if field_errors:
            raise ValidationFailed(field_errors)

        try:
            group = LookupService.get_by_id(
                LookupFunctionalSystemGroup, data.get("functional_system_group")
            )
        except ValueError as exc:
            raise ValidationFailed(
                [{"field": "functional_system_group", "message": str(exc)}]
            ) from exc

        # BR-013: mandatory, never optional (corrected 2026-09-17) — every
        # one of the 897 rows in the real export carries a subgroup.
        try:
            subgroup = LookupService.get_by_id(
                LookupFunctionalSubgroup, data.get("functional_subgroup")
            )
        except ValueError as exc:
            raise ValidationFailed([{"field": "functional_subgroup", "message": str(exc)}]) from exc
        if subgroup.functional_system_group_id != group.id:
            raise ValidationFailed(
                [
                    {
                        "field": "functional_subgroup",
                        "message": "Subgroup does not belong to the selected Functional Group.",
                    }
                ]
            )

        now = utcnow_iso()
        if status_code_id is None:
            status_code = StatusCode(
                functional_system_group_id=group.id,
                functional_subgroup_id=subgroup.id,
                legacy_reference_number=data.get("legacy_reference_number"),
                is_sandbox=1 if is_sandbox else 0,
                owner_id=actor_user.id,
                created_at=now,
            )
            db.session.add(status_code)
            db.session.flush()
        else:
            existing = db.session.get(StatusCode, status_code_id)
            if existing is None:
                raise NotFoundError(f"Status Code {status_code_id} not found")
            status_code = existing
            # BR-002: at most one is_current=1 revision per code — flip the
            # old one off in the same transaction as the new one is created,
            # or ux_revision_current_per_code rejects the insert.
            old_current = StatusCodeService._repo.get_current_revision(status_code_id)
            if old_current is not None:
                old_current.is_current = 0
                # Flush this UPDATE before the new row is INSERTed below:
                # ux_revision_current_per_code is a partial unique index
                # checked per-statement, and SQLAlchemy's unit-of-work does
                # not otherwise guarantee this UPDATE runs before that INSERT.
                db.session.flush()

        revision = StatusCodeRevision(
            status_code_id=status_code.id,
            revision_number=revision_number,
            is_current=1,
            owner_id=actor_user.id,
            lifecycle_status="DRAFT",
            created_by=actor_user.id,
            created_at=now,
        )
        _apply_revision_fields(revision, data)
        db.session.add(revision)
        db.session.flush()
        _set_platforms(revision, data.get("turbine_platforms") or [])
        return revision


def _apply_revision_fields(revision: StatusCodeRevision, data: dict) -> None:
    revision.title = data["title"]
    revision.description = data["description"]
    revision.software_version = data.get("software_version") or None
    revision.status_category = data["status_category"]
    revision.available_group = data["available_group"]
    revision.alarm_flag = 1 if data.get("alarm_flag") else 0
    revision.set_delay = data["set_delay"]
    revision.reset_delay = data["reset_delay"]
    revision.up_down_counter = 1 if data.get("up_down_counter") else 0
    revision.trigger_snapshot = 1 if data.get("trigger_snapshot") else 0
    revision.loadless_spinning_permitted = 1 if data.get("loadless_spinning_permitted") else 0

    revision.number_of_times_repeated = data.get("number_of_times_repeated")
    revision.repeated_over_the_course = data.get("repeated_over_the_course") or None
    revision.status_code_for_repeated_error = data.get("status_code_for_repeated_error")

    revision.yaw_program = data.get("yaw_program", 0)
    revision.manual_reset_program = data.get("manual_reset_program", 0)
    revision.auto_reset_program = data.get("auto_reset_program", 0)
    revision.converter_reactive_power_program = data.get("converter_reactive_power_program", 0)
    revision.brake_program = data.get("brake_program", 0)
    revision.umrichterprogramm_gsc = data.get("umrichterprogramm_gsc", 0)
    revision.umrichterprogramm_msc = data.get("umrichterprogramm_msc", 0)
    revision.yaw_bearing_lubrication_program = data.get("yaw_bearing_lubrication_program", 0)

    # FR-025a/SEC-013/BR-012: eight restricted fields, Engineer-proposed here,
    # only authoritative once the Administrator's Review sign-off confirms
    # them (see change_request_service._dual_signoff — admin_signoff_at
    # becoming non-null IS the confirmation, no field-specific code needed
    # there). All eight are optional (nullable FKs).
    revision.development_access_id = _resolve_access(
        LookupDevelopmentAccess, data.get("development_access")
    )
    revision.sales_access_id = _resolve_access(LookupSalesAccess, data.get("sales_access"))
    revision.tcc_access_id = _resolve_access(LookupTccAccess, data.get("tcc_access"))
    revision.service_access_id = _resolve_access(LookupServiceAccess, data.get("service_access"))
    revision.turbine_operator_package_access_id = _resolve_access(
        LookupTopAccess, data.get("turbine_operator_package_access")
    )
    revision.grid_operator_access_id = _resolve_access(
        LookupGridOperatorAccess, data.get("grid_operator_access")
    )
    revision.service_partner_access_id = _resolve_access(
        LookupServicePartnerAccess, data.get("service_partner_access")
    )
    revision.customer_access_id = _resolve_access(LookupCustomerAccess, data.get("customer_access"))


ACCESS_FIELDS = (
    "development_access",
    "sales_access",
    "tcc_access",
    "service_access",
    "turbine_operator_package_access",
    "grid_operator_access",
    "service_partner_access",
    "customer_access",
)

_ACCESS_MODELS = {
    "development_access": LookupDevelopmentAccess,
    "sales_access": LookupSalesAccess,
    "tcc_access": LookupTccAccess,
    "service_access": LookupServiceAccess,
    "turbine_operator_package_access": LookupTopAccess,
    "grid_operator_access": LookupGridOperatorAccess,
    "service_partner_access": LookupServicePartnerAccess,
    "customer_access": LookupCustomerAccess,
}


def apply_access_overrides(revision: StatusCodeRevision, overrides: dict) -> tuple[dict, dict]:
    """FR-034 / SEC-013: the Administrator's Review sign-off may confirm or
    override the eight restricted audience-access fields. `overrides` maps a
    field name to a lookup id (or ""/None to clear it); fields not named are
    left as the Engineer proposed. Returns (before, after) for only the
    fields that actually changed, for the audit trail."""
    unknown = set(overrides) - set(ACCESS_FIELDS)
    if unknown:
        raise ValueError(f"Unknown audience-access field(s): {', '.join(sorted(unknown))}")
    before: dict = {}
    after: dict = {}
    for name, raw in overrides.items():
        new_id = _resolve_access(_ACCESS_MODELS[name], raw)
        attr = f"{name}_id"
        old_id = getattr(revision, attr)
        if new_id != old_id:
            before[name] = old_id
            after[name] = new_id
            setattr(revision, attr, new_id)
    return before, after


def _resolve_access(model, value_id) -> int | None:
    if value_id is None or value_id == "":
        return None
    return LookupService.get_by_id(model, value_id).id


def _set_platforms(revision: StatusCodeRevision, platform_codes: list[str]) -> None:
    db.session.query(StatusCodeRevisionPlatform).filter(
        StatusCodeRevisionPlatform.status_code_revision_id == revision.id
    ).delete()
    for code in platform_codes:
        platform = LookupService.get_by_code(LookupTurbinePlatform, code)
        db.session.add(
            StatusCodeRevisionPlatform(
                status_code_revision_id=revision.id, turbine_platform_id=platform.id
            )
        )


def _revision_snapshot(revision: StatusCodeRevision) -> dict:
    return {
        "title": revision.title,
        "description": revision.description,
        "status_category": revision.status_category,
        "lifecycle_status": revision.lifecycle_status,
        "turbine_platforms": sorted(p.turbine_platform.code for p in revision.platforms),
    }
