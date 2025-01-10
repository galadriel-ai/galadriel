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

## when using CLI - IMPORTANT

After running `agent init` you'll need:
1.  to copy the `galadriel-agent` folder to the root of the project.
2. add the following line to `docker-compose.yml`, inside the `volumes` section:
    ```
    - ./galadriel-agent:/home/appuser/galadriel-agent
    ```
explanation:
- galadriel-agent is not yet a package, so we need to mount it as a volume inside the docker container.
- this is a temporary solution until the package is published on pypi.
