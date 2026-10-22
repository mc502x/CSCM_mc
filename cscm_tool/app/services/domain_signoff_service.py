"""Cross-Domain Sign-Off. FR-027-FR-029, BR-011. See
docs/06-data-dictionary.md §2a for the field-to-domain ownership mapping."""

from app.domain.errors import DomainError
from app.extensions import db
from app.models.change_request import ChangeRequest, DomainSignoff, DomainSignoffRequest
from app.models.lookup import LookupEngineeringDomain
from app.models.status_code import StatusCodeRevision
from app.models.user import User
from app.services.audit_service import AuditService
from app.utils import utcnow_iso


def user_domain_codes(user: User) -> frozenset[str]:
    """The User-model equivalent of AuthenticatedUser.engineering_domain_codes
    — used when the relevant user isn't the current request's actor (e.g.
    a CR's original requester, looked up by id)."""
    return frozenset(ued.engineering_domain.code for ued in user.engineering_domains)


# Fields with an "Any" owner (title, description, status_category,
# available_group — docs/06-data-dictionary.md §2a) never gate
# Submit-for-Review. The eight audience-access fields (§2d) are
# Administrator-confirmed governance, not Engineer-domain-gated (SEC-013),
# so they are deliberately absent here too. Only the dict *keys* are
# functionally load-bearing (required_domains below); the tuples document
# which fields drive that requirement.
FIELDS_OWNED_BY_DOMAIN: dict[str, tuple[str, ...]] = {
    "CONTROLS": (
        "set_delay",
        "reset_delay",
        "up_down_counter",
        "trigger_snapshot",
        "number_of_times_repeated",
        "repeated_over_the_course",
        "status_code_for_repeated_error",
        "yaw_program",
        "manual_reset_program",
        "auto_reset_program",
        "converter_reactive_power_program",
        "brake_program",
        "umrichterprogramm_gsc",
        "umrichterprogramm_msc",
        "yaw_bearing_lubrication_program",
    ),
}


class DomainSignoffService:
    @staticmethod
    def required_domains(originating_engineer_domain_codes: frozenset[str]) -> set[str]:
        """A revision always carries values for every domain-owned field, so
        every domain not covered by the originating Engineer's own tags is
        required, regardless of which specific fields they touched."""
        return set(FIELDS_OWNED_BY_DOMAIN) - originating_engineer_domain_codes

    @staticmethod
    def signed_off_domains(cr: ChangeRequest) -> set[str]:
        return {ds.engineering_domain.code for ds in cr.domain_signoffs}

    @staticmethod
    def pending_domains(
        cr: ChangeRequest, originating_engineer_domain_codes: frozenset[str]
    ) -> set[str]:
        required = DomainSignoffService.required_domains(originating_engineer_domain_codes)
        return required - DomainSignoffService.signed_off_domains(cr)

    @staticmethod
    def assert_all_required_domains_signed(
        cr: ChangeRequest, originating_engineer_domain_codes: frozenset[str]
    ) -> None:
        pending = DomainSignoffService.pending_domains(cr, originating_engineer_domain_codes)
        if pending:
            raise DomainError(
                f"Cross-Domain Sign-Off still pending for: {', '.join(sorted(pending))}"
            )

    @staticmethod
    def sign(cr: ChangeRequest, engineering_domain_code: str, actor_user) -> DomainSignoff:
        """FR-029: only a user who actually holds the named domain may sign."""
        if engineering_domain_code not in actor_user.engineering_domain_codes:
            raise DomainError(
                f"Actor does not hold the {engineering_domain_code} Engineering Domain."
            )

        domain = (
            db.session.query(LookupEngineeringDomain)
            .filter(LookupEngineeringDomain.code == engineering_domain_code)
            .first()
        )
        if domain is None:
            raise ValueError(f"Unknown engineering domain code: {engineering_domain_code}")

        existing = (
            db.session.query(DomainSignoff)
            .filter(
                DomainSignoff.change_request_id == cr.id,
                DomainSignoff.engineering_domain_id == domain.id,
            )
            .first()
        )
        if existing is not None:
            return existing

        signoff = DomainSignoff(
            change_request_id=cr.id,
            engineering_domain_id=domain.id,
            signed_off_by=actor_user.id,
            signed_off_at=utcnow_iso(),
        )
        db.session.add(signoff)
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "DOMAIN_SIGNOFF",
            actor=actor_user,
            after={"engineering_domain": engineering_domain_code},
        )
        db.session.commit()
        return signoff

    @staticmethod
    def request_signoff(
        cr: ChangeRequest, engineering_domain_code: str, target_user_id: int | None, actor_user
    ) -> DomainSignoffRequest:
        """FR-028: the originating Engineer asks for a pending domain's
        sign-off, optionally from one named Engineer who holds that domain.
        The request then surfaces on the target's Dashboard / My Change
        Requests (or on every domain holder's, if no target is named)."""
        if actor_user.id != cr.requested_by:
            raise DomainError("Only the originating Engineer may request a domain sign-off.")
        if cr.revision.lifecycle_status != "DRAFT":
            raise DomainError("Domain sign-off can only be requested while the CR is in Draft.")

        pending = DomainSignoffService.pending_domains(cr, user_domain_codes(cr.requester))
        if engineering_domain_code not in pending:
            raise ValueError(f"{engineering_domain_code} is not a pending required domain.")

        domain = (
            db.session.query(LookupEngineeringDomain)
            .filter(LookupEngineeringDomain.code == engineering_domain_code)
            .one()
        )
        if target_user_id is not None:
            target = db.session.get(User, target_user_id)
            if (
                target is None
                or not target.is_active
                or target.role.code != "ENGINEER"
                or engineering_domain_code not in user_domain_codes(target)
            ):
                raise ValueError(
                    f"Target must be an active Engineer holding the "
                    f"{engineering_domain_code} domain."
                )

        if target_user_id is None and not DomainSignoffService.domain_holders(
            engineering_domain_code
        ):
            raise ValueError(
                f"No active Engineer holds the {engineering_domain_code} domain yet, so nobody "
                "could act on this request. Ask an Administrator to tag an Engineer with it "
                "(Administration → Users)."
            )

        request_row = (
            db.session.query(DomainSignoffRequest)
            .filter(
                DomainSignoffRequest.change_request_id == cr.id,
                DomainSignoffRequest.engineering_domain_id == domain.id,
            )
            .first()
        )
        if request_row is None:
            request_row = DomainSignoffRequest(
                change_request_id=cr.id,
                engineering_domain_id=domain.id,
                requested_by=actor_user.id,
                created_at=utcnow_iso(),
            )
            db.session.add(request_row)
        request_row.target_user_id = target_user_id
        db.session.flush()
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "DOMAIN_SIGNOFF_REQUEST",
            actor=actor_user,
            after={"engineering_domain": engineering_domain_code, "target_user_id": target_user_id},
        )
        db.session.commit()
        return request_row

    @staticmethod
    def domain_holders(engineering_domain_code: str) -> list[User]:
        """Active Engineers tagged with the domain (the possible sign-off givers)."""
        return [
            u
            for u in db.session.query(User).filter(User.is_active == 1).order_by(User.full_name)
            if u.role.code == "ENGINEER" and engineering_domain_code in user_domain_codes(u)
        ]

    @staticmethod
    def open_requests_for(user_id: int) -> list[DomainSignoffRequest]:
        """Requests awaiting the user: addressed to them, or open to everyone
        holding the domain; still unsigned and the CR still in Draft."""
        user = db.session.get(User, user_id)
        if user is None:
            return []
        domains = user_domain_codes(user)
        if not domains:
            return []
        rows = (
            db.session.query(DomainSignoffRequest)
            .join(ChangeRequest, DomainSignoffRequest.change_request_id == ChangeRequest.id)
            .join(
                StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id
            )
            .filter(StatusCodeRevision.lifecycle_status == "DRAFT", ChangeRequest.state == "DRAFT")
            .order_by(DomainSignoffRequest.id.asc())
            .all()
        )
        open_rows = []
        for row in rows:
            code = row.engineering_domain.code
            if code not in domains:
                continue
            if row.target_user_id not in (None, user.id):
                continue
            if code in DomainSignoffService.signed_off_domains(row.change_request):
                continue
            open_rows.append(row)
        return open_rows
