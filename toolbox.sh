function lint {
  ruff check
}

function lint-fix {
  ruff check --fix
}

function format {
  ruff format
}

function type-check {
  mypy galadriel/
}

function unit-test {
  python -m pytest tests
}

function cov {
  python -m pytest tests/unit \
    --cov-report html:tests/reports/coverage/htmlcov \
    --cov-report xml:tests/reports/coverage/cobertura-coverage.xml \
    --cov-report term \
    --cov=galadriel
}