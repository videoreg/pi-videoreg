#!/bin/bash

# Parse command-line arguments
VIDEOREG_PROJECT_HOME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --videoreg-project-home)
            VIDEOREG_PROJECT_HOME="$2"
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Usage: $0 --videoreg-project-home <path>"
            exit 1
            ;;
    esac
done

# Check that the working directory is specified
if [ -z "$VIDEOREG_PROJECT_HOME" ]; then
    echo "Error: working directory not specified"
    echo "Usage: $0 --videoreg-project-home <path>"
    exit 1
fi

# Check that the directory exists
if [ ! -d "$VIDEOREG_PROJECT_HOME" ]; then
    echo "Error: directory $VIDEOREG_PROJECT_HOME does not exist"
    exit 1
fi

mediamtx $VIDEOREG_PROJECT_HOME/mediamtx.yml