#!/bin/bash
# =============================================================================
# Backup Script for PodoSkin Databases
# NOM-024 Compliance: Automated daily backups
# =============================================================================
# Este script realiza backups automáticos de las 3 bases de datos del sistema.
# Guarda los backups con timestamp para mantener histórico.
# 
# USO:
#   ./backup_database.sh              # Backup manual
#   crontab: 0 2 * * * /path/to/backup_database.sh  # Diario a las 2 AM
# =============================================================================

set -e  # Exit on error

# Configuración
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="podoskin-db"
DB_USER="podoskin"

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Crear directorio de backups si no existe
mkdir -p "$BACKUP_DIR"

echo "=========================================="
echo "PodoSkin Database Backup - NOM-024"
echo "Fecha: $(date)"
echo "=========================================="

# Función para hacer backup de una base de datos
backup_database() {
    local db_name=$1
    local backup_file="${BACKUP_DIR}/backup_${db_name}_${DATE}.sql"
    
    echo -n "Backing up ${db_name}... "
    
    if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$db_name" > "$backup_file" 2>/dev/null; then
        # Comprimir el backup
        gzip "$backup_file"
        echo -e "${GREEN}✓ OK${NC} (${backup_file}.gz)"
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Verificar que el contenedor existe
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}ERROR: Container ${CONTAINER_NAME} not found${NC}"
    echo "Make sure Docker Compose is running: docker-compose up -d"
    exit 1
fi

# Verificar que el contenedor está corriendo
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}ERROR: Container ${CONTAINER_NAME} is not running${NC}"
    exit 1
fi

# Realizar backups de las 3 bases de datos
backup_database "clinica_auth_db"
backup_database "clinica_core_db"
backup_database "clinica_ops_db"

# Limpiar backups antiguos (mantener últimos 30 días)
echo -n "Cleaning old backups (>30 days)... "
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete 2>/dev/null
echo -e "${GREEN}✓ OK${NC}"

# Resumen
echo "=========================================="
echo "Backup completado exitosamente"
echo "Ubicación: $BACKUP_DIR"
echo "Archivos generados:"
ls -lh "$BACKUP_DIR"/backup_*_${DATE}.sql.gz 2>/dev/null || echo "No files found"
echo "=========================================="

# Opcional: Subir a almacenamiento remoto (descomentar si se configura)
# echo "Uploading to remote storage..."
# rclone copy "$BACKUP_DIR" remote:podoskin-backups/

exit 0
