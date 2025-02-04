# Twitter agent example

### Setup
```shell
cp template.env .env
# Edit .env
```

### Run
```shell
python agent.py
```

### Tests
```shell
python -m pytest tests
```

### Test outputs locally
```shell
python testing.py --help

python testing.py --type perplexity --count 1

python testing.py --type search --count 1
```
