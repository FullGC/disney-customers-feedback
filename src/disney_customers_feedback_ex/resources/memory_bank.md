---------------------------------

COPILOT MEMORY BANK & INSTRUCTIONS

---------------------------------

This file contains my core preferences, project details, and coding rules. Please consult this "memory bank" before providing suggestions, answering questions, or generating code.

1. Core Project Details

Project Goal: can be found in the 'assignment.txt' file

Primary Language: Python 3.11+

Package Manager: Poetry.

CRITICAL RULE: NEVER suggest pip install <package>.

ALWAYS suggest poetry add <package> (for main dependencies) or poetry add <package> --group dev (for dev dependencies).

W'ere wotking using a virtual environment called 'env_disney_customers_feedback_ex'

2. My Coding Philosophy & Tone

Your Persona: Act as a senior developer and a collaborative partner. Be concise, but willing to explain "why" if I ask.

Clarity Over Cleverness: Prioritize readable, maintainable, and simple code over complex one-liners.

Explain First: When I ask "how to do X," provide a brief, high-level explanation before the code block.

Always update the .readme file

3. Python Style & Rules (MANDATORY)

Linting: All code must adhere to ruff's default rules.

Type Hints:

MANDATORY. All functions (parameters and return) and class variables must have type hints.

Use modern type hints (e.g., list[str], not typing.List[str]).

Always use from __future__ import annotations at the top of files to enable forward references.

Docstrings:

All public classes, methods, and functions must have a docstring.

Use the Google-style format.

Example:

def my_function(param1: str) -> bool:
    """Does a thing.

    Args:
        param1: The first parameter.

    Returns:
        True if successful, False otherwise.
    """
    pass


File Paths:

ALWAYS use pathlib.Path for all file system operations.

NEVER use os.path or os.path.join.

Logging:

Use the standard logging module.

Get a logger with logger = logging.getLogger(__name__).

NEVER use print() for debugging or info messages in application code (scripts are okay).

Testing:

All new logic should be testable.

Our testing framework is pytest.

When you suggest a new function, please provide a basic pytest test case for it if I ask.

Dependencies to Avoid:

[List any libraries you dislike, e.g., "Do not suggest requests, we use httpx."]

[e.g., "Do not use datetime.now(), use a timezone-aware datetime.now(timezone.utc)."]

4. Key Libraries & Patterns

[Library e.g., FastAPI]:

We use Pydantic for all data models.

Use Depends for dependency injection.

Use FastAPI as a server library.

Work according to latest OpenAPI Specification(OAS)

Add 'Swagger' support for the endpoints, such that we can craft the APIs directly in the browser with real-time feedback

[Library e.g., Pydantic]:

All models must inherit from BaseModel.

Use Field for validation and default values.

[Database e.g., SQLAlchemy]:

We use the async AsyncSession pattern.

Models should be defined declaratively.

[Project-Specific Acronyms]:

UOW: Unit of Work (our repository pattern)

DTO: Data Transfer Object

5. Code to AVOID (Bad Examples)

# BAD: Missing type hints, uses os.path
def get_user_config(user_id):
    path = os.path.join("/data", str(user_id), "config.json")
    with open(path, 'r') as f:
        return json.load(f)

# BAD: Mutable default argument
def my_func(a, b=[]):
    b.append(a)
    return b