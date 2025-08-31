# Release Checklist for v0.3.0 (What We Should Have Done)

## ✅ What We Did Right:
1. Updated version in `pyproject.toml` from `0.3.0-dev` to `0.3.0`
2. Updated CHANGELOG.md with release notes
3. Created git tag `v0.3.0`
4. Pushed tag to trigger GitHub Actions
5. GitHub Actions successfully created release with artifacts
6. Bumped version to `0.4.0-dev` after release

## ❌ What We Missed:
1. **Run tests first**: `uv run pytest` ✅ (17 passed when we ran it after)
2. **Fix linting issues**: `uv run ruff check . --fix` ❌ (49 errors found)
3. **Format code**: `uv run ruff format .` ❌ (didn't run)
4. **Commit message format**: Should have been `chore(release): prepare for v0.3.0` not `feat: ...`

## 📝 Correct Release Process for Next Time:

### Pre-release Checks:
```bash
# 1. Run tests
uv run pytest

# 2. Fix linting issues
uv run ruff check . --fix

# 3. Format code  
uv run ruff format .

# 4. Commit any fixes
git add -A
git commit -m "fix: Linting and formatting for release"
```

### Release Steps:
```bash
# 1. Update version in pyproject.toml (remove -dev)
# 2. Update CHANGELOG.md

# 3. Commit with proper message
git add -A
git commit -m "chore(release): prepare for v0.3.0"
git push

# 4. Create and push tag
git tag -a v0.3.0 -m "Release version 0.3.0"
git push origin v0.3.0

# 5. After release, bump to dev
# Update pyproject.toml to 0.4.0-dev
git add -A
git commit -m "chore: bump version to 0.4.0-dev"
git push
```

## 🎯 Key Learnings:

1. **Always run quality checks before release** - Even though the release worked, we have 49 linting errors in the released code
2. **Follow commit message conventions** - Use `chore(release):` for release commits
3. **The release still worked** - GitHub Actions is forgiving and created the release despite the issues

## 🔧 To Fix Now (Optional):

Since v0.3.0 is already released, we could:
1. Fix all linting issues in a new commit
2. These fixes will be in v0.4.0
3. Or create a v0.3.1 patch release with the fixes

```bash
# Fix issues now for next release
uv run ruff check . --fix
uv run ruff format .
git add -A  
git commit -m "fix: Address linting issues from v0.3.0"
git push
```