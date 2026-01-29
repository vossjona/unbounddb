# Contributing to UnboundDB

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Git Workflow](#git-workflow)
4. [Commit Message Conventions](#commit-message-conventions)
5. [Code Standards](#code-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Release Workflow](#release-workflow)
8. [Pull Request Process](#pull-request-process)

## Getting Started

### Prerequisites

Ensure you have the following installed:
- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) for dependency management
- [GNU Make](https://www.gnu.org/software/make/)
- Git
- Docker & Docker Compose (optional, for containerized development)

### Initial Setup

1. Clone the repository:
   ```bash
   git clone empty.git
   cd empty
   ```

2. Set up your development environment:
   ```bash
   make setup
   ```
   This will:
   - Install all project dependencies (including dev dependencies)
   - Set up pre-commit hooks for automated code quality checks

3. Copy the example environment file and configure it:
   ```bash
   cp .env.example .env
   # Edit .env with your local settings
   ```

## Development Workflow

### Branch Strategy

We use a **feature branch workflow**:

```
main (protected)
  ├── feature/TICKET-123-add-new-model
  ├── bugfix/TICKET-456-fix-data-pipeline
  ├── hotfix/TICKET-789-critical-security-fix
  └── docs/TICKET-321-update-readme
```

#### Branch Naming Convention

Format: `<type>/<ticket-id>-<short-description>`

**Types:**
- `feature/` - New features or enhancements
- `bugfix/` - Bug fixes
- `hotfix/` - Critical fixes for production issues
- `docs/` - Documentation updates
- `refactor/` - Code refactoring without functional changes
- `test/` - Adding or updating tests
- `chore/` - Maintenance tasks, dependency updates

**Examples:**
```bash
feature/DS-123-implement-sentiment-analysis
bugfix/DS-456-fix-null-pointer-in-preprocessing
docs/DS-789-add-api-documentation
```

> **Note:** The ticket ID will be automatically prepended to your commit messages by the pre-commit hook.

### Creating a New Branch

```bash
# Ensure you're on the latest main
git checkout main
git pull origin main

# Create your feature branch
git checkout -b feature/TICKET-123-short-description
```

## Git Workflow

### 1. Make Your Changes

Work on your feature branch and commit regularly:

```bash
# Stage your changes
git add <files>

# Commit with a descriptive message
git commit -m "Add sentiment analysis model"
```

### 2. Keep Your Branch Updated

Regularly sync with the main branch:

```bash
git checkout main
git pull origin main
git checkout feature/TICKET-123-short-description
git rebase main
```

### 3. Push Your Changes

```bash
git push origin feature/TICKET-123-short-description
```

### 4. Create a Pull Request

- Go to the repository in your browser
- Click "Create Pull Request"
- Fill in the PR template with:
  - Description of changes

## Commit Message Conventions

### Automatic Ticket Prefix

The pre-commit hook automatically adds the ticket ID from your branch name to commit messages.

**Branch:** `feature/DS-123-add-model`  
**Your commit:** `Add sentiment analysis model`  
**Final commit:** `DS-123: Add sentiment analysis model`

### Bypassing Pre-Commit Hooks

If you need to commit without running hooks (use sparingly):

```bash
git commit -m "Your message" --no-verify
```

## Code Standards

### Style Guidelines

This project uses:
- **Ruff** for linting and formatting (line length: 120)
- **Mypy** for type checking
- **Pre-commit hooks** for automatic enforcement

### Imports

Organize imports in the following order:
1. Standard library imports
2. Third-party imports
3. Local application imports

## Testing Guidelines

### Test Structure

```
tests/
├── unittests/           # Fast, isolated unit tests
│   ├── conftest.py      # Shared fixtures
│   └── test_*.py
├── integrationtests/    # Integration/end-to-end tests
│   └── test_*.py
└── resources/           # Test data, fixtures, mocks
```

### Running Tests

```bash
# Run all tests
make unittests
make integrationtests

# Run with coverage
make coverage

# Run specific test file
uv run pytest tests/unittests/test_module.py

# Run specific test
uv run pytest tests/unittests/test_module.py::test_function_name
```

## Release Workflow

### Version Format

We use **Semantic Versioning** with development builds:

- **Development:** `0.1.0.dev1`, `0.1.0.dev2`, ...
- **Production:** `0.1.0`, `0.2.0`, `1.0.0`, ...

### Version Components

- **Major:** Breaking changes
- **Minor:** New features (backward compatible)
- **Patch:** Bug fixes (backward compatible)
- **Release:** `dev` (development) or `prod` (production/omitted)
- **Build:** Build number for development versions

### Bumping Versions

#### Check Current Version

```bash
bump-my-version show current_version
# or
bump-my-version show-bump
```

#### Development Workflow

1. **Start new development cycle** (after release):
   ```bash
   # Bump to next minor dev version
   bump-my-version bump minor
   # Example: 0.1.0 → 0.2.0.dev1
   ```

2. **Continue development** (increment build):
   ```bash
   bump-my-version bump build
   # Example: 0.2.0.dev1 → 0.2.0.dev2
   ```

3. **Prepare for release**:
   ```bash
   bump-my-version bump release
   # or use the make target
   make release
   # Example: 0.2.0.dev2 → 0.2.0
   ```

#### Other Scenarios

```bash
# Bump patch version (bug fixes)
bump-my-version bump patch
# Example: 0.2.0 → 0.2.1.dev1

# Bump major version (breaking changes)
bump-my-version bump major
# Example: 0.2.0 → 1.0.0.dev1
```

### Release Process

1. **Ensure clean state:**
   ```bash
   git status  # Should be clean
   make check  # Run all quality checks
   make unittests  # Run tests
   ```

2. **Bump version to release:**
   ```bash
   make release
   ```

3. **Review changes:**
   ```bash
   git diff  # Check version bumps in files
   ```

4. **Commit and tag:**
   ```bash
   git add -A
   git commit -m "Release version $(bump-my-version show current_version)"
   git tag -a "v$(bump-my-version show current_version)" -m "Release v$(bump-my-version show current_version)"
   ```

5. **Push to remote:**
   ```bash
   git push origin main
   git push origin --tags
   ```

6. **Start next development cycle:**
   ```bash
   bump-my-version bump minor  # or patch/major
   git add -A
   git commit -m "Start development for next version"
   git push origin main
   ```

## Pull Request Process

### Before Submitting

- [ ] All tests pass locally (`make unittests`)
- [ ] Code passes quality checks (`make check`)
- [ ] New code has appropriate tests
- [ ] Documentation is updated (if applicable)
- [ ] Branch is up-to-date with main

### PR Template

When creating a PR, include:

```markdown
## Description
[Brief description of changes]

## Related Issue
Closes #[issue-number]
```

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **At least one approval** from a team member required
3. **Address review comments** and push updates
4. **Squash commits** if requested for cleaner history

### Merging

- Use **Squash and Merge** for feature branches
- Use **Rebase and Merge** for hotfixes (to preserve history)
- Delete branch after merging

## Development Commands Reference

```bash
# Setup
make setup                 # Initial environment setup

# Code Quality
make lint                  # Run ruff linter
make format                # Run ruff formatter
make typing                # Run mypy type checker
make check                 # Run all quality checks

# Testing
make unittests            # Run unit tests
make integrationtests     # Run integration tests
make coverage             # Run tests with coverage report

# Versioning
make release              # Bump to next release version

# Cleanup
make clean                # Clean build artifacts and cache
```
