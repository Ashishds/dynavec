#!/usr/bin/env bash
set -e

echo "========================================"
echo "      Dynavec Local Environment Setup    "
echo "========================================"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 could not be found."
    exit 1
fi
echo "[OK] Found $(python3 --version)"

# 2. Setup .env file
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "[OK] Created .env from .env.example template."
        echo "     Please configure your AWS credentials in .env"
    fi
else
    echo "[OK] Existing .env file found."
fi

# 3. Install dynavec
echo ""
echo "Installing dynavec in editable mode..."
pip install -e ".[all]" || pip install -e ".[dev]"
echo "[OK] Dynavec installed."

# 4. Diagnostics check
echo ""
echo "Running Dynavec diagnostics..."
python3 -m dynavec doctor || true

echo ""
echo "========================================"
echo "Dynavec setup complete!"
echo "To run tests:       pytest -q"
echo "To start dashboard: dynavec dashboard --port 8778"
echo "To run quickstart:  python3 examples/quickstart.py"
echo "========================================"
