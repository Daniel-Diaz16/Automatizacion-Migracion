"""
Sistema de programacion horaria con soporte para hilos y zona horaria Colombia
Los datos persistentes se almacenan en %APPDATA%/RPA_Migracion/
"""
import schedule
import threading
import time
import json
import sys
import os
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
import tareas_migracion

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


# =============================================================================
# DIRECTORIO DE DATOS EN %APPDATA%
# =============================================================================

def obtener_directorio_datos():
    """Obtiene el directorio de datos de la aplicacion en %APPDATA%/RPA_Migracion.
    En Windows usa %APPDATA%, en otros sistemas usa ~/.RPA_Migracion.
    Crea el directorio si no existe.
    """
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~')
    directorio = os.path.join(base, 'RPA_Migracion')
    os.makedirs(directorio, exist_ok=True)
    return directorio


def obtener_ruta_log(nombre='rpa_migracion'):
    """Obtiene la ruta del archivo de log diario en %APPDATA%/RPA_Migracion/logs/.
    El nombre del archivo incluye la fecha actual (Colombia) para rotacion automatica.
    """
    dir_logs = os.path.join(obtener_directorio_datos(), 'logs')
    os.makedirs(dir_logs, exist_ok=True)
    fecha = datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d')
    return os.path.join(dir_logs, f'{nombre}_{fecha}.log')


# =============================================================================
# RUTA DE HORARIOS EN APPDATA
# =============================================================================

ARCHIVO_HORARIOS = os.path.join(obtener_directorio_datos(), 'horarios.json')

# Ruta legacy (mismo directorio del script) para migracion automatica
_ARCHIVO_HORARIOS_LEGACY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'horarios.json')


def _migrar_horarios_legacy():
    """Migra horarios.json del directorio del script a %APPDATA% si corresponde.
    Solo se ejecuta si el archivo legacy existe y el nuevo no.
    """
    if os.path.exists(_ARCHIVO_HORARIOS_LEGACY) and not os.path.exists(ARCHIVO_HORARIOS):
        try:
            shutil.copy2(_ARCHIVO_HORARIOS_LEGACY, ARCHIVO_HORARIOS)
            print(f"Horarios migrados a: {ARCHIVO_HORARIOS}")
        except Exception as e:
            print(f"No se pudieron migrar los horarios: {e}")


# Ejecutar migracion al importar el modulo
_migrar_horarios_legacy()


# Horarios por defecto que se cargan si no existe el archivo JSON
HORARIOS_POR_DEFECTO = [
    {"hora": "08:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "08:50", "tarea": "acumulado_base", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"], "activo": True},
    {"hora": "09:10", "tarea": "acumulado_base", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"], "activo": True},
    {"hora": "09:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "10:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "11:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "12:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "13:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "14:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "15:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"], "activo": True},
    {"hora": "16:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "17:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
    {"hora": "18:10", "tarea": "cruce_engaged", "dias": ["lunes", "martes", "miercoles", "jueves", "viernes"], "activo": True},
]

MAPEO_DIAS_SCHEDULE = {
    "lunes": "monday",
    "martes": "tuesday",
    "miercoles": "wednesday",
    "jueves": "thursday",
    "viernes": "friday",
    "sabado": "saturday",
    "domingo": "sunday"
}

MAPEO_TAREAS = {
    "cruce_engaged": tareas_migracion.procesar_cruces_y_engaged,
    "acumulado_base": None,  # Se resuelve dinamicamente para ejecutar ambos
    "acumulado": tareas_migracion.procesar_acumulado,
    "base_cloud": tareas_migracion.procesar_base_cloud,
    "cruce": tareas_migracion.procesar_cruces,
    "engaged": tareas_migracion.procesar_engaged,
}


def cargar_horarios_json():
    """Carga la configuracion de horarios desde el archivo JSON en %APPDATA%"""
    if os.path.exists(ARCHIVO_HORARIOS):
        try:
            with open(ARCHIVO_HORARIOS, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            if isinstance(datos, list) and len(datos) > 0:
                return datos
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error cargando horarios.json: {e}. Usando valores por defecto.")
    return [h.copy() for h in HORARIOS_POR_DEFECTO]


def guardar_horarios_json(horarios):
    """Guarda la configuracion de horarios en el archivo JSON en %APPDATA%"""
    try:
        with open(ARCHIVO_HORARIOS, 'w', encoding='utf-8') as f:
            json.dump(horarios, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error guardando horarios.json: {e}")
        return False


def _ejecutar_tarea(nombre_tarea):
    """Ejecuta la tarea correspondiente segun el nombre"""
    if nombre_tarea == "acumulado_base":
        tareas_migracion.procesar_acumulado()
        tareas_migracion.procesar_base_cloud()
    elif nombre_tarea in MAPEO_TAREAS and MAPEO_TAREAS[nombre_tarea] is not None:
        MAPEO_TAREAS[nombre_tarea]()
    else:
        print(f"Tarea desconocida: {nombre_tarea}")


class ProgramadorHorario:
    """Clase que maneja la programacion de tareas con zona horaria Colombia"""

    def __init__(self):
        self.hilo_programador = None
        self._parar_evento = threading.Event()
        self.tareas_registradas = []
        self._lock = threading.Lock()

    @property
    def activo(self):
        """Propiedad que indica si el programador esta activo"""
        return not self._parar_evento.is_set() and self.hilo_programador is not None and self.hilo_programador.is_alive()

    def obtener_hora_colombia(self):
        """Retorna hora actual de Colombia"""
        return datetime.now(ZONA_COLOMBIA)

    def configurar_horarios(self, horarios_personalizados=None):
        """Configura las horas segun la configuracion proporcionada o la del JSON"""
        with self._lock:
            schedule.clear()
            self.tareas_registradas = []

            horarios = horarios_personalizados or cargar_horarios_json()

            for entrada in horarios:
                if not entrada.get("activo", True):
                    continue

                hora = entrada["hora"]
                tarea = entrada["tarea"]
                dias = entrada.get("dias", [])

                for dia in dias:
                    dia_en = MAPEO_DIAS_SCHEDULE.get(dia)
                    if not dia_en:
                        continue

                    dia_schedule = getattr(schedule.every(), dia_en, None)
                    if dia_schedule is None:
                        continue

                    dia_schedule.at(hora).do(_ejecutar_tarea, nombre_tarea=tarea)
                    self.tareas_registradas.append((tarea, hora, dia))

            print(f"Horarios configurados. {len(self.tareas_registradas)} tareas programadas")
            return True

    def ejecutar_bucle(self):
        """Bucle principal del programador - usa Event.wait() para detener instantaneamente"""
        print(f"Programador activado. Hora Colombia: {self.obtener_hora_colombia().strftime('%H:%M:%S')}")

        while not self._parar_evento.is_set():
            try:
                schedule.run_pending()
                # wait() reemplaza time.sleep(): se despierta instantaneamente
                # cuando se setea el evento (detener), maximo espera 5 segundos
                self._parar_evento.wait(timeout=5)
            except Exception as e:
                print(f"Error en programador: {str(e)}")
                self._parar_evento.wait(timeout=3)

        print("Programador desactivado")

    def iniciar(self):
        """Inicia el programador en un hilo separado"""
        if self.activo:
            print("El programador ya esta activo")
            return False

        self._parar_evento.clear()
        self.configurar_horarios()

        self.hilo_programador = threading.Thread(target=self.ejecutar_bucle, daemon=True)
        self.hilo_programador.start()

        return True

    def detener(self):
        """Detiene el programador y limpia recursos - detencion casi instantanea"""
        # Senializar al hilo que debe detenerse (despierta del wait() inmediatamente)
        self._parar_evento.set()

        # Esperar a que el hilo termine (responde en milisegundos gracias a Event)
        if self.hilo_programador and self.hilo_programador.is_alive():
            self.hilo_programador.join(timeout=2)

        # Limpiar todas las tareas de schedule
        schedule.clear()
        self.tareas_registradas = []
        self.hilo_programador = None

        return True

    def obtener_proxima_tarea(self):
        """Retorna informacion de la proxima tarea a ejecutar"""
        try:
            proximo = schedule.next_run()
            if proximo:
                return {
                    'hora': proximo.strftime('%H:%M:%S'),
                    'fecha': proximo.strftime('%d/%m/%Y')
                }
        except Exception:
            pass
        return None

    def reiniciar(self):
        """Detiene y vuelve a iniciar el programador"""
        self.detener()
        return self.iniciar()


# Instancia global
programador = ProgramadorHorario()


def iniciar_programador():
    """Funcion publica para iniciar el programador"""
    return programador.iniciar()


def detener_programador():
    """Funcion publica para detener el programador"""
    return programador.detener()


def configurar_rutinas(horarios_personalizados=None):
    """Funcion publica para configurar rutinas"""
    return programador.configurar_horarios(horarios_personalizados)


def obtener_proxima_tarea():
    """Funcion publica para obtener proxima tarea"""
    return programador.obtener_proxima_tarea()


def reiniciar_programador():
    """Funcion publica para reiniciar el programador"""
    return programador.reiniciar()
