#!/usr/bin/env python3
"""
Chatbot de Terminal - PodoSkin IA Assistant
==========================================

Interfaz de línea de comandos para interactuar con el agente IA de PodoSkin.
Permite hacer consultas complejas en lenguaje natural sobre pacientes, citas,
finanzas, horarios y más.

Uso:
    python backend/tools/terminal_chatbot.py
    
Comandos especiales:
    /help       - Mostrar ayuda
    /ejemplos   - Mostrar ejemplos de consultas
    /stats      - Mostrar estadísticas del sistema
    /clear      - Limpiar pantalla
    /history    - Ver historial de conversación
    /exit, /quit- Salir del chatbot

Ejemplos de consultas:
    - ¿Cuántas personas con sobrepeso tuvimos la semana pasada?
    - ¿Cuánto sería el 20% de las ganancias obtenidas después de gastos la semana pasada?
    - Muéstrame los pacientes que tienen citas mañana
    - ¿Cuál es el horario del Dr. Martínez esta semana?
    - Dame un resumen de las finanzas del mes
"""

import os
import sys
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import argparse

# Agregar path del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Instala 'rich' para una mejor experiencia: pip install rich")

from backend.agents.graph import run_agent
from backend.api.core.config import get_settings


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

settings = get_settings()

if RICH_AVAILABLE:
    console = Console()
else:
    console = None


# =============================================================================
# COLORES Y FORMATO (fallback si no hay rich)
# =============================================================================

class Colors:
    """Códigos ANSI para colores en terminal."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# =============================================================================
# FUNCIONES DE AYUDA
# =============================================================================

def print_welcome():
    """Mostrar mensaje de bienvenida."""
    if RICH_AVAILABLE:
        welcome_text = """
# 🦶 Bienvenido al Chatbot PodoSkin IA

Soy tu asistente inteligente para consultas sobre la clínica.
Puedo ayudarte con información sobre:

- 👥 **Pacientes**: búsquedas, historiales, estadísticas
- 📅 **Citas**: horarios, disponibilidad, confirmaciones
- 💊 **Tratamientos**: seguimiento, evoluciones
- 💰 **Finanzas**: ingresos, gastos, análisis de rentabilidad
- 📊 **Estadísticas**: métricas, reportes, análisis de datos

Escribe **/help** para ver comandos o **/ejemplos** para ver ejemplos.
Escribe **/exit** para salir.
        """
        console.print(Panel(Markdown(welcome_text), border_style="cyan", title="🤖 PodoSkin IA"))
    else:
        print(f"\n{Colors.CYAN}{'='*70}")
        print(f"{Colors.BOLD}🦶 BIENVENIDO AL CHATBOT PODOSKIN IA{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
        print("Soy tu asistente inteligente para consultas sobre la clínica.")
        print("Escribe /help para ver comandos o /ejemplos para ver ejemplos.\n")


def print_help():
    """Mostrar ayuda de comandos."""
    if RICH_AVAILABLE:
        help_text = """
## 📚 Comandos Disponibles

### Comandos Especiales
- `/help` - Mostrar esta ayuda
- `/ejemplos` - Ver ejemplos de consultas
- `/stats` - Estadísticas del sistema
- `/clear` - Limpiar pantalla
- `/history` - Ver historial de conversación
- `/exit`, `/quit` - Salir del chatbot

### Tipos de Consultas Soportadas

**📊 Estadísticas de Pacientes**
- Conteo por condiciones (sobrepeso, edad, etc.)
- Distribución demográfica
- Nuevos pacientes por período

**💰 Análisis Financiero**
- Ingresos y gastos por período
- Cálculo de ganancias netas
- Análisis de rentabilidad
- Proyecciones

**📅 Gestión de Citas**
- Horarios y disponibilidad
- Confirmaciones pendientes
- Estadísticas de asistencia

**👨‍⚕️ Información de Staff**
- Horarios de podólogos
- Carga de trabajo
- Especialidades
        """
        console.print(Panel(Markdown(help_text), border_style="blue", title="📚 Ayuda"))
    else:
        print(f"\n{Colors.BLUE}{'='*70}")
        print(f"{Colors.BOLD}📚 COMANDOS DISPONIBLES{Colors.END}")
        print(f"{Colors.BLUE}{'='*70}{Colors.END}")
        print("\nComandos Especiales:")
        print("  /help     - Mostrar esta ayuda")
        print("  /ejemplos - Ver ejemplos de consultas")
        print("  /stats    - Estadísticas del sistema")
        print("  /clear    - Limpiar pantalla")
        print("  /history  - Ver historial")
        print("  /exit     - Salir\n")


def print_examples():
    """Mostrar ejemplos de consultas."""
    if RICH_AVAILABLE:
        examples_text = """
## 💡 Ejemplos de Consultas

### 📊 Estadísticas de Pacientes
```
¿Cuántas personas con sobrepeso tuvimos la semana pasada?
Dame la lista de pacientes mayores de 60 años
¿Cuántos pacientes nuevos hubo este mes?
Muéstrame la distribución de pacientes por sexo
```

### 💰 Análisis Financiero
```
¿Cuánto sería el 20% de las ganancias después de gastos la semana pasada?
Dame un resumen de ingresos vs gastos del mes
¿Cuál fue el ingreso total de noviembre?
Muéstrame los gastos de la última semana
```

### 📅 Gestión de Citas
```
¿Qué pacientes tienen citas mañana?
Muéstrame el horario completo de esta semana
¿Cuántas citas completadas hubo hoy?
¿Hay espacios disponibles el viernes?
```

### 👨‍⚕️ Staff y Horarios
```
¿Cuál es el horario del Dr. Martínez esta semana?
¿Qué podólogos están disponibles mañana?
Muéstrame la carga de trabajo de cada podólogo
```

### 💊 Tratamientos
```
¿Cuántos tratamientos activos tenemos?
Muéstrame pacientes con tratamiento de onicomicosis
¿Qué tratamientos se completaron este mes?
```
        """
        console.print(Panel(Markdown(examples_text), border_style="green", title="💡 Ejemplos"))
    else:
        print(f"\n{Colors.GREEN}{'='*70}")
        print(f"{Colors.BOLD}💡 EJEMPLOS DE CONSULTAS{Colors.END}")
        print(f"{Colors.GREEN}{'='*70}{Colors.END}")
        print("\n📊 Estadísticas:")
        print("  - ¿Cuántas personas con sobrepeso tuvimos la semana pasada?")
        print("  - Dame la lista de pacientes mayores de 60 años")
        print("\n💰 Finanzas:")
        print("  - ¿Cuánto es el 20% de ganancias después de gastos la semana pasada?")
        print("  - Dame un resumen de ingresos vs gastos del mes")
        print("\n📅 Citas:")
        print("  - ¿Qué pacientes tienen citas mañana?")
        print("  - Muéstrame el horario completo de esta semana\n")


def print_stats():
    """Mostrar estadísticas del sistema."""
    if RICH_AVAILABLE:
        table = Table(title="📊 Estadísticas del Sistema", border_style="cyan")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")
        
        # Aquí se podrían agregar estadísticas reales del sistema
        table.add_row("Estado del Sistema", "✅ Operativo")
        table.add_row("Modelo IA", settings.CLAUDE_MODEL)
        table.add_row("Temperatura", str(settings.CLAUDE_TEMPERATURE))
        table.add_row("Max Tokens", str(settings.CLAUDE_MAX_TOKENS))
        
        console.print(table)
    else:
        print(f"\n{Colors.CYAN}{'='*70}")
        print(f"{Colors.BOLD}📊 ESTADÍSTICAS DEL SISTEMA{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"Estado: {Colors.GREEN}✅ Operativo{Colors.END}")
        print(f"Modelo IA: {settings.CLAUDE_MODEL}")
        print(f"Temperatura: {settings.CLAUDE_TEMPERATURE}")
        print(f"Max Tokens: {settings.CLAUDE_MAX_TOKENS}\n")


# =============================================================================
# FUNCIONES DE CONVERSACIÓN
# =============================================================================

class ConversationHistory:
    """Manejo del historial de conversación."""
    
    def __init__(self, max_size: int = 50):
        self.history: List[Dict[str, Any]] = []
        self.max_size = max_size
    
    def add(self, user_message: str, assistant_response: str, metadata: Optional[Dict] = None):
        """Agregar intercambio al historial."""
        entry = {
            "timestamp": datetime.now(),
            "user": user_message,
            "assistant": assistant_response,
            "metadata": metadata or {}
        }
        self.history.append(entry)
        
        # Mantener solo los últimos N mensajes
        if len(self.history) > self.max_size:
            self.history = self.history[-self.max_size:]
    
    def get_context(self, last_n: int = 5) -> str:
        """Obtener contexto de los últimos N mensajes."""
        recent = self.history[-last_n:] if len(self.history) > last_n else self.history
        
        context_parts = []
        for entry in recent:
            context_parts.append(f"Usuario: {entry['user']}")
            context_parts.append(f"Asistente: {entry['assistant']}")
        
        return "\n".join(context_parts)
    
    def display(self):
        """Mostrar historial."""
        if not self.history:
            print(f"\n{Colors.WARNING}No hay historial de conversación.{Colors.END}\n")
            return
        
        if RICH_AVAILABLE:
            table = Table(title="📜 Historial de Conversación", border_style="blue")
            table.add_column("Hora", style="cyan", width=10)
            table.add_column("Usuario", style="green")
            table.add_column("Asistente", style="yellow")
            
            for entry in self.history[-10:]:  # Últimas 10
                timestamp = entry["timestamp"].strftime("%H:%M:%S")
                user_msg = entry["user"][:40] + "..." if len(entry["user"]) > 40 else entry["user"]
                assistant_msg = entry["assistant"][:40] + "..." if len(entry["assistant"]) > 40 else entry["assistant"]
                table.add_row(timestamp, user_msg, assistant_msg)
            
            console.print(table)
        else:
            print(f"\n{Colors.BLUE}{'='*70}")
            print(f"{Colors.BOLD}📜 HISTORIAL DE CONVERSACIÓN{Colors.END}")
            print(f"{Colors.BLUE}{'='*70}{Colors.END}")
            for entry in self.history[-10:]:
                timestamp = entry["timestamp"].strftime("%H:%M:%S")
                print(f"\n[{timestamp}]")
                print(f"  Tu: {entry['user']}")
                print(f"  IA: {entry['assistant'][:100]}...")
            print()


async def process_query(query: str, history: ConversationHistory) -> Dict[str, Any]:
    """
    Procesar consulta del usuario usando el agente LangGraph.
    
    Args:
        query: Consulta en lenguaje natural
        history: Historial de conversación para contexto
        
    Returns:
        Respuesta del agente con mensaje y datos
    """
    try:
        # Agregar contexto de historial reciente
        context = history.get_context(last_n=3)
        
        # Ejecutar agente
        result = await run_agent(
            user_query=query,
            user_id=1,  # Usuario admin por defecto para chatbot terminal
            session_id=f"terminal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            thread_id=None,  # Cada consulta es independiente por ahora
            context={"conversation_history": context} if context else None
        )
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error al procesar consulta: {str(e)}",
            "error": str(e)
        }


def display_response(response: Dict[str, Any]):
    """Mostrar respuesta del asistente formateada."""
    message = response.get("message", "Sin respuesta")
    success = response.get("success", True)
    data = response.get("data", {})
    
    if RICH_AVAILABLE:
        if success:
            console.print(Panel(
                Markdown(message),
                border_style="green",
                title="🤖 Asistente"
            ))
            
            # Mostrar datos adicionales si existen
            if data and isinstance(data, dict):
                if "row_count" in data:
                    console.print(f"[dim]Resultados: {data['row_count']} registros[/dim]")
                if "processing_time_ms" in data:
                    console.print(f"[dim]Tiempo: {data['processing_time_ms']:.0f}ms[/dim]")
        else:
            console.print(Panel(
                message,
                border_style="red",
                title="⚠️ Error"
            ))
    else:
        if success:
            print(f"\n{Colors.GREEN}🤖 Asistente:{Colors.END}")
            print(message)
        else:
            print(f"\n{Colors.FAIL}⚠️ Error:{Colors.END}")
            print(message)
        print()


# =============================================================================
# MAIN LOOP
# =============================================================================

async def main_loop():
    """Loop principal del chatbot."""
    history = ConversationHistory()
    print_welcome()
    
    while True:
        try:
            # Obtener entrada del usuario
            if RICH_AVAILABLE:
                user_input = Prompt.ask("\n[bold cyan]Tú[/bold cyan]", default="").strip()
            else:
                user_input = input(f"\n{Colors.CYAN}Tú: {Colors.END}").strip()
            
            # Verificar si está vacío
            if not user_input:
                continue
            
            # Comandos especiales
            if user_input.startswith("/"):
                command = user_input.lower()
                
                if command in ["/exit", "/quit", "/salir"]:
                    if RICH_AVAILABLE:
                        console.print("\n[bold yellow]👋 ¡Hasta luego![/bold yellow]\n")
                    else:
                        print(f"\n{Colors.WARNING}👋 ¡Hasta luego!{Colors.END}\n")
                    break
                
                elif command == "/help":
                    print_help()
                
                elif command == "/ejemplos":
                    print_examples()
                
                elif command == "/stats":
                    print_stats()
                
                elif command == "/clear":
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print_welcome()
                
                elif command == "/history":
                    history.display()
                
                else:
                    print(f"{Colors.WARNING}Comando desconocido. Escribe /help para ver comandos disponibles.{Colors.END}")
                
                continue
            
            # Procesar consulta
            if RICH_AVAILABLE:
                with console.status("[bold green]Pensando...", spinner="dots"):
                    response = await process_query(user_input, history)
            else:
                print(f"{Colors.YELLOW}Pensando...{Colors.END}")
                response = await process_query(user_input, history)
            
            # Mostrar respuesta
            display_response(response)
            
            # Agregar al historial
            history.add(
                user_message=user_input,
                assistant_response=response.get("message", ""),
                metadata={
                    "success": response.get("success", True),
                    "intent": response.get("intent"),
                    "processing_time": response.get("processing_time_ms")
                }
            )
            
        except KeyboardInterrupt:
            if RICH_AVAILABLE:
                console.print("\n\n[bold yellow]👋 Interrupción detectada. ¡Hasta luego![/bold yellow]\n")
            else:
                print(f"\n\n{Colors.WARNING}👋 Interrupción detectada. ¡Hasta luego!{Colors.END}\n")
            break
        
        except Exception as e:
            if RICH_AVAILABLE:
                console.print(f"[bold red]Error inesperado: {e}[/bold red]")
            else:
                print(f"{Colors.FAIL}Error inesperado: {e}{Colors.END}")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Punto de entrada principal."""
    parser = argparse.ArgumentParser(description="Chatbot de terminal PodoSkin IA")
    parser.add_argument("--no-color", action="store_true", help="Desactivar colores")
    parser.add_argument("--single", "-s", type=str, help="Ejecutar una sola consulta y salir")
    args = parser.parse_args()
    
    # Verificar API key
    if not settings.ANTHROPIC_API_KEY:
        print(f"{Colors.FAIL}❌ ERROR: ANTHROPIC_API_KEY no configurada en .env{Colors.END}")
        print("Configura tu API key de Anthropic en el archivo .env")
        return 1
    
    # Ejecutar consulta única o modo interactivo
    if args.single:
        # Modo de consulta única
        async def single_query():
            history = ConversationHistory()
            response = await process_query(args.single, history)
            display_response(response)
        
        asyncio.run(single_query())
    else:
        # Modo interactivo
        try:
            asyncio.run(main_loop())
        except Exception as e:
            print(f"{Colors.FAIL}Error fatal: {e}{Colors.END}")
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
