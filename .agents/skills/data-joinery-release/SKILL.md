---
name: data-joinery-release
description: Release data-joinery by validating the repository, selecting the next semantic version, updating package metadata, and publishing a Git tag.
---

# Data Joinery release

Use this skill only to make a release of this repository. Do not skip a failed
check or release from a dirty or outdated checkout.

## Validate the release candidate

From the repository root, run these commands in order and continue only if all
three exit successfully:

```sh
just check
just docs-examples
just docs-build
```

After they succeed, confirm the checkout is clean, `main` is checked out,
and it exactly matches `origin/main`. Fetching is allowed to verify the
remote state, but do not automatically switch branches, merge, rebase, stash,
or discard work. Stop and explain what needs to be resolved if any condition
is not true.

```sh
git fetch origin
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse origin/main
```

## Choose the version

Find the highest existing Git tag whose complete value matches `x.x.x` (three
non-negative integer components), ignoring tags with prefixes or prerelease
suffixes. Use a version-aware numeric sort; do not rely on lexicographic sort.

Use the ask-question tool to ask whether this is a **major**, **minor**, or
**patch** bump. Do not replace that tool call with a plain-text question.

Increment the highest matching tag as follows:

- major: `MAJOR + 1.0.0`
- minor: `MAJOR.MINOR + 1.0`
- patch: `MAJOR.MINOR.PATCH + 1`

If there is no matching tag, stop and ask the user for the initial release
version; do not invent one. Before making changes, report the selected version
and verify that no tag with that exact name already exists.

## Create and publish the release

Update the `version` field in `pyproject.toml` to the selected version, then
run:

```sh
uv lock
```

Inspect the resulting diff. It must contain only the intended changes to
`pyproject.toml` and `uv.lock`; otherwise stop for user direction. A tag must
refer to the versioned package state, so create a release commit containing
those two files before tagging:

```sh
git add -- pyproject.toml uv.lock
git commit -m "Release x.x.x"
git push origin main
git tag x.x.x
git push origin x.x.x
```

Replace every `x.x.x` above with the selected version. If a commit, push, or
tag command fails, stop: do not force-push, overwrite an existing tag, or
retry by changing history.
