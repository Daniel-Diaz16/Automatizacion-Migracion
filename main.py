# --- main.py (Fragmento actualizado) ---
import sys
from datetime import datetime
from zoneinfo import ZoneInfo # Importamos la librería nativa
from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import QTimer

import tareas_migracion
import horarios

class InterfazPrincipal(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("interfaz.ui", self)
        
        # ... (conexiones de botones y configuraciones) ...

    def obtener_hora_local(self):
        """Genera la hora actual estrictamente en la zona horaria de Colombia"""
        zona_colombia = ZoneInfo("America/Bogota")
        hora_exacta = datetime.now(zona_colombia)
        return hora_exacta.strftime('%H:%M:%S')

    def log_mensaje(self, mensaje):
        """Escribe en la cajita blanca de la UI usando la hora de Colombia"""
        hora_col = self.obtener_hora_local()
        self.txt_consola.append(f"[{hora_col}] {mensaje}")
        
        # Baja el scroll automáticamente
        scrollbar = self.txt_consola.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # Cuando inicies la automatización se verá así:
    def activar_automatizacion(self):
        self.log_mensaje(">> Reloj automático ACTIVADO (Hora Colombia). Esperando cortes...")
        self.btn_iniciar_reloj.setEnabled(False)
        self.timer.start(30000)