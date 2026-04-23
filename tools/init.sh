#!/bin/bash

# Initializes environment variables for the videoreg project
# Usage: source tools/init.sh (from the project root)

# Project root — the directory from which the script is sourced
export VIDEOREG_PROJECT_HOME="$PWD"

# Path to the tools/bin directory
export VIDEOREG_TOOLS_HOME="$VIDEOREG_PROJECT_HOME/tools/bin"

# Add tools/bin to PATH so scripts can be called directly
export PATH="$VIDEOREG_TOOLS_HOME:$PATH"
