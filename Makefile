all: flake8 pylint coverage

flake8: flake8_pkg flake8_tests
.PHONY: flake8

flake8_pkg:
	flake8 apitoolbox
.PHONY: flake8_pkg

flake8_tests:
	flake8 tests
.PHONY: flake8_tests

pylint: pylint_pkg pylint_tests
.PHONY: pylint

pylint_pkg:
	pylint apitoolbox
.PHONY: pylint_pkg

pylint_tests:
	pylint tests  --disable=missing-docstring,unused-argument,too-many-ancestors,unexpected-keyword-arg
.PHONY: pylint_tests

test:
	pytest -xvv tests
.PHONY: test

coverage:
	pytest --cov=apitoolbox --cov-report=term-missing --cov-fail-under=100 tests/
.PHONY: coverage

pyenv:
	virtualenv -p python3 pyenv
	pyenv/bin/pip install -e .[dev,prod]
.PHONY: pyenv
