"""S14 User Management, S15 Lookup/Vocabulary Management, S16 Audit Log Search."""

from typing import cast

from flask import flash, redirect, render_template, request, url_for

from app.auth.decorators import current_user, require_role_web
from app.domain.errors import (
    DomainError,
    LastAdministratorError,
    NotFoundError,
    PasswordPolicyError,
)
from app.models.lookup import LookupFunctionalSystemGroup
from app.services.audit_service import AuditService
from app.services.lookup_admin_service import LookupAdminService
from app.services.lookup_service import VOCABULARY_MODELS, LookupService
from app.services.user_service import UserService
from app.ui import ui_bp

_ROLES = ["ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER", "VIEWER"]


@ui_bp.route("/admin/users")
@require_role_web("ADMINISTRATOR")
def user_list():
    users = UserService.list_users()
    domains = LookupService.list_vocabulary("engineering-domains")
    return render_template("admin/users.html", users=users, roles=_ROLES, domains=domains)


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
        flash(str(exc), "error")
    else:
        flash("User created.", "success")
    return redirect(url_for("ui.user_list"))


@ui_bp.route("/admin/users/<int:user_id>/update", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def user_update(user_id):
    try:
        UserService.update_user(
            user_id,
            full_name=request.form.get("full_name") or None,
            role_code=request.form.get("role") or None,
            engineering_domain_codes=request.form.getlist("engineering_domains"),
            is_active=request.form.get("is_active") == "on",
            actor=current_user,
        )
    except LastAdministratorError as exc:
        flash(str(exc), "error")
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        flash("User updated.", "success")
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
        flash("Password reset.", "success")
    return redirect(url_for("ui.user_list"))


@ui_bp.route("/admin/lookups")
@require_role_web("ADMINISTRATOR")
def lookup_admin():
    vocabulary = request.args.get("vocabulary", "turbine-platforms")
    if vocabulary not in VOCABULARY_MODELS:
        vocabulary = "turbine-platforms"

    if vocabulary == "functional-subgroups":
        groups = LookupService.list_vocabulary("functional-system-groups")
        values = []
        for group in groups:
            group_code = cast(LookupFunctionalSystemGroup, group).code
            values.extend(
                LookupService.list_vocabulary(vocabulary, functional_system_group_code=group_code)
            )
    else:
        values = LookupService.list_vocabulary(vocabulary)
        groups = []

    return render_template(
        "admin/lookups.html",
        vocabularies=sorted(VOCABULARY_MODELS.keys()),
        vocabulary=vocabulary,
        values=values,
        groups=groups,
    )


@ui_bp.route("/admin/lookups/<vocabulary>/new", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def lookup_value_new(vocabulary):
    data = {
        "code": request.form.get("code", ""),
        "label": request.form.get("label", ""),
        "description": request.form.get("description") or None,
        "functional_system_group": request.form.get("functional_system_group") or None,
        "sub_range_start": request.form.get("sub_range_start", type=int),
        "sub_range_end": request.form.get("sub_range_end", type=int),
    }
    try:
        LookupAdminService.create_value(vocabulary, data, current_user)
    except (DomainError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        flash("Value added.", "success")
    return redirect(url_for("ui.lookup_admin", vocabulary=vocabulary))


@ui_bp.route("/admin/lookups/<vocabulary>/<int:value_id>/update", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def lookup_value_update(vocabulary, value_id):
    data = {
        "label": request.form.get("label"),
        "is_active": request.form.get("is_active") == "on",
    }
    try:
        LookupAdminService.update_value(vocabulary, value_id, data, current_user)
    except NotFoundError:
        flash("Value not found.", "error")
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        flash("Value updated.", "success")
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
        date_from=request.args.get("date_from") or None,
        date_to=request.args.get("date_to") or None,
        page=page,
        page_size=50,
    )
    return render_template("admin/audit_log.html", entries=entries, total=total, page=page)
