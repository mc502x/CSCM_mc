"""The version of the application (FR-184). One place: the footer of the menu and of the login page,
`/api/v1/health` and `/api/v1/health/ready` show it, and tests/system/test_version.py keeps
pyproject.toml equal to it. Raise it with every release, together with the git tag `v<VERSION>`.
The REST contract has its own version (docs/artifacts/openapi.yaml `info.version`)."""

VERSION = "4.16.0"
