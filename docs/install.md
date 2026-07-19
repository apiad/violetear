# Installation

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) or pip

## Core package

The core package provides the styling and markup layers with **zero dependencies**:

```bash
pip install violetear
```

or with uv:

```bash
uv add violetear
```

## Full-stack extras

To build interactive full-stack apps (adds FastAPI + uvicorn):

```bash
pip install "violetear[server]"
```

or with uv:

```bash
uv add "violetear[server]"
```

## Development install

```bash
git clone https://github.com/apiad/violetear.git
cd violetear
uv sync --all-extras
```

Run tests:

```bash
uv run pytest tests/
```
