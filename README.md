# rlberry 

![pytest](https://github.com/rlberry-py/rlberry/workflows/test/badge.svg)


# Install

Creating a virtual environment and installing:

```
conda create -n rlberry python=3.7
conda activate rlberry
pip install -e .
```

# Tests

To run tests, run `pytest`.

With coverage: install and run pytest-cov
```
pip install pytest-cov
pytest --cov=rlberry --cov-report html:cov_html
```

