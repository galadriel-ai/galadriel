# Galadriel Agent

## Setup
```shell
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
# or 
pip install -e .

cp template.env .env
nano .env
```

## Run an agent
This takes the agent definition from `agents/daige.json`
```shell
python main.py
```
Can also run in docker
```shell
docker compose up --build
```


## Linting etc
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


## Deployment

```shell
./deploy.sh
```