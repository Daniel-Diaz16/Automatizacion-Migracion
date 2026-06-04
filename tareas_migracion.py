# --- tareas_migracion.py ---
import Base_Genesys_Cloud
import Genesys_Engaged
import Acomulado_Genesys_Cloud
import Cruce_Genesys_Cloud

def procesar_acumulado():
    try:
        Acomulado_Genesys_Cloud.ejecutar_acumulado()
    except Exception as e:
        print(f"[ERROR en Acumulado]: {e}")

def procesar_base_cloud():
    try:
        Base_Genesys_Cloud.ejecutar_base_cloud()
    except Exception as e:
        print(f"[ERROR en Base Cloud]: {e}")

def procesar_cruces_y_engaged():
    try:
        Cruce_Genesys_Cloud.ejecutar_cruce_cloud()
        Genesys_Engaged.ejecutar_base_engaged()
    except Exception as e:
        print(f"[ERROR en Cruces/Engaged]: {e}")