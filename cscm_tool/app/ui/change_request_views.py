"""S8 My Change Requests, S9 Review Queue, S9a Approval Queue,
S10 Change Request Detail/Decision, S10a Domain Sign-Off (folded into S10)."""

from flask import flash, redirect, render_template, request, url_for

from app.api.v1.serializers import revision_payload
from app.auth.decorators import current_user, login_required_web, require_role_web
from app.domain.errors import DomainError, InvalidTransitionError, SegregationOfDutiesViolation
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.status_code import StatusCodeRevision
from app.services.change_request_service import ChangeRequestService
from app.services.domain_signoff_service import DomainSignoffService, user_domain_codes
from app.ui import ui_bp


@ui_bp.route("/change-requests/mine")
@login_required_web
def my_change_requests():
    crs = (
        db.session.query(ChangeRequest)
        .filter(ChangeRequest.requested_by == current_user.id)
        .order_by(ChangeRequest.id.desc())
        .all()
    )
    return render_template("change_requests/mine.html", crs=crs)


@ui_bp.route("/change-requests/review-queue")
@require_role_web("REVIEWER", "ADMINISTRATOR")
def review_queue():
    crs = (
        db.session.query(ChangeRequest)
        .join(StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id)
        .filter(StatusCodeRevision.lifecycle_status == "REVIEW")
        .order_by(ChangeRequest.id.asc())
        .all()
    )
    return render_template("change_requests/review_queue.html", crs=crs)


@ui_bp.route("/change-requests/approval-queue")
@require_role_web("CHIEF_ENGINEER")
def approval_queue():
    crs = (
        db.session.query(ChangeRequest)
        .join(StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id)
        .filter(StatusCodeRevision.lifecycle_status == "PENDING_APPROVAL")
        .order_by(ChangeRequest.id.asc())
        .all()
    )
    return render_template("change_requests/approval_queue.html", crs=crs)


@ui_bp.route("/change-requests/<int:cr_id>")
@login_required_web
def change_request_detail(cr_id):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        flash("Change request not found.", "error")
        return redirect(url_for("ui.my_change_requests"))

    revision = cr.revision
    requester_domains = user_domain_codes(cr.requester)
    required_domains = DomainSignoffService.required_domains(requester_domains)
    signed_domains = DomainSignoffService.signed_off_domains(cr)
    pending_domains = required_domains - signed_domains
    my_domains = (
        current_user.engineering_domain_codes
        if current_user.role_code == "ENGINEER"
        else frozenset()
    )

    blocked_ce = {cr.requested_by, revision.reviewer_signoff_by, revision.admin_signoff_by}

    return render_template(
        "change_requests/detail.html",
        cr=cr,
        revision=revision_payload(revision),
        required_domains=sorted(required_domains),
        signed_domains=signed_domains,
        pending_domains=sorted(pending_domains),
        can_sign_domain=sorted(my_domains & pending_domains),
        blocked_ce=blocked_ce,
    )


@ui_bp.route("/change-requests/<int:cr_id>/submit", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def cr_submit(cr_id):
    try:
        ChangeRequestService.submit(cr_id, current_user)
    except (SegregationOfDutiesViolation, InvalidTransitionError, DomainError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Submitted for Review; identifier allocated.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/reviewer-signoff", methods=["POST"])
@require_role_web("REVIEWER")
def cr_reviewer_signoff(cr_id):
    decision = request.form.get("decision", "")
    comment = request.form.get("comment") or None
    try:
        ChangeRequestService.reviewer_signoff(cr_id, current_user, decision, comment)
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Reviewer decision recorded.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/admin-signoff", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def cr_admin_signoff(cr_id):
    decision = request.form.get("decision", "")
    comment = request.form.get("comment") or None
    try:
        ChangeRequestService.admin_signoff(cr_id, current_user, decision, comment)
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Administrator decision recorded.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/chief-engineer-decide", methods=["POST"])
@require_role_web("CHIEF_ENGINEER")
def cr_chief_engineer_decide(cr_id):
    decision = request.form.get("decision", "")
    comment = request.form.get("comment") or None
    try:
        ChangeRequestService.chief_engineer_decide(cr_id, current_user, decision, comment)
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Chief Engineer decision recorded.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/withdraw", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def cr_withdraw(cr_id):
    cr = db.session.get(ChangeRequest, cr_id)
    # A withdrawn NEW-type CR deletes its only revision, leaving the
    # status_code orphaned with zero revisions (see ChangeRequestService.withdraw)
    # so status_code_detail would 404 on it; only REVISION/DEPRECATION-type
    # withdrawals leave a valid current revision behind to redirect to.
    status_code_id = cr.revision.status_code_id if cr and cr.cr_type != "NEW" else None
    try:
        ChangeRequestService.withdraw(cr_id, current_user)
    except (SegregationOfDutiesViolation, InvalidTransitionError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.change_request_detail", cr_id=cr_id))

    flash("Change request withdrawn.", "success")
    if status_code_id:
        return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))
    return redirect(url_for("ui.my_change_requests"))


@ui_bp.route("/change-requests/<int:cr_id>/domain-signoffs", methods=["POST"])
@require_role_web("ENGINEER")
def cr_domain_signoff(cr_id):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        flash("Change request not found.", "error")
        return redirect(url_for("ui.my_change_requests"))

    domain_code = request.form.get("engineering_domain", "")
    try:
        DomainSignoffService.sign(cr, domain_code, current_user)
    except (DomainError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash(f"Signed off for {domain_code}.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))
