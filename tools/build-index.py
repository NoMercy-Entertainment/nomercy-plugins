#!/usr/bin/env python3
"""Gathers every source in sources.json into index.json.

A server reads index.json and lists what it finds. That file used to be typed by
hand, one block per *version*, so a plugin was listed once and went stale the
moment it shipped again — and its author had to open another pull request for
every release. The Internet Radio entry is three versions deep and its own CI
knows nothing about any of them.

So an author now submits one URL, once. Their own index says which versions
exist, and this brings them together.

Two rules it will not break:

**It never deletes.** A version already in index.json stays there even if no
source mentions it — the hand-written entries predate sources.json and carry
changelogs nothing can regenerate. A source that goes offline must not empty the
catalogue.

**It never invents.** Everything written comes from a source or was already in
the file. A source that cannot be fetched or parsed is reported and skipped, and
the rest of the catalogue is built without it.

Usage:
    python tools/build-index.py            # rewrite index.json
    python tools/build-index.py --check    # fail if it would change anything
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources.json"
INDEX = ROOT / "index.json"

# A plugin id is a Ulid: 26 characters of Crockford base32. It is not a GUID —
# IPlugin.Id is a Ulid, and every plugin in this catalogue uses one. The schema
# said "uuid" for a long time and described a format nothing here has ever used.
ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
VERSION = re.compile(r"^\d+(\.\d+){1,3}$")


def order(version: str) -> tuple[int, ...]:
    """Newest first, compared as numbers so 1.10.0 outranks 1.9.0."""
    return tuple(int(part) for part in version.split("."))


def fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as answer:
        return json.loads(answer.read().decode("utf-8"))


def complain(where: str, message: str) -> None:
    print(f"  {where}: {message}", file=sys.stderr)


def check_plugin(plugin: dict, where: str, problems: list[str]) -> bool:
    """Whether this plugin entry is fit to publish, saying why when it is not."""
    ok = True

    for field in ("id", "name", "description", "versions"):
        if not plugin.get(field):
            problems.append(f"{where}: a plugin has no {field}")
            ok = False

    identity = plugin.get("id", "")
    if identity and not ULID.match(identity):
        problems.append(f"{where}: '{identity}' is not a Ulid (26 of 0-9 A-Z, no I L O U)")
        ok = False

    for version in plugin.get("versions", []):
        number = version.get("version", "")
        if not VERSION.match(number):
            problems.append(f"{where}: version '{number}' is not dotted numeric")
            ok = False

        download = version.get("downloadUrl", "")
        if not download.startswith("https://"):
            problems.append(f"{where}: {number} downloads over something other than https")
            ok = False

        checksum = version.get("checksum")
        if checksum and not SHA256.match(checksum):
            problems.append(f"{where}: {number} has a checksum that is not lowercase sha-256 hex")
            ok = False

    return ok


def merge(index: dict, plugin: dict) -> None:
    """Add or update one plugin, keeping every version already listed."""
    for existing in index["plugins"]:
        if existing["id"] != plugin["id"]:
            continue

        # What the plugin says about itself is its own to change.
        for field in ("name", "description", "author", "projectUrl"):
            if plugin.get(field):
                existing[field] = plugin[field]

        known = {version["version"] for version in existing["versions"]}
        existing["versions"] += [
            version for version in plugin["versions"] if version["version"] not in known
        ]
        existing["versions"].sort(key=lambda version: order(version["version"]), reverse=True)
        return

    index["plugins"].append(plugin)


def main() -> int:
    checking = "--check" in sys.argv

    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    before = json.dumps(index, sort_keys=True)

    problems: list[str] = []
    seen: dict[str, str] = {}

    for source in sources:
        name, url = source.get("name", "?"), source["url"]
        print(f"{name}: {url}")

        try:
            document = fetch(url)
        except (urllib.error.URLError, ValueError, TimeoutError) as unreachable:
            complain(name, f"could not be read ({unreachable}); leaving the catalogue as it is")
            problems.append(f"{name}: {unreachable}")
            continue

        for plugin in document.get("plugins", []):
            if not check_plugin(plugin, name, problems):
                continue

            identity = plugin["id"]
            if identity in seen and seen[identity] != name:
                problems.append(f"{name}: id {identity} is already claimed by {seen[identity]}")
                continue

            seen[identity] = name
            merge(index, plugin)
            print(f"  {plugin['name']}: {[v['version'] for v in plugin['versions']]}")

    index["plugins"].sort(key=lambda plugin: plugin["name"].lower())
    after = json.dumps(index, sort_keys=True)

    if problems:
        print("\nproblems:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)

    if before == after:
        print("\nindex.json is already what the sources say")
        return 1 if problems else 0

    if checking:
        print("\nindex.json is not what the sources say", file=sys.stderr)
        return 1

    INDEX.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print("\nindex.json rewritten")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
