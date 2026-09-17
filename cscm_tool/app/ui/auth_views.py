"""S1 Login, S18 Account Settings."""

from flask import flash, redirect, render_template, request, url_for

from app.auth.decorators import current_user, login_required_web
from app.domain.errors import (
    AccountLockedError,
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

    if request.method == "POST":
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

    return render_template("login.html")


@ui_bp.route("/logout", methods=["POST"])
def logout():
    AuthService.logout(current_user.id if current_user else None)
    flash("Logged out.", "info")
    return redirect(url_for("ui.login"))


@ui_bp.route("/account", methods=["GET", "POST"])
@login_required_web
def account_settings():
    if request.method == "POST":
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

    return render_template("account_settings.html")
