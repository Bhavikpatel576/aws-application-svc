#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE "application-service";
    GRANT ALL PRIVILEGES ON DATABASE "application-service" TO postgres;
EOSQL