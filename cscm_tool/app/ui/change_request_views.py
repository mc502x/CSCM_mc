"""S8 My Change Requests, S9 Review Queue, S9a Approval Queue,
S10 Change Request Detail/Decision, S10a Domain Sign-Off (folded into S10)."""

from flask import flash, redirect, render_template, request, url_for

from app.api.v1.serializers import revision_payload
from app.auth.decorators import current_user, require_role_or_delegate_web, require_role_web
from app.domain.errors import (
    AccountLockedError,
    DomainError,
    ForbiddenError,
    InvalidTransitionError,
    SegregationOfDutiesViolation,
    StepUpRequiredError,
)
from app.extensions import db
from app.models.change_request import ChangeRequest, DomainSignoffRequest
from app.models.lookup import Role
from app.models.status_code import StatusCodeRevision
from app.models.user import User
from app.services.change_request_service import ChangeRequestService
from app.services.domain_signoff_service import DomainSignoffService, user_domain_codes
from app.services.lookup_service import LookupService
from app.services.revision_diff_service import RevisionDiffService
from app.ui import ui_bp

ACCESS_LABELS = (
    ("development_access", "Development"),
    ("sales_access", "Sales"),
    ("tcc_access", "TCC"),
    ("service_access", "Service"),
    ("turbine_operator_package_access", "Turbine Operator Package"),
    ("grid_operator_access", "Grid Operator"),
    ("service_partner_access", "Service Partner"),
    ("customer_access", "Customer"),
)


def _access_choices():
    """Per-field (label, [lookup values]) for the Administrator's FR-034 override."""
    from app.ui.status_code_views import _ACCESS_VOCAB_FIELDS

    return [
        (field, label, LookupService.list_vocabulary(_ACCESS_VOCAB_FIELDS[field]))
        for field, label in ACCESS_LABELS
    ]


def _active_reviewers():
    return (
        db.session.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.code == "REVIEWER", User.is_active == 1)
        .order_by(User.full_name)
        .all()
    )


def cr_domain_requests(cr):
    return (
        db.session.query(DomainSignoffRequest)
        .filter(DomainSignoffRequest.change_request_id == cr.id)
        .all()
    )


def _domain_holders(pending_domains):
    """domain code -> active Engineers holding it (targets for FR-028 requests)."""
    return {code: DomainSignoffService.domain_holders(code) for code in pending_domains}


def _sla_map(crs) -> dict:
    """cr id -> SLA info (I-08), thresholds read once for the whole queue."""
    from app.services.sla_service import SlaService

    thresholds = SlaService.thresholds()
    return {cr.id: SlaService.info(cr, thresholds=thresholds) for cr in crs}


@ui_bp.route("/change-requests/mine")
@require_role_web("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
def my_change_requests():
    query = db.session.query(ChangeRequest).filter(ChangeRequest.requested_by == current_user.id)
    import_job_id = request.args.get("import_job_id", type=int)
    if import_job_id:
        query = query.filter(ChangeRequest.import_job_id == import_job_id)
    crs = query.order_by(ChangeRequest.id.desc()).all()
    sign_requests = []
    if current_user.role_code == "ENGINEER":
        sign_requests = DomainSignoffService.open_requests_for(current_user.id)
    return render_template(
        "change_requests/mine.html",
        crs=crs,
        slas=_sla_map(crs),
        import_job_id=import_job_id,
        sign_requests=sign_requests,
    )


_DECISION_ERRORS = (
    SegregationOfDutiesViolation,
    InvalidTransitionError,
    ValueError,
    StepUpRequiredError,
    AccountLockedError,
    ForbiddenError,
)


@ui_bp.route("/change-requests/review-queue")
@require_role_or_delegate_web("REVIEWER", "ADMINISTRATOR")
def review_queue():
    crs = (
        db.session.query(ChangeRequest)
        .join(StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id)
        .filter(StatusCodeRevision.lifecycle_status == "REVIEW")
        .order_by(ChangeRequest.id.asc())
        .all()
    )
    return render_template("change_requests/review_queue.html", crs=crs, slas=_sla_map(crs))


@ui_bp.route("/change-requests/approval-queue")
@require_role_or_delegate_web("CHIEF_ENGINEER")
def approval_queue():
    crs = (
        db.session.query(ChangeRequest)
        .join(StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id)
        .filter(StatusCodeRevision.lifecycle_status == "PENDING_APPROVAL")
        .order_by(ChangeRequest.id.asc())
        .all()
    )
    return render_template("change_requests/approval_queue.html", crs=crs, slas=_sla_map(crs))


@ui_bp.route("/change-requests/<int:cr_id>")
@require_role_web("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
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

    can_comment = any(
        current_user.can_act_as(r) for r in ("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")
    )
    from app.help_content import NEXT_STEP
    from app.services.attachment_service import AttachmentService
    from app.services.change_set_service import ChangeSetService
    from app.services.field_review_service import COMMENTABLE_FIELDS, FieldReviewService
    from app.services.sla_service import SlaService
    from app.services.status_code_service import StatusCodeService

    return render_template(
        "change_requests/detail.html",
        cr=cr,
        sla=SlaService.info(cr),
        next_step=NEXT_STEP.get(revision.lifecycle_status),
        warnings=StatusCodeService.warnings_for(revision),
        field_comments=FieldReviewService.list_field_comments(cr.id),
        commentable_fields=COMMENTABLE_FIELDS,
        can_comment=can_comment,
        attachments=AttachmentService.list_for(cr.id, current_user),
        checklist=FieldReviewService.items_for(cr),
        confirmations=FieldReviewService.confirmations(cr.id),
        change_sets=[s for s in ChangeSetService.list_all() if s.status == "OPEN"],
        revision=revision_payload(revision),
        required_domains=sorted(required_domains),
        signed_domains=signed_domains,
        pending_domains=sorted(pending_domains),
        can_sign_domain=sorted(my_domains & pending_domains),
        blocked_ce=blocked_ce,
        diff=RevisionDiffService.diff_against_baseline(revision),
        access_choices=_access_choices(),
        reviewers=_active_reviewers(),
        domain_requests=cr_domain_requests(cr),
        domain_holders=_domain_holders(pending_domains),
    )


@ui_bp.route("/change-requests/<int:cr_id>/submit", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def cr_submit(cr_id):
    try:
        ChangeRequestService.submit(
            cr_id,
            current_user,
            identifier_override=(request.form.get("identifier_override") or "").strip() or None,
            override_reason=request.form.get("override_reason"),
        )
    except (SegregationOfDutiesViolation, InvalidTransitionError, DomainError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Submitted for Review; identifier allocated.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/reviewer-signoff", methods=["POST"])
@require_role_or_delegate_web("REVIEWER")
def cr_reviewer_signoff(cr_id):
    decision = request.form.get("decision", "")
    comment = request.form.get("comment") or None
    try:
        ChangeRequestService.reviewer_signoff(
            cr_id,
            current_user,
            decision,
            comment,
            reauth_password=request.form.get("current_password"),
            checklist_confirmed=request.form.getlist("checklist_confirmed", type=int),
        )
    except _DECISION_ERRORS as exc:
        flash(str(exc), "error")
    else:
        flash("Reviewer decision recorded.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/admin-signoff", methods=["POST"])
@require_role_or_delegate_web("ADMINISTRATOR")
def cr_admin_signoff(cr_id):
    decision = request.form.get("decision", "")
    comment = request.form.get("comment") or None
    # FR-034: every access field is submitted with its current/overridden value.
    overrides = {
        field: request.form.get(field, "") for field, _ in ACCESS_LABELS if field in request.form
    }
    try:
        ChangeRequestService.admin_signoff(
            cr_id,
            current_user,
            decision,
            comment,
            access_overrides=overrides or None,
            reauth_password=request.form.get("current_password"),
        )
    except _DECISION_ERRORS as exc:
        flash(str(exc), "error")
    else:
        flash("Administrator decision recorded.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/chief-engineer-decide", methods=["POST"])
@require_role_or_delegate_web("CHIEF_ENGINEER")
def cr_chief_engineer_decide(cr_id):
    decision = request.form.get("decision", "")
    comment = request.form.get("comment") or None
    try:
        ChangeRequestService.chief_engineer_decide(
            cr_id,
            current_user,
            decision,
            comment,
            reauth_password=request.form.get("current_password"),
        )
    except _DECISION_ERRORS as exc:
        flash(str(exc), "error")
    else:
        flash("Chief Engineer decision recorded.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/comments", methods=["POST"])
@require_role_web("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")
def cr_add_comment(cr_id):
    try:
        ChangeRequestService.add_comment(cr_id, current_user, request.form.get("comment", ""))
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        flash("Comment added.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/reviewer-assignment", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def cr_assign_reviewer(cr_id):
    reviewer_id = request.form.get("reviewer_id", type=int)
    try:
        ChangeRequestService.assign_reviewer(cr_id, reviewer_id, current_user)
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Reviewer assignment updated.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/<int:cr_id>/domain-signoff-requests", methods=["POST"])
@require_role_web("ENGINEER", "ADMINISTRATOR")
def cr_request_domain_signoff(cr_id):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        flash("Change request not found.", "error")
        return redirect(url_for("ui.my_change_requests"))
    try:
        DomainSignoffService.request_signoff(
            cr,
            request.form.get("engineering_domain", ""),
            request.form.get("target_user_id", type=int),
            current_user,
        )
    except (DomainError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Sign-off requested.", "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-requests/withdraw-selected", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def cr_withdraw_selected():
    ids = [int(v) for v in request.form.getlist("cr_id") if v.isdigit()]
    if not ids:
        flash("Tick at least one change request to withdraw.", "error")
        return redirect(url_for("ui.my_change_requests"))
    results = ChangeRequestService.withdraw_many(ids, current_user)
    done = sum(1 for r in results if r["ok"])
    if done:
        flash(f"{done} change request(s) withdrawn.", "success")
    for r in results:
        if not r["ok"]:
            flash(f"#{r['cr_id']}: {r['message']}", "error")
    return redirect(url_for("ui.my_change_requests"))


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
