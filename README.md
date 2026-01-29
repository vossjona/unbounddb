# UnboundDB

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](empty)
[![BitBucket](https://img.shields.io/badge/bitbucket-unbounddb-blue.svg)](empty)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://docs.astral.sh/ruff/)
[![Pre Commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

---

Helps with Unbound

__Table of contents__

1. [Getting Started](#getting-started)
2. [Developer Guide](#developer-guide) \
  2.1. [Local setup](#local-setup) \
  2.2. [Project Structure](#project-structure) \
  2.3. [GNU Make / Makefile](#makefile) \
  2.4. [Git Hooks and Pre-Commit](#git-hooks-and-pre-commit) \
  2.5. [Versioning](#versioning)

## Getting Started

To get started with UnboundDB, follow these steps:

### Step 1: Clone the Repository
```bash
git clone empty.git
cd empty
```

**TODO**

> For detailed instructions on setting up the development environment, refer to the [Developer Guide](#developer-guide).

## Developer Guide

### Local setup

Simply run the make target:

```bash
make setup
```

This will install the Python dependencies as well as installing any git hooks 
defined within the `.pre-commit-config.yaml` file.

> Under the hood, `make setup` will run:
>	```bash
>	uv sync --all-groups
>	uv run pre-commit install --install-hooks
>	```

> **Hint:** It is also possible to configure a Docker remote interpreter using the dev Docker image. This is especially
> useful when the OS is not compatible (e.g. Windows) or the project defines non-Python dependencies.
> For further information see https://www.jetbrains.com/help/pycharm/using-docker-as-a-remote-interpreter.html or
> https://www.jetbrains.com/help/pycharm/using-docker-compose-as-a-remote-interpreter.html.

### Project Structure

Some notes about the folder and file structure within this project:

```
unbounddb
│─── README.md  # this README
│─── Makefile  # contains shortcuts for certain development scripts
│─── Dockerfile  # for defining Docker images
│─── compose.yml  # for building Docker images and running Docker containers (for dev purposes)
│─── .dockerignore  # exclude files and directories to increase Docker build performance
│─── .gitignore  # contains file and folder patterns which should be excluded from git
│─── .gitattributes  # tells git how to handle different file types—for example, managing line endings, diffs, and merge behavior
│─── .editorconfig  # contains file dependent style settings
│─── .hadolint.yaml  # Dockerfile linting configuration (to be used with `hadolint ./Dockerfile`)
│─── .env  # contains settings exported as environment variables (will be git ignored by default)
│─── .env.example  # contains example settings (environment variables)
│─── .pre-commit-config.yaml  # contains git hook configs
│─── .bumpversion.toml  # should be used for bumping the project version
│─── AGENTS.md  # contains description of this project to be used by AI coding assistants
│─── pyproject.toml  # contains project metadata & dependencies as well as settings for some dev tools
│─── ruff.toml  # contains settings for linting and formatting
│─── unbounddb  # contains the actual Python source code
│   │─── __init__.py
│   │─── logs.py  # contains Python logging related logic
│   └─── settings.py  # contains settings for the project
│─── tests  # stores all test related files & folders
│   │─── resources  # contains any resource needed for running tests
│   └─── unittests  # contains pytest based unittests for this project 
│       └─── conftest.py  # provides the option to share fixtures across the whole unittests directory  
└─── configs  # contains configuration files
    └─── logging.yml  # configuration file for Python logging
```

> Note: This directory tree does not contain all files and folders but the most important ones.

### Makefile

The Makefile in this project allows you to run certain development script via corresponding targets.
To get some insight about what targets/commands are currently supported simply run: `make help`
or just `make`.

> Ensure beforehand that [Make](https://www.gnu.org/software/make/) is installed.

### Git Hooks and Pre-Commit

[Git hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) is a built-in feature of git and allows executing
certain scripts at certain events e.g. on commit, merge or push. [Pre-Commit](https://pre-commit.com/) is a Python based
tool for easy registering of such scripts/hooks via the usage of some *.pre-commit-config.yaml* file.

After having installed the pre-commit hooks anytime you run for example `git commit` all the hooks, which are defined
within the *.pre-commit-config.yaml* for the associated stage, will be triggered. You can also run certain hooks 
isolated via `pre-commit run <hook_id>`, for example `pre-commit run mypy`.

You can verify the existence of your git hooks by checking the files within the *.git/hooks* folder.

For further information check the [official pre-commit documentation](https://pre-commit.com/).

> Important: The hooks only apply to  those files, which are within the staging area, so for example you create a commit
> with only none python files ruff, mypy etc. will not get triggered. If you want to execute those hooks or
> (some specific) for all files run `pre-commit run [<hook_id>] -a`

> Note: If you want to commit/push your files without running all the configured hooks just run the git command with the
> *--no-verify* flag. For example `git commit -m "my descriptive message" --no-verify`.

### Versioning

This project uses [bump-my-version](https://callowayproject.github.io/bump-my-version/) for versioning.
Check `bump-my-version show-bump` for an overview about the version bump workflow.

#### Release a new version

Run `bump-my-version bump release` or the convenient make target `make release` to bump version to next release.

#### Bump to next development version

Run `bump-my-version bump <major|minor|patch|build>` to select the next development version.
