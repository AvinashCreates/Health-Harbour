#!/bin/sh
set -eu

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$DB_PASSWORD" \
  --set=keycloak_password="$KEYCLOAK_DB_PASSWORD" \
  --set=hapi_password="$HAPI_DB_PASSWORD" <<'SQL'
CREATE ROLE healthapp LOGIN PASSWORD :'app_password';
CREATE DATABASE healthcare_exchange OWNER healthapp;

CREATE ROLE keycloak LOGIN PASSWORD :'keycloak_password';
CREATE DATABASE keycloak OWNER keycloak;

CREATE ROLE hapi LOGIN PASSWORD :'hapi_password';
CREATE DATABASE hapi_fhir OWNER hapi;
SQL
