#!/bin/bash
set -e

cd /app
source tools/init.sh

exec vrg-run "$@"
