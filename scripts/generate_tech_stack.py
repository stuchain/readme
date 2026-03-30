#!/usr/bin/env python3
"""Rewrite the tech stack block in README.md from GitHub API + curated groups."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

LANG_SHIELDS: dict[str, tuple[str, str, str]] = {
    "Python": ("3776AB", "python", "https://www.python.org/"),
    "Rust": ("000000", "rust", "https://www.rust-lang.org/"),
    "TypeScript": ("3178C6", "typescript", "https://www.typescriptlang.org/"),
    "JavaScript": ("F7DF1E", "javascript", "https://developer.mozilla.org/docs/Web/JavaScript"),
    "Solidity": ("363636", "solidity", "https://soliditylang.org/"),
    "Go": ("00ADD8", "go", "https://go.dev/"),
    "Java": ("ED8B00", "java", "https://www.java.com/"),
    "Shell": ("4EAA25", "gnubash", "https://www.gnu.org/software/bash/"),
    "PowerShell": ("5391FE", "powershell", "https://learn.microsoft.com/powershell/"),
    "HTML": ("E34F26", "html5", "https://developer.mozilla.org/docs/Web/HTML"),
    "CSS": ("1572B6", "css3", "https://developer.mozilla.org/docs/Web/CSS"),
}

STATIC_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "Web &amp; UI",
        [
            '<a href="https://react.dev/"><img src="https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB&labelColor=1a1b27" alt="React" /></a>',
            '<a href="https://nextjs.org/"><img src="https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white&labelColor=1a1b27" alt="Next.js" /></a>',
            '<a href="https://streamlit.io/"><img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white&labelColor=1a1b27" alt="Streamlit" /></a>',
            '<img src="https://img.shields.io/badge/HTML%2FCSS-7aa2f7?style=flat-square&labelColor=1a1b27" alt="HTML/CSS" />',
        ],
    ),
    (
        "Backend &amp; data",
        [
            '<img src="https://img.shields.io/badge/Rust%20(axum%2C%20tokio)-7aa2f7?style=flat-square&logo=rust&logoColor=white&labelColor=1a1b27" alt="Rust axum tokio" />',
            '<img src="https://img.shields.io/badge/Python%20services-3776AB?style=flat-square&logo=python&logoColor=white&labelColor=1a1b27" alt="Python services" />',
            '<a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/SQLite%20(sqlx)-003B57?style=flat-square&logo=sqlite&logoColor=white&labelColor=1a1b27" alt="SQLite sqlx" /></a>',
            '<img src="https://img.shields.io/badge/MQTT%20pipelines-7aa2f7?style=flat-square&labelColor=1a1b27" alt="MQTT" />',
        ],
    ),
    (
        "Chain &amp; security",
        [
            '<img src="https://img.shields.io/badge/Hardhat-F7DF1E?style=flat-square&labelColor=1a1b27" alt="Hardhat" />',
            '<a href="https://soliditylang.org/"><img src="https://img.shields.io/badge/Solidity-363636?style=flat-square&logo=solidity&logoColor=white&labelColor=1a1b27" alt="Solidity" /></a>',
            '<img src="https://img.shields.io/badge/Local%20chains-7aa2f7?style=flat-square&labelColor=1a1b27" alt="Local chains" />',
            '<a href="https://solana.com/"><img src="https://img.shields.io/badge/Solana%20demos-9945FF?style=flat-square&logo=solana&logoColor=white&labelColor=1a1b27" alt="Solana" /></a>',
            '<img src="https://img.shields.io/badge/Crypto%20%26%20protocols-7aa2f7?style=flat-square&labelColor=1a1b27" alt="Cryptography" />',
        ],
    ),
    (
        "DevOps",
        [
            '<a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white&labelColor=1a1b27" alt="Docker" /></a>',
            '<a href="https://github.com/features/actions"><img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white&labelColor=1a1b27" alt="GitHub Actions" /></a>',
            '<img src="https://img.shields.io/badge/PowerShell-5391FE?style=flat-square&logo=powershell&logoColor=white&labelColor=1a1b27" alt="PowerShell" />',
            '<img src="https://img.shields.io/badge/bash-4EAA25?style=flat-square&logo=gnubash&logoColor=white&labelColor=1a1b27" alt="bash" />',
        ],
    ),
]


def http_get_json(url: str, token: str | None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "readme-tech-stack-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_all_repos(user: str, token: str | None) -> list[dict]:
    page = 1
    out: list[dict] = []
    while True:
        url = f"https://api.github.com/users/{urllib.parse.quote(user)}/repos?per_page=100&page={page}&sort=updated&type=owner"
        batch = http_get_json(url, token)
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


def aggregate_languages(repos: list[dict], token: str | None) -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in repos:
        lang_url = repo.get("languages_url")
        if not lang_url:
            continue
        try:
            langs = http_get_json(lang_url, token)
        except Exception:
            continue
        if not isinstance(langs, dict):
            continue
        for lang, bytes_count in langs.items():
            totals[lang] = totals.get(lang, 0) + int(bytes_count or 0)
    return totals


def language_badge(lang: str) -> str:
    enc = urllib.parse.quote(lang.replace("-", "--"))
    if lang in LANG_SHIELDS:
        color, logo, href = LANG_SHIELDS[lang]
        badge = (
            f"https://img.shields.io/badge/{enc}-{color}"
            f"?style=flat-square&logo={logo}&logoColor=white&labelColor=1a1b27"
        )
        return f'<a href="{href}"><img src="{badge}" alt="{lang}" /></a>'
    badge = f"https://img.shields.io/badge/{enc}-64748b?style=flat-square&labelColor=1a1b27"
    return f'<img src="{badge}" alt="{lang}" />'


def render_section(title: str, badges: list[str]) -> str:
    lines = ['<p align="center">', f"  <strong>{title}</strong><br />"]
    lines.extend(f"  {b}" for b in badges)
    lines.append("</p>")
    return "\n".join(lines)


def main() -> int:
    user = os.environ.get("GITHUB_USER", "stuchain")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    exclude = {
        x.strip().lower()
        for x in os.environ.get("EXCLUDE_REPOS", "readme,portfolio").split(",")
        if x.strip()
    }
    max_langs = int(os.environ.get("MAX_TECH_LANGS", "8"))

    repos = fetch_all_repos(user, token)
    filtered = [
        r
        for r in repos
        if not r.get("fork")
        and not r.get("archived")
        and not r.get("private")
        and r.get("name", "").lower() not in exclude
    ]

    totals = aggregate_languages(filtered, token)
    sorted_langs = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    lang_badges = [language_badge(lang) for lang, _ in sorted_langs[:max_langs]]
    if not lang_badges:
        lang_badges = [
            language_badge("Python"),
            language_badge("Rust"),
            language_badge("TypeScript"),
            language_badge("JavaScript"),
            language_badge("Solidity"),
        ]

    blocks = [render_section("Languages", lang_badges)]
    for title, badges in STATIC_SECTIONS:
        blocks.append(render_section(title, badges))
    body = "\n".join(blocks) + "\n"

    pattern = r"<!-- TECH-STACK:START -->.*?<!-- TECH-STACK:END -->"
    with open(README, encoding="utf-8") as f:
        content = f.read()

    replacement = f"<!-- TECH-STACK:START -->\n{body}<!-- TECH-STACK:END -->"
    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    else:
        print("README.md: TECH-STACK markers not found", file=sys.stderr)
        return 1

    with open(README, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Updated Tech stack section.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

