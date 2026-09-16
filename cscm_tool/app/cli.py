"""Operational CLI commands. `flask create-admin` bootstraps the very first
Administrator account: there is no in-app way to create the first user,
since ordinary user creation itself requires an authenticated Administrator
(US-009) — this command is the one deliberate exception to that rule."""

import click
from flask import Flask

from app.domain.errors import PasswordPolicyError
from app.services.user_service import UserService


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--full-name", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username: str, email: str, full_name: str, password: str) -> None:
        """Create an Administrator account (intended for the first user)."""
        try:
            user = UserService.create_user(
                username=username,
                email=email,
                full_name=full_name,
                role_code="ADMINISTRATOR",
                password=password,
                actor=None,
            )
        except PasswordPolicyError as exc:
            for violation in exc.violations:
                click.echo(f"  - {violation}", err=True)
            raise click.ClickException("Password does not meet policy.") from exc
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        click.echo(f"Created Administrator '{user.username}' (id={user.id}).")
