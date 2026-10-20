"""Static AST & pattern security scanner across 6 threat families."""

from __future__ import annotations

import re

THREAT_FAMILIES = {
    "exfiltration": [
        re.compile(
            r"(?i)\b(?:curl|wget|fetch)\b.*(?:\|\s*(?:bash|sh|pwsh|powershell)|--upload-file|-T\s+|-d\s+@)"
        ),
        re.compile(r"(?i)\b(?:nc|ncat|netcat)\b.*-[le]"),
        re.compile(r"/dev/tcp/\d+\.\d+\.\d+\.\d+/\d+"),
    ],
    "injection": [
        re.compile(r"(?i)\bignore\s+(?:all\s+|any\s+)?previous\s+instructions\b"),
        re.compile(r"(?i)\bsystem\s+prompt\s+override\b"),
        re.compile(
            r"(?i)\bdisregard\s+(?:all\s+|any\s+)?(?:prior|previous)\s+(?:guidelines|instructions)\b"
        ),
    ],
    "destructive": [
        re.compile(r"(?i)\brm\s+-(?:rf|fr)\s+(?:/|~|\$HOME|\*\s*$)"),
        re.compile(r"(?i)\bdel\s+/[sfq]\s+[a-z]:\\"),
        re.compile(r"(?i)\bmkfs(?:\.\w+)?\b"),
        re.compile(r"(?i)\bdd\s+if=.*of=/dev/[sh]d[a-z]"),
    ],
    "persistence": [
        re.compile(r"(?i)\bcrontab\b"),
        re.compile(r"(?i)\b(?:~/\.(?:bashrc|zshrc|profile)|/etc/cron)"),
        re.compile(r"(?i)\b(?:systemctl\s+enable|launchctl\s+load)\b"),
    ],
    "network": [
        re.compile(r"(?i)\b(?:ngrok|localtunnel|cloudflared)\b"),
        re.compile(r"(?i)\b(?:ssh\s+-R|reverse\s+tunnel)\b"),
    ],
    "obfuscation": [
        re.compile(r"(?i)\b(?:base64\s+-d|base64\s+--decode)\s*\|\s*(?:bash|sh|pwsh)"),
        re.compile(
            r"(?i)\b(?:eval|exec)\s*\(\s*(?:base64\.|bytes\.fromhex|__import__)"
        ),
    ],
}


def scan(text: str) -> list[dict[str, str]]:
    """Scan text across all 6 threat families and return list of violation records."""
    violations: list[dict[str, str]] = []
    lines = text.splitlines()

    for family, patterns in THREAT_FAMILIES.items():
        for pat in patterns:
            for idx, line in enumerate(lines):
                m = pat.search(line)
                if m:
                    violations.append(
                        {
                            "family": family,
                            "line": str(idx + 1),
                            "snippet": line.strip()[:100],
                        }
                    )
    return violations
