#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PROJECT_ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT_DIR"

echo "Current working directory: $(pwd)"
echo "Starting Python extract script..."

python3 extract.py \

EXIT_CODE=$? 
if [ $EXIT_CODE -eq 0 ]; then
    echo "Python extract script finished successfully at $(date)."
else
    echo "Python extract script failed with exit code $EXIT_CODE at $(date)."
fi