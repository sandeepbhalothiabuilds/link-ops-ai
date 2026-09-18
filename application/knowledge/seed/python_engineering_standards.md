# Python engineering standards

Use Python 3.12, explicit type hints, small modules, Pydantic validation at system
boundaries, and deterministic tests. Domain logic must not depend on the web framework.
Prefer interfaces for persistence and messaging so local tests do not require AWS.
