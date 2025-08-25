#!/bin/bash
# A simple script to lint, fix, sort imports, and format Python code

echo ">> Running Ruff (lint & fix)..."
ruff check . --fix

echo ">> Sorting imports with isort..."
isort .

echo ">> Formatting code with Black..."
black .

echo ">> All done"
