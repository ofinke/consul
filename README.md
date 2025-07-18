# **Consul 🧑‍🔬**

Consul is a set of simple CLI based LLM Tools and Agents for my personal needs. Focus is mainly on agents for assistance with Python code development. The library is build on top of `langgraph` framework. The project is under MIT license.


# Installation

## Environment variables


## Local

For local project installation, run

```bash
uv sync --all-extras --frozen
```

Cli interface can be then called with

```bash
uv run consul
```


## Global

For global installation, from project root directory run either
```bash
pip install -e .
```
or to install it in separate venv with
```bash
pipx install -e .
```

CLI is then invoked by calling

```bash
consul
```
