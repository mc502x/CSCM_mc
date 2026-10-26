"""The hand-over to the team repository (FR-188, scripts/handover.py): the audit, the clean export and
the guard on the push, on small throw-away Git repositories.

TC-075. Requirements: FR-188, NFR-013.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from app import branding

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
VERSION = "9.9.9"
RELEASE_FILES = (
    "Full-Documentation.pdf",
    "Software-Description.pdf",
    "User-Manual.pdf",
    "Test-Report.pdf",
    "Design-Showcase-Management.pptx",
    "Design-Showcase-Management.pdf",
    "Design-Showcase-Team.pptx",
    "Design-Showcase-Team.pdf",
)


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("handover", ROOT / "scripts" / "handover.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["handover"] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=Dev", "-c", "user.email=dev@example.test", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _write(root: Path, rel: str, text: str | bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))


def _clean_files(root: Path) -> None:
    _write(root, "cscm_tool/app/version.py", f'VERSION = "{VERSION}"\n')
    _write(root, "cscm_tool/pyproject.toml", f'[project]\nversion = "{VERSION}"\n')
    _write(root, "README.md", f"Ask {branding.OWNER_NAME}, {branding.OWNER_EMAIL}.\n")
    _write(root, "docs/24-test-report.md", "| **Verdict** | **PASS** |\n")
    for name in RELEASE_FILES:
        _write(root, f"releases/v{VERSION}/CSCM-Tool_v{VERSION}_{name}", b"x")


def _repo(tmp_path: Path, extra: dict[str, str | bytes] | None = None) -> Path:
    repo = tmp_path / "dev"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "dev")
    _clean_files(repo)
    for rel, text in (extra or {}).items():
        _write(repo, rel, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "work")
    _git(repo, "tag", f"v{VERSION}")
    return repo


def _audit(tool, repo: Path, tmp_path: Path) -> list[str]:
    tree = tmp_path / "tree"
    tool.extract(repo, f"v{VERSION}", tree)
    return tool.audit(tree, f"v{VERSION}")


def test_a_clean_tree_passes_the_audit(tool, tmp_path):
    assert _audit(tool, _repo(tmp_path), tmp_path) == []


def test_every_kind_of_finding_stops_the_handover(tool, tmp_path):
    account, repository = "mc" + "502x", "CSCM" + "_mc"
    repo = _repo(
        tmp_path,
        {
            "docs/guide.md": f"clone https://github.com/{account}/{repository}.git\n",
            "cscm_tool/app/keys.py": "-----BEGIN RSA PRIVATE KEY-----\nabc\n",
            "cscm_tool/.env": "SECRET_KEY=x\n",
            "cscm_tool/instance/cscm.db": b"SQLite",
            "data/backup.db": b"SQLite",
            "docs/notes.md": "see C:\\Users\\someone\\project and write to somebody@private-mail.org\n",
            "docs/big.md": "x" * (5 * 1024 * 1024 + 10),
        },
    )
    _write(repo, "cscm_tool/app/version.py", 'VERSION = "1.0.0"\n')
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "more")
    _git(repo, "tag", "-f", f"v{VERSION}")
    (repo / "releases" / f"v{VERSION}" / f"CSCM-Tool_v{VERSION}_Test-Report.pdf").unlink()
    _write(repo, "docs/24-test-report.md", "| **Verdict** | **FAIL** |\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "worse")
    _git(repo, "tag", "-f", f"v{VERSION}")
    found = "\n".join(_audit(tool, repo, tmp_path))
    for expected in (
        "docs/guide.md: names the account or the repository",
        "cscm_tool/app/keys.py: contains a private key",
        "cscm_tool/.env: a local settings file",
        "cscm_tool/instance/cscm.db",
        "data/backup.db: a file that is data",
        "docs/notes.md: contains a path of a personal machine",
        "docs/notes.md: e-mail address somebody@private-mail.org",
        "docs/big.md: larger than 5 MB",
        "app/version.py says 1.0.0, the tag says 9.9.9",
        f"CSCM-Tool_v{VERSION}_Test-Report.pdf is missing",
        "the verdict is not PASS",
    ):
        assert expected in found, expected


def test_the_export_is_one_commit_by_the_named_author_with_the_tag(tool, tmp_path):
    repo = _repo(tmp_path)
    _write(repo, "docs/more.md", "more work\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "second commit of the development history")
    _git(repo, "tag", "-f", f"v{VERSION}")
    out = tmp_path / "team"
    code = tool.main(
        [
            "--tag",
            f"v{VERSION}",
            "--repo",
            str(repo),
            "--out",
            str(out),
            "--author",
            "Release Owner <owner@example.org>",
        ]
    )
    assert code == 0
    assert _git(out, "rev-list", "--count", "HEAD") == "1"  # no development history
    assert _git(out, "branch", "--show-current") == "main"
    assert _git(out, "log", "-1", "--format=%an <%ae>") == "Release Owner <owner@example.org>"
    assert _git(out, "log", "-1", "--format=%cn <%ce>") == "Release Owner <owner@example.org>"
    assert "Co-Authored-By" not in _git(out, "log", "-1", "--format=%B")
    assert branding.LONG_NAME in _git(out, "log", "-1", "--format=%B")
    assert _git(out, "tag") == f"v{VERSION}" and _git(out, "cat-file", "-t", f"v{VERSION}") == "tag"
    assert (out / "docs" / "more.md").is_file()
    assert _git(out, "remote") == ""  # nothing is connected, nothing was pushed
    with pytest.raises(SystemExit, match="empty"):  # the export needs a new, empty folder
        tool.main(
            [
                "--tag",
                f"v{VERSION}",
                "--repo",
                str(repo),
                "--out",
                str(out),
                "--author",
                "A <a@example.org>",
            ]
        )


def test_a_tag_that_does_not_exist_and_a_push_without_confirmation_are_refused(
    tool, tmp_path, capsys
):
    repo = _repo(tmp_path)
    assert tool.main(["--tag", "v0.0.1", "--repo", str(repo), "--audit-only"]) == 2
    out = tmp_path / "team"
    refused = tool.main(
        [
            "--tag",
            f"v{VERSION}",
            "--repo",
            str(repo),
            "--out",
            str(out),
            "--author",
            "O <o@example.org>",
            "--push",
        ]
    )
    assert refused == 2 and "nothing was pushed" in capsys.readouterr().out
    assert _git(out, "remote") == ""  # no remote was even added
    dirty = _repo(tmp_path / "second", {"docs/x.md": "contact somebody@private-mail.org\n"})
    assert (
        tool.main(
            [
                "--tag",
                f"v{VERSION}",
                "--repo",
                str(dirty),
                "--out",
                str(tmp_path / "t2"),
                "--author",
                "O <o@example.org>",
            ]
        )
        == 1
    )
    assert not (tmp_path / "t2").exists()  # a finding stops the export


def test_the_repository_carries_its_team_files():
    owners = (REPO / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert owners.splitlines()[-1].startswith("* @")
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/ci.py" in workflow and "verify:" in workflow and "deploy-scripts:" in workflow
    assert "Checklist" in (REPO / ".github" / "pull_request_template.md").read_text(
        encoding="utf-8"
    )
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "ci.py --pdf --showcase" in contributing and "first_start.py" in contributing
    assert not (REPO / "tree.7z").exists()
