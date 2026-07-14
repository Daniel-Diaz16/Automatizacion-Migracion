"""
Orquestador de tareas de migración con ejecución en hilos separados.

Funcionalidades principales:
1. Clase TareaEjecutor para manejar tareas en hilos independientes
2. Estado de tareas (activo/inactivo) con thread-safety
3. Ejecución de funciones específicas por módulo
4. Tareas disponibles:
   - procesar_acumulado()    → Acomulado_Genesys_Cloud.main()
   - procesar_base_cloud()   → Base_Genesys_Cloud.main()
   - procesar_cruces()       → Cruce_Genesys_Cloud.main()
   - procesar_engaged()      → Genesys_Engaged.procesar_automatizacion()
   - procesar_cruces_y_engaged() → Cruce + Engaged en paralelo
5. Monitoreo de estado de tareas
6. Espera de finalización con timeout
"""

import sys
import threading
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


class TareaEjecutor:
    """Clase que maneja la ejecucion de tareas en hilos separados"""

    def __init__(self, nombre, modulo, funcion=None):
        self.nombre = nombre
        self.modulo = modulo
        self.funcion = funcion
        self.hilo = None
        self.activo = False
        self.ultimo_resultado = None
        self.ultimo_error = None
        self._lock = threading.Lock()

    def ejecutar(self):
        """Ejecuta la tarea en un hilo separado"""
        with self._lock:
            if self.activo:
                print(f"[{self.nombre}] Ya esta en ejecucion")
                return False
            self.activo = True

        self.hilo = threading.Thread(target=self._run, daemon=True)
        self.hilo.start()
        return True

    def _run(self):
        """Metodo interno que ejecuta la tarea"""
        hora_inicio = datetime.now(ZONA_COLOMBIA)
        print(f"[{self.nombre}] Iniciando a las {hora_inicio.strftime('%H:%M:%S')}")

        try:
            # Importar modulo dinamicamente
            if self.modulo not in sys.modules:
                __import__(self.modulo)

            modulo_importado = sys.modules[self.modulo]

            # Determinar que funcion ejecutar
            if self.funcion and hasattr(modulo_importado, self.funcion):
                func = getattr(modulo_importado, self.funcion)
                func()
            elif hasattr(modulo_importado, 'main'):
                modulo_importado.main()
            else:
                print(f"[{self.nombre}] No se encontro funcion de entrada en {self.modulo}")
                self.ultimo_resultado = False
                self.ultimo_error = f"Sin funcion de entrada en {self.modulo}"
                return

            self.ultimo_resultado = True
            self.ultimo_error = None
            hora_fin = datetime.now(ZONA_COLOMBIA)
            duracion = (hora_fin - hora_inicio).total_seconds()
            print(f"[{self.nombre}] Finalizado correctamente. Duracion: {duracion:.1f} segundos")

        except Exception as e:
            self.ultimo_resultado = False
            self.ultimo_error = str(e)
            print(f"[{self.nombre}] ERROR: {str(e)}")
            traceback.print_exc()
        finally:
            with self._lock:
                self.activo = False

    def esta_ejecutando(self):
        return self.activo


# Instancias globales de tareas
tarea_acumulado = TareaEjecutor("ACUMULADO", "Acomulado_Genesys_Cloud", "main")
tarea_base_cloud = TareaEjecutor("BASE_CLOUD", "Base_Genesys_Cloud", "main")
tarea_cruce = TareaEjecutor("CRUCE", "Cruce_Genesys_Cloud", "main")
tarea_engaged = TareaEjecutor("ENGAGED", "Genesys_Engaged", "procesar_automatizacion")


def procesar_acumulado():
    """Ejecuta el proceso de acumulado en hilo separado"""
    return tarea_acumulado.ejecutar()


def procesar_base_cloud():
    """Ejecuta el proceso de base cloud en hilo separado"""
    return tarea_base_cloud.ejecutar()


def procesar_cruces():
    """Ejecuta el proceso de cruce en hilo separado"""
    return tarea_cruce.ejecutar()


def procesar_engaged():
    """Ejecuta el proceso de engaged en hilo separado"""
    return tarea_engaged.ejecutar()


def procesar_cruces_y_engaged():
    """Ejecuta cruce y engaged en paralelo"""
    resultado_cruce = tarea_cruce.ejecutar()
    resultado_engaged = tarea_engaged.ejecutar()
    return resultado_cruce and resultado_engaged


def estado_tareas():
    """Retorna el estado de todas las tareas"""
    return {
        'acumulado': tarea_acumulado.esta_ejecutando(),
        'base_cloud': tarea_base_cloud.esta_ejecutando(),
        'cruce': tarea_cruce.esta_ejecutando(),
        'engaged': tarea_engaged.esta_ejecutando()
    }


def esperar_tareas(tiempo_maximo_segundos=300):
    """Espera a que todas las tareas terminen"""
    import time
    inicio = time.time()
    while any([
        tarea_acumulado.esta_ejecutando(),
        tarea_base_cloud.esta_ejecutando(),
        tarea_cruce.esta_ejecutando(),
        tarea_engaged.esta_ejecutando()
    ]):
        if time.time() - inicio > tiempo_maximo_segundos:
            print("Tiempo de espera agotado")
            return False
        time.sleep(1)
    return True
