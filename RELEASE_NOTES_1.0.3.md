# Khora Kernel 1.0.3 Release Notes

This release contains various bug fixes, security enhancements, and new features to improve the stability and usability of the Khora Kernel.

## 🛠️ Bug Fixes

- **Fixed Playwright template path in plugin.py** - Corrected the template path in the Playwright plugin to properly locate templates.
- **Fixed pre-commit YAML rendering** - Moved the precommit config to template directory for proper Jinja rendering.
- **Fixed Python package discovery for tests** - Added proper `__init__.py` files to the test directories to resolve import issues.
- **Fixed self_test.py KG validation** - Treat missing Knowledge Graph as a warning rather than an error.
- **Fixed GitHub Actions output handling** - Replaced manual file hacks in `context-delta.yml` workflow.
- **Fixed `.gitignore` for generated `.khora/` directory** - Updated gitignore patterns to handle both `.khora/` and `.khora`.

## ✨ New Features

- **Added graph renderer for Knowledge Graph** - Implemented `render_kg.py --format graph` option to visualize knowledge graphs.
- **Added TruffleHog exclude stub** - Added well-documented template for excluding false positives in security scans.
- **Added tests for repo_inspect** - Added minimal test suite for the repo inspection functionality.

## 🔒 Security

- **Enhanced TruffleHog configuration** - Added a properly documented exclude file to reduce false positives.

## 🧹 Housekeeping

- **Removed duplicate knowledge docs** - Deduplicated Knowledge Graph reference docs by keeping the one in `/docs` directory.

## ✅ Validation & Testing

The Khora Kernel 1.0.3 release has passed:
- All self-tests (`python .khorkernel/scripts/self_test.py`)
- All pre-commit checks (`pre-commit run --all-files`)
- All pytest tests (`pytest`)
- repo_inspect heuristic score ≥ 95/100
