# Git Branching Strategy - LangOrch

## Branch Structure

### Main Branches

- **`main`**: Production-ready code. Only stable releases.
- **`develop/v0.X`**: Development branch for version X (e.g., `develop/v0.4`)
- **`release/v0.X`**: Release branches for stable versions (e.g., `release/v0.3`)

### Supporting Branches

- **`feature/*`**: New features (e.g., `feature/langgraph-integration`)
- **`bugfix/*`**: Bug fixes for current development
- **`hotfix/*`**: Critical fixes for production (branch from `main`)

## Workflow

### 1. Starting a New Version

```bash
# From main, create development branch
git checkout main
git checkout -b develop/v0.4
git push -u origin develop/v0.4
```

### 2. Working on Features

```bash
# Create feature branch from develop
git checkout develop/v0.4
git checkout -b feature/langgraph-integration
git push -u origin feature/langgraph-integration

# Work on feature...
git add .
git commit -m "feat: add LangGraph integration"

# When done, merge back to develop
git checkout develop/v0.4
git merge --no-ff feature/langgraph-integration
git push origin develop/v0.4
```

### 3. Releasing a Version

```bash
# Create release branch
git checkout develop/v0.4
git checkout -b release/v0.4
git push -u origin release/v0.4

# Update version files
echo "0.4.0" > VERSION
# Update CHANGELOG.md

git add VERSION CHANGELOG.md
git commit -m "chore: bump version to 0.4.0"

# Merge to main
git checkout main
git merge --no-ff release/v0.4
git push origin main

# Tag the release
git tag -a v0.4.0 -m "Release v0.4.0: LangGraph Multi-Agent System"
git push origin v0.4.0
```

### 4. Hotfixes

```bash
# Create hotfix from main
git checkout main
git checkout -b hotfix/critical-bug-fix
git push -u origin hotfix/critical-bug-fix

# Fix and commit
git add .
git commit -m "fix: critical bug in authentication"

# Merge to both main and develop
git checkout main
git merge --no-ff hotfix/critical-bug-fix
git push origin main

git checkout develop/v0.4
git merge --no-ff hotfix/critical-bug-fix
git push origin develop/v0.4

# Tag the hotfix
git tag -a v0.3.1 -m "Hotfix v0.3.1: Fix authentication bug"
git push origin v0.3.1
```

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add LangGraph multi-agent workflow
fix: resolve timeout issue in transform operation
docs: update API documentation for v0.4
refactor: migrate to LangChain for RAG operations
```

## Version Numbering

Using [Semantic Versioning](https://semver.org/):

- **MAJOR** version (v1.0.0): Breaking changes
- **MINOR** version (v0.4.0): New features, backward compatible
- **PATCH** version (v0.3.1): Bug fixes, backward compatible

## Current Versions

- **v0.3.0** (2026-01-08): Basic RAG with async operations
- **v0.4.0** (In Development): LangGraph multi-agent system
