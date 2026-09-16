"""Cross-Domain Sign-Off. FR-027-FR-029, BR-011. See
docs/06-data-dictionary.md §2a for the field-to-domain ownership mapping."""

from app.domain.errors import DomainError
from app.extensions import db
from app.models.change_request import ChangeRequest, DomainSignoff
from app.models.lookup import LookupEngineeringDomain
from app.models.user import User
from app.services.audit_service import AuditService
from app.utils import utcnow_iso


def user_domain_codes(user: User) -> frozenset[str]:
    """The User-model equivalent of AuthenticatedUser.engineering_domain_codes
    — used when the relevant user isn't the current request's actor (e.g.
    a CR's original requester, looked up by id)."""
    return frozenset(ued.engineering_domain.code for ued in user.engineering_domains)


# Fields with an "Any" owner (docs/06-data-dictionary.md §2a) never gate
# Submit-for-Review. access_rights_id is Administrator-confirmed governance,
# not Engineer-domain-gated (SEC-013), so it is deliberately absent here too.
FIELDS_OWNED_BY_DOMAIN: dict[str, tuple[str, ...]] = {
    "CONTROLS": (
        "brake_program",
        "reset_program",
        "software_version",
        "operational_state",
        "delay_before_alarm_seconds",
        "delay_before_reset_seconds",
        "alarm_behaviour",
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
