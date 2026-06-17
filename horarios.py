"""
Sistema de programacion horaria con soporte para hilos
"""
import schedule
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import tareas_migracion

class ProgramadorHorario:
    """Clase que maneja la programacion de tareas"""
    
    def __init__(self):
        self.hilo_programador = None
        self.activo = False
        self.tareas_registradas = []
        
    def obtener_hora_colombia(self):
        """Retorna hora actual de Colombia"""
        zona = ZoneInfo("America/Bogota")
        return datetime.now(zona)
    
    def configurar_horarios(self):
        """Configura todas las horas segun el requerimiento"""
        
        # Limpiar configuraciones previas
        schedule.clear()
        self.tareas_registradas = []
        
        # Dias laborales: Lunes a Viernes
        dias_laborales = [
            schedule.every().monday,
            schedule.every().tuesday,
            schedule.every().wednesday,
            schedule.every().thursday,
            schedule.every().friday
        ]
        
        # Configurar tareas de acumulado y base (08:50 y 09:10)
        horarios_base = ["08:50", "09:10"]
        
        # Para Lunes a Viernes
        for dia in dias_laborales:
            for hora in horarios_base:
                trabajo = dia.at(hora).do(tareas_migracion.procesar_acumulado)
                self.tareas_registradas.append(("ACUMULADO", hora, "LUN-VIE"))
                
                trabajo = dia.at(hora).do(tareas_migracion.procesar_base_cloud)
                self.tareas_registradas.append(("BASE_CLOUD", hora, "LUN-VIE"))
        
        # Para Sabados (mismos horarios)
        for hora in horarios_base:
            trabajo = schedule.every().saturday.at(hora).do(tareas_migracion.procesar_acumulado)
            self.tareas_registradas.append(("ACUMULADO", hora, "SABADO"))
            
            trabajo = schedule.every().saturday.at(hora).do(tareas_migracion.procesar_base_cloud)
            self.tareas_registradas.append(("BASE_CLOUD", hora, "SABADO"))
        
        # Horarios para cruces y engaged (de 08:10 a 18:10 cada hora)
        horarios_cruce = [
            "08:10", "09:10", "10:00", "11:10", "12:10",
            "13:10", "14:10", "15:10", "16:10", "17:10", "18:10"
        ]
        
        # Lunes a Viernes
        for dia in dias_laborales:
            for hora in horarios_cruce:
                trabajo = dia.at(hora).do(tareas_migracion.procesar_cruces_y_engaged)
                self.tareas_registradas.append(("CRUCE+ENGAGED", hora, "LUN-VIE"))
        
        # Sabados (hasta 15:10)
        horarios_sabado = ["08:10", "09:10", "10:10", "11:10", "12:10", "13:10", "14:10", "15:10"]
        for hora in horarios_sabado:
            trabajo = schedule.every().saturday.at(hora).do(tareas_migracion.procesar_cruces_y_engaged)
            self.tareas_registradas.append(("CRUCE+ENGAGED", hora, "SABADO"))
        
        print(f"Horarios configurados. {len(self.tareas_registradas)} tareas programadas")
        return True
    
    def ejecutar_bucle(self):
        """Bucle principal del programador"""
        print(f"Programador activado. Hora Colombia: {self.obtener_hora_colombia().strftime('%H:%M:%S')}")
        
        while self.activo:
            try:
                schedule.run_pending()
                time.sleep(30)
            except Exception as e:
                print(f"Error en programador: {str(e)}")
                time.sleep(60)
        
        print("Programador desactivado")
    
    def iniciar(self):
        """Inicia el programador en un hilo separado"""
        if self.activo:
            print("El programador ya esta activo")
            return False
        
        self.configurar_horarios()
        self.activo = True
        
        self.hilo_programador = threading.Thread(target=self.ejecutar_bucle, daemon=True)
        self.hilo_programador.start()
        
        return True
    
    def detener(self):
        """Detiene el programador"""
        if not self.activo:
            return False
        
        self.activo = False
        
        if self.hilo_programador:
            self.hilo_programador.join(timeout=5)
        
        return True
    
    def obtener_proxima_tarea(self):
        """Retorna informacion de la proxima tarea a ejecutar"""
        proximo = schedule.next_run()
        if proximo:
            return {
                'hora': proximo.strftime('%H:%M:%S'),
                'fecha': proximo.strftime('%d/%m/%Y')
            }
        return None

# Instancia global
programador = ProgramadorHorario()

def iniciar_programador():
    """Funcion publica para iniciar el programador"""
    return programador.iniciar()

def detener_programador():
    """Funcion publica para detener el programador"""
    return programador.detener()

def configurar_rutinas():
    """Funcion publica para configurar rutinas"""
    return programador.configurar_horarios()

def obtener_proxima_tarea():
    """Funcion publica para obtener proxima tarea"""
    return programador.obtener_proxima_tarea()