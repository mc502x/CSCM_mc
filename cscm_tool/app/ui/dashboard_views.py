"""S2 Dashboard: role-relevant summary + quick links."""

from flask import render_template

from app.auth.decorators import current_user, login_required_web
from app.extensions import db
from app.models.change_request import ChangeRequest, DomainSignoff
from app.models.status_code import StatusCodeRevision
from app.services.domain_signoff_service import DomainSignoffService, user_domain_codes
from app.ui import ui_bp


@ui_bp.route("/")
@login_required_web
def dashboard():
    stats = {}

    if current_user.role_code in ("ENGINEER", "ADMINISTRATOR"):
        stats["my_open_crs"] = (
            db.session.query(ChangeRequest)
            .filter(
                ChangeRequest.requested_by == current_user.id,
                ChangeRequest.state.in_(("DRAFT", "REVIEW", "PENDING_APPROVAL")),
            )
            .count()
        )

    if current_user.role_code == "ENGINEER":
        pending_domain_requests = 0
        open_crs = (
            db.session.query(ChangeRequest)
            .join(
                StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id
            )
            .filter(
                ChangeRequest.state == "DRAFT",
                StatusCodeRevision.lifecycle_status == "DRAFT",
            )
            .all()
        )
        for cr in open_crs:
            requester_domains = user_domain_codes(cr.requester)
            if DomainSignoffService.pending_domains(cr, requester_domains):
                pending_domain_requests += 1
        stats["pending_domain_requests"] = pending_domain_requests

        signed_by_me = (
            db.session.query(DomainSignoff)
            .filter(DomainSignoff.signed_off_by == current_user.id)
            .count()
        )
        stats["domain_signoffs_given"] = signed_by_me

    if current_user.role_code in ("REVIEWER", "ADMINISTRATOR"):
        stats["awaiting_reviewer_signoff"] = (
            db.session.query(ChangeRequest)
            .join(
                StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id
            )
            .filter(
                StatusCodeRevision.lifecycle_status == "REVIEW",
                StatusCodeRevision.reviewer_signoff_by.is_(None),
                ChangeRequest.requested_by != current_user.id,
            )
            .count()
        )
        stats["awaiting_admin_signoff"] = (
            db.session.query(ChangeRequest)
            .join(
                StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id
            )
            .filter(
                StatusCodeRevision.lifecycle_status == "REVIEW",
                StatusCodeRevision.admin_signoff_by.is_(None),
                ChangeRequest.requested_by != current_user.id,
            )
            .count()
        )

    if current_user.role_code == "CHIEF_ENGINEER":
        stats["awaiting_approval"] = (
            db.session.query(StatusCodeRevision)
            .filter(StatusCodeRevision.lifecycle_status == "PENDING_APPROVAL")
            .count()
        )

    return render_template("dashboard.html", stats=stats)
