import os
import sys
import logging
import warnings
import io
import glob
import pandas as pd
import requests



warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('automatizacion_engaged.log', encoding='utf-8')
    ]
)

SPREADSHEET_ID = "1R2BJO1lL1e3CZ5s2_5QT-U8vpeZBRQmRwkJUGu74HEQ"
GID = "1826436126"

OUTPUT_FILENAME = r"C:\\Users\\User\\Grupo de Servicios Integrales Chile S.A\\Mildred Casas - VTR Operaciones\\02.Migracion\\10.Corte Migracion\\Formulario Engaged.xlsx"
RUTA_DOTACION = r"C:\\Users\\User\\Grupo de Servicios Integrales Chile S.A\\Mildred Casas - VTR Operaciones\\02.Migracion\\10.Corte Migracion\\Dotacion VTR Operaciones.xlsx"
RUTA_LLAMadas = r"C:\\Users\\User\\Grupo de Servicios Integrales Chile S.A\\Mildred Casas - VTR Operaciones\\02.Migracion\\10.Corte Migracion\\Llamada x agente.csv"
RUTA_CUARTILES = r"C:\\Users\\User\\Grupo de Servicios Integrales Chile S.A\\Mildred Casas - VTR Operaciones\\02.Migracion\\10.Corte Migracion\\Cuartiles.xlsx"
RUTA_MALLA_TURNOS = r"C:\\Users\\User\\Grupo de Servicios Integrales Chile S.A\\Mildred Casas - VTR Operaciones\\02.Migracion\\10.Corte Migracion\\Malla de turnos diaria.xlsx"
RUTA_CAMPAIGN = r"C:\\Users\\User\\Grupo de Servicios Integrales Chile S.A\\Mildred Casas - VTR Operaciones\\02.Migracion\\10.Corte Migracion\\Campaign Activity.csv"
RUTA_BASES_RSL = r"C:\\Users\\User\\Grupo de Servicios Integrales Chile S.A\\Mildred Casas - VTR Operaciones\\02.Migracion\\10.Corte Migracion\\Genesys Engaged Bases"


def limpiar_dni(dni_series):
    s = pd.to_numeric(dni_series, errors='coerce').astype('Int64').astype(str)
    return s.replace('<NA>', '')

def cargar_fuentes_externas():
    df_dotacion = pd.DataFrame()
    df_llamadas = pd.DataFrame()
    df_cuartiles = pd.DataFrame()
    df_malla_turnos = pd.DataFrame()

    try:
        if os.path.exists(RUTA_DOTACION):
            try:
                df_dotacion = pd.read_excel(RUTA_DOTACION, sheet_name='DOTACION', dtype=str)
                df_dotacion.columns = df_dotacion.columns.str.replace(r'\xa0', ' ', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()
                if 'Genesys Engaged' in df_dotacion.columns and 'NOMBRE COMPLETO' in df_dotacion.columns:
                    df_dotacion['Genesys Engaged'] = df_dotacion['Genesys Engaged'].astype(str).str.strip()
                    df_dotacion['NOMBRE COMPLETO'] = df_dotacion['NOMBRE COMPLETO'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip().str.title()
                    if 'DNI' in df_dotacion.columns:
                        df_dotacion['DNI'] = limpiar_dni(df_dotacion['DNI'])
                    cols = ['Genesys Engaged', 'NOMBRE COMPLETO', 'SUPERVISOR', 'FECHA INGRESO', 'DNI','SEDE']
                    df_dotacion = df_dotacion[[c for c in cols if c in df_dotacion.columns]].dropna(subset=['Genesys Engaged']).drop_duplicates(subset=['Genesys Engaged'])
            except Exception as e:
                logging.error(f"Error cargando Dotación: {e}")

        if os.path.exists(RUTA_LLAMadas):
            try:
                df_llamadas = pd.read_csv(RUTA_LLAMadas, sep=',', encoding='utf-8', on_bad_lines='skip')
                df_llamadas.columns = df_llamadas.columns.str.strip()
                if 'Name' in df_llamadas.columns:
                    nombres = df_llamadas['Name'].astype(str).str.split(',', n=1, expand=True)
                    df_llamadas['Nombre'] = nombres[1].str.strip() + " " + nombres[0].str.strip() if nombres.shape[1] == 2 else nombres[0].str.strip()
                    reemplazos = {
                        "Andrea Ruiz Pena": "Andrea Carolina Ruiz Peña",
                        "Brian Alejandro Cantor Umana": "Brian Alejandro Cantor Umaña",
                        "Monica Catano Solarte": "Monica Cataño Solarte",
                        "Luis Angel Parada Nunez": "Luis Angel Parada Nuñez",
                        "Marlon jose Mora Moncada": "Marlon Jose Mora Moncada",
                        "Yuliana Ximena Ordonez Cifuentes": "Yuliana Ximena Ordoñez Cifuentes",
                        "Yulieth Mayerly Tunubala": "Yulieth Mayerly Tunubala Pillimue",
                        "Heidy Valentina Vanegas Castaneda": "Heidy Valentina Vanegas Castañeda",
                        "Maria Paula Gaitan Gaitan": "Maria Paula Gaitan Viajan",
                        "Angela Kargy Quintero Ollares": "Angela Kargy Quintero Ollarves",
                        "Estefany Ali Ali": "Estefany Ali",
                        "Leonardo Hernandez  Aguilar": "Leonardo Hernandez Aguilar", # Ojo: tenía un doble espacio
                        "Jeison Andres Morales Piratoba": "Andres Jeison Morales Piratoba",
                        "Jeimmy Paola Rojas Zarate": "Jeimmy Paola Rojas Zarate",
                        "Jorge Camilo Casallas Casallas": "Jorge Camilo Casallas",
                        "Andres Felipe Zizou Barrios": "Andres Felipe Zizou Barrios Bermudez",
                        "Sharon Johana Suarez Montanez": "Sharon Johana Suarez Montañez",
                        "Edna Rocio Riano Latorre": "Edna Rocio Riaño Latorre",
                        "Daniela Fernanda Randazzo Briceno": "Daniela Fernanda Randazzo Briceno",
                        "Daniel Felipe Ramos Umana": "Daniel Felipe Ramos Umaña"
}
                    df_llamadas['Nombre'] = df_llamadas['Nombre'].replace(reemplazos)
            except Exception as e:
                logging.error(f"Error cargando Llamadas: {e}")

        if os.path.exists(RUTA_CUARTILES):
            try:
                df_cuartiles = pd.read_excel(RUTA_CUARTILES, dtype=str)
                df_cuartiles.columns = df_cuartiles.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
                if 'DNI' in df_cuartiles.columns and 'Cuartil' in df_cuartiles.columns:
                    df_cuartiles['DNI'] = limpiar_dni(df_cuartiles['DNI'])
                    df_cuartiles = df_cuartiles[['DNI', 'Cuartil']].dropna(subset=['DNI']).drop_duplicates(subset=['DNI'])
            except Exception as e:
                logging.error(f"Error cargando Cuartiles: {e}")

        if os.path.exists(RUTA_MALLA_TURNOS):
            try:
                df_malla_turnos = pd.read_excel(RUTA_MALLA_TURNOS, dtype=str)
                df_malla_turnos.columns = df_malla_turnos.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
                if 'DNI' in df_malla_turnos.columns and 'Turno' in df_malla_turnos.columns:
                    df_malla_turnos['DNI'] = limpiar_dni(df_malla_turnos['DNI'])
                    df_malla_turnos = df_malla_turnos[['DNI', 'Turno']].dropna(subset=['DNI']).drop_duplicates(subset=['DNI'])
            except Exception as e:
                logging.error(f"Error cargando Malla Turnos: {e}")

        return df_dotacion, df_llamadas, df_cuartiles, df_malla_turnos
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def cargar_y_transformar_campaign():
    """Procesa el archivo Campaign Activity CSV según reglas de Power Query"""
    df_campaign = pd.DataFrame()
    if os.path.exists(RUTA_CAMPAIGN):
        try:
            df_campaign = pd.read_csv(RUTA_CAMPAIGN, sep=None, engine='python', encoding='utf-8', on_bad_lines='skip')
            df_campaign.columns = df_campaign.columns.str.strip()

            if 'Name' in df_campaign.columns:
                df_campaign = df_campaign[df_campaign['Name'].isin(["CV_IBRCOL_CL_OUT_CLR_CONT_01", "CV_IBRCOL_CL_OUT_CLR_CONT_02"])]
                
                renombres_1 = {
                    "Answers": "Contacto (Answer)",
                    "Records Completed": "Gestiones Completas"
                }
                df_campaign.rename(columns=renombres_1, inplace=True)
                
                orden_deseado = [
                    "Name", "Hit Ratio", "Estimated Time", "Gestiones Completas", "Contacto (Answer)", 
                    "Dialed Abandoned", "Dialed Answering Machine", "Attempt Busies", "Attempts Cancelled", 
                    "Attempts made", "DoNotCall Results", "Dropped Results", "Fax Modem Results", 
                    "No Answer Result", "Wrong Party Result", "SIT Detected"
                ]
                cols_existentes = [col for col in orden_deseado if col in df_campaign.columns]
                df_campaign = df_campaign[cols_existentes]
                
                renombres_2 = {
                    "No Answer Result": "No Contacto (No Answer Result)"
                }
                df_campaign.rename(columns=renombres_2, inplace=True)

        except Exception as e:
            logging.error(f"Error procesando Campaign Activity: {e}")
    else:
        logging.warning(f"No se encontró el archivo Campaign Activity en: {RUTA_CAMPAIGN}")
        
    return df_campaign


def aplicar_transformaciones_y_cruces(df_origen, df_dotacion, df_llamadas, df_cuartiles, df_malla_turnos):
    df = df_origen.copy()
    df.columns = df.columns.str.strip()

    if 'TIPO CAMPAÑA' in df.columns:
        # 1. Limpiamos la columna: a texto, sin espacios en los bordes y todo en mayúscula
        df['TIPO CAMPAÑA'] = df['TIPO CAMPAÑA'].astype(str).str.strip().str.upper()
        
        # 2. Aplicamos el filtro
        campañas_a_excluir = ["PILOTO CLOUD", "MIGRACION NORMAL CLOUD", "HOME PASS", "APAGADO NODOS", "BASE CLIENTES COLABORADORES", "BASE MANUAL CLIENTE DESISTE", "PILOTO CTO CLOUD"]
        df = df[~df['TIPO CAMPAÑA'].isin(campañas_a_excluir)]
        logging.info("Filtro aplicado de forma segura: Se excluyeron las campañas")
    else:
        logging.warning("No se encontró la columna 'TIPO DE CAMPAÑA' en el formulario original.")

    if 'Marca temporal' in df.columns:
        dt_temporal = pd.to_datetime(df['Marca temporal'], errors='coerce')
        df['Marca temporal'] = dt_temporal.dt.strftime('%d/%m/%Y %H:%M')
        df['Fecha'] = dt_temporal.dt.strftime('%d/%m/%Y')
        df['Hora'] = dt_temporal.dt.strftime('%H:%M')
    
    if 'TIPIFICACION' in df.columns:
        condiciones = ["ACEPTA AGENDA - MIGRACION - SOP", "ACEPTA REINGRESO MIGRACION - SOP"]
        df['Migración Engaged'] = df['TIPIFICACION'].isin(condiciones).astype(int)
        df['No Acepta Engaged'] = (df['TIPIFICACION'] == "NO ACEPTA").astype(int)

    df['Gestion Engaged'] = 1
    df['Base Engaged'] = "Genesys Engaged"
    if 'CONTACTO' in df.columns:
        df['Contacto Engaged'] = (df['CONTACTO'] == "SI").astype(int)

    col_usu = 'Usuarios' if 'Usuarios' in df.columns else 'USUARIO'
    if col_usu in df.columns and not df_dotacion.empty and 'Genesys Engaged' in df_dotacion.columns:
        df['Temp_Key'] = df[col_usu].astype(str).str.strip()
        df = pd.merge(df, df_dotacion, how='left', left_on='Temp_Key', right_on='Genesys Engaged')
        df.drop(columns=['Temp_Key'], inplace=True)
        if 'FECHA INGRESO' in df.columns:
            fecha_dt = pd.to_datetime(df['FECHA INGRESO'], errors='coerce')
            dias = (pd.Timestamp.today().normalize() - fecha_dt).dt.days
            def calc_ant(d):
                if pd.isna(d): return "No aplica"
                if d > 36: return "Vigente"
                elif d > 6: return "Prematuro"
                return "OJT"
            df['Antiguedad'] = dias.apply(calc_ant)
            df['FECHA INGRESO'] = fecha_dt.dt.strftime('%d/%m/%Y')
    else:
        for c in ['Genesys Engaged', 'SUPERVISOR', 'NOMBRE COMPLETO', 'FECHA INGRESO', 'DNI','SEDE']: df[c] = "Error"

    if 'NOMBRE COMPLETO' in df.columns and not df_llamadas.empty:
        df = pd.merge(df, df_llamadas, left_on='NOMBRE COMPLETO', right_on='Nombre', how='left')
        if 'Nombre' in df.columns: df.drop(columns=['Nombre'], inplace=True)

    if 'DNI' in df.columns and not df_cuartiles.empty:
        df = pd.merge(df, df_cuartiles, how='left', on='DNI')
    if df_malla_turnos.empty:
        logging.warning("No se cruzaron los Turnos: El archivo 'Malla de Turnos' está vacío o no se cargó.")
    elif 'DNI' not in df.columns:
        logging.warning("No se cruzaron los Turnos: El archivo principal no tiene la columna 'DNI' (Revisa el archivo de Dotación).")
    elif 'Turno' not in df_malla_turnos.columns:
        logging.warning("No se cruzaron los Turnos: La malla cargó, pero no existe la columna llamada exactamente 'Turno'.")
    else:
        df = pd.merge(df, df_malla_turnos, how='left', on='DNI')
        logging.info("✅ Cruce de Malla de Turnos realizado con éxito.")

    columnas_a_eliminar = [
        'FECHA DE LA BASE', 'FECHA', 'Unnamed: 18', 'Genesys Engaged', 
        'OBSERVACIÓN', 'NUMERO DE PEDIDO', 'NUMERO TICKET', 'FECHA INGRESO', 
        'Login Time', 'Ready Time', 'Out', 'Not Ready Time', 'ACW Time', 
        'Break Time', 'Lunch Time', 'Offline Time', 'Ringing Time', 
        'Dialing Time', 'Handle Time', 'In Time', 'Out Time', 'Internal Time',
        'Calls Dropped', 'Internal', 'Held', 'Transfers Made', 'Consult Made',
        'AHT', 'Avg ACW Time', 'Avg Hold Time', 'Avg In Time', 'Avg Out Time', 
        'Avg Ring Time', 'Name','Hold Time','Consult Time','Base Engaged'
    ]

    for c in columnas_a_eliminar:
        if c in df.columns: 
            df.drop(columns=[c], inplace=True)

    return df


def obtener_conteo_rsl():
    """Lee los archivos .rsl en la ruta y suma la cantidad total de filas o registros."""
    archivos = glob.glob(os.path.join(RUTA_BASES_RSL, "*.rsl"))
    total_registros = 0
    
    if not archivos:
        logging.warning("No se encontraron archivos .rsl para el conteo.")
        return total_registros
        
    for archivo in archivos:
        try:
            # Leemos el archivo usando Pandas para contar las filas reales de datos
            df_temp = pd.read_csv(archivo, sep='|', encoding='latin-1', dtype=str, on_bad_lines='skip')
            total_registros += len(df_temp)
            logging.info(f"Conteo: {os.path.basename(archivo)} tiene {len(df_temp)} registros.")
        except Exception as e:
            logging.error(f"Error al contar filas en {os.path.basename(archivo)}: {e}")
            
    return total_registros


def procesar_automatizacion():
    export_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx&gid={GID}"
    try:
        response = requests.get(export_url, timeout=30)
        if response.status_code == 200:
            df_origen = pd.read_excel(io.BytesIO(response.content), engine='openpyxl')
            
            df_dotacion, df_llamadas, df_cuartiles, df_malla_turnos = cargar_fuentes_externas()
            df_final = aplicar_transformaciones_y_cruces(df_origen, df_dotacion, df_llamadas, df_cuartiles, df_malla_turnos)
            df_campaign = cargar_y_transformar_campaign()
            total_registros_rsl = obtener_conteo_rsl()
            df_conteo = pd.DataFrame({
                "Genesys Engaged": [total_registros_rsl]
            })
            
            carpeta_destino = os.path.dirname(OUTPUT_FILENAME)
            if not os.path.exists(carpeta_destino):
                os.makedirs(carpeta_destino)


            with pd.ExcelWriter(OUTPUT_FILENAME, engine='openpyxl') as writer:
                df_final.to_excel(writer, sheet_name='Formulario Engaged', index=False)
                

                if not df_campaign.empty:
                    df_campaign.to_excel(writer, sheet_name='Campaign Activity', index=False)
                    

                df_conteo.to_excel(writer, sheet_name='Conteo Engaged', index=False)
                    
            logging.info(f"¡Reporte guardado exitosamente en: {OUTPUT_FILENAME} con sus hojas correspondientes!")
            return True
        else:
            logging.error(f"Error de acceso HTTP: {response.status_code}")
    except Exception as e:
        logging.error(f"Error crítico: {str(e)}")

if __name__ == "__main__":
    procesar_automatizacion()