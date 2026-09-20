"""Builds assets/languages.svg: a compact donut chart of your most used languages
plus repository, star and follower counts. Uses only the Python standard library.

Usage:
  python generate_stats.py          # reads GITHUB_TOKEN and USERNAME from the environment
  python generate_stats.py --demo   # sample data, for previewing the design
"""
import json, math, os, sys, urllib.request
from xml.sax.saxutils import escape

OUT = "languages.svg"
EXCLUDE = {"Jupyter Notebook", "HTML"}   # languages hidden from the chart; set() shows everything
TOP_N = 5
PALETTE = ["#4C9AFF", "#2DD4BF", "#F5B942", "#A78BFA", "#F472B6"]
OTHER = "#94A3B8"
TEXT = "#7D8590"          # readable on both light and dark GitHub themes


def api(path, token):
    req = urllib.request.Request("https://api.github.com" + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect(user, token):
    info = api(f"/users/{user}", token)
    repos, page = [], 1
    while True:
        chunk = api(f"/users/{user}/repos?per_page=100&type=owner&page={page}", token)
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    own = [r for r in repos if not r.get("fork")]
    langs = {}
    for r in own:
        for name, size in api(f"/repos/{user}/{r['name']}/languages", token).items():
            if name not in EXCLUDE:
                langs[name] = langs.get(name, 0) + size
    return {
        "repos": info.get("public_repos", len(own)),
        "followers": info.get("followers", 0),
        "stars": sum(r.get("stargazers_count", 0) for r in own),
        "langs": langs,
    }


def render(d):
    total = sum(d["langs"].values())
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])
    top, rest = items[:TOP_N], sum(v for _, v in items[TOP_N:])
    segs = [(n, v, PALETTE[i]) for i, (n, v) in enumerate(top)]
    if rest:
        segs.append(("Other", rest, OTHER))

    cx = cy = 100
    r, sw = 64, 24
    C = 2 * math.pi * r
    rings, legend, start = [], [], 0.0

    rings.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TEXT}" stroke-opacity=".15" stroke-width="{sw}"/>')
    for i, (name, val, col) in enumerate(segs):
        frac = val / total
        gap = 3 if len(segs) > 1 else 0
        length = max(C * frac - gap, 0.5)
        rings.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{col}" stroke-width="{sw}" '
            f'stroke-dasharray="{length:.2f} {C - length:.2f}" stroke-dashoffset="{-start:.2f}" '
            f'transform="rotate(-90 {cx} {cy})">'
            f'<animate attributeName="stroke-dasharray" from="0 {C:.2f}" to="{length:.2f} {C - length:.2f}" dur="1s" fill="freeze"/></circle>')
        start += C * frac
        y = 58 + i * 26
        legend.append(
            f'<rect x="222" y="{y - 10}" width="11" height="11" rx="3" fill="{col}"/>'
            f'<text x="242" y="{y}" fill="{TEXT}" font-size="14">{escape(name)}</text>'
            f'<text x="510" y="{y}" fill="{TEXT}" font-size="14" font-weight="600" text-anchor="end">{100 * frac:.1f}%</text>')
    if not segs:
        legend.append(f'<text x="222" y="70" fill="{TEXT}" font-size="14">Languages appear here once your</text>'
                      f'<text x="222" y="92" fill="{TEXT}" font-size="14">repositories contain code.</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="520" height="200" viewBox="0 0 520 200" role="img" aria-label="Most used languages and repository counts" font-family="'Segoe UI', -apple-system, 'Helvetica Neue', Arial, sans-serif">
  {"".join(rings)}
  <text x="{cx}" y="{cy + 8}" fill="{TEXT}" font-size="32" font-weight="600" text-anchor="middle">{d["repos"]}</text>
  <text x="{cx}" y="{cy + 28}" fill="{TEXT}" font-size="11" text-anchor="middle">repositories</text>
  <text x="222" y="28" fill="{TEXT}" font-size="13" font-weight="600">Most used languages</text>
  {"".join(legend)}
  <text x="222" y="188" fill="{TEXT}" font-size="12">{d["stars"]} stars  ·  {d["followers"]} followers</text>
</svg>
'''


if __name__ == "__main__":
    if "--demo" in sys.argv:
        data = {"repos": 6, "followers": 4, "stars": 3,
                "langs": {"Python": 5800, "R": 3100, "HTML": 900}}
    else:
        data = collect(os.environ["USERNAME"], os.environ.get("GITHUB_TOKEN"))
    open(OUT, "w", encoding="utf-8").write(render(data))
    print("wrote", OUT)
