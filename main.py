"""
Aplicacion principal del sistema de migraciones
Los datos persistentes (horarios, logs) se almacenan en %APPDATA%/RPA_Migracion/
"""
import sys
import os
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject, QTime
from PyQt6.QtWidgets import QMessageBox, QApplication
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
        self._recargando = False  # Flag para evitar recargas concurrentes del programador

        self.cargar_interfaz()
        self.inicializar_tablas()
        self.conectar_botones()
        self.configurar_temporizadores()
        self.inicializar_senales_ui()
        self.inicializar_redireccion_consola()
        self.cargar_horarios_en_tabla()
        self.mostrar_mensaje_bienvenida()

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
        self.setGeometry(100, 100, 600, 450)

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

        layout_botones.addWidget(self.btn_iniciar_reloj)
        layout_botones.addWidget(self.btn_ejecutar_manual)
        layout_botones.addWidget(self.btn_detener_programador)
        layout.addLayout(layout_botones)

        self.txt_consola = QtWidgets.QTextEdit()
        self.txt_consola.setReadOnly(True)
        layout.addWidget(self.txt_consola)

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

    def inicializar_senales_ui(self):
        """Configura las senales thread-safe para actualizar la UI desde hilos secundarios.
        Sin estas senales, modificar widgets desde otros hilos causa errores y crasheos
        en PyQt6, lo que era la causa principal del error al modificar horarios.
        """
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

        # Temporador para rotacion de log (cada 60 segundos)
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
        """Detiene el programador automatico usando senales thread-safe.
        La detencion del hilo es casi instantanea gracias a threading.Event,
        y las actualizaciones de UI se hacen via senales para evitar crasheos.
        """
        print("Deteniendo programador...")

        def _detener():
            try:
                resultado = horarios.detener_programador()
                # Actualizar UI via senales thread-safe (NO modificar widgets directamente)
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
        """Ejecuta el proceso de cruce y engaged manualmente.
        Usa senales thread-safe para rehabilitar el boton al finalizar.
        """
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
                # Rehabilitar boton via senal thread-safe
                self.senales.habilitar_boton_manual.emit(True)

        self._hilo_manual = threading.Thread(target=ejecutar, daemon=True)
        self._hilo_manual.start()

    # =========================================================================
    # GESTION DE HORARIOS DESDE LA INTERFAZ
    # =========================================================================

    def cargar_horarios_en_tabla(self):
        """Carga los horarios del JSON en la tabla de la interfaz.
        El JSON se lee desde %APPDATA%/RPA_Migracion/horarios.json.
        """
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

            # Guardar el indice del JSON como ID interno (columna oculta)
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
        """Obtiene el indice del horario en el JSON a partir de la fila de la tabla.
        Retorna None si no se puede obtener un indice valido.
        """
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
        """Modifica el horario seleccionado en la tabla.
        Corregido: usa _obtener_indice_horario() para validacion robusta del indice,
        y try/except para capturar errores inesperados que antes causaban crasheos.
        """
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
        """Recarga la configuracion del programador si esta activo.
        Usa un flag para evitar recargas concurrentes que podrian causar errores.
        La recarga se hace en hilo secundario para no bloquear la UI.
        """
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
        """Maneja el evento de cierre de la aplicacion.
        Detiene el programador y cierra el archivo de log.
        """
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
    """Dialogo para agregar o modificar un horario.
    Corregido: manejo robusto de datos iniciales con validacion completa.
    """

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

        # Pre-seleccionar dias si hay datos
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
        """Retorna los datos del dialogo como diccionario.
        Retorna None si no se selecciono ningun dia.
        """
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
