# --- horarios.py ---
import schedule
import tareas_migracion 

def configurar_rutinas():
    """Configura todas las horas de lunes a sábado"""
    dias = [schedule.every().monday, schedule.every().tuesday, 
            schedule.every().wednesday, schedule.every().thursday, 
            schedule.every().friday]
    
    # 1. Acumulado y Base
    for dia in dias + [schedule.every().saturday]:
        dia.at("08:50").do(tareas_migracion.procesar_acumulado)
        dia.at("09:10").do(tareas_migracion.procesar_base_cloud)

    # 2. Cruces Lun - Vie
    for dia in dias:
        for hora in ["08:10", "09:10", "10:10", "11:10", "12:10", "13:10", "14:10", "15:10", "16:10", "17:10", "18:10"]:
            dia.at(hora).do(tareas_migracion.procesar_cruces_y_engaged)

    # 3. Cruces Sábados
    for hora in ["08:10", "09:10", "10:10", "11:10", "12:10", "13:10", "14:10", "15:10"]:
        schedule.every().saturday.at(hora).do(tareas_migracion.procesar_cruces_y_engaged)

def revisar_reloj():
    """Esta función la llamará la Interfaz cada cierto tiempo"""
    schedule.run_pending()