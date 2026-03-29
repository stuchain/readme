#!/usr/bin/env python3
"""Rewrite <!-- FEATURED-REPOS:START --> ... END in README.md from GitHub API."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

# shields.io simple-icons slugs for common GitHub language names
LANG_SHIELDS: dict[str, tuple[str, str]] = {
    "Python": ("3776AB", "python"),
    "Rust": ("000000", "rust"),
    "TypeScript": ("3178C6", "typescript"),
    "JavaScript": ("F7DF1E", "javascript"),
    "Java": ("ED8B00", "java"),
    "Go": ("00ADD8", "go"),
    "C++": ("00599C", "cplusplus"),
    "C": ("555555", "c"),
    "Solidity": ("363636", "solidity"),
    "Shell": ("4EAA25", "gnubash"),
    "PowerShell": ("5391FE", "powershell"),
    "HTML": ("E34F26", "html5"),
    "CSS": ("1572B6", "css3"),
    "Ruby": ("CC342D", "ruby"),
    "PHP": ("777BB4", "php"),
    "Swift": ("FA7343", "swift"),
    "Kotlin": ("7F52FF", "kotlin"),
    "Dart": ("0175C2", "dart"),
}


def http_get_json(url: str, token: str | None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "readme-featured-generator",
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


def language_badge(lang: str | None) -> str:
    if not lang:
        return ""
    if lang in LANG_SHIELDS:
        color, logo = LANG_SHIELDS[lang]
        enc = urllib.parse.quote(lang.replace("-", "--"))
        return (
            f'<img src="https://img.shields.io/badge/{enc}-{color}'
            f'?style=flat-square&logo={logo}&logoColor=white&labelColor=1a1b27" alt="{lang}" />'
        )
    enc = urllib.parse.quote(lang.replace("-", "--"))
    return (
        f'<img src="https://img.shields.io/badge/{enc}-64748b?style=flat-square&labelColor=1a1b27" alt="{lang}" />'
    )


def topic_badge(topic: str) -> str:
    # shields: escape hyphens in label as --
    label = urllib.parse.quote(topic.replace("-", "--"), safe="")
    return (
        f'<img src="https://img.shields.io/badge/{label}-8b5cf6?style=flat-square&labelColor=1a1b27" '
        f'alt="topic: {topic}" />'
    )


def sanitize_description(text: str | None, limit: int = 320) -> str:
    if not text:
        return "*No description yet.*"
    one = " ".join(text.split())
    if len(one) > limit:
        one = one[: limit - 1].rsplit(" ", 1)[0] + "…"
    return one


def render_repo(owner: str, r: dict, max_topics: int) -> str:
    name = r["name"]
    url = r["html_url"]
    stars = r["stargazers_count"]
    lang = r.get("language")
    topics = r.get("topics") or []
    desc = sanitize_description(r.get("description"))

    star_shield = (
        f"https://img.shields.io/github/stars/{owner}/{name}"
        f"?style=flat-square&logo=github&label=stars&labelColor=1a1b27&color=3fb950"
    )

    parts = [
        f"### [{name}]({url})",
        "",
        '<p align="left">',
        f'  <a href="{url}"><img src="{star_shield}" alt="GitHub stars" /></a>',
    ]
    if lang:
        parts.append(f"  {language_badge(lang)}")
    for t in topics[:max_topics]:
        parts.append(f"  {topic_badge(t)}")
    parts.extend(["</p>", "", desc, "", "---", ""])
    return "\n".join(parts)


def main() -> int:
    user = os.environ.get("GITHUB_USER", "stuchain")
    exclude = {
        x.strip().lower()
        for x in os.environ.get("EXCLUDE_REPOS", "readme,portfolio").split(",")
        if x.strip()
    }
    max_repos = int(os.environ.get("MAX_FEATURED", "6"))
    max_topics = int(os.environ.get("MAX_TOPICS", "3"))
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    try:
        repos = fetch_all_repos(user, token)
    except urllib.error.HTTPError as e:
        print(f"GitHub API error: {e}", file=sys.stderr)
        return 1

    filtered = []
    for r in repos:
        if r.get("fork"):
            continue
        if r.get("archived"):
            continue
        if r.get("name", "").lower() in exclude:
            continue
        if r.get("private"):
            continue
        filtered.append(r)

    filtered.sort(key=lambda x: (-(x.get("stargazers_count") or 0), x.get("pushed_at") or ""))
    picked = filtered[:max_repos]

    if not picked:
        body = "\n*No public repositories matched the filters.*\n"
    else:
        body = "\n".join(render_repo(user, r, max_topics) for r in picked).rstrip() + "\n"

    block = f"<!-- FEATURED-REPOS:START -->\n{body}<!-- FEATURED-REPOS:END -->"

    with open(README, encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!-- FEATURED-REPOS:START -->.*?<!-- FEATURED-REPOS:END -->"
    if not re.search(pattern, content, flags=re.DOTALL):
        print("README.md: markers <!-- FEATURED-REPOS:START/END --> not found", file=sys.stderr)
        return 1

    new_content = re.sub(pattern, block, content, count=1, flags=re.DOTALL)
    with open(README, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated Featured section with {len(picked)} repo(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
