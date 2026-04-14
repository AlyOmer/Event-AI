#!/bin/bash
# Using uv to run the server
# Make sure you are in the packages/agentic_event_orchestrator directory

# uv run automatically handles virtual environment creation and dependency installation from pyproject.toml
uv run python3 server.py
