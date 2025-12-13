-- ============================================================================
-- MIGRACIÓN 001: Agregar campos obligatorios NOM-024-SSA3-2012
-- Fecha: 13 de diciembre de 2024
-- ============================================================================

-- Ver archivo completo en:
-- backend/schemas/migrations/001_add_nom024_fields.sql

-- Este archivo contiene:
-- 1. Campos obligatorios de pacientes (CURP, domicilio estructurado, etc.)
-- 2. Médico asignado vs médico que atendió
-- 3. Trigger de inmutabilidad en audit_log
-- 4. Tablas nuevas: access_log, firmas_electronicas, intercambio_expedientes
-- 5. Índices y constraints

-- Ejecutar con: psql -U podoskin < 001_add_nom024_fields.sql
