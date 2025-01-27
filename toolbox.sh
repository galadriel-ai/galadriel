function lint {
  pylint --rcfile=setup.cfg galadriel_agent/*
}

function format {
  black .
}

function type-check {
  mypy galadriel_agent
}

function unit-test {
  python -m pytest tests
}

function cov {
  python -m pytest tests/unit \
    --cov-report html:tests/reports/coverage/htmlcov \
    --cov-report xml:tests/reports/coverage/cobertura-coverage.xml \
    --cov-report term \
    --cov=galadriel_agent
}