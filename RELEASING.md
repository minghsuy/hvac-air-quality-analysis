# Release Process

This document describes how to release a new version of hvac-air-quality.

## Prerequisites

- Ensure all tests pass: `uv run pytest`
- Ensure code is formatted: `uv run ruff format .`
- Ensure no linting issues: `uv run ruff check .`
- Update CHANGELOG.md with release notes

## Release Steps

### 1. Update Version

Update the version in:
- `pyproject.toml` (change from `X.Y.Z-dev` to `X.Y.Z`)
- `src/hvac_air_quality/__init__.py`

### 2. Update Changelog

If using git-cliff for automated changelog:
```bash
git cliff --tag vX.Y.Z --output CHANGELOG.md
```

Otherwise, manually update CHANGELOG.md:
- Move items from "Unreleased" to the new version section
- Add the release date
- Add comparison links at the bottom

### 3. Commit Release

```bash
git add -A
git commit -m "chore(release): prepare for vX.Y.Z"
git push
```

### 4. Create and Push Tag

```bash
git tag -a vX.Y.Z -m "Release version X.Y.Z"
git push origin vX.Y.Z
```

This will trigger the GitHub Actions release workflow which will:
- Build the package
- Create a GitHub release with changelog
- Upload wheel and sdist artifacts
- Publish to PyPI (if configured)

### 5. Bump Version for Development

After release, update version to next development version:
- `pyproject.toml`: Change to `X.Y.Z+1-dev`
- `src/hvac_air_quality/__init__.py`: Same update

```bash
git add -A
git commit -m "chore: bump version to X.Y.Z+1-dev"
git push
```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for new functionality in a backward compatible manner
- PATCH version for backward compatible bug fixes

Development versions use `-dev` suffix.

## Manual Release (if Actions fail)

```bash
# Build the package
uv build

# Check the build
ls dist/

# Upload to PyPI (requires PyPI token)
uv publish
```

## Post-Release Checklist

- [ ] Verify GitHub release was created
- [ ] Verify artifacts were uploaded to release
- [ ] Test installation: `uv pip install hvac-air-quality==X.Y.Z`
- [ ] Update any documentation that references the version
- [ ] Announce release (if applicable)