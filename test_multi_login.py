#!/usr/bin/env python3
"""
Script de prueba para verificar el login multi-método.
Prueba login con username, email y ID estructurado.
"""

import requests
import sys

API_BASE_URL = "http://localhost:8000/api/v1"

def test_login(identifier: str, password: str, method_name: str):
    """Prueba login con un método específico"""
    print(f"\n{'='*60}")
    print(f"🔐 Probando login con {method_name}")
    print(f"{'='*60}")
    print(f"Identifier: {identifier}")
    print(f"Password: {'*' * len(password)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "username": identifier,
                "password": password
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ LOGIN EXITOSO")
            print(f"   Token: {data['access_token'][:50]}...")
            print(f"   Usuario: {data['user']['nombre_usuario']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Rol: {data['user']['rol']}")
            if data['user'].get('has_gemini_key'):
                print(f"   Gemini Key: {data['user']['gemini_key_status']}")
            return True
        else:
            print(f"❌ LOGIN FALLIDO")
            print(f"   Status: {response.status_code}")
            print(f"   Error: {response.json().get('detail', 'Unknown error')}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ ERROR DE CONEXIÓN")
        print(f"   No se pudo conectar al backend en {API_BASE_URL}")
        print(f"   ¿Está corriendo el servidor?")
        return False
    except Exception as e:
        print(f"❌ ERROR INESPERADO: {e}")
        return False


def main():
    print("="*60)
    print("🧪 TEST DE LOGIN MULTI-MÉTODO")
    print("="*60)
    print(f"API: {API_BASE_URL}")
    print()
    
    # Resultados
    results = []
    
    # Test 1: Login con username "admin"
    results.append(test_login("admin", "Admin2024!", "USERNAME (admin)"))
    
    # Test 2: Login con email
    results.append(test_login("admin@podoskin.local", "Admin2024!", "EMAIL (admin@podoskin.local)"))
    
    # Test 3: Login con username "santiago.ornelas"
    results.append(test_login("santiago.ornelas", "Ornelas2025!", "USERNAME (santiago.ornelas)"))
    
    # Test 4: Login con email de Santiago
    results.append(test_login("santiago@podoskin.com", "Ornelas2025!", "EMAIL (santiago@podoskin.com)"))
    
    # Test 5: Login con ID estructurado
    results.append(test_login("ASGO-1213-00001", "Ornelas2025!", "ID ESTRUCTURADO (ASGO-1213-00001)"))
    
    # Test 6: Login con credenciales incorrectas
    results.append(not test_login("admin", "WrongPassword!", "CREDENCIALES INCORRECTAS (debe fallar)"))
    
    # Resumen
    print(f"\n{'='*60}")
    print("📊 RESUMEN DE RESULTADOS")
    print(f"{'='*60}")
    
    tests_passed = sum(results)
    tests_total = len(results)
    
    print(f"✅ Tests exitosos: {tests_passed}/{tests_total}")
    print(f"❌ Tests fallidos: {tests_total - tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        return 0
    else:
        print("\n⚠️  Algunos tests fallaron. Revisar logs arriba.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
