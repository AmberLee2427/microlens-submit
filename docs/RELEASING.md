# Release Process

This document captures the workflow for cutting a microlens-submit release. It mirrors the
automation we use on other projects while keeping the Python packaging needs of this library
in mind.

## 1. Bump the Version

Use the helper script to increment the semantic version and seed a changelog entry:

```bash
python scripts/bump_version.py patch   # or minor / major
```

After running the script:

- Fill in the placeholder bullet points in `CHANGELOG.md`.
- Double-check any documentation references to the new version.
- Run the test suite in the supported environments.
- Commit the changes through a pull request as usual.

## 2. Prepare the Release Tag

Once the changelog entry is complete and merged, generate release notes and stage the files:

```bash
python scripts/bump_version.py release --dry-run
```

Review `RELEASE_NOTES.md`. When you are happy with the copy, run the release action without
`--dry-run` to create a release commit and annotated tag:

```bash
python scripts/bump_version.py release
```

Push the commit and tag:

```bash
git push origin main
git push origin vX.Y.Z
```

## 3. GitHub Release Workflow

Pushing a tag that matches `v*` triggers `.github/workflows/release.yml`. The job:

- builds an sdist and wheel
- installs the wheel in a fresh virtual environment and runs the tests
- uploads the artifacts to TestPyPI (when `TEST_PYPI_API_TOKEN` is configured)
- uploads the artifacts to PyPI (when `PYPI_API_TOKEN` is configured)
- creates a GitHub release seeded from `RELEASE_NOTES.md`

Secrets required for publishing:

- `TEST_PYPI_API_TOKEN`
- `PYPI_API_TOKEN`

Both tokens should be scoped to the `__token__` username. If the secrets are missing, the
publish steps are skipped.

## 4. Post-release Follow-up

- Monitor the workflow run and confirm the uploads on TestPyPI/PyPI.
- Announce the new version to beta testers or the relevant distribution channels.
- Update downstream projects or documentation if necessary.
