#!/bin/bash
# Startup shell script for the Continuous News Aggregator Runner
#
# This script starts the continuous runner with predefined settings:
# - 1 minute intervals between runs
# - No maximum iterations (runs indefinitely)
# - INFO logging level
# - Console-only logging (no log file)

echo "============================================================"
echo "Starting Continuous News Aggregator Runner"
echo "============================================================"
echo "Settings:"
echo "  - Interval: 1 minute"
echo "  - Max iterations: Unlimited"
echo "  - Log level: INFO"
echo "  - Log output: Console only"
echo "============================================================"
echo
echo "Press Ctrl+C to stop the runner gracefully"
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the parent directory (where continuous_runner.py is located)
cd "$SCRIPT_DIR/.."

# Start the continuous runner
poetry run python continuous_runner.py --interval 1m --no-log-file --log-level INFO

echo
echo "Newsbot runner has stopped."
