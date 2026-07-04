import json
import os


CONFIG_FILE = "config.json"


def ask(prompt, default=""):
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default
    return input(f"{prompt}: ").strip()


def ask_yes_no(prompt, default="n"):
    value = input(f"{prompt} [y/N]: ").strip().lower()
    if not value:
        value = default
    return value in ("y", "yes")


def slugify(text):
    slug = text.lower().strip()
    keep = []
    last_was_dash = False

    for char in slug:
        if char.isalnum():
            keep.append(char)
            last_was_dash = False
        elif char in (" ", "-", "_"):
            if not last_was_dash:
                keep.append("-")
                last_was_dash = True

    return "".join(keep).strip("-") or "page"


def collect_body():
    print("\nEnter page paragraphs. Leave blank when finished.")
    body = []

    while True:
        paragraph = input("> ").strip()
        if not paragraph:
            break
        body.append(paragraph)

    return body


def collect_links():
    link_groups = []

    while ask_yes_no("\nAdd a link/resource group?"):
        group_title = ask("Group title", "Resources")
        links = []

        while ask_yes_no(f"Add a link to '{group_title}'?"):
            label = ask("Link label")
            url = ask("URL")
            description = ask("Description", "")
            link_type = ask("Type/label", "Resource")

            links.append({
                "label": label,
                "url": url,
                "description": description,
                "type": link_type
            })

        link_groups.append({
            "title": group_title,
            "links": links
        })

    return link_groups


def collect_pages():
    pages = []

    print("\nCreating home page.")
    home_intro = ask("Home intro")
    home_body = collect_body()

    pages.append({
        "slug": "index",
        "title": "Home",
        "intro": home_intro,
        "body": home_body
    })

    while ask_yes_no("\nAdd another page?"):
        title = ask("Page title")
        slug = ask("Page slug", slugify(title))
        intro = ask("Page intro", "")
        body = collect_body()

        page = {
            "slug": slug,
            "title": title,
            "intro": intro,
            "body": body
        }

        if ask_yes_no("Add links/resources to this page?"):
            page["link_groups"] = collect_links()

        pages.append(page)

    return pages


def main():
    if os.path.exists(CONFIG_FILE):
        overwrite = ask_yes_no("config.json already exists. Overwrite it?")
        if not overwrite:
            print("Cancelled. Existing config.json was not changed.")
            return

    print("Finding Your Neighborhood config creator\n")

    site_title = ask("Site title")
    site_description = ask("Site description")

    pages = collect_pages()

    config = {
        "site": {
            "title": site_title,
            "description": site_description
        },
        "pages": pages
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print("\nconfig.json created.")
    print("Next: run python build.py")


if __name__ == "__main__":
    main()