#!/usr/bin/env bash
set -euo pipefail

echo "🔬 Running unit tests..."

# Optional: Activate virtual environment if needed
# source .venv/bin/activate

# Run pytest for unit tests only
pytest tests/unit \
  --disable-warnings \
  --tb=short \
  -q

echo "✅ Unit tests passed."
