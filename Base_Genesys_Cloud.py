"""
Módulo de consolidación de bases de datos Genesys Cloud.

Funcionalidades principales:
1. Busca archivos CSV en múltiples carpetas (Cargue Actual, Histórico, Cloud Bases)
2. Detecta automáticamente separadores (coma o punto y coma)
3. Limpia caracteres especiales y espacios en columnas
4. Extrae y formatea fechas desde vCampaignEffectiveDate (formato YYYYMMDD)
5. Limpia números de teléfono (últimos 9 dígitos)
6. Consolida todos los archivos en un solo Excel

La configuración de rutas se carga desde %APPDATA%/RPA_Migracion/rutas_config.json
"""

import pandas as pd
import glob
import os
import json
import sys
from datetime import datetime, timedelta


# =============================================================================
# FUNCION PARA CARGAR RUTAS DESDE JSON
# =============================================================================

def obtener_ruta_config():
    """Obtiene la ruta donde se guarda la configuración en AppData/Roaming"""
    app_data = os.getenv('APPDATA')
    config_dir = os.path.join(app_data, 'RPA_Migracion')
    return os.path.join(config_dir, 'rutas_config.json')


def cargar_rutas_modulo():
    """Carga las rutas del módulo Base_Genesys_Cloud desde el JSON"""
    ruta_config = obtener_ruta_config()
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'Base_Genesys_Cloud' in config:
                return config['Base_Genesys_Cloud']
        except:
            pass
    # Si no existe, usar rutas por defecto
    return {
        'ruta_base': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\09. Bases Genesys\01. Contact_List',
        'ruta_salida': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Cloud.xlsx',
        'ruta_bases_cloud': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Cloud Bases'
    }


# Cargar rutas desde JSON
_RUTAS = cargar_rutas_modulo()

# Asignar variables globales
ruta_base = _RUTAS['ruta_base']
ruta_salida = _RUTAS['ruta_salida']
ruta_bases_cloud = _RUTAS['ruta_bases_cloud']


# =============================================================================
# FUNCIONES DE FECHAS DINÁMICAS (MES ACTUAL Y MES PASADO)
# =============================================================================

hoy = datetime.now()
mes_pasado_fecha = hoy.replace(day=1) - timedelta(days=6)

meses_espanol = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# --- MES ACTUAL (Histórico) ---
anio_actual = hoy.strftime('%Y')
num_mes_actual = hoy.strftime('%m')
nombre_mes_actual = meses_espanol[hoy.month]
carpeta_mes_actual = f"{num_mes_actual}. {nombre_mes_actual}"

# --- MES PASADO (Histórico) ---
anio_pasado = mes_pasado_fecha.strftime('%Y')
num_mes_pasado = mes_pasado_fecha.strftime('%m')
nombre_mes_pasado = meses_espanol[mes_pasado_fecha.month]
carpeta_mes_pasado = f"{num_mes_pasado}. {nombre_mes_pasado}"


# =============================================================================
# CONSTRUCCIÓN DE RUTAS DINÁMICAS
# =============================================================================

# Ruta de Cargue Actual
ruta_cargue_actual = os.path.join(ruta_base, 'Cargue Actual')

# Rutas de Histórico (mes actual y mes pasado)
ruta_historico_mes_actual = os.path.join(ruta_base, 'Historico', anio_actual, carpeta_mes_actual)
ruta_historico_mes_pasado = os.path.join(ruta_base, 'Historico', anio_pasado, carpeta_mes_pasado)


# =============================================================================
# COLUMNAS REQUERIDAS
# =============================================================================

columnas_expandidas = [
    'inin-outbound-id',
    'vCampaignEffectiveDate',
    'RUT_PERSONA',
    'FONO_CONTACTO',
    'Fono1',
    'Segment_of_Origin'
]


# =============================================================================
# PROCESO PRINCIPAL
# =============================================================================

def main():
    """Funcion principal que ejecuta todo el proceso de Base Genesys Cloud"""

    print("Buscando archivos en todas las rutas...")
    print(f" -> Cargue Actual: {ruta_cargue_actual}")
    print(f" -> Histórico Mes Actual: {ruta_historico_mes_actual}")
    print(f" -> Histórico Mes Pasado: {ruta_historico_mes_pasado}")
    print(f" -> Cloud Bases: {ruta_bases_cloud}")

    # Buscar archivos en cada carpeta
    archivos_actual = glob.glob(os.path.join(ruta_cargue_actual, "*.csv"))
    archivos_mes_actual = glob.glob(os.path.join(ruta_historico_mes_actual, "*.csv"))
    archivos_mes_pasado = glob.glob(os.path.join(ruta_historico_mes_pasado, "*.csv"))
    archivos_cloud = glob.glob(os.path.join(ruta_bases_cloud, "*.csv"))

    # Consolidar todos los archivos
    archivos_csv = archivos_actual + archivos_mes_actual + archivos_mes_pasado + archivos_cloud

    if not archivos_csv:
        print("\nNo se encontraron archivos CSV en ninguna de las rutas.")
        return

    print(f"\nSe encontraron {len(archivos_csv)} archivos en total. Iniciando consolidación...")
    lista_tablas = []

    for archivo in archivos_csv:
        try:
            try:
                datos = pd.read_csv(
                    archivo, sep=',', encoding='utf-8-sig', dtype=str, on_bad_lines='skip')
                if len(datos.columns) == 1:
                    raise ValueError("Probable separador punto y coma")
            except Exception:
                datos = pd.read_csv(
                    archivo, sep=';', encoding='latin1', dtype=str, on_bad_lines='skip')

            datos.columns = datos.columns.str.replace('"', '').str.replace(
                'ï»¿', '').str.replace('\ufeff', '').str.replace('\xa0', ' ')
            datos.columns = datos.columns.str.replace(
                r'\s+', ' ', regex=True).str.strip()

            cols_presentes = [
                col for col in columnas_expandidas if col in datos.columns]

            if not cols_presentes:
                print(
                    f"  -> Advertencia: Sin columnas requeridas en {os.path.basename(archivo)}")
                continue

            datos = datos[cols_presentes].copy()
            datos = datos.apply(lambda x: x.str.replace('\xa0', ' ').str.replace(
                r'\s+', ' ', regex=True).str.strip() if x.dtype == "object" else x)

            if 'vCampaignEffectiveDate' in datos.columns:
                fecha_temporal = pd.to_datetime(
                    datos['vCampaignEffectiveDate'], format='%Y%m%d', errors='coerce')
                datos['Fecha_Base'] = fecha_temporal.dt.strftime('%d/%m/%Y')
                datos['Origen_Archivo'] = os.path.basename(archivo)

            for col_fono in ['FONO_CONTACTO', 'Fono1']:
                if col_fono in datos.columns:
                    datos[col_fono] = datos[col_fono].apply(lambda x: str(
                        x).strip()[-9:] if pd.notna(x) and str(x).strip() != "" else None)

            lista_tablas.append(datos)
            print(f"Cargado: {os.path.basename(archivo)}")

        except Exception as e:
            print(f"Error en {os.path.basename(archivo)}: {e}")

    if lista_tablas:
        df_final = pd.concat(lista_tablas, ignore_index=True)

        print("Limpiando caracteres especiales...")
        diccionario_caracteres = {
            '\xc3\xa1': 'á', '\xc3\xa9': 'é', '\xc3\xad': 'í', '\xc3\xb3': 'ó', '\xc3\xba': 'ú',
            '\xc3\xb1': 'ñ', '\xc3\x91': 'Ñ', '\xc2\xb0': '°', '\xc2\x94': ''
        }

        for col in df_final.select_dtypes(include=['object', 'string']).columns:
            for mal, bien in diccionario_caracteres.items():
                df_final[col] = df_final[col].str.replace(
                    mal, bien, regex=False)

        columnas_finales = ['Fecha_Base', 'RUT_PERSONA',
                            'inin-outbound-id', 'FONO_CONTACTO', 'Fono1', 'Segment_of_Origin']
        cols_definitivas = [
            col for col in columnas_finales if col in df_final.columns]
        df_final = df_final[cols_definitivas]
        print("Exportando archivo a Excel, esto puede tomar unos segundos...")
        df_final.to_excel(ruta_salida, index=False, engine='openpyxl')

        print(f"\n--- EXITO: Archivo guardado con {len(df_final)} filas ---")
        print(f"Ruta: {ruta_salida}")
    else:
        print("\nError: No se procesó ninguna información.")


if __name__ == "__main__":
    main()
