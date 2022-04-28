all: pylint coverage

pylint: pylint_pkg pylint_tests
.PHONY: pylint

pylint_pkg:
	pylint apitoolbox
.PHONY: pylint_pkg

pylint_tests:
	pylint tests  --disable=missing-docstring,unused-argument,too-many-ancestors,unexpected-keyword-arg,duplicate-code
.PHONY: pylint_tests

test:
	pytest -xvv tests
.PHONY: test

coverage:
	pytest --cov=apitoolbox --cov-report=term-missing --cov-fail-under=100 tests/
.PHONY: coverage

clean:
	rm -rf build dist *.egg-info
	find apitoolbox tests -name __pycache__ -prune -exec rm -rf '{}' ';'
.PHONY: clean
