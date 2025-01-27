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