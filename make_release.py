#!/usr/bin/env python3

import toml
import subprocess
import sys
from pathlib import Path


def bump_version(version: str, level: str) -> str:
    major, minor, patch = map(int, version.split("."))
    if level == "major":
        return f"{major + 1}.0.0"
    elif level == "minor":
        return f"{major}.{minor + 1}.0"
    elif level == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError("Invalid bump level. Use: major, minor, or patch.")


def update_pyproject(new_version: str):
    path = Path("pyproject.toml")
    data = toml.load(path)
    data["project"]["version"] = new_version
    with open(path, "w") as f:
        toml.dump(data, f)


def git_commit_tag_push(version: str):
    subprocess.run(["/usr/bin/git", "add", "pyproject.toml"], check=True)
    subprocess.run(["/usr/bin/git", "commit", "-m", f"Release v{version}"], check=True)
    subprocess.run(["/usr/bin/git", "tag", f"v{version}"], check=True)
    subprocess.run(["/usr/bin/git", "push"], check=True)
    subprocess.run(["/usr/bin/git", "push", "origin", f"v{version}"], check=True)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"major", "minor", "patch"}:
        print("Usage: python release.py [major|minor|patch]")
        sys.exit(1)

    bump_level = sys.argv[1]
    pyproject = toml.load("pyproject.toml")
    current_version = pyproject["project"]["version"]
    new_version = bump_version(current_version, bump_level)

    update_pyproject(new_version)
    git_commit_tag_push(new_version)

    print(f"✅ Released version v{new_version}")


if __name__ == "__main__":
    main()
