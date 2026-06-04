"""
Aplicacion principal del sistema de migraciones
"""
import sys
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import QMessageBox, QApplication
import tareas_migracion
import horarios
import sys
import os

def resource_path(relative_path):
    """Obtiene la ruta correcta tanto en desarrollo como en ejecutable"""
    try:
        # Cuando está compilado como .exe
        base_path = sys._MEIPASS
    except Exception:
        # Cuando se ejecuta como script normal
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ConsolaRedirigida(QObject):
    """Redirige la salida de consola a un widget de texto"""
    texto_recibido = pyqtSignal(str)
    
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.texto_recibido.connect(self._escribir_widget)
    
    def write(self, texto):
        if texto and texto.strip():
            self.texto_recibido.emit(texto)
    
    def _escribir_widget(self, texto):
        self.widget.append(texto.strip())
    
    def flush(self):
        pass

class InterfazPrincipal(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        
        self.redirigir_consola = None
        self.estado_actualizador = None
        
        self.cargar_interfaz()
        self.inicializar_tablas()
        self.conectar_botones()
        self.configurar_temporizadores()
        self.inicializar_redireccion_consola()
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
        self.tabla_estado.setHorizontalHeaderLabels(["Proceso", "Estado", "Última Ejecución", "Duración"])
        self.tabla_estado.setColumnWidth(0, 200)
        self.tabla_estado.setColumnWidth(1, 100)
        self.tabla_estado.setColumnWidth(2, 180)
        self.tabla_estado.setColumnWidth(3, 100)
        
        # Datos iniciales
        procesos = [
            ("Acumulado Genesys Cloud", "⚪ Inactivo", "-", "-"),
            ("Base Genesys Cloud", "⚪ Inactivo", "-", "-"),
            ("Cruce Genesys Cloud", "⚪ Inactivo", "-", "-"),
            ("Genesys Engaged", "⚪ Inactivo", "-", "-"),
        ]
        
        for row, (proceso, estado, ultima, duracion) in enumerate(procesos):
            self.tabla_estado.insertRow(row)
            self.tabla_estado.setItem(row, 0, QtWidgets.QTableWidgetItem(proceso))
            self.tabla_estado.setItem(row, 1, QtWidgets.QTableWidgetItem(estado))
            self.tabla_estado.setItem(row, 2, QtWidgets.QTableWidgetItem(ultima))
            self.tabla_estado.setItem(row, 3, QtWidgets.QTableWidgetItem(duracion))
        
        # Tabla de horarios
        self.tabla_horarios.setColumnCount(3)
        self.tabla_horarios.setHorizontalHeaderLabels(["Horario", "Tarea", "Días"])
        self.tabla_horarios.setColumnWidth(0, 100)
        self.tabla_horarios.setColumnWidth(1, 250)
        self.tabla_horarios.setColumnWidth(2, 200)
        
        horarios_data = [
            ("08:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("08:50", "Acumulado + Base Cloud", "Lunes a Sábado"),
            ("09:10", "Acumulado + Base Cloud", "Lunes a Sábado"),
            ("10:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("11:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("12:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("13:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("14:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("15:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("16:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("17:10", "Cruce + Engaged", "Lunes a Viernes"),
            ("18:10", "Cruce + Engaged", "Lunes a Viernes"),
        ]
        
        for row, (horario, tarea, dias) in enumerate(horarios_data):
            self.tabla_horarios.insertRow(row)
            self.tabla_horarios.setItem(row, 0, QtWidgets.QTableWidgetItem(horario))
            self.tabla_horarios.setItem(row, 1, QtWidgets.QTableWidgetItem(tarea))
            self.tabla_horarios.setItem(row, 2, QtWidgets.QTableWidgetItem(dias))

    def crear_interfaz_por_defecto(self):
        """Crea la interfaz por codigo si no existe el archivo .ui"""
        self.setWindowTitle("Panel de Automatizacion de Migraciones")
        self.setGeometry(100, 100, 600, 450)
        
        # Widget central
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        
        # Titulo
        self.lbl_title = QtWidgets.QLabel("Control de Migracion y Gestion")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fuente = self.lbl_title.font()
        fuente.setPointSize(14)
        fuente.setBold(True)
        self.lbl_title.setFont(fuente)
        layout.addWidget(self.lbl_title)
        
        # Zona horaria
        self.lbl_zona = QtWidgets.QLabel("Aviso: Las migraciones operan bajo horario colombiano")
        self.lbl_zona.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_zona)
        
        # Botones
        layout_botones = QtWidgets.QHBoxLayout()
        self.btn_iniciar_reloj = QtWidgets.QPushButton("Activar Programador")
        self.btn_ejecutar_manual = QtWidgets.QPushButton("Ejecutar Cruce Manual")
        self.btn_detener_programador = QtWidgets.QPushButton("Detener Programador")
        self.btn_detener_programador.setEnabled(False)
        
        layout_botones.addWidget(self.btn_iniciar_reloj)
        layout_botones.addWidget(self.btn_ejecutar_manual)
        layout_botones.addWidget(self.btn_detener_programador)
        layout.addLayout(layout_botones)
        
        # Consola
        self.txt_consola = QtWidgets.QTextEdit()
        self.txt_consola.setReadOnly(True)
        layout.addWidget(self.txt_consola)
    
    def conectar_botones(self):
        """Conecta los botones a sus funciones"""
        self.btn_iniciar_reloj.clicked.connect(self.activar_programador)
        self.btn_ejecutar_manual.clicked.connect(self.ejecutar_proceso_manual)
        
        # Boton detener programador (si existe)
        if hasattr(self, 'btn_detener_programador'):
            self.btn_detener_programador.clicked.connect(self.detener_programador)
    
    def configurar_temporizadores(self):
        """Configura los temporizadores para actualizaciones"""
        self.temporador_estado = QTimer()
        self.temporador_estado.timeout.connect(self.actualizar_estado)
        self.temporador_estado.start(5000)
    
    def inicializar_redireccion_consola(self):
        """Redirige stdout a la consola de la interfaz"""
        self.redirigir_consola = ConsolaRedirigida(self.txt_consola)
        sys.stdout = self.redirigir_consola
    
    def mostrar_mensaje_bienvenida(self):
        """Muestra mensaje de bienvenida con informacion del sistema"""
        hora_colombia = datetime.now(ZoneInfo("America/Bogota"))
        mensaje = f"""
Sistema de Automatizacion de Migraciones Iniciado
Zona horaria: Colombia (America/Bogota)
Hora actual: {hora_colombia.strftime('%H:%M:%S')}
Fecha: {hora_colombia.strftime('%d/%m/%Y')}

Procesos disponibles:
- Acumulado Genesys Cloud
- Base Genesys Cloud
- Cruce Genesys Cloud
- Genesys Engaged
        """
        print(mensaje.strip())
    
    def obtener_hora_local(self):
        """Retorna hora actual de Colombia formateada"""
        hora = datetime.now(ZoneInfo("America/Bogota"))
        return hora.strftime('%H:%M:%S')
    
    def obtener_fecha_hora_completa(self):
        """Retorna fecha y hora completa de Colombia"""
        ahora = datetime.now(ZoneInfo("America/Bogota"))
        return ahora.strftime('%d/%m/%Y %H:%M:%S')
    
    def activar_programador(self):
        """Activa el programador automatico"""
        resultado = horarios.iniciar_programador()
        
        if resultado:
            self.btn_iniciar_reloj.setEnabled(False)
            if hasattr(self, 'btn_detener_programador'):
                self.btn_detener_programador.setEnabled(True)
            print("Programador automatico ACTIVADO")
            
            proxima = horarios.obtener_proxima_tarea()
            if proxima:
                print(f"Proxima ejecucion: {proxima['hora']} del {proxima['fecha']}")
            else:
                print("No hay tareas programadas. Verificar configuracion.")
        else:
            QMessageBox.warning(self, "Error", "No se pudo activar el programador")
    
    def detener_programador(self):
        """Detiene el programador automatico"""
        resultado = horarios.detener_programador()
        
        if resultado:
            self.btn_iniciar_reloj.setEnabled(True)
            if hasattr(self, 'btn_detener_programador'):
                self.btn_detener_programador.setEnabled(False)
            print("Programador automatico DETENIDO")
    
    def ejecutar_proceso_manual(self):
        """Ejecuta el proceso de cruce y engaged manualmente"""
        self.btn_ejecutar_manual.setEnabled(False)
        
        print("Iniciando ejecucion manual...")
        print(f"Hora de inicio: {self.obtener_fecha_hora_completa()}")
        
        # Ejecutar en un hilo separado para no bloquear
        import threading
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
                # Re-habilitar boton en el hilo principal
                from PyQt6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(self.btn_ejecutar_manual, "setEnabled", 
                                        Qt.ConnectionType.QueuedConnection,
                                        Qt.Argument(bool, True))
        
        hilo = threading.Thread(target=ejecutar, daemon=True)
        hilo.start()
    
    def actualizar_estado(self):
        """Actualiza el estado de las tareas en la interfaz"""
        estado = tareas_migracion.estado_tareas()
        
        # Solo mostrar si hay cambios de estado
        if any(estado.values()):
            procesos_activos = [nombre for nombre, activo in estado.items() if activo]
            if procesos_activos:
                self.txt_consola.append(f"[ESTADO] Procesos activos: {', '.join(procesos_activos)}")
    
    def closeEvent(self, event):
        """Maneja el evento de cierre de la aplicacion"""
        if horarios.programador.activo:
            respuesta = QMessageBox.question(
                self,
                "Confirmar Salida",
                "El programador esta activo. Desea detenerlo y salir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if respuesta == QMessageBox.StandardButton.Yes:
                horarios.detener_programador()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    """Punto de entrada principal"""
    app = QApplication(sys.argv)
    ventana = InterfazPrincipal()
    ventana.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()