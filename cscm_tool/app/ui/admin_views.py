"""S14 User Management, S15 Lookup/Vocabulary Management (incl. Functional
System Group / Subgroup administration, EPIC-16), S16 Audit Log Search."""

from flask import flash, redirect, render_template, request, url_for

from app.auth.decorators import current_user, require_role_web
from app.auth.roles import ROLE_CODES, USER_LIST_ROLES, assignable_roles, may_change_role
from app.domain.errors import (
    DomainError,
    LastAdministratorError,
    NotFoundError,
    PasswordPolicyError,
)
from app.i18n import translate as _
from app.services.audit_service import AuditService
from app.services.lookup_admin_service import LookupAdminService
from app.services.lookup_service import VOCABULARY_MODELS, LookupService
from app.services.user_service import UserService
from app.ui import ui_bp

_ROLES = list(ROLE_CODES)


@ui_bp.route("/admin/users")
@require_role_web(*USER_LIST_ROLES)
def user_list():
    users = UserService.list_users()
    domains = LookupService.list_vocabulary("engineering-domains")
    actor_role = current_user.role_code
    return render_template(
        "admin/users.html",
        users=users,
        roles=_ROLES,
        domains=domains,
        is_admin=actor_role == "ADMINISTRATOR",
        assignable=assignable_roles(actor_role),
        may_change_role=lambda user: any(
            may_change_role(actor_role, user.role.code, r) for r in assignable_roles(actor_role)
        ),
    )


@ui_bp.route("/admin/users/<int:user_id>")
@require_role_web(*USER_LIST_ROLES)
def user_detail(user_id):
    try:
        user = UserService.get_user(user_id)
        usage = UserService.usage(user_id)
    except NotFoundError:
        flash(_("User not found."), "error")
        return redirect(url_for("ui.user_list"))
    actor_role = current_user.role_code
    return render_template(
        "admin/user_detail.html",
        user=user,
        usage=usage,
        roles=_ROLES,
        domains=LookupService.list_vocabulary("engineering-domains"),
        is_admin=actor_role == "ADMINISTRATOR",
        is_self=user.id == current_user.id,
        assignable=assignable_roles(actor_role),
        may_change_role=any(
            may_change_role(actor_role, user.role.code, r) for r in assignable_roles(actor_role)
        ),
    )


@ui_bp.route("/admin/users/<int:user_id>/active", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def user_set_active(user_id):
    """The Deactivate / Activate buttons. A deactivated account cannot sign in and an open session
    ends with its next request; nothing it did is lost."""
    active = request.form.get("active") == "1"
    try:
        UserService.update_user(user_id, is_active=active, actor=current_user)
    except (LastAdministratorError, DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("User activated.") if active else _("User deactivated."), "success")
    return redirect(request.form.get("next") or url_for("ui.user_list"))


@ui_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def user_delete(user_id):
    try:
        UserService.delete_user(user_id, current_user, request.form.get("current_password"))
    except (LastAdministratorError, DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
        return redirect(url_for("ui.user_detail", user_id=user_id))
    flash(_("User deleted."), "success")
    return redirect(url_for("ui.user_list"))


@ui_bp.route("/admin/users/new", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def user_new():
    try:
        UserService.create_user(
            username=request.form.get("username", ""),
            email=request.form.get("email", ""),
            full_name=request.form.get("full_name", ""),
            role_code=request.form.get("role", "VIEWER"),
            password=request.form.get("password", ""),
            engineering_domain_codes=request.form.getlist("engineering_domains"),
            actor=current_user,
        )
    except PasswordPolicyError as exc:
        for v in exc.violations:
            flash(v, "error")
    except ValueError as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("User created."), "success")
    return redirect(url_for("ui.user_list"))


@ui_bp.route("/admin/users/<int:user_id>/update", methods=["POST"])
@require_role_web(*USER_LIST_ROLES)
def user_update(user_id):
    try:
        if current_user.role_code == "ADMINISTRATOR":
            UserService.update_user(
                user_id,
                full_name=request.form.get("full_name") or None,
                role_code=request.form.get("role") or None,
                engineering_domain_codes=request.form.getlist("engineering_domains"),
                is_active=request.form.get("is_active") == "on",
                actor=current_user,
            )
        else:  # StCd Owner: the role is all they may change (BR-024)
            UserService.update_user(
                user_id, role_code=request.form.get("role") or None, actor=current_user
            )
    except (LastAdministratorError, DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("User updated."), "success")
    return redirect(url_for("ui.user_list"))


@ui_bp.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def user_reset_password(user_id):
    new_password = request.form.get("new_password", "")
    try:
        UserService.force_reset_password(user_id, new_password, actor=current_user)
    except PasswordPolicyError as exc:
        for v in exc.violations:
            flash(v, "error")
    else:
        flash(_("Password reset."), "success")
    return redirect(url_for("ui.user_list"))


@ui_bp.route("/admin/lookups")
@require_role_web("ADMINISTRATOR")
def lookup_admin():
    vocabulary = request.args.get("vocabulary", "turbine-platforms")
    if vocabulary not in VOCABULARY_MODELS:
        vocabulary = "turbine-platforms"

    selected_group_id = None
    if vocabulary == "functional-subgroups":
        groups = LookupService.list_vocabulary("functional-system-groups")
        selected_group_id = request.args.get("functional_system_group", type=int) or (
            groups[0].id if groups else None  # type: ignore[attr-defined]
        )
        values = (
            LookupService.list_vocabulary(vocabulary, functional_system_group_id=selected_group_id)
            if selected_group_id
            else []
        )
    elif vocabulary == "functional-system-groups":
        values = LookupService.list_vocabulary(vocabulary)
        groups = []
    else:
        values = LookupService.list_vocabulary(vocabulary)
        groups = []

    return render_template(
        "admin/lookups.html",
        vocabularies=sorted(VOCABULARY_MODELS.keys()),
        vocabulary=vocabulary,
        values=values,
        groups=groups,
        selected_group_id=selected_group_id,
    )


@ui_bp.route("/admin/lookups/<vocabulary>/new", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def lookup_value_new(vocabulary):
    data = {
        "code": request.form.get("code", ""),
        "label": request.form.get("label", ""),
    }
    try:
        LookupAdminService.create_value(vocabulary, data, current_user)
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Value added."), "success")
    return redirect(url_for("ui.lookup_admin", vocabulary=vocabulary))


@ui_bp.route("/admin/lookups/functional-system-groups/new", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def functional_system_group_new():
    """FR-048g/h (EPIC-16): into any currently free range, non-overlap
    validated (service layer + trg_prevent_group_overlap backstop)."""
    data = {
        "code": request.form.get("code", ""),
        "label": request.form.get("label", ""),
        "range_start": request.form.get("range_start", type=int),
        "range_end": request.form.get("range_end", type=int),
    }
    try:
        group = LookupAdminService.create_functional_system_group(data, current_user)
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Functional System Group '%(code)s' created.", code=group.code), "success")
    return redirect(url_for("ui.lookup_admin", vocabulary="functional-system-groups"))


@ui_bp.route("/admin/lookups/functional-subgroups/new", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def functional_subgroup_new():
    """FR-048e/f (EPIC-16): within an existing group, non-overlap validated."""
    group_id = request.form.get("functional_system_group", type=int)
    data = {
        "functional_system_group": group_id,
        "code": request.form.get("code", ""),
        "label": request.form.get("label", ""),
        "sub_range_start": request.form.get("sub_range_start", type=int),
        "sub_range_end": request.form.get("sub_range_end", type=int),
    }
    try:
        LookupAdminService.create_functional_subgroup(data, current_user)
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Functional Subgroup added."), "success")
    return redirect(
        url_for(
            "ui.lookup_admin", vocabulary="functional-subgroups", functional_system_group=group_id
        )
    )


@ui_bp.route("/admin/lookups/<vocabulary>/<int:value_id>/update", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def lookup_value_update(vocabulary, value_id):
    data = {
        "label": request.form.get("label"),
        "description": request.form.get("description") or None,
        "is_active": request.form.get("is_active") == "on",
    }
    try:
        LookupAdminService.update_value(vocabulary, value_id, data, current_user)
    except NotFoundError:
        flash(_("Value not found."), "error")
    except ValueError as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Value updated."), "success")
    return redirect(url_for("ui.lookup_admin", vocabulary=vocabulary))


@ui_bp.route("/admin/audit-log")
@require_role_web("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")
def audit_log():
    page = request.args.get("page", 1, type=int)
    entries, total = AuditService.search(
        current_user,
        entity_type=request.args.get("entity_type") or None,
        entity_id=request.args.get("entity_id", type=int),
        actor_id=request.args.get("actor_id", type=int),
        action=request.args.get("action") or None,
        date_from=request.args.get("date_from") or None,
        date_to=request.args.get("date_to") or None,
        page=page,
        page_size=50,
    )
    return render_template("admin/audit_log.html", entries=entries, total=total, page=page)
