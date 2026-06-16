"""
Aplicacion principal del sistema de migraciones
Los datos persistentes (horarios, logs) se almacenan en %APPDATA%/RPA_Migracion/
"""
import sys
import os
import threading
import importlib
from datetime import datetime
from zoneinfo import ZoneInfo
from PyQt6 import QtWidgets, uic, QtGui
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject, QTime
from PyQt6.QtWidgets import QMessageBox, QApplication, QFileDialog
import tareas_migracion
import horarios

ZONA_COLOMBIA = ZoneInfo("America/Bogota")

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

TAREAS_DISPONIBLES = {
    "Cruce + Engaged": "cruce_engaged",
    "Acumulado + Base Cloud": "acumulado_base",
    "Acumulado": "acumulado",
    "Base Cloud": "base_cloud",
    "Cruce": "cruce",
    "Engaged": "engaged",
}


def resource_path(relative_path):
    """Obtiene la ruta correcta tanto en desarrollo como en ejecutable"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# =============================================================================
# SENALES THREAD-SAFE PARA ACTUALIZAR LA UI
# =============================================================================

class SenalesUI(QObject):
    """Senales para actualizar la UI de forma segura desde hilos secundarios.
    PyQt6 requiere que toda modificacion de widgets se haga desde el hilo principal.
    Estas senales garantizan que los cambios de estado de botones y labels
    se ejecuten en el hilo principal evitando errores y crasheos.
    """
    habilitar_boton_iniciar = pyqtSignal(bool)
    habilitar_boton_detener = pyqtSignal(bool)
    habilitar_boton_manual = pyqtSignal(bool)
    actualizar_estado_label = pyqtSignal(str)
    mensaje_consola = pyqtSignal(str)


class ConsolaRedirigida(QObject):
    """Redirige la salida de consola al widget de texto y a un archivo de log.
    El archivo de log se guarda en %APPDATA%/RPA_Migracion/logs/ con rotacion diaria.
    Es thread-safe: usa un Lock para proteger la escritura al archivo.
    """
    texto_recibido = pyqtSignal(str)

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.archivo_log = None
        self._lock = threading.Lock()
        self.texto_recibido.connect(self._escribir_widget)
        self._abrir_log()

    def _abrir_log(self):
        """Abre el archivo de log diario en %APPDATA%/RPA_Migracion/logs/"""
        try:
            ruta_log = horarios.obtener_ruta_log()
            self.archivo_log = open(ruta_log, 'a', encoding='utf-8')
        except Exception as e:
            print(f"No se pudo abrir archivo de log: {e}")

    def write(self, texto):
        if texto and texto.strip():
            self.texto_recibido.emit(texto)
            with self._lock:
                if self.archivo_log:
                    try:
                        timestamp = datetime.now(ZONA_COLOMBIA).strftime('%H:%M:%S')
                        self.archivo_log.write(f"[{timestamp}] {texto.rstrip()}\n")
                        self.archivo_log.flush()
                    except Exception:
                        pass

    def _escribir_widget(self, texto):
        self.widget.append(texto.strip())

    def flush(self):
        with self._lock:
            if self.archivo_log:
                try:
                    self.archivo_log.flush()
                except Exception:
                    pass

    def cerrar_log(self):
        """Cierra el archivo de log de forma segura"""
        with self._lock:
            if self.archivo_log:
                try:
                    self.archivo_log.close()
                except Exception:
                    pass
                self.archivo_log = None

    def rotar_log_si_necesario(self):
        """Verifica si el archivo de log debe rotar (nuevo dia) y lo rota"""
        try:
            ruta_esperada = horarios.obtener_ruta_log()
            with self._lock:
                if self.archivo_log and hasattr(self.archivo_log, 'name'):
                    if self.archivo_log.name != ruta_esperada:
                        self.archivo_log.close()
                        self.archivo_log = open(ruta_esperada, 'a', encoding='utf-8')
        except Exception:
            pass


class InterfazPrincipal(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.redirigir_consola = None
        self._hilo_manual = None
        self._recargando = False

        self.cargar_interfaz()
        self.inicializar_tablas()
        self.conectar_botones()
        self.configurar_temporizadores()
        self.inicializar_senales_ui()
        self.inicializar_redireccion_consola()
        self.cargar_horarios_en_tabla()
        self.mostrar_mensaje_bienvenida()
        self.inicializar_rutas()
        self.cargar_codigo_modulo()

    def cargar_interfaz(self):
        """Carga el archivo de interfaz o crea una por defecto"""
        try:
            ui_path = resource_path("interfaz.ui")
            uic.loadUi(ui_path, self)
        except FileNotFoundError:
            self.crear_interfaz_por_defecto()
        except Exception as e:
            print(f"Error cargando interfaz: {str(e)}")
            self.crear_interfaz_por_defecto()

    def inicializar_tablas(self):
        """Inicializa las tablas de estado y horarios"""

        # Tabla de estado de procesos
        self.tabla_estado.setColumnCount(4)
        self.tabla_estado.setHorizontalHeaderLabels(["Proceso", "Estado", "Ultima Ejecucion", "Duracion"])
        self.tabla_estado.setColumnWidth(0, 200)
        self.tabla_estado.setColumnWidth(1, 100)
        self.tabla_estado.setColumnWidth(2, 180)
        self.tabla_estado.setColumnWidth(3, 100)

        procesos = [
            ("Acumulado Genesys Cloud", "Inactivo", "-", "-"),
            ("Base Genesys Cloud", "Inactivo", "-", "-"),
            ("Cruce Genesys Cloud", "Inactivo", "-", "-"),
            ("Genesys Engaged", "Inactivo", "-", "-"),
        ]

        for row, (proceso, estado, ultima, duracion) in enumerate(procesos):
            self.tabla_estado.insertRow(row)
            self.tabla_estado.setItem(row, 0, QtWidgets.QTableWidgetItem(proceso))
            self.tabla_estado.setItem(row, 1, QtWidgets.QTableWidgetItem(estado))
            self.tabla_estado.setItem(row, 2, QtWidgets.QTableWidgetItem(ultima))
            self.tabla_estado.setItem(row, 3, QtWidgets.QTableWidgetItem(duracion))

        # Tabla de horarios - columna 4 oculta para ID interno
        self.tabla_horarios.setColumnCount(5)
        self.tabla_horarios.setHorizontalHeaderLabels(["Hora", "Tarea", "Dias", "Activo", "ID"])
        self.tabla_horarios.setColumnWidth(0, 70)
        self.tabla_horarios.setColumnWidth(1, 200)
        self.tabla_horarios.setColumnWidth(2, 200)
        self.tabla_horarios.setColumnWidth(3, 60)
        self.tabla_horarios.setColumnWidth(4, 0)
        self.tabla_horarios.setColumnHidden(4, True)

    def crear_interfaz_por_defecto(self):
        """Crea la interfaz por codigo si no existe el archivo .ui"""
        self.setWindowTitle("Panel de Automatizacion de Migraciones")
        self.setGeometry(100, 100, 780, 620)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self.lbl_title = QtWidgets.QLabel("Control de Migracion y Gestion")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fuente = self.lbl_title.font()
        fuente.setPointSize(14)
        fuente.setBold(True)
        self.lbl_title.setFont(fuente)
        layout.addWidget(self.lbl_title)

        self.lbl_zona = QtWidgets.QLabel("Aviso: Las migraciones operan bajo horario colombiano")
        self.lbl_zona.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_zona)

        layout_botones = QtWidgets.QHBoxLayout()
        self.btn_iniciar_reloj = QtWidgets.QPushButton("Activar Programador")
        self.btn_ejecutar_manual = QtWidgets.QPushButton("Ejecutar Cruce Manual")
        self.btn_detener_programador = QtWidgets.QPushButton("Detener Programador")
        self.btn_detener_programador.setEnabled(False)
        self.btn_limpiar_consola = QtWidgets.QPushButton("Limpiar Consola")

        layout_botones.addWidget(self.btn_iniciar_reloj)
        layout_botones.addWidget(self.btn_ejecutar_manual)
        layout_botones.addWidget(self.btn_detener_programador)
        layout_botones.addWidget(self.btn_limpiar_consola)
        layout.addLayout(layout_botones)

        self.progress_bar = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_bar)

        self.tab_widget = QtWidgets.QTabWidget()
        
        # Pestaña Consola
        self.tab_consola = QtWidgets.QWidget()
        layout_consola = QtWidgets.QVBoxLayout(self.tab_consola)
        self.txt_consola = QtWidgets.QTextEdit()
        self.txt_consola.setReadOnly(True)
        layout_consola.addWidget(self.txt_consola)
        self.tab_widget.addTab(self.tab_consola, "Consola")
        
        # Pestaña Estado
        self.tab_estado = QtWidgets.QWidget()
        layout_estado = QtWidgets.QVBoxLayout(self.tab_estado)
        self.tabla_estado = QtWidgets.QTableWidget()
        layout_estado.addWidget(self.tabla_estado)
        self.tab_widget.addTab(self.tab_estado, "Estado")
        
        # Pestaña Horarios
        self.tab_horarios = QtWidgets.QWidget()
        layout_horarios = QtWidgets.QVBoxLayout(self.tab_horarios)
        self.tabla_horarios = QtWidgets.QTableWidget()
        layout_horarios.addWidget(self.tabla_horarios)
        self.tab_widget.addTab(self.tab_horarios, "Horarios")
        
        # Pestaña Rutas
        self.tab_rutas = QtWidgets.QWidget()
        layout_rutas = QtWidgets.QVBoxLayout(self.tab_rutas)
        self.combo_modulos_rutas = QtWidgets.QComboBox()
        self.combo_modulos_rutas.addItems(['Acomulado_Genesys_Cloud', 'Base_Genesys_Cloud', 'Base_Genesys_Engaged', 'Cruce_Genesys_Cloud', 'Genesys_Engaged'])
        layout_rutas.addWidget(self.combo_modulos_rutas)
        self.tabla_rutas = QtWidgets.QTableWidget()
        layout_rutas.addWidget(self.tabla_rutas)
        layout_btn_rutas = QtWidgets.QHBoxLayout()
        self.btn_guardar_rutas = QtWidgets.QPushButton("Guardar")
        self.btn_restaurar_rutas = QtWidgets.QPushButton("Restaurar")
        layout_btn_rutas.addWidget(self.btn_guardar_rutas)
        layout_btn_rutas.addWidget(self.btn_restaurar_rutas)
        layout_rutas.addLayout(layout_btn_rutas)
        self.tab_widget.addTab(self.tab_rutas, "Rutas")
        
        # Pestaña Editor
        self.tab_editor = QtWidgets.QWidget()
        layout_editor = QtWidgets.QVBoxLayout(self.tab_editor)
        self.combo_modulos_editor = QtWidgets.QComboBox()
        self.combo_modulos_editor.addItems([
            'Acomulado_Genesys_Cloud.py', 'Base_Genesys_Cloud.py', 
            'Cruce_Genesys_Cloud.py', 'Genesys_Engaged.py',
            'horarios.py', 'tareas_migracion.py'
        ])
        layout_editor.addWidget(self.combo_modulos_editor)
        self.txt_editor_codigo = QtWidgets.QTextEdit()
        self.txt_editor_codigo.setFont(QtGui.QFont("Consolas", 9))
        layout_editor.addWidget(self.txt_editor_codigo)
        layout_btn_editor = QtWidgets.QHBoxLayout()
        self.btn_cargar_codigo = QtWidgets.QPushButton("Cargar")
        self.btn_guardar_codigo = QtWidgets.QPushButton("Guardar")
        layout_btn_editor.addWidget(self.btn_cargar_codigo)
        layout_btn_editor.addWidget(self.btn_guardar_codigo)
        layout_editor.addLayout(layout_btn_editor)
        self.tab_widget.addTab(self.tab_editor, "Editor")
        
        layout.addWidget(self.tab_widget)

        self.lbl_estado = QtWidgets.QLabel("Estado: Sistema listo | Programador: INACTIVO")
        self.lbl_estado.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_estado)

    def conectar_botones(self):
        """Conecta los botones a sus funciones"""
        self.btn_iniciar_reloj.clicked.connect(self.activar_programador)
        self.btn_ejecutar_manual.clicked.connect(self.ejecutar_proceso_manual)

        if hasattr(self, 'btn_detener_programador'):
            self.btn_detener_programador.clicked.connect(self.detener_programador)

        if hasattr(self, 'btn_limpiar_consola'):
            self.btn_limpiar_consola.clicked.connect(self.limpiar_consola)

        # Botones de gestion de horarios
        if hasattr(self, 'btn_agregar_horario'):
            self.btn_agregar_horario.clicked.connect(self.agregar_horario)
        if hasattr(self, 'btn_modificar_horario'):
            self.btn_modificar_horario.clicked.connect(self.modificar_horario)
        if hasattr(self, 'btn_eliminar_horario'):
            self.btn_eliminar_horario.clicked.connect(self.eliminar_horario)
        if hasattr(self, 'btn_activar_horario'):
            self.btn_activar_horario.clicked.connect(self.toggle_horario_activo)
        
        # Botones de la pestaña de rutas
        if hasattr(self, 'btn_guardar_rutas'):
            self.btn_guardar_rutas.clicked.connect(self.guardar_rutas)
        if hasattr(self, 'btn_restaurar_rutas'):
            self.btn_restaurar_rutas.clicked.connect(self.restaurar_rutas)
        if hasattr(self, 'combo_modulos_rutas'):
            self.combo_modulos_rutas.currentIndexChanged.connect(self.cargar_rutas_modulo)

        # Botones del editor de codigo
        if hasattr(self, 'btn_cargar_codigo'):
            self.btn_cargar_codigo.clicked.connect(self.cargar_codigo_modulo)
        if hasattr(self, 'btn_guardar_codigo'):
            self.btn_guardar_codigo.clicked.connect(self.guardar_codigo_modulo)
        if hasattr(self, 'combo_modulos_editor'):
            self.combo_modulos_editor.currentIndexChanged.connect(self.cargar_codigo_modulo)

    def inicializar_senales_ui(self):
        """Configura las senales thread-safe para actualizar la UI desde hilos secundarios."""
        self.senales = SenalesUI()
        self.senales.habilitar_boton_iniciar.connect(self.btn_iniciar_reloj.setEnabled)
        self.senales.habilitar_boton_manual.connect(self.btn_ejecutar_manual.setEnabled)
        self.senales.actualizar_estado_label.connect(self.actualizar_label_estado)

        if hasattr(self, 'btn_detener_programador'):
            self.senales.habilitar_boton_detener.connect(self.btn_detener_programador.setEnabled)

    def configurar_temporizadores(self):
        """Configura los temporizadores para actualizaciones"""
        self.temporador_estado = QTimer()
        self.temporador_estado.timeout.connect(self.actualizar_estado)
        self.temporador_estado.start(5000)

        self.temporador_log = QTimer()
        self.temporador_log.timeout.connect(self._rotar_log)
        self.temporador_log.start(60000)

    def _rotar_log(self):
        """Verifica si es necesario rotar el archivo de log (cambio de dia)"""
        if self.redirigir_consola:
            self.redirigir_consola.rotar_log_si_necesario()

    def inicializar_redireccion_consola(self):
        """Redirige stdout a la consola de la interfaz y al archivo de log en APPDATA"""
        self.redirigir_consola = ConsolaRedirigida(self.txt_consola)
        sys.stdout = self.redirigir_consola

    def mostrar_mensaje_bienvenida(self):
        """Muestra mensaje de bienvenida con informacion del sistema"""
        hora_colombia = datetime.now(ZONA_COLOMBIA)
        dir_datos = horarios.obtener_directorio_datos()
        mensaje = f"""
Sistema de Automatizacion de Migraciones Iniciado
Zona horaria: Colombia (America/Bogota)
Hora actual: {hora_colombia.strftime('%H:%M:%S')}
Fecha: {hora_colombia.strftime('%d/%m/%Y')}
Datos y logs en: {dir_datos}

Procesos disponibles:
- Acumulado Genesys Cloud
- Base Genesys Cloud
- Cruce Genesys Cloud
- Genesys Engaged
        """
        print(mensaje.strip())

    def obtener_hora_local(self):
        """Retorna hora actual de Colombia formateada"""
        hora = datetime.now(ZONA_COLOMBIA)
        return hora.strftime('%H:%M:%S')

    def obtener_fecha_hora_completa(self):
        """Retorna fecha y hora completa de Colombia"""
        ahora = datetime.now(ZONA_COLOMBIA)
        return ahora.strftime('%d/%m/%Y %H:%M:%S')

    # =========================================================================
    # GESTION DEL PROGRAMADOR
    # =========================================================================

    def activar_programador(self):
        """Activa el programador automatico"""
        resultado = horarios.iniciar_programador()

        if resultado:
            self.btn_iniciar_reloj.setEnabled(False)
            if hasattr(self, 'btn_detener_programador'):
                self.btn_detener_programador.setEnabled(True)
            self.actualizar_label_estado("ACTIVO")
            print("Programador automatico ACTIVADO")

            proxima = horarios.obtener_proxima_tarea()
            if proxima:
                print(f"Proxima ejecucion: {proxima['hora']} del {proxima['fecha']}")
            else:
                print("No hay tareas programadas. Verificar configuracion.")
        else:
            QMessageBox.warning(self, "Error", "No se pudo activar el programador")

    def detener_programador(self):
        """Detiene el programador automatico usando senales thread-safe."""
        print("Deteniendo programador...")

        def _detener():
            try:
                resultado = horarios.detener_programador()
                if resultado:
                    self.senales.habilitar_boton_iniciar.emit(True)
                    self.senales.habilitar_boton_detener.emit(False)
                    self.senales.actualizar_estado_label.emit("INACTIVO")
                    print("Programador automatico DETENIDO")
                else:
                    print("Error al detener el programador")
            except Exception as e:
                print(f"Error deteniendo programador: {e}")

        threading.Thread(target=_detener, daemon=True).start()

    def actualizar_label_estado(self, estado_programador):
        """Actualiza la etiqueta de estado en la barra inferior"""
        if hasattr(self, 'lbl_estado'):
            texto = f"Estado: Sistema listo | Programador: {estado_programador}"
            self.lbl_estado.setText(texto)

    # =========================================================================
    # EJECUCION MANUAL
    # =========================================================================

    def ejecutar_proceso_manual(self):
        """Ejecuta el proceso de cruce y engaged manualmente."""
        if self._hilo_manual and self._hilo_manual.is_alive():
            print("Ya hay una ejecucion manual en curso. Espere a que termine.")
            return

        self.btn_ejecutar_manual.setEnabled(False)

        print("Iniciando ejecucion manual...")
        print(f"Hora de inicio: {self.obtener_fecha_hora_completa()}")

        def ejecutar():
            try:
                resultado = tareas_migracion.procesar_cruces_y_engaged()
                if resultado:
                    print("Proceso manual completado exitosamente")
                else:
                    print("Proceso manual fallo - revisar logs")
            except Exception as e:
                print(f"Error en proceso manual: {str(e)}")
            finally:
                self.senales.habilitar_boton_manual.emit(True)

        self._hilo_manual = threading.Thread(target=ejecutar, daemon=True)
        self._hilo_manual.start()

    # =========================================================================
    # GESTION DE HORARIOS DESDE LA INTERFAZ
    # =========================================================================

    def cargar_horarios_en_tabla(self):
        """Carga los horarios del JSON en la tabla de la interfaz."""
        horarios_data = horarios.cargar_horarios_json()

        self.tabla_horarios.setRowCount(0)

        for i, entrada in enumerate(horarios_data):
            self.tabla_horarios.insertRow(i)

            hora = entrada.get("hora", "")
            tarea_key = entrada.get("tarea", "")
            tarea_label = self._obtener_label_tarea(tarea_key)
            dias = entrada.get("dias", [])
            dias_texto = self._dias_a_texto(dias)
            activo = entrada.get("activo", True)

            self.tabla_horarios.setItem(i, 0, QtWidgets.QTableWidgetItem(hora))
            self.tabla_horarios.setItem(i, 1, QtWidgets.QTableWidgetItem(tarea_label))
            self.tabla_horarios.setItem(i, 2, QtWidgets.QTableWidgetItem(dias_texto))

            item_activo = QtWidgets.QTableWidgetItem("Si" if activo else "No")
            if activo:
                item_activo.setForeground(Qt.GlobalColor.darkGreen)
            else:
                item_activo.setForeground(Qt.GlobalColor.red)
            self.tabla_horarios.setItem(i, 3, item_activo)

            self.tabla_horarios.setItem(i, 4, QtWidgets.QTableWidgetItem(str(i)))

    def _obtener_label_tarea(self, tarea_key):
        """Obtiene la etiqueta legible de una tarea"""
        for label, key in TAREAS_DISPONIBLES.items():
            if key == tarea_key:
                return label
        return tarea_key

    def _obtener_key_tarea(self, tarea_label):
        """Obtiene la key de una tarea a partir de su etiqueta"""
        return TAREAS_DISPONIBLES.get(tarea_label, tarea_label)

    def _dias_a_texto(self, dias):
        """Convierte lista de dias a texto legible"""
        if not dias:
            return ""

        orden = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
        dias_ordenados = [d for d in orden if d in dias]

        if dias_ordenados == ["lunes", "martes", "miercoles", "jueves", "viernes"]:
            return "Lunes a Viernes"
        if dias_ordenados == ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]:
            return "Lunes a Sabado"
        if dias_ordenados == ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]:
            return "Todos los dias"

        nombres = {
            "lunes": "Lun", "martes": "Mar", "miercoles": "Mie",
            "jueves": "Jue", "viernes": "Vie", "sabado": "Sab", "domingo": "Dom"
        }
        return ", ".join(nombres.get(d, d) for d in dias_ordenados)

    def _texto_a_dias(self, texto):
        """Convierte texto de dias a lista de dias"""
        texto = texto.strip().lower()

        if texto in ["lunes a viernes", "lun-vie", "lun a vie"]:
            return ["lunes", "martes", "miercoles", "jueves", "viernes"]
        if texto in ["lunes a sabado", "lun-sab", "lun a sab"]:
            return ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
        if texto in ["todos los dias", "lunes a domingo", "lun-dom"]:
            return ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

        mapeo = {
            "lun": "lunes", "mar": "martes", "mie": "miercoles",
            "jue": "jueves", "vie": "viernes", "sab": "sabado", "dom": "domingo",
            "lunes": "lunes", "martes": "martes", "miercoles": "miercoles",
            "jueves": "jueves", "viernes": "viernes", "sabado": "sabado", "domingo": "domingo"
        }

        dias = []
        for parte in texto.replace(",", " ").split():
            if parte in mapeo:
                dias.append(mapeo[parte])
        return dias

    def _obtener_indice_horario(self, fila):
        """Obtiene el indice del horario en el JSON a partir de la fila de la tabla."""
        indice_item = self.tabla_horarios.item(fila, 4)
        if not indice_item:
            return None
        try:
            indice = int(indice_item.text())
        except (ValueError, AttributeError):
            return None

        horarios_data = horarios.cargar_horarios_json()
        if 0 <= indice < len(horarios_data):
            return indice

        return None

    def agregar_horario(self):
        """Abre dialogo para agregar un nuevo horario"""
        dialogo = DialogoHorario(self, titulo="Agregar Horario")
        if dialogo.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            datos = dialogo.obtener_datos()
            if datos:
                horarios_data = horarios.cargar_horarios_json()
                horarios_data.append(datos)
                if horarios.guardar_horarios_json(horarios_data):
                    self.cargar_horarios_en_tabla()
                    self._recargar_programador_si_activo()
                    print(f"Horario agregado: {datos['hora']} - {datos['tarea']}")
                else:
                    QMessageBox.warning(self, "Error", "No se pudo guardar el horario")

    def modificar_horario(self):
        """Modifica el horario seleccionado en la tabla."""
        fila = self.tabla_horarios.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Atencion", "Seleccione un horario para modificar")
            return

        try:
            indice = self._obtener_indice_horario(fila)
            if indice is None:
                QMessageBox.warning(self, "Error",
                    "No se pudo identificar el horario.\n"
                    "Intente seleccionarlo nuevamente en la tabla.")
                return

            horarios_data = horarios.cargar_horarios_json()
            datos_actuales = horarios_data[indice]

            dialogo = DialogoHorario(self, titulo="Modificar Horario", datos=datos_actuales)
            if dialogo.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                datos = dialogo.obtener_datos()
                if datos:
                    horarios_data[indice] = datos
                    if horarios.guardar_horarios_json(horarios_data):
                        self.cargar_horarios_en_tabla()
                        self._recargar_programador_si_activo()
                        print(f"Horario modificado: {datos['hora']} - {datos['tarea']}")
                    else:
                        QMessageBox.warning(self, "Error", "No se pudo guardar el horario")

        except Exception as e:
            print(f"Error al modificar horario: {e}")
            QMessageBox.critical(self, "Error", f"Ocurrio un error al modificar:\n{str(e)}")

    def eliminar_horario(self):
        """Elimina el horario seleccionado de la tabla"""
        fila = self.tabla_horarios.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Atencion", "Seleccione un horario para eliminar")
            return

        indice = self._obtener_indice_horario(fila)
        if indice is None:
            QMessageBox.warning(self, "Error",
                "No se pudo identificar el horario.\n"
                "Intente seleccionarlo nuevamente en la tabla.")
            return

        respuesta = QMessageBox.question(
            self,
            "Confirmar Eliminacion",
            "Esta seguro de eliminar el horario seleccionado?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            horarios_data = horarios.cargar_horarios_json()
            if 0 <= indice < len(horarios_data):
                eliminado = horarios_data.pop(indice)
                if horarios.guardar_horarios_json(horarios_data):
                    self.cargar_horarios_en_tabla()
                    self._recargar_programador_si_activo()
                    print(f"Horario eliminado: {eliminado.get('hora', '')} - {eliminado.get('tarea', '')}")

    def toggle_horario_activo(self):
        """Activa o desactiva el horario seleccionado"""
        fila = self.tabla_horarios.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Atencion", "Seleccione un horario para activar/desactivar")
            return

        indice = self._obtener_indice_horario(fila)
        if indice is None:
            QMessageBox.warning(self, "Error",
                "No se pudo identificar el horario.\n"
                "Intente seleccionarlo nuevamente en la tabla.")
            return

        horarios_data = horarios.cargar_horarios_json()
        if 0 <= indice < len(horarios_data):
            horarios_data[indice]["activo"] = not horarios_data[indice].get("activo", True)
            if horarios.guardar_horarios_json(horarios_data):
                self.cargar_horarios_en_tabla()
                self._recargar_programador_si_activo()
                estado = "activado" if horarios_data[indice]["activo"] else "desactivado"
                print(f"Horario {estado}: {horarios_data[indice]['hora']} - {horarios_data[indice]['tarea']}")

    def _recargar_programador_si_activo(self):
        """Recarga la configuracion del programador si esta activo."""
        if not horarios.programador.activo:
            return

        if self._recargando:
            print("Recarga de programador ya en curso, esperando...")
            return

        self._recargando = True

        def _recargar():
            try:
                horarios.reiniciar_programador()
                print("Programador recargado con nuevos horarios")
            except Exception as e:
                print(f"Error recargando programador: {e}")
            finally:
                self._recargando = False

        threading.Thread(target=_recargar, daemon=True).start()

    # =========================================================================
    # GESTION DE RUTAS DE ARCHIVOS CON EXPLORADOR
    # =========================================================================

    def inicializar_rutas(self):
        """Inicializa la tabla de rutas con la configuración actual y botón explorador"""
        if hasattr(self, 'tabla_rutas'):
            self.tabla_rutas.setColumnCount(3)
            self.tabla_rutas.setHorizontalHeaderLabels(["Variable", "Ruta", "Explorar"])
            self.tabla_rutas.setColumnWidth(0, 200)
            self.tabla_rutas.setColumnWidth(1, 420)
            self.tabla_rutas.setColumnWidth(2, 60)
            self.cargar_rutas_modulo()

    def cargar_rutas_modulo(self):
        """Carga las rutas del módulo seleccionado en la tabla con botones de exploración"""
        if not hasattr(self, 'tabla_rutas') or not hasattr(self, 'combo_modulos_rutas'):
            return

        modulo = self.combo_modulos_rutas.currentText()
        self.tabla_rutas.setRowCount(0)

        config_rutas = horarios.cargar_configuracion_rutas()

        if modulo in config_rutas:
            for row, (key, value) in enumerate(config_rutas[modulo].items()):
                self.tabla_rutas.insertRow(row)
                
                self.tabla_rutas.setItem(row, 0, QtWidgets.QTableWidgetItem(key))
                
                item_ruta = QtWidgets.QTableWidgetItem(value)
                item_ruta.setFlags(item_ruta.flags() | Qt.ItemFlag.ItemIsEditable)
                self.tabla_rutas.setItem(row, 1, item_ruta)
                
                btn_explorar = QtWidgets.QPushButton("...")
                btn_explorar.setObjectName("btn_explorar_ruta")
                btn_explorar.setMinimumSize(30, 25)
                btn_explorar.setMaximumSize(35, 28)
                btn_explorar.clicked.connect(lambda checked, r=row: self.explorar_ruta(r))
                btn_explorar.setToolTip("Seleccionar carpeta o archivo con el explorador")
                
                btn_explorar.setStyleSheet("""
                    QPushButton {
                        background-color: #805ad5;
                        border: none;
                        border-radius: 4px;
                        color: white;
                        font-weight: bold;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #6b46c1;
                    }
                """)
                
                self.tabla_rutas.setCellWidget(row, 2, btn_explorar)

    def explorar_ruta(self, fila):
        """Abre el explorador de archivos para seleccionar una ruta"""
        if fila < 0 or fila >= self.tabla_rutas.rowCount():
            return
            
        item_ruta = self.tabla_rutas.item(fila, 1)
        if not item_ruta:
            return
            
        ruta_actual = item_ruta.text()
        
        item_variable = self.tabla_rutas.item(fila, 0)
        variable = item_variable.text() if item_variable else ""
        
        es_carpeta = any(palabra in variable.lower() for palabra in 
                        ['carpeta', 'base', 'dir', 'ruta_', '_path'])
        
        if not es_carpeta:
            extensiones = ['.csv', '.xlsx', '.xls', '.txt', '.log', '.py']
            tiene_extension = any(ruta_actual.lower().endswith(ext) for ext in extensiones)
            es_carpeta = not tiene_extension
        
        if es_carpeta:
            ruta_seleccionada = QFileDialog.getExistingDirectory(
                self,
                f"Seleccionar carpeta para: {variable}",
                ruta_actual if os.path.exists(ruta_actual) else os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly
            )
        else:
            extension = os.path.splitext(ruta_actual)[1] if ruta_actual else ""
            filtro = f"*{extension}" if extension else "Todos los archivos (*.*)"
            
            ruta_seleccionada, _ = QFileDialog.getOpenFileName(
                self,
                f"Seleccionar archivo para: {variable}",
                ruta_actual if os.path.exists(os.path.dirname(ruta_actual)) else os.path.expanduser("~"),
                f"{filtro};;Todos los archivos (*.*)"
            )
        
        if ruta_seleccionada:
            self.tabla_rutas.setItem(fila, 1, QtWidgets.QTableWidgetItem(ruta_seleccionada))
            print(f"Ruta actualizada: {ruta_seleccionada}")

    def guardar_rutas(self):
        """Guarda las rutas modificadas en AppData/Roaming"""
        if not hasattr(self, 'tabla_rutas') or not hasattr(self, 'combo_modulos_rutas'):
            return

        modulo = self.combo_modulos_rutas.currentText()
        config_rutas = horarios.cargar_configuracion_rutas()

        for row in range(self.tabla_rutas.rowCount()):
            key_item = self.tabla_rutas.item(row, 0)
            value_item = self.tabla_rutas.item(row, 1)
            if key_item and value_item:
                if modulo not in config_rutas:
                    config_rutas[modulo] = {}
                config_rutas[modulo][key_item.text()] = value_item.text()

        if horarios.guardar_configuracion_rutas(config_rutas):
            print(f"Rutas del módulo {modulo} guardadas correctamente")
            QMessageBox.information(self, "Exito", f"Rutas del módulo {modulo} guardadas correctamente")
            
            try:
                modulos_a_recargar = [
                    'Acomulado_Genesys_Cloud',
                    'Base_Genesys_Cloud',
                    'Base_Genesys_Engaged', 
                    'Cruce_Genesys_Cloud',
                    'Genesys_Engaged'
                ]
                for nombre_modulo in modulos_a_recargar:
                    if nombre_modulo in sys.modules:
                        importlib.reload(sys.modules[nombre_modulo])
                print("Modulos recargados con nuevas rutas")
            except Exception as e:
                print(f"Advertencia: No se pudieron recargar todos los modulos: {e}")
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar la configuración de rutas")

    def restaurar_rutas(self):
        """Restaura las rutas a los valores por defecto"""
        respuesta = QMessageBox.question(
            self,
            "Confirmar",
            "Esta seguro de restaurar todas las rutas a los valores por defecto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            config_default = horarios._rutas_por_defecto()
            if horarios.guardar_configuracion_rutas(config_default):
                self.cargar_rutas_modulo()
                print("Rutas restauradas a valores por defecto")
                QMessageBox.information(self, "Exito", "Rutas restauradas a valores por defecto")

    # =========================================================================
    # EDITOR DE CODIGO
    # =========================================================================

    def cargar_codigo_modulo(self):
        """Carga el código del módulo seleccionado en el editor"""
        if not hasattr(self, 'combo_modulos_editor') or not hasattr(self, 'txt_editor_codigo'):
            return

        modulo = self.combo_modulos_editor.currentText()
        ruta_actual = os.path.join(os.path.dirname(os.path.abspath(__file__)), modulo)

        if os.path.exists(ruta_actual):
            try:
                with open(ruta_actual, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                self.txt_editor_codigo.setText(contenido)
                print(f"Codigo de {modulo} cargado")
            except Exception as e:
                print(f"Error al cargar {modulo}: {str(e)}")
                self.txt_editor_codigo.setText(f"# Error al cargar el archivo:\n# {str(e)}")
        else:
            self.txt_editor_codigo.setText(f"# El archivo {modulo} no existe en el directorio actual")
            print(f"Advertencia: {modulo} no encontrado")

    def guardar_codigo_modulo(self):
        """Guarda los cambios del editor en el archivo del módulo"""
        if not hasattr(self, 'combo_modulos_editor') or not hasattr(self, 'txt_editor_codigo'):
            return

        modulo = self.combo_modulos_editor.currentText()
        ruta_actual = os.path.join(os.path.dirname(os.path.abspath(__file__)), modulo)

        respuesta = QMessageBox.question(
            self,
            "Confirmar",
            f"Esta seguro de guardar los cambios en {modulo}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                contenido = self.txt_editor_codigo.toPlainText()
                with open(ruta_actual, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                print(f"Codigo de {modulo} guardado correctamente")
                QMessageBox.information(self, "Exito", f"{modulo} guardado correctamente")
                
                nombre_modulo = modulo.replace('.py', '')
                if nombre_modulo in sys.modules:
                    try:
                        importlib.reload(sys.modules[nombre_modulo])
                        print(f"Modulo {nombre_modulo} recargado")
                    except Exception as e:
                        print(f"No se pudo recargar {nombre_modulo}: {e}")
                        print("Recomendacion: Reinicie la aplicacion para aplicar los cambios")
            except Exception as e:
                print(f"Error al guardar {modulo}: {str(e)}")
                QMessageBox.critical(self, "Error", f"Error al guardar:\n{str(e)}")

    # =========================================================================
    # ACTUALIZACION DE ESTADO
    # =========================================================================

    def actualizar_estado(self):
        """Actualiza el estado de las tareas en la interfaz"""
        estado = tareas_migracion.estado_tareas()

        if any(estado.values()):
            procesos_activos = [nombre for nombre, activo in estado.items() if activo]
            if procesos_activos:
                self.txt_consola.append(f"[ESTADO] Procesos activos: {', '.join(procesos_activos)}")

    # =========================================================================
    # EVENTOS
    # =========================================================================

    def closeEvent(self, event):
        """Maneja el evento de cierre de la aplicacion."""
        if horarios.programador.activo:
            respuesta = QMessageBox.question(
                self,
                "Confirmar Salida",
                "El programador esta activo. Desea detenerlo y salir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if respuesta == QMessageBox.StandardButton.Yes:
                horarios.detener_programador()
                self._cerrar_recursos()
                event.accept()
            else:
                event.ignore()
        else:
            self._cerrar_recursos()
            event.accept()

    def _cerrar_recursos(self):
        """Cierra recursos antes de salir (log file, etc.)"""
        if self.redirigir_consola:
            self.redirigir_consola.cerrar_log()

    def limpiar_consola(self):
        self.txt_consola.clear()


class DialogoHorario(QtWidgets.QDialog):
    """Dialogo para agregar o modificar un horario."""

    def __init__(self, parent=None, titulo="Horario", datos=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(350)

        layout = QtWidgets.QVBoxLayout(self)

        # Hora
        layout_hora = QtWidgets.QHBoxLayout()
        layout_hora.addWidget(QtWidgets.QLabel("Hora (HH:MM):"))
        self.input_hora = QtWidgets.QTimeEdit()
        self.input_hora.setDisplayFormat("HH:mm")
        if datos and "hora" in datos:
            try:
                partes = str(datos["hora"]).split(":")
                if len(partes) == 2:
                    self.input_hora.setTime(QTime(int(partes[0]), int(partes[1])))
            except (ValueError, TypeError):
                pass
        layout_hora.addWidget(self.input_hora)
        layout.addLayout(layout_hora)

        # Tarea
        layout_tarea = QtWidgets.QHBoxLayout()
        layout_tarea.addWidget(QtWidgets.QLabel("Tarea:"))
        self.combo_tarea = QtWidgets.QComboBox()
        for label in TAREAS_DISPONIBLES:
            self.combo_tarea.addItem(label)
        if datos and "tarea" in datos:
            tarea_key = datos["tarea"]
            for i, (label, key) in enumerate(TAREAS_DISPONIBLES.items()):
                if key == tarea_key:
                    self.combo_tarea.setCurrentIndex(i)
                    break
        layout_tarea.addWidget(self.combo_tarea)
        layout.addLayout(layout_tarea)

        # Dias
        layout.addWidget(QtWidgets.QLabel("Dias:"))
        self.check_dias = {}
        grid_dias = QtWidgets.QGridLayout()
        nombres_dias = [
            ("Lunes", "lunes"), ("Martes", "martes"),
            ("Miercoles", "miercoles"), ("Jueves", "jueves"),
            ("Viernes", "viernes"), ("Sabado", "sabado"),
            ("Domingo", "domingo")
        ]
        for i, (nombre, key) in enumerate(nombres_dias):
            cb = QtWidgets.QCheckBox(nombre)
            self.check_dias[key] = cb
            grid_dias.addWidget(cb, i // 4, i % 4)

        if datos and "dias" in datos:
            for dia in datos["dias"]:
                if dia in self.check_dias:
                    self.check_dias[dia].setChecked(True)

        layout.addLayout(grid_dias)

        # Activo
        self.check_activo = QtWidgets.QCheckBox("Activo")
        self.check_activo.setChecked(datos.get("activo", True) if datos else True)
        layout.addWidget(self.check_activo)

        # Botones
        layout_botones = QtWidgets.QHBoxLayout()
        btn_aceptar = QtWidgets.QPushButton("Aceptar")
        btn_cancelar = QtWidgets.QPushButton("Cancelar")
        btn_aceptar.clicked.connect(self.accept)
        btn_cancelar.clicked.connect(self.reject)
        layout_botones.addWidget(btn_aceptar)
        layout_botones.addWidget(btn_cancelar)
        layout.addLayout(layout_botones)

    def obtener_datos(self):
        """Retorna los datos del dialogo como diccionario."""
        hora = self.input_hora.time().toString("HH:mm")
        tarea_label = self.combo_tarea.currentText()
        tarea_key = TAREAS_DISPONIBLES.get(tarea_label, tarea_label)

        dias = [key for key, cb in self.check_dias.items() if cb.isChecked()]

        if not dias:
            QtWidgets.QMessageBox.warning(self, "Atencion", "Seleccione al menos un dia")
            return None

        return {
            "hora": hora,
            "tarea": tarea_key,
            "dias": dias,
            "activo": self.check_activo.isChecked()
        }


def main():
    """Punto de entrada principal"""
    app = QApplication(sys.argv)
    ventana = InterfazPrincipal()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()