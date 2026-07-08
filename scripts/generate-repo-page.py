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
    <meta name="description" content="AliveOS pacman repository - minimalist packages for a clean, developer-optimized workflow.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Roboto+Mono&display=swap" rel="stylesheet">
    <link rel="icon" type="image/png" sizes="32x32" href="https://aliveos.org/assets/favicon-32.png">
    <link rel="icon" type="image/x-icon" href="https://aliveos.org/assets/favicon.ico">
    <link rel="apple-touch-icon" sizes="180x180" href="https://aliveos.org/assets/apple-touch-icon.png">
    <style>
        :root {{
            --bg-color: #0d1117;
            --text-color: #c9d1d9;
            --header-text: #f0f6fc;
            --accent-blue: #58a6ff;
            --accent-purple: #8957e5;
            --secondary-bg: #161b22;
            --grid-line: #21262d;
            --footer-text: #8b949e;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            background-image: linear-gradient(rgba(13, 17, 23, 0.86), rgba(13, 17, 23, 0.93)), url('https://aliveos.org/assets/background.jpg');
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
            color: var(--text-color);
            min-height: 100vh;
            text-align: center;
            position: relative;
        }}

        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: linear-gradient(var(--grid-line) 1px, transparent 1px),
                              linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
            background-size: 50px 50px;
            z-index: -1;
            opacity: 0.08;
            pointer-events: none;
        }}

        .container {{
            max-width: 960px;
            width: 100%;
            box-sizing: border-box;
            padding: 2rem;
            position: relative;
            z-index: 1;
            margin: 0 auto;
        }}

        .header-section {{
            margin-bottom: 3rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}

        .header-section .logo-link {{
            display: inline-block;
            line-height: 0;
            text-decoration: none;
        }}

        .header-section img.logo {{
            max-width: 150px;
            height: auto;
            margin-bottom: 1rem;
            filter: drop-shadow(0 0 10px rgba(88, 166, 255, 0.2));
        }}

        .header-section h1 {{
            font-size: 3.5rem;
            font-weight: 800;
            margin: 0.5rem 0;
            background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-purple) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }}

        .header-section .tagline {{
            font-size: 1.25rem;
            color: #8b949e;
            max-width: 600px;
        }}

        .site-nav {{
            margin-top: 1.5rem;
            display: flex;
            gap: 1.25rem;
            justify-content: center;
            font-family: 'Roboto Mono', monospace;
            font-size: 0.95rem;
        }}

        .site-nav a {{
            color: var(--text-color);
            text-decoration: none;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            transition: color 0.2s ease, background-color 0.2s ease;
        }}

        .site-nav a:hover {{
            color: var(--header-text);
            background-color: var(--secondary-bg);
        }}

        .section-heading {{
            font-size: 1.6rem;
            color: var(--header-text);
            margin-bottom: 2rem;
            text-align: left;
            padding-left: 1rem;
            border-left: 3px solid var(--accent-blue);
        }}

        .setup-card {{
            background-color: var(--secondary-bg);
            border: 1px solid var(--grid-line);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            text-align: left;
        }}

        .setup-card h3 {{
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--header-text);
            margin-bottom: 1rem;
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
            color: var(--text-color);
        }}

        .setup-steps li {{
            margin-bottom: 0.5rem;
        }}

        pre {{
            background-color: var(--secondary-bg);
            border: 1px solid var(--grid-line);
            border-radius: 8px;
            padding: 1rem;
            overflow-x: auto;
            margin: 0 0 1rem;
        }}

        pre code {{
            font-family: 'Roboto Mono', monospace;
            font-size: 0.85rem;
            color: var(--text-color);
            background: none;
            border: none;
            padding: 0;
        }}

        code {{
            font-family: 'Roboto Mono', monospace;
            font-size: 0.88em;
            background-color: var(--secondary-bg);
            border: 1px solid var(--grid-line);
            border-radius: 4px;
            padding: 0.1rem 0.35rem;
            color: var(--accent-blue);
        }}

        .table-wrapper {{
            background-color: var(--secondary-bg);
            border: 1px solid var(--grid-line);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 2rem;
        }}

        .table-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--grid-line);
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .table-header h3 {{
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--header-text);
        }}

        .badge {{
            display: inline-block;
            background: var(--accent-purple);
            color: #fff;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .table-scroll {{
            max-height: 600px;
            overflow-y: auto;
        }}

        .pkg-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
            text-align: left;
        }}

        .pkg-table thead {{
            position: sticky;
            top: 0;
            z-index: 2;
        }}

        .pkg-table th {{
            padding: 0.7rem 1rem;
            background-color: var(--bg-color);
            color: var(--footer-text);
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--grid-line);
        }}

        .pkg-table td {{
            padding: 0.6rem 1rem;
            border-bottom: 1px solid var(--grid-line);
            vertical-align: top;
        }}

        .pkg-table tr:hover td {{
            background-color: rgba(88, 166, 255, 0.04);
        }}

        .pkg-name {{
            font-weight: 600;
            white-space: nowrap;
        }}

        .pkg-name a {{
            color: var(--accent-blue);
            text-decoration: none;
        }}

        .pkg-name a:hover {{
            text-decoration: underline;
        }}

        .pkg-size {{
            text-align: right;
            white-space: nowrap;
            color: var(--footer-text);
            font-family: 'Roboto Mono', monospace;
            font-size: 0.85rem;
        }}

        footer {{
            margin-top: 4rem;
            font-size: 0.85rem;
            color: var(--footer-text);
            padding: 2rem 0;
            border-top: 1px solid var(--grid-line);
        }}

        footer a {{
            color: var(--accent-blue);
            text-decoration: none;
            margin: 0 0.5rem;
        }}

        footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header-section">
            <a href="https://aliveos.org" class="logo-link"><img src="https://aliveos.org/assets/aliveos-logo.png" alt="AliveOS Logo" class="logo"></a>
            <h1>AliveOS</h1>
            <p class="tagline">Package Repository &mdash; minimalist packages for a clean, developer-optimized workflow.</p>
            <nav class="site-nav">
                <a href="https://aliveos.org">Home</a>
                <a href="https://aliveos.org/news/">News</a>
                <a href="https://github.com/Twilight0/aliveos-repo">GitHub</a>
                <a href="https://github.com/Twilight0/aliveos-repo/releases">Releases</a>
                <a href="https://github.com/Twilight0/aliveos/discussions">Forum</a>
            </nav>
        </div>

        <div class="setup-card">
            <h3>Quick Setup</h3>
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
                    <p style="color:var(--footer-text); margin-bottom: 0.5rem; font-size: 0.9rem;">Then run:</p>
                    <pre><code>sudo pacman -Syu
sudo pacman -S &lt;package-name&gt;</code></pre>
                </div>
            </div>
        </div>

        <div class="table-wrapper">
            <div class="table-header">
                <h3>Packages</h3>
                <span class="badge">{len(packages)}</span>
            </div>
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
{rows}                    </tbody>
                </table>
            </div>
        </div>

        <footer>
            <p>&copy; 2026 AliveOS Project. All rights reserved.</p>
            <p>
                <a href="https://aliveos.org">aliveos.org</a> |
                <a href="https://github.com/Twilight0/aliveos-repo">View on GitHub</a> |
                <a href="https://github.com/Twilight0/aliveos/discussions">Forum</a>
            </p>
            <p style="margin-top: 0.5rem; font-family: 'Roboto Mono', monospace; font-size: 0.8rem;">Build: {commit_sha}</p>
        </footer>
    </div>
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
