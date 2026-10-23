"""S1 Login, S18 Account Settings."""

from flask import abort, flash, redirect, render_template, request, session, url_for

from app.auth import windows
from app.auth.decorators import current_user, login_required_web
from app.domain.errors import (
    AccountLockedError,
    ForbiddenError,
    InvalidCredentialsError,
    PasswordPolicyError,
    RateLimitedError,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.ui import ui_bp


@ui_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user:
        return redirect(url_for("ui.dashboard"))

    if windows.mode() == "windows" and request.args.get("password") != "1":
        return redirect(url_for("ui.login_windows", next=request.args.get("next")))

    if request.method == "POST":
        if not windows.password_login_allowed():
            flash("Passwords are not used here: sign in with Windows.", "error")
            return redirect(url_for("ui.login_windows"))
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        try:
            AuthService.login(username, password, request.remote_addr)
        except RateLimitedError as exc:
            flash(str(exc), "error")
        except AccountLockedError as exc:
            flash(str(exc), "error")
        except InvalidCredentialsError:
            flash("Invalid username or password.", "error")
        else:
            next_path = request.args.get("next") or url_for("ui.dashboard")
            return redirect(next_path)

    return render_template(
        "login.html",
        password_login=windows.password_login_allowed(),
        windows_login=windows.windows_login_allowed(),
        simulated=windows.simulation_enabled(),
    )


def _safe_next() -> str:
    target = request.values.get("next") or ""
    return (
        target
        if target.startswith("/") and not target.startswith("//")
        else url_for("ui.dashboard")
    )


@ui_bp.route("/login/windows")
def login_windows():
    """FR-163: the Windows sign-in. With an identity from the gateway the person is signed in at
    once; on a developer machine the simulation page asks for the identity instead."""
    if current_user:
        return redirect(url_for("ui.dashboard"))
    if not windows.windows_login_allowed():
        abort(404)
    identity, source = windows.request_identity()
    if identity:
        try:
            AuthService.windows_login(identity, source, request.remote_addr)
        except (InvalidCredentialsError, RateLimitedError, ForbiddenError) as exc:
            flash(str(exc), "error")
            return render_template("login_windows.html", simulated=False, error=True), 403
        return redirect(_safe_next())
    if windows.simulation_enabled():
        from app.extensions import db
        from app.models.user import User

        emails = [
            e
            for (e,) in db.session.query(User.email)
            .filter(User.is_active == 1)
            .order_by(User.email)
        ]
        return render_template("login_windows.html", simulated=True, emails=emails, error=False)
    return render_template("login_windows.html", simulated=False, error=False), 401


@ui_bp.route("/login/windows/simulate", methods=["POST"])
def login_windows_simulate():
    """Development only: pretend to be a Windows user. Everything after this line is the code a real
    deployment runs, with the typed identity standing in for the gateway's header."""
    if not windows.simulation_enabled():
        abort(404)
    identity = (request.form.get("identity") or "").strip()
    if not identity:
        flash("Enter the Windows identity, e.g. name@corp.example or CORP\\name.", "error")
        return redirect(url_for("ui.login_windows"))
    try:
        AuthService.windows_login(identity, "simulation", request.remote_addr)
    except (InvalidCredentialsError, RateLimitedError, ForbiddenError) as exc:
        session.pop(windows.SIMULATED_KEY, None)
        flash(str(exc), "error")
        return redirect(url_for("ui.login_windows"))
    return redirect(_safe_next())


@ui_bp.route("/logout", methods=["POST"])
def logout():
    AuthService.logout(current_user.id if current_user else None)
    flash("Logged out.", "info")
    return redirect(url_for("ui.login"))


@ui_bp.route("/account", methods=["GET", "POST"])
@login_required_web
def account_settings():
    if request.method == "POST":
        if not windows.password_login_allowed():
            flash("Your password is managed in Windows, not here.", "error")
            return redirect(url_for("ui.account_settings"))
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        user = UserService.get_user(current_user.id)
        try:
            UserService.change_own_password(user, current_password, new_password)
        except PasswordPolicyError as exc:
            for violation in exc.violations:
                flash(violation, "error")
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash("Password changed. Please log in again.", "success")
            AuthService.logout(current_user.id)
            return redirect(url_for("ui.login"))

    return render_template("account_settings.html", password_login=windows.password_login_allowed())
