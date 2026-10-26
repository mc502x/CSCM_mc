"""The hand-over of a release to the team repository (FR-188): audit, clean export, push.

    python scripts/handover.py --tag v4.16.0 --author "Name <name@example.org>" --out ../team-export
    python scripts/handover.py --tag v4.16.0 --author "..." --out ../team-export \\
        --remote <address of the team repository> --push --yes

The first release of a team repository is a *clean start* (option A of docs/15 section 9): the tree
of the release tag becomes ONE commit on `main`, tagged with the release, with the author you name.
The history of the development machine stays where it is. Steps:

  1. audit   scans the tree of the tag for what must not leave: the Git account and repository
             names, keys and tokens, databases, `.env` files, personal paths, e-mail addresses other
             than the owner's, large files, a version that disagrees with the tag, missing release
             files, a test report that is not green. Any finding stops the hand-over.
  2. export  `git archive` of the tag into an empty folder, `git init -b main`, one commit, one
             annotated tag. Nothing leaves the machine.
  3. push    only with --remote, --push and --yes together: `git push` of `main` and the tag
             to the remote. Never forced; a remote that already holds other history refuses it.

It uses only git and the Python standard library."""

import argparse
import re
import shutil
import subprocess  # nosec B404 - runs git with fixed arguments
import sys
import tarfile
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from app import branding  # noqa: E402

# written in pieces so that this file does not contain what it looks for
FORBIDDEN = (
    "mc" + "502x",
    "CSCM" + "_mc",
    "github.com/" + "mc",
    "free" + "net.de",
    "max." + "cash",
)
SECRET_PATTERNS = {
    "a private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "a GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "an AWS key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "a long secret in a setting": re.compile(
        r"^(?:SECRET_KEY|AUDIT_HMAC_KEY|MANIFEST_SIGNING_KEY)\s*=\s*[0-9a-fA-F]{32,}\s*$", re.M
    ),
}
PERSONAL_PATH = re.compile(r"[A-Za-z]:[\\/]Users[\\/][A-Za-z]|/Users/[a-z]|Z:[\\/]CSCM_")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ALLOWED_EMAIL = re.compile(
    r"@(example\.(test|org|com|internal)|corp\.example|localhost|users\.noreply\.github\.com)$|^"
    + re.escape(branding.OWNER_EMAIL)
    + "$|^(a|name|user|me|you)@",
    re.I,
)
BINARY_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".7z", ".zip", ".bak", ".pem", ".key", ".pfx"}
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".ico",
    ".ttf",
    ".pdf",
    ".pptx",
    ".xlsx",
    ".woff",
    ".woff2",
    ".gz",
    ".mo",
}
MAX_BYTES = 5 * 1024 * 1024
TEXT_LIMIT = (
    4 * 1024 * 1024
)  # larger text files (the generated translation catalogue) are scanned for names only


def git(
    *args: str, cwd: Path, check: bool = True, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=cwd, capture_output=True, check=check, input=input_bytes
    )


def extract(repo: Path, tag: str, target: Path) -> None:
    """The tracked files of `tag`, nothing else."""
    archive = git("archive", "--format=tar", tag, cwd=repo).stdout
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as handle:
        handle.write(archive)
        handle.seek(0)
        with tarfile.open(fileobj=handle) as tar:
            tar.extractall(
                target, filter="data"
            )  # nosec B202 - our own archive, with the safe filter


def audit(tree: Path, tag: str) -> list[str]:
    """What stops the hand-over; an empty list means the tree may go."""
    found: list[str] = []
    version = tag.lstrip("v")
    for path in sorted(p for p in tree.rglob("*") if p.is_file()):
        rel = path.relative_to(tree).as_posix()
        if path.suffix.lower() in BINARY_SUFFIXES:
            found.append(f"{rel}: a file that is data or an archive, not source")
            continue
        if (
            rel == ".env"
            or rel.endswith("/.env")
            or "/instance/" in f"/{rel}"
            or rel.startswith("instance/")
        ):
            found.append(f"{rel}: a local settings file or data folder")
            continue
        if path.stat().st_size > MAX_BYTES:
            found.append(f"{rel}: larger than {MAX_BYTES // 1024 // 1024} MB")
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in FORBIDDEN:
            if word in text:
                found.append(f"{rel}: names the account or the repository ('{word[:4]}...')")
        if path.stat().st_size > TEXT_LIMIT:
            continue
        for what, pattern in SECRET_PATTERNS.items():
            if pattern.search(text) and not rel.startswith("cscm_tool/tests/"):
                found.append(f"{rel}: contains {what}")
        if PERSONAL_PATH.search(text) and not rel.startswith(
            ("cscm_tool/tests/", "cscm_tool/scripts/handover")
        ):
            found.append(f"{rel}: contains a path of a personal machine")
        for address in sorted(set(EMAIL.findall(text))):
            if not ALLOWED_EMAIL.search(address) and not rel.startswith(
                ("cscm_tool/tests/", "cscm_tool/scripts/handover")
            ):
                found.append(f"{rel}: e-mail address {address}")
    found += _release_checks(tree, version, tag)
    return found


def _release_checks(tree: Path, version: str, tag: str) -> list[str]:
    found = []
    version_file = tree / "cscm_tool" / "app" / "version.py"
    pyproject = tree / "cscm_tool" / "pyproject.toml"
    if not version_file.is_file():
        return [f"{tag}: cscm_tool/app/version.py is missing"]
    in_code = re.search(r'VERSION\s*=\s*"([^"]+)"', version_file.read_text(encoding="utf-8"))
    if not in_code or in_code.group(1) != version:
        found.append(
            f"app/version.py says {in_code.group(1) if in_code else '?'}, the tag says {version}"
        )
    if pyproject.is_file() and not re.search(
        rf'^version\s*=\s*"{re.escape(version)}"', pyproject.read_text(encoding="utf-8"), re.M
    ):
        found.append(f"pyproject.toml does not say {version}")
    folder = tree / "releases" / f"v{version}"
    if folder.is_dir():
        for name in (
            "Full-Documentation.pdf",
            "Software-Description.pdf",
            "User-Manual.pdf",
            "Test-Report.pdf",
            "Design-Showcase-Management.pptx",
            "Design-Showcase-Management.pdf",
            "Design-Showcase-Team.pptx",
            "Design-Showcase-Team.pdf",
        ):
            if not (folder / f"CSCM-Tool_v{version}_{name}").is_file():
                found.append(f"releases/v{version}: CSCM-Tool_v{version}_{name} is missing")
    else:
        found.append(f"releases/v{version} does not exist")
    report = tree / "docs" / "24-test-report.md"
    if report.is_file():
        text = report.read_text(encoding="utf-8")
        if not re.search(r"\| \*\*Verdict\*\* \| \*\*PASS\*\*", text):
            found.append("docs/24-test-report.md: the verdict is not PASS")
    return found


def export(tree: Path, out: Path, tag: str, author: str, message: str) -> None:
    """A new repository in `out`: one commit on main with the files of the tag, one tag."""
    match = re.fullmatch(r"\s*(.+?)\s*<([^<>@\s]+@[^<>\s]+)>\s*", author)
    if not match:
        raise SystemExit('--author must look like "Name <name@example.org>"')
    name, email = match.groups()
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty; the export needs a new, empty folder")
    shutil.copytree(tree, out, dirs_exist_ok=True)
    env = [
        "-c",
        f"user.name={name}",
        "-c",
        f"user.email={email}",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.autocrlf=false",
    ]
    git("init", "-q", "-b", "main", cwd=out)
    git(*env, "add", "-A", cwd=out)
    git(*env, "commit", "-q", "-m", message, cwd=out)
    git(*env, "tag", "-a", tag, "-m", f"CSCM Tool {tag.lstrip('v')}", cwd=out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hand a release over to the team repository.")
    parser.add_argument("--tag", required=True, help="the release tag, for example v4.16.0")
    parser.add_argument(
        "--repo", type=Path, default=APP_DIR.parent, help="the development repository"
    )
    parser.add_argument("--out", type=Path, help="an empty folder for the clean repository")
    parser.add_argument("--author", help='"Name <email>" of the first commit')
    parser.add_argument("--message", help="message of the first commit")
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--remote", help="address of the team repository (to push to)")
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--yes", action="store_true", help="confirm the push")
    args = parser.parse_args(argv)

    version = args.tag.lstrip("v")
    with tempfile.TemporaryDirectory(prefix="cscm_handover_") as scratch:
        tree = Path(scratch) / "tree"
        try:
            extract(args.repo, args.tag, tree)
        except subprocess.CalledProcessError as exc:
            print(
                f"The tag {args.tag} does not exist in {args.repo}: {exc.stderr.decode(errors='ignore').strip()}"
            )
            return 2
        print(f"Audit of {args.tag} ({sum(1 for p in tree.rglob('*') if p.is_file())} files)")
        findings = audit(tree, args.tag)
        for line in findings:
            print("  STOP:", line)
        if findings:
            print(f"{len(findings)} finding(s): nothing was exported or pushed.")
            return 1
        print(
            "  clean: no names, keys, data, personal paths or stray addresses; version and release files agree"
        )
        if args.audit_only:
            return 0
        if not args.out or not args.author:
            print("--out and --author are needed to export.")
            return 2
        message = args.message or (
            f"CSCM Tool {version} - first release of the team repository\n\n"
            f"{branding.LONG_NAME}. The state of the development repository at {args.tag}."
        )
        export(tree, args.out, args.tag, args.author, message)
        print(f"Exported: {args.out} (one commit on main, tag {args.tag})")
    if args.push:
        if not (args.remote and args.yes):
            print("A push needs --remote <address> and --yes; nothing was pushed.")
            return 2
        git("remote", "add", "team", args.remote, cwd=args.out)
        git("push", "team", "main", cwd=args.out)
        git("push", "team", args.tag, cwd=args.out)
        print(f"Pushed main and {args.tag} to {args.remote}")
    else:
        print("Not pushed. To push: add --remote <address> --push --yes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
