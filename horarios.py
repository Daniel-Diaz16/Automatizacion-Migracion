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
    """Obtiene el directorio de datos de la aplicacion en %APPDATA%/RPA_Migracion."""
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~')
    directorio = os.path.join(base, 'RPA_Migracion')
    os.makedirs(directorio, exist_ok=True)
    return directorio


def obtener_ruta_log(nombre='rpa_migracion'):
    """Obtiene la ruta del archivo de log diario en %APPDATA%/RPA_Migracion/logs/."""
    dir_logs = os.path.join(obtener_directorio_datos(), 'logs')
    os.makedirs(dir_logs, exist_ok=True)
    fecha = datetime.now(ZONA_COLOMBIA).strftime('%Y-%m-%d')
    return os.path.join(dir_logs, f'{nombre}_{fecha}.log')


# =============================================================================
# RUTA DE HORARIOS EN APPDATA
# =============================================================================

ARCHIVO_HORARIOS = os.path.join(obtener_directorio_datos(), 'horarios.json')
_ARCHIVO_HORARIOS_LEGACY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'horarios.json')


def _migrar_horarios_legacy():
    if os.path.exists(_ARCHIVO_HORARIOS_LEGACY) and not os.path.exists(ARCHIVO_HORARIOS):
        try:
            shutil.copy2(_ARCHIVO_HORARIOS_LEGACY, ARCHIVO_HORARIOS)
            print(f"Horarios migrados a: {ARCHIVO_HORARIOS}")
        except Exception as e:
            print(f"No se pudieron migrar los horarios: {e}")

_migrar_horarios_legacy()


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
    "acumulado_base": None,
    "acumulado": tareas_migracion.procesar_acumulado,
    "base_cloud": tareas_migracion.procesar_base_cloud,
    "cruce": tareas_migracion.procesar_cruces,
    "engaged": tareas_migracion.procesar_engaged,
}


def cargar_horarios_json():
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
    try:
        with open(ARCHIVO_HORARIOS, 'w', encoding='utf-8') as f:
            json.dump(horarios, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error guardando horarios.json: {e}")
        return False


def _ejecutar_tarea(nombre_tarea):
    if nombre_tarea == "acumulado_base":
        tareas_migracion.procesar_acumulado()
        tareas_migracion.procesar_base_cloud()
    elif nombre_tarea in MAPEO_TAREAS and MAPEO_TAREAS[nombre_tarea] is not None:
        MAPEO_TAREAS[nombre_tarea]()
    else:
        print(f"Tarea desconocida: {nombre_tarea}")


class ProgramadorHorario:
    def __init__(self):
        self.hilo_programador = None
        self._parar_evento = threading.Event()
        self.tareas_registradas = []
        self._lock = threading.Lock()

    @property
    def activo(self):
        return not self._parar_evento.is_set() and self.hilo_programador is not None and self.hilo_programador.is_alive()

    def obtener_hora_colombia(self):
        return datetime.now(ZONA_COLOMBIA)

    def configurar_horarios(self, horarios_personalizados=None):
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
        print(f"Programador activado. Hora Colombia: {self.obtener_hora_colombia().strftime('%H:%M:%S')}")
        while not self._parar_evento.is_set():
            try:
                schedule.run_pending()
                self._parar_evento.wait(timeout=5)
            except Exception as e:
                print(f"Error en programador: {str(e)}")
                self._parar_evento.wait(timeout=3)
        print("Programador desactivado")

    def iniciar(self):
        if self.activo:
            print("El programador ya esta activo")
            return False
        self._parar_evento.clear()
        self.configurar_horarios()
        self.hilo_programador = threading.Thread(target=self.ejecutar_bucle, daemon=True)
        self.hilo_programador.start()
        return True

    def detener(self):
        self._parar_evento.set()
        if self.hilo_programador and self.hilo_programador.is_alive():
            self.hilo_programador.join(timeout=2)
        schedule.clear()
        self.tareas_registradas = []
        self.hilo_programador = None
        return True

    def obtener_proxima_tarea(self):
        try:
            proximo = schedule.next_run()
            if proximo:
                return {'hora': proximo.strftime('%H:%M:%S'), 'fecha': proximo.strftime('%d/%m/%Y')}
        except Exception:
            pass
        return None

    def reiniciar(self):
        self.detener()
        return self.iniciar()


programador = ProgramadorHorario()


def iniciar_programador():
    return programador.iniciar()


def detener_programador():
    return programador.detener()


def configurar_rutinas(horarios_personalizados=None):
    return programador.configurar_horarios(horarios_personalizados)


def obtener_proxima_tarea():
    return programador.obtener_proxima_tarea()


def reiniciar_programador():
    return programador.reiniciar()


# =============================================================================
# CONFIGURACION DE RUTAS EN APPDATA - CON TODAS LAS RUTAS
# =============================================================================

def _rutas_por_defecto():
    """Retorna las rutas por defecto para todos los modulos - CON TODAS LAS RUTAS"""
    return {
        'Acomulado_Genesys_Cloud': {
            'ruta_carpeta': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\09. Bases Genesys\02. Interacciones\Historico\2026',
            'ruta_salida': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Acomulado.csv',
            'ruta_dotacion': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Dotacion VTR Operaciones.xlsx'
        },
        'Base_Genesys_Cloud': {
            'ruta_base': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\09. Bases Genesys\01. Contact_List',
            'ruta_salida': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Cloud.xlsx',
            'ruta_cargue_actual': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\09. Bases Genesys\01. Contact_List\Cargue Actual',
            'ruta_historico_mes_pasado': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\09. Bases Genesys\01. Contact_List\Historico',
            'ruta_bases_cloud': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Cloud Bases'
        },
        'Base_Genesys_Engaged': {
            'RUTA_BASES': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Engaged Bases',
            'RUTA_SALIDA': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Engaged.xlsx'
        },
        'Cruce_Genesys_Cloud': {
            'ruta_carpeta': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Cloud',
            'ruta_salida': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Consolidada_Agentes.csv',
            'ruta_base_genesys': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Cloud.xlsx',
            'ruta_dotacion': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Dotacion VTR Operaciones.xlsx',
            'ruta_cuartiles': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Cuartiles.xlsx',
            'ruta_malla_de_turnos': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Malla de turnos diaria.xlsx',
            'ruta_genesys_bases': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Cloud Bases',
            'ruta_acomulado': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Acomulado.csv'
        },
        'Genesys_Engaged': {
            'OUTPUT_FILENAME': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Formulario Engaged.xlsx',
            'RUTA_DOTACION': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Dotacion VTR Operaciones.xlsx',
            'RUTA_LLAMadas': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Llamada x agente.csv',
            'RUTA_CUARTILES': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Cuartiles.xlsx',
            'RUTA_MALLA_TURNOS': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Malla de turnos diaria.xlsx',
            'RUTA_CAMPAIGN': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Campaign Activity.csv',
            'RUTA_BASES_RSL': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Engaged Bases'
        }
    }


def obtener_ruta_config():
    app_data = os.getenv('APPDATA')
    config_dir = os.path.join(app_data, 'RPA_Migracion')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, 'rutas_config.json')


def cargar_configuracion_rutas():
    ruta_config = obtener_ruta_config()
    rutas_por_defecto = _rutas_por_defecto()
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error cargando configuracion de rutas: {e}. Usando valores por defecto.")
            return rutas_por_defecto
    else:
        guardar_configuracion_rutas(rutas_por_defecto)
        return rutas_por_defecto


def guardar_configuracion_rutas(config):
    ruta_config = obtener_ruta_config()
    try:
        with open(ruta_config, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando configuración de rutas: {e}")
        return False


def actualizar_rutas_en_modulos(config):
    """Actualiza las variables de ruta en los módulos cargados"""
    try:
        import importlib
        modulos_a_recargar = ['Acomulado_Genesys_Cloud', 'Base_Genesys_Cloud', 'Base_Genesys_Engaged', 'Cruce_Genesys_Cloud', 'Genesys_Engaged']
        for nombre_modulo in modulos_a_recargar:
            if nombre_modulo in sys.modules:
                modulo = sys.modules[nombre_modulo]
                if nombre_modulo in config:
                    for key, value in config[nombre_modulo].items():
                        if hasattr(modulo, key):
                            setattr(modulo, key, value)
                importlib.reload(modulo)
        return True
    except Exception as e:
        print(f"Error actualizando modulos: {e}")
        return False