import re
import os
from typing import Tuple

# ── Patterns to detect ────────────────────────────────────

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"disregard.*instructions",
    r"you are now",
    r"act as",
    r"pretend you are",
    r"forget.*told",
    r"new personality",
    r"override.*system",
    r"bypass.*filter",
    r"jailbreak",
    r"dan mode",
    r"developer mode",
    r"sudo mode",
    r"\{\{.*\}\}",       # template injection
    r"<\|.*\|>",         # special tokens
    r"system:",          # fake system prompts
    r"assistant:",       # role injection
]

SECRET_PATTERNS = [
    r"sk-ant-[a-zA-Z0-9\-_]{20,}",           # Anthropic key
    r"AKIA[0-9A-Z]{16}",                       # AWS access key
    r"github_pat_[a-zA-Z0-9_]{20,}",           # GitHub PAT
    r"ghp_[a-zA-Z0-9]{36}",                    # GitHub token
    r"-----BEGIN.*PRIVATE KEY-----",           # Private key
    r"password\s*=\s*['\"][^'\"]{8,}['\"]",   # Hardcoded password
    r"secret\s*=\s*['\"][^'\"]{8,}['\"]",     # Hardcoded secret
    r"api_key\s*=\s*['\"][^'\"]{8,}['\"]",    # Hardcoded API key
    r"token\s*=\s*['\"][^'\"]{20,}['\"]",     # Hardcoded token
]

MALICIOUS_REPO_PATTERNS = [
    r"\.\.",             # path traversal
    r"[/\\]",            # path separators
    r"[<>:\"|?*]",       # invalid chars
    r"^-",               # starts with dash
    r"\.git$",           # ends with .git
    r"(con|prn|aux|nul|com[0-9]|lpt[0-9])$",  # Windows reserved
]

OFF_TOPIC_KEYWORDS = [
    "hack", "crack", "exploit", "malware", "virus",
    "ransomware", "phishing", "ddos", "botnet",
    "steal", "bypass security", "unauthorized access",
    "illegal", "weapon", "drugs"
]

PRODUCT_KEYWORDS = [
    "app", "api", "platform", "system", "tool", "service",
    "website", "dashboard", "portal", "bot", "automation",
    "saas", "web", "mobile", "backend", "frontend",
    "database", "integration", "management", "tracker",
    "builder", "generator", "analyzer", "monitor"
]


# ── Input checks ─────────────────────────────────────────

def check_prompt_injection(text: str) -> Tuple[bool, str]:
    """Returns (is_safe, reason)"""
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return False, f"Prompt injection detected: {pattern}"
    return True, "clean"


def check_off_topic(text: str) -> Tuple[bool, str]:
    """Returns (is_safe, reason)"""
    text_lower = text.lower()

    # Check for malicious intent first
    for keyword in OFF_TOPIC_KEYWORDS:
        if keyword in text_lower:
            return False, f"Malicious intent detected: {keyword}"

    # Check if it's actually about building a product
    has_product_keyword = any(
        kw in text_lower for kw in PRODUCT_KEYWORDS
    )
    if not has_product_keyword and len(text.split()) > 3:
        return False, "Request does not appear to be about building a software product"

    return True, "on topic"


def check_malicious_content(text: str) -> Tuple[bool, str]:
    """Returns (is_safe, reason)"""
    # Check for extremely long inputs (potential DoS)
    if len(text) > 2000:
        return False, "Input too long — maximum 2000 characters"

    # Check for null bytes or control characters
    if "\x00" in text or "\x1a" in text:
        return False, "Input contains invalid control characters"

    return True, "clean"


# ── Output checks ─────────────────────────────────────────

def check_secrets_in_output(text: str) -> Tuple[bool, str]:
    """Returns (is_safe, detected_secret_type)"""
    for pattern in SECRET_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return False, f"Secret detected matching pattern: {pattern[:30]}"
    return True, "clean"


def check_repo_name(name: str) -> Tuple[bool, str]:
    """Returns (is_safe, reason)"""
    for pattern in MALICIOUS_REPO_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            return False, f"Malicious repo name pattern: {pattern}"

    # Must be reasonable length
    if len(name) > 100:
        return False, "Repo name too long"
    if len(name) < 2:
        return False, "Repo name too short"

    # Only allow safe characters
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-_\.]*$', name):
        return False, "Repo name contains unsafe characters"

    return True, "clean"


def scan_code_for_secrets(code: str) -> Tuple[bool, list]:
    """
    Scans generated code for hardcoded secrets.
    Returns (is_clean, list_of_issues)
    """
    issues = []
    lines = code.split("\n")

    for i, line in enumerate(lines, 1):
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                # Skip if it's referencing env vars (safe)
                if "os.getenv" in line or "os.environ" in line:
                    continue
                if "process.env" in line:
                    continue
                issues.append(f"Line {i}: potential secret ({pattern[:20]}...)")

    return len(issues) == 0, issues


# ── Main guard functions ──────────────────────────────────

def guard_input(requirement: str) -> Tuple[bool, str]:
    """
    Run all input checks.
    Returns (is_safe, reason)
    """
    print("[NeMo] Running input guardrails...")

    checks = [
        check_prompt_injection(requirement),
        check_off_topic(requirement),
        check_malicious_content(requirement),
    ]

    for is_safe, reason in checks:
        if not is_safe:
            print(f"  [NeMo] BLOCKED: {reason}")
            return False, reason

    print("  [NeMo] Input passed all checks ✅")
    return True, "clean"


def guard_output(plan: dict, files: dict) -> Tuple[bool, dict]:
    """
    Run all output checks on plan and generated files.
    Returns (is_safe, sanitized_files)
    """
    print("[NeMo] Running output guardrails...")

    # Check repo name
    repo_safe, reason = check_repo_name(plan.get("repo_name", ""))
    if not repo_safe:
        print(f"  [NeMo] BLOCKED repo name: {reason}")
        return False, {}

    # Scan each file for secrets
    clean_files = {}
    blocked = 0

    for path, content in files.items():
        is_clean, issues = scan_code_for_secrets(content)
        if is_clean:
            clean_files[path] = content
        else:
            print(f"  [NeMo] Removed secrets from {path}:")
            for issue in issues:
                print(f"    - {issue}")
            # Remove the problematic lines
            clean_content = sanitize_secrets(content)
            clean_files[path] = clean_content
            blocked += 1

    if blocked > 0:
        print(f"  [NeMo] Sanitized {blocked} files ⚠️")
    else:
        print(f"  [NeMo] All {len(files)} files passed ✅")

    return True, clean_files


def sanitize_secrets(code: str) -> str:
    """Replace hardcoded secrets with env var references"""
    for pattern in SECRET_PATTERNS:
        code = re.sub(
            pattern,
            "os.getenv('SECRET_REDACTED')",
            code,
            flags=re.IGNORECASE
        )
    return code