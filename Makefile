.PHONY: test test-cov lint type-check format check-all install-dev clean

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt
	pip install -e .

# Run all tests
test:
	pytest tests/ -v

# Run tests with coverage report
test-cov:
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

# Lint the code
lint:
	flake8 tunatale/ tests/
	black --check tunatale/ tests/
	isort --check-only tunatale/ tests/

# Run type checking
type-check:
	mypy tunatale/ tests/

# Format the code
format:
	black tunatale/ tests/
	isort tunatale/ tests/

# Run all checks
check-all: lint type-check test

# Clean up
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]'`
	rm -f `find . -type f -name '*~'`
	rm -f `find . -type f -name '.*~'`
	rm -rf .cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
	rm -f .mypy_cache
	rm -rf .pytest_cache
	
# Show help
help:
	@echo "Available commands:"
	@echo "  install-dev   Install development dependencies"
	@echo "  test          Run tests"
	@echo "  test-cov      Run tests with coverage report"
	@echo "  lint          Run code linters"
	@echo "  type-check    Run static type checking"
	@echo "  format        Format code"
	@echo "  check-all     Run all checks (lint, type-check, test)"
	@echo "  clean         Clean up generated files"
	@echo "  help          Show this help message"
