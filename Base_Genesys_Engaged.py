import os
import glob
import pandas as pd
import logging
import json
import sys

# Configuración de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


# =============================================================================
# FUNCION PARA CARGAR RUTAS DESDE JSON
# =============================================================================

def obtener_ruta_config():
    """Obtiene la ruta donde se guarda la configuración en AppData/Roaming"""
    app_data = os.getenv('APPDATA')
    config_dir = os.path.join(app_data, 'RPA_Migracion')
    return os.path.join(config_dir, 'rutas_config.json')


def cargar_rutas_modulo():
    """Carga las rutas del módulo Base_Genesys_Engaged desde el JSON"""
    ruta_config = obtener_ruta_config()
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'Base_Genesys_Engaged' in config:
                return config['Base_Genesys_Engaged']
        except:
            pass
    # Si no existe, usar rutas por defecto
    return {
        'RUTA_BASES': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Engaged Bases',
        'RUTA_SALIDA': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Engaged.xlsx'
    }


# Cargar rutas desde JSON
_RUTAS = cargar_rutas_modulo()

# Asignar variables globales
RUTA_BASES = _RUTAS['RUTA_BASES']
RUTA_SALIDA = _RUTAS['RUTA_SALIDA']


# =============================================================================
# PROCESO PRINCIPAL
# =============================================================================

def procesar_engaged_eficiente():
    """Procesa los archivos .rsl y genera la base consolidada de Genesys Engaged"""
    archivos = glob.glob(os.path.join(RUTA_BASES, "*.rsl"))
    lista_df = []

    if not archivos:
        logging.warning("No se encontraron archivos .rsl en: %s", RUTA_BASES)
        return False

    logging.info("Procesando %d archivos .rsl...", len(archivos))

    for archivo in archivos:
        logging.info("Procesando: %s", os.path.basename(archivo))
        
        try:
            # 1. Leemos el archivo | como delimitador
            df = pd.read_csv(archivo, sep='|', encoding='latin-1', dtype=str, on_bad_lines='skip')
            
            # 2. Lógica de limpieza dinámica
            primera_fila = df.iloc[0]
            
            # Extraemos lo que está antes del '=' para los nombres
            nuevos_nombres = [str(val).split('=')[0] for val in primera_fila]
            
            # Renombramos las columnas
            df.columns = nuevos_nombres
            
            def limpiar_celda(x):
                s = str(x)
                if '=' in s:
                    return s.split('=', 1)[1]
                return s

            # Aplicamos la limpieza a todo el DataFrame
            df = df.map(limpiar_celda)
            
            # Agregamos columna de origen
            df['Origen_Archivo'] = os.path.basename(archivo)
            
            lista_df.append(df)
            logging.info("  -> %d filas procesadas", len(df))

        except Exception as e:
            logging.error("Error procesando %s: %s", os.path.basename(archivo), str(e))

    # 3. Consolidar todo
    if lista_df:
        logging.info("Consolidando archivos y preparando para guardar...")
        final_df = pd.concat(lista_df, ignore_index=True)
        
        # Eliminamos filas que sean iguales al encabezado (si quedaron restos)
        final_df = final_df[final_df.iloc[:, 0] != final_df.columns[0]]
        
        # Guardamos en Excel
        try:
            final_df.to_excel(RUTA_SALIDA, index=False, engine='openpyxl')
            logging.info("Archivo guardado exitosamente en: %s", RUTA_SALIDA)
            logging.info("Total de registros: %d", len(final_df))
            return True
        except Exception as e:
            logging.error("Error guardando archivo: %s", str(e))
            return False
    else:
        logging.warning("No se procesó ningún archivo o la carpeta está vacía.")
        return False


def main():
    """Punto de entrada principal"""
    procesar_engaged_eficiente()


if __name__ == "__main__":
    main() 