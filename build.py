import json
import os
import shutil
import subprocess
from datetime import datetime

OUTPUT_DIR = "docs"
CONFIG_FILE = "config.json"

FORBIDDEN_PATTERNS = [
    "google-analytics",
    "googletagmanager",
    "doubleclick",
    "adsbygoogle",
    "facebook.net",
    "document.cookie",
    "navigator.sendBeacon",
    "localStorage",
    "sessionStorage",
    "XMLHttpRequest",
    "fetch("
]

# ─── LOAD CONFIG ─────────────────────────────────────────

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ─── BUILD HTML ──────────────────────────────────────────

def build_page(site, page, pages):
    nav_links = ""
    for p in pages:
        filename = "index.html" if p["slug"] == "index" else f"{p['slug']}.html"
        nav_links += f'<a href="{filename}">{p["title"]}</a> '

    body_html = "".join([f"<p>{p}</p>" for p in page.get("body", [])])

    links_html = ""
    for link in page.get("links", []):
        links_html += f"""
        <li>
            <a href="{link['url']}" target="_blank">{link['label']}</a>
            <div>{link.get('description','')}</div>
        </li>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{page["title"]} - {site["title"]}</title>
<style>
body {{
    font-family: Georgia, serif;
    max-width: 700px;
    margin: auto;
    padding: 2rem;
    background: #111;
    color: #eee;
}}
a {{ color: #c9a84c; }}
nav a {{ margin-right: 10px; }}
</style>
</head>

<body>

<h1>{site["title"]}</h1>
<p>{site["description"]}</p>

<nav>{nav_links}</nav>

<hr>

<h2>{page["title"]}</h2>
<p>{page.get("intro","")}</p>

{body_html}

<ul>
{links_html}
</ul>

<hr>
<p>No tracking. No data collected.</p>
<p>{datetime.now().strftime("%Y-%m-%d")}</p>

</body>
</html>
"""

# ─── BUILD SITE ──────────────────────────────────────────

def build_site(config):
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)

    os.makedirs(OUTPUT_DIR)

    for page in config["pages"]:
        html = build_page(config["site"], page, config["pages"])

        filename = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        path = os.path.join(OUTPUT_DIR, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

    # prevent Jekyll
    open(os.path.join(OUTPUT_DIR, ".nojekyll"), "w").close()

# ─── MORALITY HARD STOP ──────────────────────────────────

def check_output():
    for root, _, files in os.walk(OUTPUT_DIR):
        for file in files:
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern in content:
                        raise Exception(f"HARD STOP: Forbidden pattern '{pattern}' found in {file}")

# ─── GIT PUSH ────────────────────────────────────────────

def push():
    subprocess.run(["git", "add", "docs"], check=True)

    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        print("No changes to commit")
        return

    subprocess.run(["git", "commit", "-m", "Update site"], check=True)
    subprocess.run(["git", "push"], check=True)

# ─── MAIN ────────────────────────────────────────────────

def main():
    config = load_config()
    build_site(config)
    check_output()
    push()

    print("Site built and pushed successfully.")

if __name__ == "__main__":
    main()

