"""Operational CLI commands. `flask create-admin` bootstraps the very first
Administrator account: there is no in-app way to create the first user,
since ordinary user creation itself requires an authenticated Administrator
(US-009) — this command is the one deliberate exception to that rule.

The other commands are the jobs an OS scheduler runs (deploy/): `backup-db` (I-09),
`send-reminders` (I-08), `audit-verify` / `audit-archive` (I-18) and the offline checks
`verify-backup` and `verify-export` (I-06, I-09). Each exits non-zero on failure so a
scheduler or CI job notices."""

import json
import sys
from pathlib import Path

import click
from flask import Flask

from app.domain.errors import PasswordPolicyError
from app.services.user_service import UserService


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True, envvar="CSCM_ADMIN_USERNAME")
    @click.option("--email", prompt=True, envvar="CSCM_ADMIN_EMAIL")
    @click.option("--full-name", prompt=True, envvar="CSCM_ADMIN_FULL_NAME")
    @click.option(
        "--password",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        envvar="CSCM_ADMIN_PASSWORD",  # lets an installer pass it without a command-line argument
    )
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


def register_operations_commands(app: Flask) -> None:
    @app.cli.command("backup-db")
    @click.option("--dest", default=None, help="Backup directory (default: BACKUP_DIR).")
    @click.option("--keep", default=14, show_default=True, help="Generations to keep.")
    def backup_db(dest: str | None, keep: int) -> None:
        """Online backup of the database, verified by a restore smoke test (I-09)."""
        from flask import current_app

        from app.services import backup_service

        target = dest or current_app.config.get("BACKUP_DIR")
        if not target:
            raise click.ClickException("Give --dest or set BACKUP_DIR.")
        status = backup_service.create_backup(target, keep=keep)
        click.echo(
            json.dumps(
                {
                    k: status[k]
                    for k in (
                        "last_file",
                        "ok",
                        "integrity_ok",
                        "restore_ok",
                        "audit_chain_ok",
                        "size_bytes",
                    )
                }
            )
        )
        if not status["ok"]:
            raise click.ClickException("The backup was written but failed verification.")

    @app.cli.command("verify-backup")
    @click.argument("path", type=click.Path(exists=True, dir_okay=False))
    def verify_backup(path: str) -> None:
        """Integrity check + restore smoke test + audit-chain check of one backup file."""
        from app.services import backup_service

        result = backup_service.verify_backup(path)
        click.echo(json.dumps(result, indent=2))
        if not result.get("ok"):
            raise click.ClickException("Backup verification FAILED.")

    @app.cli.command("send-reminders")
    def send_reminders() -> None:
        """Remind whoever holds the next decision about stalled change requests (I-08)."""
        from app.services.notification_service import NotificationService

        click.echo(json.dumps(NotificationService.send_reminders()))

    @app.cli.command("audit-verify")
    @click.option("--no-anchor", is_flag=True, help="Do not update the stored anchor.")
    def audit_verify(no_anchor: bool) -> None:
        """Verify the audit-log hash chain (I-18). Non-zero exit when it is broken."""
        from app.audit_chain import AuditChainService

        result = AuditChainService.verify(update_anchor=not no_anchor)
        click.echo(json.dumps(result, indent=2))
        if not result["ok"]:
            raise click.ClickException("Audit chain verification FAILED.")

    @app.cli.command("audit-archive")
    @click.option("--dest", required=True, type=click.Path(file_okay=False))
    @click.option("--older-than-years", default=7.0, show_default=True)
    def audit_archive(dest: str, older_than_years: float) -> None:
        """Archive (never delete) audit entries past the retention period (I-18)."""
        from app.audit_chain import AuditChainService

        click.echo(json.dumps(AuditChainService.archive(dest, older_than_years)))

    @app.cli.command("verify-export")
    @click.argument("file", type=click.Path(exists=True, dir_okay=False))
    @click.argument("manifest", type=click.Path(exists=True, dir_okay=False))
    def verify_export(file: str, manifest: str) -> None:
        """Check an exported FILE against its MANIFEST.json without the database (I-06)."""
        from app.services import manifest_service

        manifest_data = json.loads(Path(manifest).read_text(encoding="utf-8"))
        result = manifest_service.verify_file(
            Path(file).read_bytes(), manifest_data, Path(file).name
        )
        click.echo(json.dumps(result, indent=2))
        if not result["ok"]:
            click.echo("MISMATCH: the file is not what the manifest describes.", err=True)
            sys.exit(1)
