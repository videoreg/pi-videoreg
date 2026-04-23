#!/bin/bash

# Parse command-line arguments
VIDEOREG_PROJECT_HOME=""
LOG_LEVEL="INFO"  # Default value
ENV=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --videoreg-project-home)
            VIDEOREG_PROJECT_HOME="$2"
            shift 2
            ;;
        --log-level)
            if [[ "$2" =~ ^(DEBUG|INFO|WARNING|ERROR)$ ]]; then
                LOG_LEVEL="$2"
                shift 2
            else
                echo "Error: invalid value for --log-level: $2"
                echo "Allowed values: DEBUG, INFO, WARNING, ERROR"
                exit 1
            fi
            ;;
        --env)
            ENV="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 --videoreg-project-home <path> [--log-level <level>] [--env <env>]"
            exit 1
            ;;
    esac
done

# Check that the working directory is specified
if [ -z "$VIDEOREG_PROJECT_HOME" ]; then
    echo "Error: working directory not specified"
    echo "Usage: $0 --videoreg-project-home <path> [--log-level <level>]"
    exit 1
fi

# Check that the directory exists
if [ ! -d "$VIDEOREG_PROJECT_HOME" ]; then
    echo "Error: directory $VIDEOREG_PROJECT_HOME does not exist"
    exit 1
fi

PYTHON_CMD="\"$VIDEOREG_PROJECT_HOME/.venv/bin/python3\" \"$VIDEOREG_PROJECT_HOME/run.py\" --service=\"vrg-camera\" --videoreg-project-home=\"$VIDEOREG_PROJECT_HOME\" --log-level=\"$LOG_LEVEL\""
if [[ -n "$ENV" ]]; then
    PYTHON_CMD="$PYTHON_CMD --env=\"$ENV\""
fi
eval $PYTHON_CMD