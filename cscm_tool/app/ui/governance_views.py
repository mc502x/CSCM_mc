"""Screens of the improvement pack that belong to the review workflow: notices (I-08), language
(I-22), change sets (I-11), stalled requests (I-08), delegation (I-16), the review checklist and
field comments (I-23), evidence attachments (I-13), reviewer balancing (I-30), settings, and help
(I-35). Handlers stay thin - the service layer owns every rule."""

from datetime import UTC, datetime, timedelta

from flask import (
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth.decorators import (
    current_user,
    login_required_web,
    require_role_or_delegate_web,
    require_role_web,
)
from app.auth.roles import OVERSIGHT_ROLES
from app.domain.errors import DomainError, NotFoundError
from app.extensions import db
from app.help_content import NEXT_STEP, QUICK_START, ROLE_GLOSSARY, STATE_GLOSSARY, TERM_GLOSSARY
from app.i18n import LANGUAGES, hidden_languages
from app.i18n import translate as _
from app.models.change_request import ChangeRequest
from app.models.lookup import LookupFunctionalSystemGroup, Role
from app.models.user import User
from app.services.attachment_service import AttachmentService
from app.services.change_request_service import ChangeRequestService
from app.services.change_set_service import ChangeSetService
from app.services.delegation_service import DelegationService
from app.services.field_review_service import COMMENTABLE_FIELDS, FieldReviewService
from app.services.lookup_service import LookupService
from app.services.notification_service import NotificationService
from app.services.settings_service import SettingsService
from app.services.sla_service import SlaService
from app.ui import ui_bp

_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
_ERRORS = (DomainError, ValueError)


# ---------------------------------------------------------------- notices / language / help
@ui_bp.route("/notifications")
@login_required_web
def notifications():
    return render_template(
        "notifications.html",
        notices=NotificationService.list_for(current_user.id),
    )


@ui_bp.route("/notifications/read", methods=["POST"])
@login_required_web
def notifications_read():
    notice_id = request.form.get("notification_id", type=int)
    if notice_id:
        try:
            NotificationService.mark_read(notice_id, current_user)
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
    else:
        NotificationService.mark_all_read(current_user)
        flash(_("All notices marked as read."), "success")
    return redirect(url_for("ui.notifications"))


@ui_bp.route("/language", methods=["POST"])
def set_language():
    language = request.form.get("lang", "")
    if language in LANGUAGES and language not in hidden_languages():
        session["ui_lang"] = language
        if current_user:
            user = db.session.get(User, current_user.id)
            if user is not None:
                user.ui_language = language
                db.session.commit()
    target = request.referrer or url_for("ui.dashboard")
    return redirect(target)


@ui_bp.route("/help")
@login_required_web
def help_page():
    return render_template(
        "help.html",
        quick_start=QUICK_START,
        role_glossary=ROLE_GLOSSARY,
        state_glossary=STATE_GLOSSARY,
        terms={k: v for k, v in TERM_GLOSSARY.items() if ":" not in k},
        next_steps=NEXT_STEP,
    )


# ---------------------------------------------------------------- change sets (I-11)
@ui_bp.route("/change-sets")
@require_role_web(*OVERSIGHT_ROLES)
def change_set_list():
    return render_template("change_sets/list.html", change_sets=ChangeSetService.list_all())


@ui_bp.route("/change-sets/new", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER", "CHIEF_ENGINEER")
def change_set_new():
    if request.method == "POST":
        try:
            change_set = ChangeSetService.create(
                request.form.get("name", ""),
                request.form.get("description"),
                request.form.get("target_software_version") or None,
                current_user,
            )
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
        else:
            flash(_("Change set created."), "success")
            return redirect(url_for("ui.change_set_detail", change_set_id=change_set.id))
    versions = LookupService.list_vocabulary("controller-software-versions")
    return render_template("change_sets/new.html", versions=versions)


@ui_bp.route("/change-sets/<int:change_set_id>")
@require_role_web(*OVERSIGHT_ROLES)
def change_set_detail(change_set_id):
    try:
        overview = ChangeSetService.overview(change_set_id)
    except NotFoundError:
        flash(_("Change set not found."), "error")
        return redirect(url_for("ui.change_set_list"))
    mine = (
        db.session.query(ChangeRequest)
        .filter(
            ChangeRequest.requested_by == current_user.id, ChangeRequest.change_set_id.is_(None)
        )
        .order_by(ChangeRequest.id.desc())
        .all()
        if current_user.role_code in ("ENGINEER", "ADMINISTRATOR")
        else []
    )
    mine = [
        cr for cr in mine if cr.revision.lifecycle_status in ("DRAFT", "REVIEW", "PENDING_APPROVAL")
    ]
    return render_template(
        "change_sets/detail.html",
        overview=overview,
        addable=mine,
        results=request.args.get("results"),
    )


@ui_bp.route("/change-sets/<int:change_set_id>/add", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def change_set_add(change_set_id):
    try:
        ChangeSetService.add_cr(
            change_set_id, request.form.get("cr_id", type=int) or 0, current_user
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Change request added to the set."), "success")
    return redirect(url_for("ui.change_set_detail", change_set_id=change_set_id))


@ui_bp.route("/change-requests/<int:cr_id>/change-set", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def change_set_add_from_cr(cr_id):
    try:
        ChangeSetService.add_cr(
            request.form.get("change_set_id", type=int) or 0, cr_id, current_user
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Change request added to the set."), "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/change-sets/<int:change_set_id>/remove/<int:cr_id>", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def change_set_remove(change_set_id, cr_id):
    try:
        ChangeSetService.remove_cr(change_set_id, cr_id, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Change request removed from the set."), "success")
    return redirect(url_for("ui.change_set_detail", change_set_id=change_set_id))


@ui_bp.route("/change-sets/<int:change_set_id>/close", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def change_set_close(change_set_id):
    try:
        ChangeSetService.close(change_set_id, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Change set closed."), "success")
    return redirect(url_for("ui.change_set_detail", change_set_id=change_set_id))


@ui_bp.route("/change-sets/<int:change_set_id>/decide", methods=["POST"])
@require_role_or_delegate_web("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")
def change_set_decide(change_set_id):
    """Each selected CR is decided by its own service call (see ChangeSetService)."""
    try:
        results = ChangeSetService.bulk_decide(
            change_set_id,
            request.form.get("step", ""),
            request.form.get("decision", ""),
            request.form.get("comment") or None,
            current_user,
            request.form.get("current_password"),
            cr_ids=request.form.getlist("cr_ids", type=int) or None,
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        ok = sum(1 for r in results if r["ok"])
        flash(
            _("%(ok)s of %(n)s decisions recorded.", ok=ok, n=len(results)),
            "success" if ok else "error",
        )
        for r in results:
            if not r["ok"]:
                flash(f"CR #{r['cr_id']}: {r['message']}", "error")
    return redirect(url_for("ui.change_set_detail", change_set_id=change_set_id))


# ---------------------------------------------------------------- stalled requests (I-08, I-30)
@ui_bp.route("/admin/stalled")
@require_role_web("ADMINISTRATOR")
def stalled_requests():
    return render_template(
        "admin/stalled.html",
        rows=SlaService.stalled(),
        thresholds=SlaService.thresholds(),
        workloads=ChangeRequestService.reviewer_workloads(),
        reviewers=db.session.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.code == "REVIEWER", User.is_active == 1)
        .order_by(User.full_name)
        .all(),
    )


@ui_bp.route("/change-requests/<int:cr_id>/reviewer-assignment/auto", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def cr_auto_assign_reviewer(cr_id):
    try:
        cr = ChangeRequestService.auto_assign_reviewer(cr_id, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        reviewer = cr.assigned_reviewer
        flash(
            _(
                "Assigned to %(name)s (fewest open reviews).",
                name=reviewer.full_name if reviewer else "-",
            ),
            "success",
        )
    return redirect(request.referrer or url_for("ui.change_request_detail", cr_id=cr_id))


# ---------------------------------------------------------------- delegation (I-16)
@ui_bp.route("/delegation", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")
def delegations():
    if request.method == "POST":
        try:
            DelegationService.create(
                request.form.get("delegator_id", type=int) or current_user.id,
                request.form.get("delegate_id", type=int) or 0,
                request.form.get("valid_from", ""),
                request.form.get("valid_to", ""),
                current_user,
            )
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
        else:
            flash(_("Delegation created."), "success")
        return redirect(url_for("ui.delegations"))
    candidates = (
        db.session.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(User.is_active == 1, Role.code != "VIEWER", User.id != current_user.id)
        .order_by(User.full_name)
        .all()
    )
    today = datetime.now(UTC).date()
    return render_template(
        "delegations.html",
        delegations=DelegationService.list_for(current_user),
        candidates=candidates,
        today=today.isoformat(),
        default_end=(today + timedelta(days=7)).isoformat(),
    )


@ui_bp.route("/delegation/<int:delegation_id>/revoke", methods=["POST"])
@require_role_web("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")
def delegation_revoke(delegation_id):
    try:
        DelegationService.revoke(delegation_id, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Delegation revoked."), "success")
    return redirect(url_for("ui.delegations"))


# ---------------------------------------------------------------- review checklist (I-23)
@ui_bp.route("/admin/review-checklist", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR")
def review_checklist():
    if request.method == "POST":
        try:
            FieldReviewService.create_item(
                request.form.get("text", ""),
                request.form.get("functional_system_group", type=int),
                current_user,
                sort_order=request.form.get("sort_order", 0, type=int),
            )
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
        else:
            flash(_("Checklist item added."), "success")
        return redirect(url_for("ui.review_checklist"))
    return render_template(
        "admin/review_checklist.html",
        items=FieldReviewService.list_items(include_inactive=True),
        groups=db.session.query(LookupFunctionalSystemGroup)
        .order_by(LookupFunctionalSystemGroup.sort_order)
        .all(),
    )


@ui_bp.route("/admin/review-checklist/<int:item_id>/toggle", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def review_checklist_toggle(item_id):
    items = {i.id: i for i in FieldReviewService.list_items(include_inactive=True)}
    item = items.get(item_id)
    if item is None:
        abort(404)
    try:
        FieldReviewService.update_item(item_id, {"is_active": not item.is_active}, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    return redirect(url_for("ui.review_checklist"))


# ---------------------------------------------------------------- field comments / evidence
@ui_bp.route("/change-requests/<int:cr_id>/field-comments", methods=["POST"])
@require_role_or_delegate_web("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")
def cr_add_field_comment(cr_id):
    try:
        FieldReviewService.add_field_comment(
            cr_id, request.form.get("field", ""), request.form.get("comment", ""), current_user
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Field comment added."), "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/field-comments/<int:comment_id>/resolve", methods=["POST"])
@require_role_web(*_WORKING)
def field_comment_resolve(comment_id):
    try:
        comment = FieldReviewService.resolve_field_comment(comment_id, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
        return redirect(request.referrer or url_for("ui.my_change_requests"))
    flash(_("Comment marked as resolved."), "success")
    return redirect(url_for("ui.change_request_detail", cr_id=comment.change_request_id))


@ui_bp.route("/change-requests/<int:cr_id>/attachments", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def cr_add_attachment(cr_id):
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        flash(_("Choose a file to attach."), "error")
    else:
        try:
            AttachmentService.add(
                cr_id, upload.filename, upload.read(), request.form.get("description"), current_user
            )
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
        else:
            flash(_("Evidence attached."), "success")
    return redirect(url_for("ui.change_request_detail", cr_id=cr_id))


@ui_bp.route("/attachments/<int:attachment_id>")
@require_role_web(*_WORKING)
def attachment_download(attachment_id):
    try:
        path, attachment = AttachmentService.get_for_download(attachment_id, current_user)
    except _ERRORS:
        abort(404)
    return Response(
        path.read_bytes(),
        mimetype=attachment.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
            "X-Content-SHA256": attachment.sha256,
        },
    )


@ui_bp.route("/attachments/<int:attachment_id>/delete", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def attachment_delete(attachment_id):
    from app.models.change_request import CrAttachment

    attachment = db.session.get(CrAttachment, attachment_id)
    cr_id = attachment.change_request_id if attachment else None
    try:
        AttachmentService.delete(attachment_id, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Evidence removed."), "success")
    return redirect(
        url_for("ui.change_request_detail", cr_id=cr_id) if cr_id else url_for("ui.dashboard")
    )


# ---------------------------------------------------------------- settings (I-08, I-19, I-30)
@ui_bp.route("/admin/settings", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR")
def app_settings():
    if request.method == "POST":
        values = {k[len("s_") :]: v for k, v in request.form.items() if k.startswith("s_")}
        try:
            SettingsService.update(values, current_user)
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
        else:
            flash(_("Settings saved."), "success")
        return redirect(url_for("ui.app_settings"))
    return render_template("admin/settings.html", settings=SettingsService.all())


__all__ = ["COMMENTABLE_FIELDS"]
