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


def fetch_repo_languages(repo: dict, token: str | None) -> list[str]:
    """
    Return all languages for a repo, sorted by bytes desc.
    Falls back to the repo's primary language when the API has no data.
    """
    url = repo.get("languages_url")
    primary = repo.get("language")
    if not url:
        return [primary] if primary else []
    try:
        data = http_get_json(url, token)
    except urllib.error.HTTPError:
        return [primary] if primary else []
    if not isinstance(data, dict) or not data:
        return [primary] if primary else []

    ordered = sorted(data.items(), key=lambda kv: kv[1], reverse=True)
    names = [name for name, _ in ordered]
    if not names and primary:
        return [primary]
    return names


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


def repo_badges_p(owner: str, r: dict, max_topics: int) -> str:
    """
    Shared badges block for the featured layouts (stars + language + topic badges).
    """
    url = r["html_url"]
    name = r["name"]
    lang = r.get("language")
    topics = r.get("topics") or []

    star_shield = (
        f"https://img.shields.io/github/stars/{owner}/{name}"
        f"?style=flat-square&logo=github&label=stars&labelColor=1a1b27&color=3fb950"
    )

    parts = ['<p align="left">', f'  <a href="{url}"><img src="{star_shield}" alt="GitHub stars" /></a>']
    if lang:
        parts.append(f"  {language_badge(lang)}")
    for t in topics[:max_topics]:
        parts.append(f"  {topic_badge(t)}")
    parts.append("</p>")
    return "\n".join(parts)


def render_repo_option2_cell(owner: str, r: dict, max_topics: int) -> str:
    name = r["name"]
    url = r["html_url"]
    stars = r.get("stargazers_count") or 0
    desc = sanitize_description(r.get("description"))
    topics = r.get("topics") or []
    all_langs = r.get("_all_languages") or []

    tech_parts: list[str] = []
    if all_langs:
        tech_parts = ['<p align="left">']
        for lang in all_langs:
            tech_parts.append(f"  {language_badge(lang)}")
        tech_parts.append("</p>")

    tags_parts: list[str] = []
    if topics[:max_topics]:
        tags_parts = ['<p align="left">', '  <strong>Tags:</strong>']
        for t in topics[:max_topics]:
            tags_parts.append(f"  {topic_badge(t)}")
        tags_parts.append("</p>")

    return "\n".join(
        [
            f'<p><strong><a href="{url}">{name}</a></strong> <strong>★ {stars}</strong></p>',
            *(tech_parts if tech_parts else []),
            "",
            desc,
            "",
            *(tags_parts if tags_parts else []),
        ]
    )


def render_option2(owner: str, picked: list[dict], max_topics: int) -> str:
    if not picked:
        return "\n*No public repositories matched the filters.*\n"

    out = ['<table width="100%">']
    last = len(picked) - 1
    for i, r in enumerate(picked):
        if i % 2 == 0:
            out.append("<tr>")
        out.append(f'<td width="50%" valign="top">')
        out.append(render_repo_option2_cell(owner, r, max_topics))
        out.append("</td>")
        if i % 2 == 1 or i == last:
            out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def render_option3(owner: str, picked: list[dict], max_topics: int) -> str:
    if not picked:
        return "\n*No public repositories matched the filters.*\n"

    out = ["<ul>"]
    for r in picked:
        name = r["name"]
        url = r["html_url"]
        lang = r.get("language")
        topics = r.get("topics") or []
        desc = sanitize_description(r.get("description"))

        star_shield = (
            f"https://img.shields.io/github/stars/{owner}/{name}"
            f"?style=flat-square&logo=github&label=stars&labelColor=1a1b27&color=3fb950"
        )

        pieces: list[str] = []
        pieces.append(f"<strong><a href=\"{url}\">{name}</a></strong>")
        pieces.append("<br />")
        pieces.append(f'<a href="{url}"><img src="{star_shield}" alt="GitHub stars" /></a>')
        if lang:
            pieces.append(language_badge(lang))
        for t in topics[:max_topics]:
            pieces.append(topic_badge(t))
        pieces.append("<br />")
        pieces.append(desc)

        out.append(f"<li>{''.join(pieces)}</li>")
    out.append("</ul>")
    return "\n".join(out)


def render_option4(owner: str, picked: list[dict], max_topics: int) -> str:
    if not picked:
        return "\n*No public repositories matched the filters.*\n"

    out = [
        '<table width="100%">',
        "<tr>",
        '<td valign="top" width="26%"><strong>Repo</strong></td>',
        '<td valign="top" width="34%"><strong>Tech</strong></td>',
        '<td valign="top"><strong>Summary</strong></td>',
        "</tr>",
    ]

    for r in picked:
        name = r["name"]
        url = r["html_url"]
        lang = r.get("language")
        topics = r.get("topics") or []
        desc = sanitize_description(r.get("description"))

        star_shield = (
            f"https://img.shields.io/github/stars/{owner}/{name}"
            f"?style=flat-square&logo=github&label=stars&labelColor=1a1b27&color=3fb950"
        )

        tech_parts: list[str] = []
        tech_parts.append(f'<a href="{url}"><img src="{star_shield}" alt="GitHub stars" /></a>')
        if lang:
            tech_parts.append(language_badge(lang))
        for t in topics[:max_topics]:
            tech_parts.append(topic_badge(t))

        out.extend(
            [
                "<tr>",
                f'<td valign="top"><strong><a href="{url}">{name}</a></strong></td>',
                f'<td valign="top">{"".join(tech_parts)}</td>',
                f"<td valign=\"top\">{desc}</td>",
                "</tr>",
            ]
        )

    out.append("</table>")
    return "\n".join(out)


def main() -> int:
    user = os.environ.get("GITHUB_USER", "stuchain")
    exclude = {
        x.strip().lower()
        for x in os.environ.get("EXCLUDE_REPOS", "readme,portfolio").split(",")
        if x.strip()
    }
    max_featured_raw = os.environ.get("MAX_FEATURED", "6").strip().lower()
    # Support selecting all repos to keep README fully in sync.
    # MAX_FEATURED="all" (or 0/-1/none) means "no limit".
    if max_featured_raw in {"all", "inf", "infinity", "none", "0", "-1"}:
        max_repos: int | None = None
    else:
        max_repos = int(max_featured_raw)
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
    picked = filtered if max_repos is None else filtered[:max_repos]
    for repo in picked:
        repo["_all_languages"] = fetch_repo_languages(repo, token)

    if not picked:
        body_option1 = "\n*No public repositories matched the filters.*\n"
        body_option2 = body_option1
        body_option3 = body_option1
        body_option4 = body_option1
    else:
        body_option1 = "\n".join(render_repo(user, r, max_topics) for r in picked).rstrip() + "\n"
        body_option2 = render_option2(user, picked, max_topics).rstrip() + "\n"
        body_option3 = render_option3(user, picked, max_topics).rstrip() + "\n"
        body_option4 = render_option4(user, picked, max_topics).rstrip() + "\n"

    def wrap_marker(option: str, body: str) -> str:
        return f"<!-- FEATURED-OPTION{option}:START -->\n{body}<!-- FEATURED-OPTION{option}:END -->"

    block_option1 = wrap_marker("1", body_option1)
    block_option2 = wrap_marker("2", body_option2)
    block_option3 = wrap_marker("3", body_option3)
    block_option4 = wrap_marker("4", body_option4)

    with open(README, encoding="utf-8") as f:
        content = f.read()

    option_pattern = r"<!-- FEATURED-OPTION{n}:START -->.*?<!-- FEATURED-OPTION{n}:END -->"
    old_pattern = r"<!-- FEATURED-REPOS:START -->.*?<!-- FEATURED-REPOS:END -->"

    def has_marker(n: str) -> bool:
        return re.search(option_pattern.format(n=n), content, flags=re.DOTALL) is not None

    option_blocks = {
        "1": block_option1,
        "2": block_option2,
        "3": block_option3,
        "4": block_option4,
    }

    option_present = {str(n): has_marker(str(n)) for n in (1, 2, 3, 4)}

    # New scheme (preferred): 4 separate marker blocks (OPTION1..OPTION4).
    # We replace only the marker blocks that actually exist in the README, so you can
    # keep a single option (e.g. only OPTION2) without breaking regeneration.
    if any(option_present.values()):
        new_content = content
        for n in ("1", "2", "3", "4"):
            if option_present[n]:
                new_content = re.sub(
                    option_pattern.format(n=n),
                    option_blocks[n],
                    new_content,
                    count=1,
                    flags=re.DOTALL,
                )
    # Backward compatible scheme: single FEATURED-REPOS marker (writes Option 1 only).
    elif re.search(old_pattern, content, flags=re.DOTALL) is not None:
        new_content = re.sub(
            old_pattern,
            f"<!-- FEATURED-REPOS:START -->\n{body_option1}<!-- FEATURED-REPOS:END -->",
            content,
            count=1,
            flags=re.DOTALL,
        )
    else:
        print(
            "README.md: markers <!-- FEATURED-OPTION1..4:START/END --> or FEATURED-REPOS:START/END not found",
            file=sys.stderr,
        )
        return 1

    with open(README, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated Featured section with {len(picked)} repo(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
