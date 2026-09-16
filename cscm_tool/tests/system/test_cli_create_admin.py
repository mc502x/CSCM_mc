from app.extensions import db
from app.models.user import User


def test_create_admin_cli_command(app):
    runner = app.test_cli_runner()

    cli_input = (
        "firstadmin\nadmin@example.com\nFirst Admin\n"
        "a genuinely long passphrase\na genuinely long passphrase\n"
    )
    result = runner.invoke(args=["create-admin"], input=cli_input)

    assert result.exit_code == 0, result.output
    assert "Created Administrator 'firstadmin'" in result.output

    with app.app_context():
        user = db.session.query(User).filter(User.username == "firstadmin").first()
        assert user is not None
        assert user.role.code == "ADMINISTRATOR"


def test_create_admin_cli_rejects_weak_password(app):
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=["create-admin"],
        input="weakadmin\nweak@example.com\nWeak Admin\nshort\nshort\n",
    )

    assert result.exit_code != 0
