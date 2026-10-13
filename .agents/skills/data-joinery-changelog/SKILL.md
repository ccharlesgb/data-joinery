---
name: data-joinery-changelog
description: Draft and maintain data-joinery's user-facing CHANGELOG.md from Git release history. Use during a release or when asked to update the changelog.
---

# Data Joinery changelog

Maintain the repository-root `CHANGELOG.md` using [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).

## Find the changes

- For a new release, compare the latest released version tag with `main` (`git log <tag>..main` and `git diff <tag> main`). Use the exact `x.y.z` tag, not a similarly named branch or prefixed tag. Also read the existing `Unreleased` section. If the intended release commit differs from `main`, inspect that exact range and say so.
- For historical backfills, compare each adjacent pair of release tags; inspect the initial release against its parent or repository root. Use tag dates for released headings.
- Treat commit subjects as leads. Check changed public code, tests, and docs to establish what users can observe. Combine related commits into a single clear entry.

## Write for package users

- Include notable additions, changed behavior, fixes, deprecations, removals, and security changes. Make migration steps or breaking changes explicit.
- Exclude internal refactors, test/build/release machinery, agent instructions, and documentation-only edits that do not change package behavior. Dependency or compatibility changes belong when they affect installation or supported use.
- Use `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, and `Security` only when populated. Keep newest versions first, retain `Unreleased` at the top, use `YYYY-MM-DD` release dates, and link versions to GitHub tag comparisons.
- Do not paste a Git log into the changelog. Do not claim a change without evidence or assign it to a version where it was not released.

## Approval at release time

Account for the full release range in the proposed version section. Show its exact text to the developer for explicit approval **before** changing release files, committing, tagging, or publishing. Revise it if requested and seek approval again. Once approved, move the relevant `Unreleased` entries into the dated version section, leave an empty `Unreleased` heading, and include `CHANGELOG.md` in the release commit. If the section needs further substantive changes, seek approval of the revised text. Approval of the proposed text does not authorize unrelated changes.
