# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Consul is a CLI-based LLM tool and agent framework built on LangChain/LangGraph for Python code development assistance. It provides configurable AI flows for different tasks like chat and documentation generation.

## Development Commands

### Package Management
- `uv sync` - Sync dependencies from uv.lock
- `uv add <package>` - Add a new dependency
- `uv run <command>` - Run commands in the project environment

### Code Quality
- `uv run ruff check` - Run linting checks
- `uv run ruff format` - Format code
- `uv run ruff check --fix` - Auto-fix linting issues

### Running the Application
- `uv run consul` - Start the CLI application
- `uv run consul --flow chat` - Start chat flow (default)
- `uv run consul --flow docs` - Start documentation agent flow
- `uv run consul --help` - Show CLI help

## Architecture

### Core Components
- **Flows**: Base flow system in `src/consul/flows/base.py` - abstract classes for LangGraph-based tasks
- **Configuration**: YAML-based flow configs in `configs/` directory define LLM settings and prompts
- **CLI**: Click-based interface in `src/consul/cli/main.py` with flow selection and conversation memory

### Flow System
The application uses a flow-based architecture where each "flow" is a LangGraph-powered AI agent:

- `BaseFlow` class provides common functionality (LLM setup, graph compilation, execution)
- Flow configs are YAML files that specify LLM models, parameters, and system prompts
- Two main flow types:
  - **ChatTask**: Simple chat interface
  - **ReactAgentFlow**: ReAct framework agent with tools (used for docs flow)

### Key Files
- `src/consul/flows/base.py` - Core flow abstraction and base classes
- `src/consul/flows/tasks/chat.py` - Simple chat implementation
- `src/consul/flows/agents/react.py` - ReAct agent implementation
- `src/consul/core/config/flows.py` - Flow configuration loading and validation
- `configs/*.yaml` - Flow configuration files

### Configuration System
- Flow configs in `configs/` define LLM settings, prompts, and agent parameters
- Settings use Pydantic for validation and environment variable support
- Azure OpenAI integration for LLM backend

### Tools and Agents
The docs flow includes tools like `load_file` and `save_to_markdown` for file operations within the project directory.