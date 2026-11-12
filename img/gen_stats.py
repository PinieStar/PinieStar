#!/usr/bin/env python3
"""Buat kartu statistik bertema terminal (SVG) langsung dari GitHub API.
Dijalankan oleh GitHub Actions; hasilnya ditulis ke folder img/.
Pakai: python scripts/gen_stats.py [--offline]
"""
import json, os, sys, urllib.request
from xml.sax.saxutils import escape as esc

USER = os.environ.get("GH_USER", "PinieStar")
TOKEN = os.environ.get("GITHUB_TOKEN")
PINS = []                          # isi nama repo untuk membuat kartu pin
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "img")

MONO = "ui-monospace, SFMono-Regular, 'JetBrains Mono', Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"
BG, PANEL, LINE = "#0d1117", "#161b22", "#30363d"
G, GD, T, C = "#58a6ff", "#8b949e", "#c9d1d9", "#79c0ff"


# ---------- API ----------
def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "stats-card",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def graphql(query):
    req = urllib.request.Request("https://api.github.com/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "stats-card"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    u = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner")
    own = [r for r in repos if not r["fork"]]
    langs = {}
    for r in own:
        try:
            for k, v in api(f"/repos/{USER}/{r['name']}/languages").items():
                langs[k] = langs.get(k, 0) + v
        except Exception:
            pass
    data = {
        "repos": u["public_repos"], "followers": u["followers"], "following": u["following"],
        "stars": sum(r["stargazers_count"] for r in own), "forks": sum(r["forks_count"] for r in own),
        "commits": None, "prs": None, "issues": None,
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
        "pins": {r["name"]: r for r in repos if r["name"] in PINS},
    }
    if TOKEN:
        try:
            cc = graphql('{user(login:"%s"){contributionsCollection{totalCommitContributions '
                         'totalPullRequestContributions totalIssueContributions}}}' % USER)
            cc = cc["data"]["user"]["contributionsCollection"]
            data["commits"], data["prs"], data["issues"] = (cc["totalCommitContributions"],
                                                            cc["totalPullRequestContributions"],
                                                            cc["totalIssueContributions"])
        except Exception:
            pass
    return data


def offline():
    """Data awal sementara; diganti data asli saat workflow pertama berjalan."""
    return {"repos": 5, "followers": 4, "following": 6, "stars": None, "forks": None,
            "commits": None, "prs": None, "issues": None, "langs": [("Shell", 1)],
            "pins": {}}


# ---------- SVG helper ----------
def wrap(w, h, body, label):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}" font-family="{MONO}">
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" fill-opacity="0.07"/></pattern>
<clipPath id="round"><rect width="{w}" height="{h}" rx="12"/></clipPath></defs>
<g clip-path="url(#round)"><rect width="{w}" height="{h}" fill="{BG}"/>{body}<rect width="{w}" height="{h}" fill="url(#scan)"/></g>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="12" fill="none" stroke="{LINE}"/></svg>'''


def titlebar(w, title):
    return (f'<rect width="{w}" height="34" fill="{PANEL}"/><line x1="0" y1="34" x2="{w}" y2="34" stroke="{LINE}"/>'
            f'<circle cx="22" cy="17" r="5" fill="#ff5f56"/><circle cx="40" cy="17" r="5" fill="#ffbd2e"/><circle cx="58" cy="17" r="5" fill="#27c93f"/>'
            f'<text x="{w//2}" y="22" text-anchor="middle" font-size="13" fill="{GD}">{esc(title)}</text>')


def t(x, y, s, fill=T, size=15, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" xml:space="preserve" style="white-space:pre" {extra}>{esc(s)}</text>'


def prompt(x, y, cmd, cursor=False, size=15):
    cur = (f'<tspan fill="{G}">█<animate attributeName="fill" values="{G};{G};{BG};{BG}" keyTimes="0;0.5;0.5;1" '
           f'dur="1.1s" repeatCount="indefinite"/></tspan>') if cursor else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" xml:space="preserve" style="white-space:pre">'
            f'<tspan fill="{G}" font-weight="700">root@piniestar</tspan><tspan fill="{C}">:~# </tspan>'
            f'<tspan fill="{T}">{esc(cmd)}</tspan>{cur}</text>')


def fmt(v):
    return "-" if v is None else f"{v:,}"


# ---------- kartu ----------
def stats_card(d):
    rows = [("repos", d["repos"]), ("followers", d["followers"]), ("following", d["following"]),
            ("stars", d["stars"]), ("commits_this_year", d["commits"]), ("pull_requests", d["prs"]),
            ("issues", d["issues"])]
    rows = [(k, v) for k, v in rows if v is not None]
    h = 34 + 24 + 30 + len(rows) * 28 + 70
    b = titlebar(1200, "stats.json") + prompt(30, 74, f"gh api users/{USER} --jq .stats")
    b += t(30, 108, "{", GD)
    for i, (k, v) in enumerate(rows):
        y = 136 + i * 28
        b += t(60, y, f'"{k}"', G) + t(290, y, ":", GD) + t(310, y, fmt(v) + ("," if i < len(rows) - 1 else ""), C)
    y = 136 + len(rows) * 28
    b += t(30, y, "}", GD) + prompt(30, y + 34, "", cursor=True)
    return wrap(1200, h, b, "GitHub stats: " + ", ".join(f"{k} {v}" for k, v in rows)), "stats-card.svg"


def langs_card(d):
    langs = d["langs"][:6]
    total = sum(v for _, v in langs) or 1
    h = 34 + 24 + 30 + len(langs) * 30 + 70
    b = titlebar(1200, "languages.log") + prompt(30, 74, "linguist --top")
    for i, (name, v) in enumerate(langs):
        y = 114 + i * 30
        pct = v * 100 / total
        b += t(30, y, name, C) + f'<rect x="200" y="{y-12}" width="800" height="12" rx="2" fill="{LINE}"/>'
        b += f'<rect x="200" y="{y-12}" width="{max(4, 800*pct/100):.0f}" height="12" rx="2" fill="{G}"/>'
        b += t(1020, y, f"{pct:.1f}%", T)
    y = 114 + len(langs) * 30 + 12
    b += prompt(30, y + 10, "", cursor=True)
    return wrap(1200, h, b, "Top languages: " + ", ".join(n for n, _ in langs)), "langs-card.svg"


def pin_card(r):
    h = 34 + 24 + 30 + 4 * 28 + 70
    desc = r.get("description") or "(no description)"
    b = titlebar(1200, r["name"]) + prompt(30, 74, f"gh repo view {USER}/{r['name']}")
    items = [("name", r["name"], G), ("about", desc, T), ("language", r.get("language") or "-", C),
             ("stars / forks", f"{fmt(r.get('stargazers_count'))} / {fmt(r.get('forks_count'))}", C)]
    for i, (k, v, col) in enumerate(items):
        y = 114 + i * 28
        b += t(30, y, k, GD) + t(220, y, v, col)
    b += prompt(30, 114 + 4 * 28 + 22, "", cursor=True)
    return wrap(1200, h, b, f"repo {r['name']}: {desc}"), f"pin-{r['name']}.svg"


def main():
    d = offline() if "--offline" in sys.argv else collect()
    os.makedirs(OUT, exist_ok=True)
    cards = [stats_card(d), langs_card(d)] + [pin_card(r) for r in d["pins"].values()]
    for svg, name in cards:
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print("wrote", name)


if __name__ == "__main__":
    main()
