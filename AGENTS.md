# AGENTS.md - Project Guidelines

This file provides project-specific guidance for the UnboundDB codebase that goes beyond general
coding practices.  
It focuses on patterns and conventions unique to this project.

## Project Overview

{Description of the project, its purpose, and key components.}

### Service Architecture

{List of components and their interactions}

## PYTHON-SPECIFIC STANDARDS

### Type Hints & Annotations

- **Required on all functions**: Return types and all parameters
- **Required on class attributes**: Use type annotations for all class variables
- **Use | appropriately**: `type | None` for nullable values
- **Generic types**: Prefer `list[str]`, `dict[str]` over `List[str]`, `Dict[str, Any]`

### Async/Await Patterns

- **All I/O operations must be async**: Database queries, API calls, file operations
- **Use `asyncio` properly**: Never block the event loop
- **Async context managers**: Use `async with` for database sessions

### Python Code Organization

- **Import order**: Standard library → Third-party → Local imports
- **Use `__all__` in `__init__.py`**: Explicitly export public APIs
- **Google-style docstrings**: Required for all public functions/classes
- **Pydantic/dataclasses.dataclass/typing.NamedTuple**: For all data structures

## SERVICE ARCHITECTURE

### Key Database Models (if any)

{Description of key database models and their relationships}

### External Service Integration (if any)

{Description of any external services the project interacts with, e.g., LLMs, APIs}

### {Other Architectural Patterns}

## CRITICAL IMPLEMENTATION PATTERNS

### {placeholder for specific implementation patterns}

### Async Database Sessions

{Python code example for async database sessions in this project}

### Background Jobs with FastAPI

{Python code example for background jobs using FastAPI's `BackgroundTasks` from this project}

### Structured LLM Outputs

{Python code example for structured LLM outputs, e.g., using Pydantic models from this project}

### Logging Pattern

{Description of the logging pattern used in this project}

### Error Handling Pattern

{Description of the error handling pattern used in this project}

## API PATTERNS

### FastAPI Dependencies

{List of FastAPI dependencies used in this project}

### API Response Models

{List of Pydantic models used for API responses}

## DEVELOPMENT WORKFLOW

### Running Services

{Commands to run the application, e.g., using Docker or directly with FastAPI}

### Testing Strategy

- **Unit tests** (`tests/unittests/`): Mock all external dependencies
- **Integration tests** (`tests/integrationtests/`): Use real database
- **Fixtures**: Use `pytest` fixtures for common test data
- **Async tests**: Always use `pytest.mark.asyncio` decorator
- **Coverage target**: 80%+ for critical code

```bash  
make unittests          # Run unit tests only
make integrationtests   # Run integration tests only
```  

## QUALITY CHECKS

### Required Checks (All Must Pass)

```bash  
make format      # Ruff formatting
make lint        # Ruff linting
make typing      # MyPy type checking
make unittests   # Unit tests
make integrationtests  # Integration tests
```  

Or use pre-commit: `pre-commit run`

### Python-Specific Quality Tools

- **Ruff**: Fast Python linter & formatter
- **MyPy**: Static type checking

## ENVIRONMENT CONFIGURATION

### Configuration Management

- **Use environment variables**: Never hardcode secrets
- **Pydantic Settings**: Use `pydantic_settings.BaseSettings` for config validation
- **`.env` files**: For local development only

### Required Environment Variables

Read necessary environment variables from `.env.example`.

## DEFINITION OF DONE

Code is considered complete only when ALL of the following are satisfied:

- ✅ Code formatting passes: `make format`
- ✅ Linting checks pass: `make lint`
- ✅ Type checking passes: `make typing`
- ✅ Unit tests pass: `make unittests`
- ✅ Integration tests pass: `make integrationtests`
- ✅ Feature is fully functional end-to-end
- ✅ Old/replaced code has been removed
- ✅ All public functions have docstrings