#!/usr/bin/env python3
# Khora Kernel - Playwright Plugin v1.0.2
# Adds browser testing capabilities to the project

import pathlib
import os
import sys

def render(project_root, manifest, jinja_env):
    """
    Main entry point for the Playwright plugin.
    
    Args:
        project_root (pathlib.Path): Path to the project root
        manifest (dict): The parsed KERNEL_MANIFEST.yaml contents
        jinja_env (jinja2.Environment): Configured Jinja environment
    """
    print("Running Playwright plugin...")
    
    # Get the project name from the manifest
    project_name = manifest.get('project', 'khora-app')
    
    # Create the Playwright test directory structure
    tests_dir = project_root / "tests" / "ui"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    fixtures_dir = tests_dir / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    
    pages_dir = tests_dir / "pages"
    pages_dir.mkdir(exist_ok=True)
    
    screenshots_dir = tests_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    
    # Create configuration files
    
    # 1. playwright.config.py
    config_content = """# Playwright Configuration

from playwright.sync_api import Page, expect
import os
from typing import Dict, Any

# See https://playwright.dev/python/docs/test-configuration
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "smoke: mark test as a smoke test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as a slow test"
    )

# Base URL for all tests
BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")

# Test options
DEFAULT_TIMEOUT = 30000  # 30 seconds
SCREENSHOT_ON_FAILURE = True
TRACE_ON_FAILURE = True

# Browser configurations
browser_configs = {
    "chromium": {
        "headless": True,
        "slow_mo": 100 if os.environ.get("DEBUG") else 0,
        "viewport": {"width": 1280, "height": 720},
        "screenshot": "only-on-failure",
        "video": "retain-on-failure",
        "trace": "retain-on-failure",
    },
    "firefox": {
        "headless": True,
        "slow_mo": 100 if os.environ.get("DEBUG") else 0,
        "viewport": {"width": 1280, "height": 720},
        "screenshot": "only-on-failure",
        "video": "retain-on-failure",
        "trace": "retain-on-failure",
    },
}

# Directory paths
SCREENSHOT_DIR = "tests/ui/screenshots"
TRACE_DIR = "tests/ui/traces"
VIDEO_DIR = "tests/ui/videos"

def pytest_addoption(parser):
    parser.addoption("--browser", default="chromium", help="Browser to run tests on")
    parser.addoption("--headed", action="store_true", default=False, help="Run tests in headed mode")
    parser.addoption("--slowmo", default=0, help="Slow down execution by ms")
    parser.addoption("--device", default=None, help="Run tests on a specific device emulation")

# Create directories if they don't exist
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(TRACE_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
"""
    
    (tests_dir / "playwright.config.py").write_text(config_content)
    
    # 2. conftest.py
    # Load the template
    conftest_template = jinja_env.get_template("conftest.py.j2")
    # Render the template (no variables needed for now)
    conftest_content_rendered = conftest_template.render()
    # Write the rendered content
    (tests_dir / "conftest.py").write_text(conftest_content_rendered)
    
    # 3. Page object model example
    page_model_content = """# Page Object Model for Home Page

from playwright.sync_api import Page, expect

class HomePage:
    def __init__(self, page: Page):
        self.page = page
        self.url = "/"
        self.title = page.locator("h1")
        self.login_button = page.locator("text=Login")
        self.register_button = page.locator("text=Register")
    
    def navigate(self):
        self.page.goto(self.url)
        return self
    
    def go_to_login(self):
        self.login_button.click()
        # Wait for navigation
        self.page.wait_for_url("**/login")
    
    def go_to_register(self):
        self.register_button.click()
        # Wait for navigation
        self.page.wait_for_url("**/register")
    
    def get_title_text(self) -> str:
        return self.title.text_content()
    
    # Add more methods as needed
"""
    
    (pages_dir / "home_page.py").write_text(page_model_content)
    
    # 4. Sample test
    test_content = """# Sample Playwright Test

import pytest
from playwright.sync_api import Page, expect

from ..pages.home_page import HomePage

@pytest.mark.smoke
def test_home_page_loads(page: Page):
    # Navigate to the home page
    page.goto("/")
    
    # Expect the page to have a title
    expect(page).to_have_title(containing="${project}")

@pytest.mark.smoke
def test_home_page_using_page_object(page: Page):
    # Initialize our page object
    home_page = HomePage(page)
    
    # Navigate using the page object
    home_page.navigate()
    
    # Verify title text
    title_text = home_page.get_title_text()
    assert title_text, "Title should not be empty"
    
    # Verify navigation is possible
    home_page.go_to_login()
    expect(page).to_have_url(containing="/login")
"""
    
    test_content = test_content.replace("${project}", project_name)
    (tests_dir / "test_home.py").write_text(test_content)
    
    # 5. Create a test fixture
    fixture_content = """# Example Test Fixtures

import pytest
from typing import Dict, Any

# Sample user data fixture
@pytest.fixture
def user_data() -> Dict[str, Any]:
    return {
        "email": "test@example.com",
        "password": "securepassword123",
        "username": "testuser",
    }

# Sample authenticated user fixture
@pytest.fixture
def authenticated_page(page, user_data):
    # Navigate to login page
    page.goto("/login")
    
    # Fill the login form
    page.fill("input[name='email']", user_data["email"])
    page.fill("input[name='password']", user_data["password"])
    
    # Submit the form
    page.click("button[type='submit']")
    
    # Wait for navigation to complete
    page.wait_for_url("**/dashboard")
    
    # Verify we're logged in (adjust selector based on your app)
    assert page.is_visible("text=Dashboard"), "Login failed"
    
    return page
"""
    
    (fixtures_dir / "authentication.py").write_text(fixture_content)
    
    # 6. Create a requirements file
    requirements_content = """# UI testing requirements
playwright==1.35.0
pytest==7.3.1
pytest-playwright==0.3.3
"""
    
    (tests_dir / "requirements.txt").write_text(requirements_content)
    
    # 7. Create a README.md for the tests
    readme_content = f"""# {project_name} UI Tests

This directory contains UI tests for {project_name} using Playwright.

## Structure

```
tests/ui/
├── conftest.py             # Pytest configuration
├── playwright.config.py    # Playwright configuration
├── requirements.txt        # Dependencies
├── fixtures/               # Test fixtures
│   └── authentication.py   # Authentication helpers
├── pages/                  # Page object models
│   └── home_page.py        # Home page model
├── screenshots/            # Test failure screenshots
└── test_*.py               # Test files
```

## Installation

Install the required dependencies:

```bash
pip install -r tests/ui/requirements.txt
playwright install
```

## Running Tests

Run all UI tests:

```bash
pytest tests/ui/
```

Run only smoke tests:

```bash
pytest tests/ui/ -m smoke
```

Run with a specific browser:

```bash
pytest tests/ui/ --browser firefox
```

Run in headed mode (to see the browser):

```bash
pytest tests/ui/ --headed
```

## Writing Tests

Follow these best practices:

1. Use the Page Object Model pattern for maintainability
2. Add appropriate markers (@pytest.mark.smoke, etc.)
3. Leverage fixtures for common setup tasks
4. Use descriptive test names that explain the behavior

## CI/CD Integration

These tests are automatically run in CI via GitHub Actions workflow.
"""
    
    (tests_dir / "README.md").write_text(readme_content)
    
    # Create GitHub workflow for Playwright tests
    workflow_dir = project_root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    playwright_workflow_content = """name: UI Tests

on:
  push:
    branches: [ main ]
    paths:
      - 'src/**'
      - 'tests/ui/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'src/**'
      - 'tests/ui/**'

jobs:
  playwright:
    name: 'Playwright Tests'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r tests/ui/requirements.txt
      
      - name: Install Playwright browsers
        run: |
          playwright install chromium
      
      - name: Ensure API is running
        run: |
          # Start your application in the background
          # This could be a docker-compose setup or direct application start
          # For example:
          # docker-compose up -d
          # Or: python -m src.app.api &
          # Sleep to allow startup
          sleep 10
      
      - name: Run Playwright tests
        run: |
          pytest tests/ui/ -v --browser chromium
      
      - name: Upload test artifacts
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-artifacts
          path: |
            tests/ui/screenshots/
            tests/ui/traces/
            tests/ui/videos/
          retention-days: 7
"""
    
    (workflow_dir / "playwright.yml").write_text(playwright_workflow_content)
    
    print(f"✅ Playwright testing framework created in {tests_dir.relative_to(project_root)}")
    print("  Note: You'll need to customize the tests for your specific application.")
    print(f"✅ GitHub workflow for Playwright tests created in {workflow_dir.relative_to(project_root)}/playwright.yml")
    
    return True