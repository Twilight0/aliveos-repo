#!/usr/bin/env python3

"""Generate an HTML storefront page for the AliveOS pacman repository."""

import gzip
import io
import os
import sys
import tarfile
from pathlib import Path
from html import escape


def parse_desc(data: str) -> dict:
    info = {}
    key = None
    for line in data.splitlines():
        line = line.strip()
        if line.startswith("%") and line.endswith("%"):
            key = line[1:-1]
        elif key:
            if key not in info:
                info[key] = line
            key = None
    return info


def human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def generate_html(packages: list[dict], commit_sha: str) -> str:
    rows = ""
    for pkg in sorted(packages, key=lambda p: p.get("NAME", "")):
        name = escape(pkg.get("NAME", ""))
        version = escape(pkg.get("VERSION", ""))
        desc = escape(pkg.get("DESC", ""))
        filename = escape(pkg.get("FILENAME", ""))
        csize = int(pkg.get("CSIZE", 0))
        url = pkg.get("URL", "")

        download_url = f"https://github.com/Twilight0/aliveos-repo/releases/download/latest/{filename}"

        rows += f"""        <tr>
          <td class="pkg-name"><a href="{download_url}" target="_blank">{name}</a></td>
          <td>{version}</td>
          <td>{desc}</td>
          <td class="pkg-size">{human_size(csize)}</td>
        </tr>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AliveOS Package Repository</title>
  <style>
    :root {{
      --bg-primary: #0a0a1a;
      --bg-secondary: #1a1a3e;
      --bg-card: #1e1e3f;
      --text-primary: #e8e8ff;
      --text-secondary: #a0a0cc;
      --accent: #7c5cbf;
      --accent-light: #9b7de0;
      --border: #2a2a5a;
      --code-bg: #12122a;
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
      background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
      color: var(--text-primary);
      min-height: 100vh;
      line-height: 1.6;
    }}

    header {{
      padding: 2rem 1rem;
      text-align: center;
      border-bottom: 1px solid var(--border);
    }}

    header h1 {{
      font-size: 2.2rem;
      font-weight: 300;
      letter-spacing: 0.05em;
      margin-bottom: 0.3rem;
    }}

    header h1 span {{
      color: var(--accent-light);
      font-weight: 600;
    }}

    header p {{
      color: var(--text-secondary);
      font-size: 1rem;
    }}

    nav {{
      margin-top: 1rem;
      display: flex;
      gap: 1.5rem;
      justify-content: center;
      flex-wrap: wrap;
    }}

    nav a {{
      color: var(--accent-light);
      text-decoration: none;
      font-size: 0.9rem;
      transition: color 0.2s;
    }}

    nav a:hover {{
      color: #fff;
    }}

    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 2rem 1rem;
    }}

    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem 2rem;
      margin-bottom: 1.5rem;
    }}

    .card h2 {{
      font-size: 1.1rem;
      font-weight: 500;
      color: var(--accent-light);
      margin-bottom: 1rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .setup-steps {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }}

    @media (max-width: 700px) {{
      .setup-steps {{ grid-template-columns: 1fr; }}
    }}

    .setup-steps ol {{
      padding-left: 1.2rem;
    }}

    .setup-steps li {{
      margin-bottom: 0.5rem;
    }}

    pre {{
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.2rem;
      overflow-x: auto;
      font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
      font-size: 0.85rem;
      color: var(--text-primary);
      white-space: pre;
    }}

    code {{
      font-family: inherit;
    }}

    .pkg-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}

    .pkg-table thead {{
      position: sticky;
      top: 0;
    }}

    .pkg-table th {{
      text-align: left;
      padding: 0.7rem 1rem;
      background: var(--bg-primary);
      color: var(--accent-light);
      font-weight: 500;
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      border-bottom: 2px solid var(--accent);
    }}

    .pkg-table td {{
      padding: 0.6rem 1rem;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}

    .pkg-table tr:hover td {{
      background: rgba(124, 92, 191, 0.08);
    }}

    .pkg-name {{
      font-weight: 500;
      white-space: nowrap;
    }}

    .pkg-name a {{
      color: var(--accent-light);
      text-decoration: none;
    }}

    .pkg-name a:hover {{
      text-decoration: underline;
      color: #fff;
    }}

    .pkg-size {{
      text-align: right;
      white-space: nowrap;
      color: var(--text-secondary);
    }}

    .badge {{
      display: inline-block;
      background: var(--accent);
      color: #fff;
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      vertical-align: middle;
      margin-left: 0.5rem;
    }}

    .table-scroll {{
      max-height: 600px;
      overflow-y: auto;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}

    footer {{
      text-align: center;
      padding: 2rem 1rem;
      color: var(--text-secondary);
      font-size: 0.8rem;
      border-top: 1px solid var(--border);
      margin-top: 2rem;
    }}

    footer a {{
      color: var(--accent-light);
      text-decoration: none;
    }}

    footer a:hover {{
      color: #fff;
    }}
  </style>
</head>
<body>

<header>
  <h1><span>AliveOS</span> Package Repository</h1>
  <p>Minimalist packages for a clean, developer-optimized workflow</p>
  <nav>
    <a href="https://aliveos.org">Home</a>
    <a href="https://github.com/Twilight0/aliveos-repo">GitHub</a>
    <a href="https://github.com/Twilight0/aliveos-repo/releases">Releases</a>
    <a href="https://aliveos.org">Forum</a>
  </nav>
</header>

<main>
  <div class="card">
    <h2>Quick Setup</h2>
    <div class="setup-steps">
      <div>
        <ol>
          <li>Add the repository to <code>/etc/pacman.conf</code></li>
          <li>Sync and install packages</li>
        </ol>
        <pre><code>[aliveos-repo]
SigLevel = Optional TrustAll
Server = https://github.com/Twilight0/aliveos-repo/releases/download/latest</code></pre>
      </div>
      <div>
        <p style="color:var(--text-secondary); margin-bottom: 0.5rem;">Then run:</p>
        <pre><code>sudo pacman -Syu
sudo pacman -S &lt;package-name&gt;</code></pre>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Packages <span class="badge">{len(packages)}</span></h2>
    <div class="table-scroll">
      <table class="pkg-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Version</th>
            <th>Description</th>
            <th style="text-align:right">Size</th>
          </tr>
        </thead>
        <tbody>
{rows}        </tbody>
      </table>
    </div>
  </div>
</main>

<footer>
  &copy; 2026 AliveOS Project &mdash;
  <a href="https://aliveos.org">aliveos.org</a> &middot;
  <a href="https://github.com/Twilight0/aliveos-repo">View on GitHub</a>
  <br>
  Build: <code>{commit_sha}</code>
</footer>

</body>
</html>"""


def main():
    if len(sys.argv) < 2:
        print("Usage: generate-repo-page.py <x86_64-dir> [commit-sha]", file=sys.stderr)
        sys.exit(1)

    x86_64_dir = Path(sys.argv[1])
    commit_sha = sys.argv[2] if len(sys.argv) > 2 else "unknown"

    db_path = x86_64_dir / "aliveos-repo.db.tar.gz"
    if not db_path.exists():
        # Try the raw .db file
        db_path = x86_64_dir / "aliveos-repo.db"

    if not db_path.exists():
        print(f"Error: {db_path} not found", file=sys.stderr)
        sys.exit(1)

    packages = []
    with gzip.open(db_path, "rb") as gz:
        with tarfile.open(fileobj=gz) as tar:
            for member in tar.getmembers():
                if member.name.endswith("/desc"):
                    f = tar.extractfile(member)
                    if f:
                        data = f.read().decode("utf-8", errors="replace")
                        info = parse_desc(data)
                        if "NAME" in info:
                            packages.append(info)

    html = generate_html(packages, commit_sha)

    out_path = x86_64_dir.parent / "index.html"
    out_path.write_text(html)
    print(f"Generated {out_path} with {len(packages)} packages")


if __name__ == "__main__":
    main()
