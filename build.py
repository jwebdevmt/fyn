import json
import os
import shutil
import subprocess
from html import escape
from pathlib import Path

OUTPUT_DIR = "docs"
CONFIG_FILE = "config.json"

FORBIDDEN_PATTERNS = [
    "<script",
    "google-analytics",
    "googletagmanager",
    "doubleclick",
    "adsbygoogle",
    "facebook.net",
    "document.cookie",
    "navigator.sendbeacon",
    "localstorage",
    "sessionstorage",
    "xmlhttprequest",
    "fetch("
]


def load_template(name):
    with open(Path("templates") / name, "r", encoding="utf-8") as f:
        return f.read()


def render(template, context):
    for key, value in context.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template


def e(value):
    return escape(str(value), quote=True)


def build_nav(pages):
    nav = ""
    for page in pages:
        filename = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        nav += f'<a href="{filename}">{e(page["title"])}</a> '
    return nav


def render_resource_card(link):
    label = e(link.get("label", ""))
    url = e(link.get("url", ""))
    description = e(link.get("description", ""))
    link_type = e(link.get("type", ""))
    return f"""
    <div class="resource-card">
        <div class="resource-type">{link_type}</div>
        <h3><a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a></h3>
        <p>{description}</p>
        <div class="resource-url">{url}</div>
    </div>
    """


def build_links(page):
    links_html = ""
    if page.get("link_groups"):
        for group in page["link_groups"]:
            links_html += f"""
            <section class="resource-group">
                <h3>{e(group.get("title", ""))}</h3>
                <div class="resource-list">
            """
            for link in group.get("links", []):
                links_html += render_resource_card(link)
            links_html += """
                </div>
            </section>
            """
    elif page.get("links"):
        links_html += '<div class="resource-list">'
        for link in page["links"]:
            links_html += render_resource_card(link)
        links_html += "</div>"
    return links_html


def build_page(site, page, pages):
    base_template = load_template("base.html")
    page_template = load_template("page.html")

    body_html = ""
    for paragraph in page.get("body", []):
        body_html += f"<p>{e(paragraph)}</p>"

    # Suppress the redundant "Home" heading on the index page.
    # The site title in the header already identifies the space.
    if page["slug"] == "index":
        page_heading = ""
    else:
        page_heading = f"<h2>{e(page['title'])}</h2>"

    page_content = render(page_template, {
        "page_heading": page_heading,
        "page_title": e(page["title"]),
        "intro": e(page.get("intro", "")),
        "body": body_html,
        "links": build_links(page)
    })

    full_page = render(base_template, {
        "title": e(page["title"]),
        "site_title": e(site["title"]),
        "site_description": e(site["description"]),
        "nav": build_nav(pages),
        "content": page_content
    })

    return full_page


def validate_config(config):
    if "site" not in config:
        raise Exception("Missing site block in config.json")
    if "pages" not in config:
        raise Exception("Missing pages block in config.json")
    if not config["site"].get("title"):
        raise Exception("Missing site title")
    if not config["site"].get("description"):
        raise Exception("Missing site description")

    slugs = set()
    for page in config["pages"]:
        slug = page.get("slug")
        title = page.get("title")
        if not slug:
            raise Exception("A page is missing a slug")
        if not title:
            raise Exception(f"Page '{slug}' is missing a title")
        if slug in slugs:
            raise Exception(f"Duplicate page slug: {slug}")
        slugs.add(slug)


def clean_output():
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)


def copy_assets(theme="dark"):
    dest = os.path.join(OUTPUT_DIR, "assets")
    os.makedirs(dest, exist_ok=True)

    # Choose stylesheet based on theme setting in config.
    # Copies the chosen file as style.css so templates need no changes.
    if theme == "light":
        src_css = "assets/style-light.css"
    else:
        src_css = "assets/style.css"

    if os.path.exists(src_css):
        shutil.copyfile(src_css, os.path.join(dest, "style.css"))

    # Copy any other assets (images etc.) excluding the css source files.
    if os.path.exists("assets"):
        for item in os.listdir("assets"):
            if item in ("style.css", "style-light.css"):
                continue
            s = os.path.join("assets", item)
            d = os.path.join(dest, item)
            if os.path.isfile(s):
                shutil.copyfile(s, d)
            elif os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)


def preserve_cname(config):
    custom_domain = config.get("site", {}).get("custom_domain", "").strip()
    if custom_domain:
        with open(os.path.join(OUTPUT_DIR, "CNAME"), "w", encoding="utf-8") as f:
            f.write(custom_domain + "\n")
        return
    if os.path.exists("CNAME"):
        shutil.copyfile("CNAME", os.path.join(OUTPUT_DIR, "CNAME"))


def write_site(config):
    theme = config.get("site", {}).get("theme", "dark")
    clean_output()
    for page in config["pages"]:
        html = build_page(config["site"], page, config["pages"])
        filename = "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    open(os.path.join(OUTPUT_DIR, ".nojekyll"), "w").close()
    copy_assets(theme)
    preserve_cname(config)


def integrity_check():
    violations = []
    for root, _, files in os.walk(OUTPUT_DIR):
        for filename in files:
            path = os.path.join(root, filename)
            if not filename.endswith((".html", ".css", ".js", ".xml", ".txt")):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.lower() in content:
                    violations.append(f"{path}: {pattern}")
    if violations:
        print("Integrity check failed.")
        for violation in violations:
            print(" -", violation)
        raise Exception("HARD STOP: forbidden pattern detected.")
    print("Integrity check passed.")


def push():
    subprocess.run(["git", "add", OUTPUT_DIR], check=True)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        print("No changes to commit.")
        return
    subprocess.run(["git", "commit", "-m", "Update site"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("Pushed to GitHub.")


def ask_to_push():
    answer = input("Push to GitHub now? [y/N]: ").strip().lower()
    return answer in ("y", "yes")


def main():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    validate_config(config)
    write_site(config)
    integrity_check()
    print("Build complete.")
    if ask_to_push():
        push()
    else:
        print("Skipping push.")


if __name__ == "__main__":
    main()
