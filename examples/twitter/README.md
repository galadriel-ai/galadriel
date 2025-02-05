# Twitter agent example

### Install the requirements

It's recommended to use a virtual env

In the root of the repo:
```shell
pip install -e ".[dev]"
```

### Modify the .env

**Paid tier of the Twitter API is required for full functionality,**
for just posting free tier will suffice.

```shell
cp template.env .env
```

### Run

```shell
python agent.py
```

## Deployment

In the root of the repo
```
git pull
source venv/bin/activate
pip install -e ".[dev]"
cd examples/twitter

pgrep -af python
# something like this: 3153266 python agent.py
kill <pid>
# Deploy
nohup python agent.py --name daige > logs.log 2>&1 &

tail -f logs.log -n 100
```


### Tests

```shell
python -m pytest tests
```

### Test outputs locally

This enables changing the code/prompting without actually posting on Twitter :)

```shell
python testing.py --help

python testing.py --type perplexity --count 1

python testing.py --type search --count 1
```

### Generate a quote for a given tweet ID

```shell
python manual_tweet.py --name <agent_name> --tweet_id <tweet_id>
```

It will show the generated tweet and ask if it should post it.
