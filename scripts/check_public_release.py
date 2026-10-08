"""Read-only public-release gate; prints paths/reason codes, never matched values.

Default mode reads four named Secret Manager versions directly into memory and
compares all Git-tracked and nonignored untracked files. Ignored local artifacts
are used only as private-value fingerprints; they are not upload candidates.
No file, GitHub, credential, cloud or customer writes occur. --source-only is for
offline CI and explicitly does not certify a secret-verified public release.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import quote

PROJECT = "ai-leadscore"
SECRET_NAMES = ("OPENAI_API_KEY", "PROSPECTIQ_ADMIN_KEY", "PROSPECTIQ_DB_PASSWORD", "FIREWIRE_GHL_API_KEY")
MAX_BYTES = 32 * 1024 * 1024
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?![\w.-])")
PHONE = re.compile(r"(?<!\w)(?:\+1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\w)|\+[1-9]\d{7,14}(?!\d)")
CAPABILITY = re.compile(r"/p(?:\?[^\s\"'<>#]*)?#([A-Za-z0-9_-]{24,})(?![A-Za-z0-9_-])")
TEAMS = re.compile(r"https?://(?:teams\.microsoft\.com|teams\.live\.com|teams\.cloud\.microsoft)/[^\s\"'<>]+", re.I)
PATTERNS = {
    "PROVIDER_KEY_SHAPE": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b|\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "JWT_CREDENTIAL_SHAPE": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "PRIVATE_KEY_MATERIAL": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "MEETING_PASSCODE": re.compile(r"(?i)(?:passcode|meeting[_ -]?password)[\"']?\s*[=:]\s*[\"']?([A-Za-z0-9_-]{5,})"),
}
SAFE_DOMAINS = {"example.com", "example.org", "example.net", "example.test", "localhost"}
SAFE_PUBLIC_EMAILS = {"info@firewireads.com", "support@firewireads.com", "privacy@firewireads.com"}


class AuditError(RuntimeError):
    pass


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False, timeout=30)
    if result.returncode:
        raise AuditError("Git inventory failed; output omitted")
    return result.stdout


def inventory(root):
    declared_root = Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if declared_root != root.resolve():
        raise AuditError("Run against the dedicated ProspectIQ Git repository root")
    candidates = sorted(set(git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
                            .decode("utf-8").split("\0")) - {""})
    ignored = [value for value in git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard")
               .decode("utf-8").split("\0") if value]
    return candidates, ignored


def safe_email(value, allowed):
    lower = value.lower()
    domain = lower.rsplit("@", 1)[-1]
    return (domain in SAFE_DOMAINS or domain.endswith(".example") or domain.endswith(".test")
            or domain.endswith(".gserviceaccount.com") or lower in SAFE_PUBLIC_EMAILS or lower in allowed)


def safe_phone(value, allowed):
    digits = re.sub(r"\D", "", value)
    nanp = digits[1:] if len(digits) == 11 and digits.startswith("1") else digits
    # NANP's reserved fictional 555-0100..0199 range, not all 555 exchanges.
    return (len(nanp) == 10 and nanp[3:8] == "55501") or digits in allowed


def nonpublic_emails(content, allowed):
    for match in EMAIL.finditer(content):
        value = match.group()
        # URL-validation tests use literal dummy userinfo, not a recipient address.
        if value.split("@", 1)[0] in {"pass", "password"} and content[max(0, match.start() - 5):match.start()] == "user:":
            continue
        if not safe_email(value, allowed):
            yield value


def safe_capability(value):
    # Obvious repeated-character test fixtures have no real access capability.
    return len(set(value)) == 1 or value in {"secret-access-token", "synthetic-example-token"}


def private_fingerprints(root, ignored, allowed_emails, allowed_phones):
    values = set()
    for relative in ignored:
        if not relative.replace("\\", "/").startswith("artifacts/"):
            continue
        path = root / relative
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        content = path.read_bytes().decode("utf-8", errors="ignore")
        values.update(nonpublic_emails(content, allowed_emails))
        values.update(value for value in PHONE.findall(content) if not safe_phone(value, allowed_phones))
        values.update(value for value in CAPABILITY.findall(content) if not safe_capability(value))
        values.update(TEAMS.findall(content))
        values.update(PATTERNS["MEETING_PASSCODE"].findall(content))
    return values


def secret_fingerprints():
    import google.auth
    from google.cloud import secretmanager

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    client = secretmanager.SecretManagerServiceClient(credentials=credentials)
    values = set()
    for name in SECRET_NAMES:
        payload = client.access_secret_version(name=f"projects/{PROJECT}/secrets/{name}/versions/latest",
                                               timeout=30).payload.data
        if len(payload) < 8:
            raise AuditError("Named credential is too short for a safe exact-value audit")
        values.add(payload)
        values.add(base64.b64encode(payload))
        decoded = payload.decode("utf-8")
        values.add(quote(decoded, safe="").encode())
        values.add(json.dumps(decoded)[1:-1].encode())
    return values


def audit(root, *, source_only=False, public_emails=(), public_phones=()):
    candidates, ignored = inventory(root)
    allowed_emails = {value.lower() for value in public_emails}
    allowed_phones = {re.sub(r"\D", "", value) for value in public_phones}
    fingerprints = private_fingerprints(root, ignored, allowed_emails, allowed_phones)
    secrets = set() if source_only else secret_fingerprints()
    findings = []
    scanned = 0
    for relative in candidates:
        path = root / relative
        if not path.exists():  # Tracked deletions have no working-tree content to upload.
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            findings.append({"path": relative, "reason": "SYMLINK_OR_OUTSIDE_ROOT"})
            continue
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            findings.append({"path": relative, "reason": "UNSUPPORTED_OR_OVERSIZE_FILE"})
            continue
        scanned += 1
        raw = path.read_bytes()
        content = raw.decode("utf-8", errors="ignore")
        reasons = set()
        if any(value in raw for value in secrets):
            reasons.add("KNOWN_SECRET_VALUE")
        if any(value.encode() in raw for value in fingerprints):
            reasons.add("KNOWN_PRIVATE_ARTIFACT_VALUE")
        for reason, pattern in PATTERNS.items():
            if pattern.search(content):
                reasons.add(reason)
        if any(nonpublic_emails(content, allowed_emails)):
            reasons.add("NONPUBLIC_EMAIL")
        if any(not safe_phone(value, allowed_phones) for value in PHONE.findall(content)):
            reasons.add("NONPUBLIC_PHONE")
        if any(not safe_capability(value) for value in CAPABILITY.findall(content)):
            reasons.add("PRIVATE_CAPABILITY_URL")
        if TEAMS.search(content):
            reasons.add("PRIVATE_MEETING_URL")
        findings.extend({"path": relative, "reason": reason} for reason in sorted(reasons))
    try:
        version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    except (KeyError, FileNotFoundError, tomllib.TOMLDecodeError):
        version = None
    main = (root / "app" / "main.py").read_text(encoding="utf-8")
    if version != "1.1.0" or not re.search(r'FastAPI\([^\n]+version="1\.1\.0"', main):
        findings.append({"path": "pyproject.toml / app/main.py", "reason": "V1_1_VERSION_MISMATCH"})
    return {"status": "BLOCKED" if findings else "SOURCE_CHECKS_PASSED_SECRET_CHECK_SKIPPED" if source_only
            else "PASS", "files_scanned": scanned, "ignored_files_not_upload_candidates": len(ignored),
            "known_secret_versions_checked": 0 if source_only else len(SECRET_NAMES),
            "private_artifact_fingerprints_checked": len(fingerprints), "source_version": version,
            "findings": findings, "history_scanned": False,
            "scope": "working-tree tracked and nonignored untracked upload candidates"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-only", action="store_true", help="Offline checks only; not a secret-verified release gate")
    parser.add_argument("--allow-public-email", action="append", default=[], help="Exact independently verified public address")
    parser.add_argument("--allow-public-phone", action="append", default=[], help="Exact independently verified public demo number")
    args = parser.parse_args()
    try:
        result = audit(args.root.resolve(), source_only=args.source_only,
                       public_emails=args.allow_public_email, public_phones=args.allow_public_phone)
        print(json.dumps(result))
        return 1 if result["findings"] else 0
    except AuditError as error:
        print(json.dumps({"status": "BLOCKED", "error": str(error)}))
    except Exception as error:
        print(json.dumps({"status": "BLOCKED", "error_type": type(error).__name__, "diagnostics": "omitted"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
