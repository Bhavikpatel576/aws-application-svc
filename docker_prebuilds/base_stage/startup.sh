#!/bin/sh

# Abort on any error (including if wait-for-it fails).
set -e

# Wait for the db to be up
/opt/startup/wait-for-it.sh db:5432
# Add some sleep because it lies about being ready
sleep 5

# Okay now go
exec "$@"