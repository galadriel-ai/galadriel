# Galadriel Agent development setup 

### Requirement

- Python >=3.10
- Git

### Setup for local development

```shell
pip install -e ".[dev]"
```

## Run an agent example agent
```shell
cd examples/{example}
pip install -r requirements.txt  # if relevant for the example
cp template.env .env  # If relevant for the example
python main.py
```

## Linting, code formatting, type-checking ❗❗❗
```shell
source toolbox.sh
lint
format
type-check
```

## Testing
Ensure that dev dependencies are installed
```shell
source toolbox.sh
unit-test
```
