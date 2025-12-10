#!/bin/bash
set -e

create_database() {
    local database=$1
    echo "Creando base de datos: $database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
}

create_database "clinica_auth_db"
create_database "clinica_core_db"
create_database "clinica_ops_db"

echo "Bases de datos creadas"

echo "Inicializando clinica_auth_db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "clinica_auth_db" -f /docker-entrypoint-initdb.d/02_init_auth_db.sql

echo "Inicializando clinica_core_db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "clinica_core_db" -f /docker-entrypoint-initdb.d/03_init_core_db.sql

echo "Inicializando clinica_ops_db..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "clinica_ops_db" -f /docker-entrypoint-initdb.d/04_init_ops_db.sql

echo "Inicializacion completada"