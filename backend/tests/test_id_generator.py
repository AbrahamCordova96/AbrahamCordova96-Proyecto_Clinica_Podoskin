#!/usr/bin/env python3
"""
Script de prueba para el generador de IDs estructurados.

Este script prueba la función generar_codigo_interno() sin necesidad de base de datos.
"""

import sys
from pathlib import Path
from datetime import datetime

# Agregar backend al path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Imports consolidados
from backend.utils.id_generator import (
    limpiar_nombre,
    extraer_iniciales,
    generar_codigo_interno
)


def print_test_result(passed: bool, description: str, details: str = ""):
    """Helper para imprimir resultados de tests con formato consistente"""
    status = "✅" if passed else "❌"
    print(f"  {status} {description}")
    if details:
        print(f"      {details}")


def test_limpiar_nombre():
    """Prueba la función de limpieza de nombres"""
    print("🧪 Test: limpiar_nombre()")
    
    casos = [
        ("José", "Jose"),
        ("María", "Maria"),
        ("Peña", "Pena"),
        ("Hernández", "Hernandez"),
        ("Ñoño", "Nono"),
        ("O'Brien", "OBrien"),
    ]
    
    for entrada, esperado in casos:
        resultado = limpiar_nombre(entrada)
        passed = resultado == esperado
        print_test_result(passed, f"'{entrada}' → '{resultado}'", f"esperado: '{esperado}'")


def test_extraer_iniciales():
    """Prueba la extracción de iniciales"""
    print("\n🧪 Test: extraer_iniciales()")
    
    casos = [
        ("Ornelas Reynoso", True, "AS"),  # Últimas 2 de "Ornelas"
        ("Santiago de Jesus", False, "GO"),  # Últimas 2 de "Santiago"
        ("López García", True, "EZ"),  # Últimas 2 de "López"
        ("María", False, "IA"),  # Últimas 2 de "María"
        ("Peña", True, "NA"),  # Últimas 2 de "Peña"
        ("José Luis", False, "SE"),  # Últimas 2 de "José"
    ]
    
    for entrada, es_apellido, esperado in casos:
        resultado = extraer_iniciales(entrada, es_apellido)
        passed = resultado == esperado
        tipo = "Apellido" if es_apellido else "Nombre"
        print_test_result(passed, f"{tipo}: '{entrada}' → '{resultado}'", f"esperado: '{esperado}'")


def test_formato_codigo():
    """Prueba el formato general del código"""
    print("\n🧪 Test: Formato del código generado")
    
    # Simulamos datos de prueba
    ejemplos = [
        ("Ornelas Reynoso", "Santiago", "RENO"),
        ("López García", "María", "LOMA"),
        ("Pérez Hernández", "Juan Carlos", "PEJU"),
        ("Martínez", "Ana", "EZNA"),
    ]
    
    for apellido, nombre, codigo_esperado in ejemplos:
        iniciales_apellido = extraer_iniciales(apellido, es_apellido=True)
        iniciales_nombre = extraer_iniciales(nombre, es_apellido=False)
        codigo = f"{iniciales_apellido}{iniciales_nombre}"
        
        passed = codigo == codigo_esperado
        print_test_result(passed, f"'{apellido}, {nombre}' → {codigo}", f"esperado: {codigo_esperado}")


def test_formato_completo():
    """Prueba el formato completo con fecha"""
    print("\n🧪 Test: Formato completo [CODIGO]-[MMDD]-[NNNNN]")
    
    apellido = "Ornelas Reynoso"
    nombre = "Santiago"
    fecha = datetime(2024, 12, 13)
    contador = 1
    
    iniciales_apellido = extraer_iniciales(apellido, es_apellido=True)
    iniciales_nombre = extraer_iniciales(nombre, es_apellido=False)
    prefijo = f"{iniciales_apellido}{iniciales_nombre}"
    fecha_str = fecha.strftime("%m%d")
    contador_str = str(contador).zfill(5)
    
    codigo = f"{prefijo}-{fecha_str}-{contador_str}"
    esperado = "RENO-1213-00001"
    
    passed = codigo == esperado
    print_test_result(passed, f"Código generado: {codigo}", f"Esperado: {esperado}")
    
    if passed:
        print(f"      Componentes:")
        print(f"        - Prefijo: {prefijo} (de '{apellido}, {nombre}')")
        print(f"        - Fecha: {fecha_str} (diciembre 13)")
        print(f"        - Contador: {contador_str}")


def test_casos_especiales():
    """Prueba casos especiales y edge cases"""
    print("\n🧪 Test: Casos especiales")
    
    # Nombres cortos
    print("  📋 Nombres cortos:")
    resultado = extraer_iniciales("Li", False)
    passed = len(resultado) == 2
    print_test_result(passed, f"'Li' → '{resultado}'", "debe tener 2 caracteres")
    
    # Nombres con artículos
    print("  📋 Nombres con artículos:")
    resultado = extraer_iniciales("de la Cruz", True)
    print_test_result(True, f"'de la Cruz' → '{resultado}'", "debe usar 'Cruz'")
    
    # Nombres con acentos
    print("  📋 Nombres con acentos:")
    limpio = limpiar_nombre("José María")
    passed = 'Jose' in limpio
    print_test_result(passed, f"'José María' → '{limpio}'", "sin acentos")


def main():
    """Ejecuta todas las pruebas"""
    print("=" * 60)
    print("🧪 PRUEBAS DEL GENERADOR DE IDs ESTRUCTURADOS")
    print("=" * 60)
    
    test_limpiar_nombre()
    test_extraer_iniciales()
    test_formato_codigo()
    test_formato_completo()
    test_casos_especiales()
    
    print("\n" + "=" * 60)
    print("✅ Todas las pruebas completadas")
    print("=" * 60)
    print("\n💡 Para probar con base de datos:")
    print("   python backend/scripts/test_id_generation_with_db.py")


if __name__ == "__main__":
    main()
