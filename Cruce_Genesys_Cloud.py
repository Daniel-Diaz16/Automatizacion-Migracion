import pandas as pd
import glob
import os
import warnings
import json
import sys
from datetime import datetime, timedelta

# Silenciar advertencias de formato
warnings.simplefilter("ignore", UserWarning)


# =============================================================================
# FUNCION PARA CARGAR RUTAS DESDE JSON
# =============================================================================

def obtener_ruta_config():
    """Obtiene la ruta donde se guarda la configuración en AppData/Roaming"""
    app_data = os.getenv('APPDATA')
    config_dir = os.path.join(app_data, 'RPA_Migracion')
    return os.path.join(config_dir, 'rutas_config.json')


def cargar_rutas_modulo():
    """Carga las rutas del módulo Cruce_Genesys_Cloud desde el JSON"""
    ruta_config = obtener_ruta_config()
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'Cruce_Genesys_Cloud' in config:
                return config['Cruce_Genesys_Cloud']
        except:
            pass
    # Si no existe, usar rutas por defecto
    return {
        'ruta_carpeta': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Cloud',
        'ruta_salida': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Consolidada_Agentes.csv',
        'ruta_base_genesys': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Cloud.xlsx',
        'ruta_dotacion': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Dotacion VTR Operaciones.xlsx',
        'ruta_cuartiles': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Cuartiles.xlsx',
        'ruta_malla_de_turnos': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Malla de turnos diaria.xlsx',
        'ruta_genesys_bases': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Cloud Bases',
        'ruta_acomulado': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Acomulado.csv'
    }


# Cargar rutas desde JSON
_RUTAS = cargar_rutas_modulo()

# Asignar variables globales
ruta_carpeta = _RUTAS['ruta_carpeta']
ruta_salida = _RUTAS['ruta_salida']
ruta_base_genesys = _RUTAS['ruta_base_genesys']
ruta_dotacion = _RUTAS['ruta_dotacion']
ruta_cuartiles = _RUTAS['ruta_cuartiles']
ruta_malla_de_turnos = _RUTAS['ruta_malla_de_turnos']
ruta_genesys_bases = _RUTAS['ruta_genesys_bases']
ruta_acomulado = _RUTAS['ruta_acomulado']


# =============================================================================
# FUNCIONES DE LIMPIEZA
# =============================================================================

def extraer_tipificacion(conclusion):
    if pd.isna(conclusion) or str(conclusion).strip() == "":
        return None
    partes = [parte.strip() for parte in str(conclusion).split(";")]
    if len(partes) >= 2:
        return partes[1]
    return conclusion


def crear_agente_inicial(usuario):
    if pd.isna(usuario) or str(usuario).strip() == "":
        return "Discador"

    usuario_str = str(usuario)
    sin_punto_y_coma = usuario_str.split(';')[0]

    if "_" in sin_punto_y_coma:
        partes = sin_punto_y_coma.split('_')
        nombre_extraido = partes[2] if len(partes) >= 3 else sin_punto_y_coma
    else:
        nombre_extraido = sin_punto_y_coma

    return nombre_extraido.strip().title()


# =============================================================================
# DICCIONARIOS
# =============================================================================

reemplazos_nombres = {
    "Diana Carolina Llorente  Almanza": "Diana Carolina Llorente Almanza",
    "Angie Nicole Abril Marino": "Angie Nicole Abril Mariño",
    "ANDRÉS FELIPE ZIZOU BARRIOS BERMÚDEZ": "Andres Felipe Zizou Barrios Bermudez",
    "Andrés Felipe Zizou Barrios Bermúdez": "Andres Felipe Zizou Barrios Bermudez",
    "Andrã%81S Felipe Zizou Barrios Bermã%9ADez": "Andres Felipe Zizou Barrios Bermudez",
    "ANDRÃ‰S FELIPE ZIZOU BARRIOS BERMÃšDEZ": "Andres Felipe Zizou Barrios Bermudez",
    "CARLOS MANUEL CAMARGO ANAYA": "Carlos Manuel Camargo Anaya",
    "Jostin  Almario Rios": "Jostin Almario Rios",
    "Jostin#(00A0) Almario Rios": "Jostin Almario Rios",
    "JOSTIN  ALMARIO RIOS": "Jostin Almario Rios",
    "Jostin Â Almario Rios" : "Jostin Almario Rios",
    "Jorge Camilo Casallas Casallas": "Jorge Camilo Casallas",
    "JORGE CAMILO CASALLAS CASALLAS": "Jorge Camilo Casallas",
    "Jorge Camilo Casallas ": "Jorge Camilo Casallas",
    "Maria Alejandra Valest Toro": "Maira Alejandra Valest Toro",
    "Leidy Viviana Molano Martínez": "Leidy Viviana Molano Martinez",
    "Leidy Viviana Molano Martã%8DNez": "Leidy Viviana Molano Martinez",
    "Quintero Ollarves Angela Kargy": "Angela Kargy Quintero Ollarves",
    "QUINTERO OLLARVES ANGELA KARGY": "Angela Kargy Quintero Ollarves",
    "Nicolas  Pineda Guerra": "Nicolas Pineda Guerra",
    "Sergio Ivan Osorio Nungo": "Sergio Ivan Osorio Ñungo",
    "Nicolas Gomez  Betancourt": "Nicolas Gomez Betancourt",
    "Maria Fernanda   Olaya Cortes": "Maria Fernanda Olaya Cortes",
    "Estefany  Ali Ali": "Estefany Ali",
    "Estefany Ali Ali": "Estefany Ali",
    "Edna Rocio Riano Latorre": "Edna Rocio Riaño Latorre",
    "Leonardo  Hernandez Aguilar": "Leonardo Hernandez Aguilar",
    "Sharon Johana Suarez Montanez": "Sharon Johana Suarez Montañez",
    "Sharon Johana Suarez Montaã%91Ez": "Sharon Johana Suarez Montañez",
    "Luis Angel Parada Nunez": "Luis Angel Parada Nuñez",
    "Luis Angel Parada Nuã%91Ez": "Luis Angel Parada Nuñez",
    "Veronica Isabel Herazo Betancourth": "Veronica Isabel Herazo Betancourth",
    "Jeimmy Paola Rojas Zarate": "Jeimmy Paola Rojas Zarate",
    "Estefany Ali": "Estefany Ali",
    "Jorge Camilo Casallas": "Jorge Camilo Casallas",
    "Maria Paula Gaitan Gaitan": "Maria Paula Gaitan Viajan",
    "Maria Paula Gaitã%81N Gaitã%81N": "Maria Paula Gaitan Viajan",
    "Yulian Daniela Malaver Rodríguez": "Yulian Daniela Malaver Rodriguez",
    "Maria Paula Gaitán Gaitán": "Maria Paula Gaitan Viajan",
    "Andrã%89S Felipe Zizou Barrios Bermã%9ADez": "Andres Felipe Zizou Barrios Bermudez",
    "Andres Felipe Zizou Barrios Bermudez": "Andres Felipe Zizou Barrios Bermudez",
    "Angelica Chiquinquira Valbuena Cordero": "Angelica Chiquinquira Valbuena Cordero",
    "Jostinâ Almario Rios": "Jostin Almario Rios",
    "Jostin  Almario Rios": "Jostin Almario Rios",
    "Yulian Daniela Malaver Rodrã%8DGuez": "Yulian Daniela Malaver Rodriguez",
    "Yulian Daniela Malaver Rodriguez": "Yulian Daniela Malaver Rodriguez",
    "Sandy Paola Penagos Sanabria": "Sandy Paola Penagos Sanabria",
    "Angie Katherine Bermudez Villagran": "Angie Katherine Bermudez Villagran",
    "Leonardo Hernandez Aguilar": "Leonardo Hernandez Aguilar",
    "Leonardo  Hernandez Aguilar": "Leonardo Hernandez Aguilar",
    "Brian Alejandro Cantor Umaã%91A": "Brian Alejandro Cantor Umaña",
    "Yuliana Ximena Ordoã%91Ez Cifuentes": "Yuliana Ximena Ordoñez Cifuentes",
    "Andrea Carolina Ruiz Peã%91A": "Andrea Carolina Ruiz Peña"
}

correccion_columnas = {
    "ExportaciÃ³n completa finalizada": "Exportación completa finalizada",
    "DuraciÃ³n": "Duración",
    "DirecciÃ³n": "Dirección",
    "ConclusiÃ³n": "Conclusión",
    "Tipo de desconexiÃ³n": "Tipo de desconexión",
    "IdentificaciÃ³n de contacto": "Identificación de contacto"
}

columnas_expandidas = [
    "Usuarios", "Fecha", "Dirección", "DNIS", "Cola", "Conclusión", "Identificación de contacto"
]


# =============================================================================
# PROCESO PRINCIPAL
# =============================================================================

def main():
    """Funcion principal que ejecuta todo el proceso de cruce Genesys Cloud"""

    # =========================================================================
    # PASO 1: CARGAR Y UNIR ARCHIVOS
    # =========================================================================
    archivos_csv = glob.glob(os.path.join(ruta_carpeta, "*.csv"))

    if not archivos_csv:
        print("No se encontraron archivos CSV en la ruta especificada.")
        return
    else:
        print(f"Se encontraron {len(archivos_csv)} archivos. Iniciando unión...")
        lista_tablas = []

        for archivo in archivos_csv:
            try:
                datos = pd.read_csv(
                    archivo, sep=';', encoding='utf-8-sig', dtype=str)
                datos.columns = datos.columns.str.strip()
                datos = datos.rename(columns=correccion_columnas)
                cols_presentes = [
                    col for col in columnas_expandidas if col in datos.columns]
                datos = datos[cols_presentes]
                datos['Origen_Archivo'] = os.path.basename(archivo)
                lista_tablas.append(datos)
                print(f"Cargado: {os.path.basename(archivo)}")
            except Exception:
                try:
                    datos = pd.read_csv(
                        archivo, sep=';', encoding='latin1', dtype=str)
                    datos.columns = datos.columns.str.strip()
                    datos = datos.rename(columns=correccion_columnas)
                    cols_presentes = [
                        col for col in columnas_expandidas if col in datos.columns]
                    datos = datos[cols_presentes]
                    datos['Origen_Archivo'] = os.path.basename(archivo)
                    lista_tablas.append(datos)
                    print(f"Cargado (con latin1): {os.path.basename(archivo)}")
                except Exception as e2:
                    print(f"Error crítico al leer {archivo}: {e2}")

    if not lista_tablas:
        print("No se pudo cargar ningun archivo.")
        return

    base_final = pd.concat(lista_tablas, ignore_index=True)

    # =========================================================================
    # PASO 2: LIMPIEZA MAESTRA DE USUARIOS
    # =========================================================================
    if "Usuarios" in base_final.columns:
        base_final['Usuarios'] = base_final['Usuarios'].apply(crear_agente_inicial)
        base_final["Usuarios"] = base_final["Usuarios"].str.replace(
            r'\s+', ' ', regex=True).str.strip().str.title()
        base_final["Usuarios"] = base_final["Usuarios"].replace(reemplazos_nombres)

    if "Fecha" in base_final.columns:
        if base_final.empty:
            base_final['Fecha.'] = ""
            base_final['Hora'] = "00:00"
        else:
            base_final['Fecha'] = base_final['Fecha'].astype(str)
            partes = base_final['Fecha'].str.split(' ', n=1, expand=True)

            if 0 in partes.columns:
                base_final['Fecha.'] = partes[0]
            else:
                base_final['Fecha.'] = base_final['Fecha']

            if 1 in partes.columns:
                base_final['Hora'] = partes[1].fillna("00:00").str.slice(0, 5)
            else:
                base_final['Hora'] = "00:00"

    if "DNIS" in base_final.columns:
        base_final['Fono'] = base_final['DNIS'].apply(
            lambda x: str(x)[-9:] if pd.notna(x) and str(x).strip() != "" else None
        )

    if "Conclusión" in base_final.columns:
        base_final['Conclusión'] = base_final['Conclusión'].str.replace(
            "ININ-OUTBOUND-CAMPAIGN-FORCED-OFF; ", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace(
            "ININ-OUTBOUND-TRANSFERRED-TO-QUEUE; ", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace(
            "ININ-OUTBOUND-", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace(
            "ININ-", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace(
            " - SOP", "", regex=False)
        base_final['Tipificacion'] = base_final['Conclusión'].apply(
            extraer_tipificacion)

    # =========================================================================
    # PASO 3: CLASIFICACIONES
    # =========================================================================
    base_final['Gestión'] = 1
    base_final['Tipo de llamada'] = "Discador"

    if "Dirección" in base_final.columns and "Usuarios" in base_final.columns:
        mask_manual = (base_final['Usuarios'] != "Discador") & (
            base_final['Dirección'].isin(["Entrante", "Saliente"]))
        base_final.loc[mask_manual, 'Tipo de llamada'] = "Manual"

    if "Tipificacion" in base_final.columns:
        lista_no_aplica = ["MIGRACION YA GENERADA POR OTRA CAMPAÑA",
                           "CLIENTE INFACTIBLE", "SIN FACTIBILIDAD"]
        base_final['No aplica'] = base_final['Tipificacion'].isin(
            lista_no_aplica).astype(int)

        lista_migracion = ["ACEPTA REINGRESO MIGRACION",
                           "ACEPTA AGENDA - MIGRACION"]
        base_final['Migracion'] = base_final['Tipificacion'].isin(
            lista_migracion).astype(int)

        lista_es_contacto = [
            "ACEPTA AGENDA - MIGRACION", "ACEPTA REINGRESO MIGRACION", "CLIENTE INFACTIBLE",
            "NO ACEPTA MIGRACION", "NO ACEPTA - DARÁ DE BAJA EL SERVICIO", "CLIENTE MOLESTO",
            "MIGRACION YA GENERADA POR OTRA CAMPAÑA", "VOLVER A LLAMAR", "NO VOLVER A LLAMAR",
            "MENOR DE EDAD", "Error de ingreso", "WRAP-UP-TIMEOUT", "NUMERO EQUIVOCADO",
            "SIN FACTIBILIDAD", "CORTA LLAMADO", "CLIENTE FALLECIDO", "CLIENTE RECLAMO SUBTEL -SOP"
        ]
        base_final['Contacto'] = base_final['Tipificacion'].apply(
            lambda x: "Contacto" if pd.notna(x) and x in lista_es_contacto else "No Contacto"
        )
        base_final['Contacto.'] = (
            base_final['Contacto'] == "Contacto").astype(int)
        base_final['Errores'] = (
            base_final['Tipificacion'] == "Error de ingreso").astype(int)
        base_final['Sin tipificar'] = (
            base_final['Tipificacion'] == "WRAP-UP-TIMEOUT").astype(int)

    if "Cola" in base_final.columns:
        diccionario_colas = {
            "COLA_OPERACIONES_MIGRACION_IBR_COLOMBIA_Q001": "Genesys Cloud",
            "COLA_OPERACIONES_CONFIRMACION_IBR_COLOMBIA_Q001": "HomePass",
            "COLA_OPERACIONES_MIGRACION_IBR_COLOMBIA_Q002": "Santiago Centro",
            "COLA_OPERACIONES_MIGRACION_IBR_COLOMBIA_Q003": "Base Infactible"
        }
        base_final['Base Cloud'] = base_final['Cola'].map(
            diccionario_colas).fillna("-")

    # =========================================================================
    # PASO 4: CRUCES CON OTRAS BASES
    # =========================================================================
    print("Realizando cruce con base Cloud...")
    try:
        df_genesys = pd.read_excel(ruta_base_genesys, dtype=str)

        base_final['Identificación de contacto'] = base_final['Identificación de contacto'].astype(str).str.strip()
        df_genesys['inin-outbound-id'] = df_genesys['inin-outbound-id'].astype(str).str.strip()
        df_genesys['FONO_CONTACTO'] = df_genesys['FONO_CONTACTO'].astype(str).str.strip()
        df_genesys['Fono1'] = df_genesys['Fono1'].astype(str).str.strip()

        genesys_b1 = df_genesys[['inin-outbound-id', 'Segment_of_Origin']].dropna(
            subset=['inin-outbound-id']).drop_duplicates(subset=['inin-outbound-id'])
        base_final = pd.merge(base_final, genesys_b1, how='left',
                              left_on='Identificación de contacto', right_on='inin-outbound-id')
        base_final = base_final.rename(columns={'Segment_of_Origin': 'Bucket_1'})

        genesys_b2 = df_genesys[['FONO_CONTACTO', 'Segment_of_Origin']].dropna(
            subset=['FONO_CONTACTO']).drop_duplicates(subset=['FONO_CONTACTO'])
        base_final = pd.merge(
            base_final, genesys_b2, how='left', left_on='Fono', right_on='FONO_CONTACTO')
        base_final = base_final.rename(columns={'Segment_of_Origin': 'Bucket_2'})

        genesys_b3 = df_genesys[['Fono1', 'Segment_of_Origin']].dropna(
            subset=['Fono1']).drop_duplicates(subset=['Fono1'])
        base_final = pd.merge(base_final, genesys_b3,
                              how='left', left_on='Fono', right_on='Fono1')
        base_final = base_final.rename(columns={'Segment_of_Origin': 'Bucket_3'})
        base_final['Bucket'] = base_final['Bucket_1'].fillna(
            base_final['Bucket_2']).fillna(base_final['Bucket_3']).fillna("No Encontrado")

    except Exception as e:
        print(f"Advertencia: No se pudo realizar el cruce con Genesys. Error: {e}")
        base_final['Bucket'] = "Error de Cruce"

    # =========================================================================
    # PASO 5: CRUCE CON DOTACIÓN
    # =========================================================================
    print("Realizando Cruce con Base de Dotación...")
    try:
        df_dotacion = pd.read_excel(ruta_dotacion, sheet_name='DOTACION', dtype=str)
        df_dotacion.columns = df_dotacion.columns.str.replace('\xa0', ' ')
        df_dotacion.columns = df_dotacion.columns.str.replace(r'\s+', ' ', regex=True).str.strip()

        if 'NOMBRE COMPLETO' in df_dotacion.columns:
            df_dotacion['NOMBRE COMPLETO'] = df_dotacion['NOMBRE COMPLETO'].astype(
                str).str.replace(r'\s+', ' ', regex=True).str.strip().str.title()
            dotacion_limpia = df_dotacion[['NOMBRE COMPLETO', 'ANDES', 'SUPERVISOR', 'FECHA INGRESO', 'DNI']].dropna(
                subset=['NOMBRE COMPLETO']).drop_duplicates(subset=['NOMBRE COMPLETO'])
            base_final = pd.merge(
                base_final, dotacion_limpia, how='left',
                left_on='Usuarios', right_on='NOMBRE COMPLETO'
            )
        else:
            print("¡Atención! Aún no se encuentra la columna NOMBRE COMPLETO.")
    except Exception as e:
        print(f"Advertencia: No se pudo realizar el cruce con Dotación. Error: {e}")
        base_final['ANDES'] = "Error de Cruce"
        base_final['SUPERVISOR'] = "Error de Cruce"

    # =========================================================================
    # PASO 6: CÁLCULOS ADICIONALES (Antigüedad)
    # =========================================================================
    print("Calculando Antiguedad de los agentes...")
    try:
        if 'FECHA INGRESO' in base_final.columns:
            base_final['FECHA INGRESO'] = pd.to_datetime(base_final['FECHA INGRESO'], errors='coerce')
            fecha_hoy = pd.Timestamp.today().normalize()
            base_final['Dias_Antiguedad'] = (fecha_hoy - base_final['FECHA INGRESO']).dt.days

            def clasificar_antiguedad(dias):
                if pd.isna(dias):
                    return "No aplica"
                if dias > 36:
                    return "Vigente"
                elif dias > 6:
                    return "Prematuro"
                else:
                    return "OJT"

            base_final['Antiguedad'] = base_final['Dias_Antiguedad'].apply(clasificar_antiguedad)
    except Exception as e:
        print(f"Advertencia: Hubo un problema al calcular la antiguedad. Error {e}")

    # =========================================================================
    # PASO 7: CRUCES CUARTILES Y TURNOS
    # =========================================================================
    print("Trayendo Cuartiles...")
    try:
        df_cuartiles = pd.read_excel(ruta_cuartiles, dtype=str)
        df_cuartiles.columns = df_cuartiles.columns.str.replace(r'\s+', ' ', regex=True)
        if 'DNI' in base_final.columns and 'DNI' in df_cuartiles.columns:
            base_final['DNI'] = base_final['DNI'].astype(str).str.strip()
            df_cuartiles['DNI'] = df_cuartiles["DNI"].astype(str).str.strip()
            cuartiles_limpio = df_cuartiles[['DNI', 'Cuartil']].dropna(subset=['DNI']).drop_duplicates(subset=['DNI'])
            base_final = pd.merge(base_final, cuartiles_limpio, how='left', on='DNI')
        else:
            print("Advertencia: No se encontró la columna DNI.")
    except Exception as e:
        print(f"Advertencia: No se pudo realizar el cruce con Cuartiles. Error: {e}")
        base_final['Cuartil'] = "Error de Cruce"

    print("Extrayendo turno...")
    try:
        df_malla_de_turnos = pd.read_excel(ruta_malla_de_turnos, dtype=str)
        df_malla_de_turnos.columns = df_malla_de_turnos.columns.str.replace(r'\s+', ' ', regex=True)
        if 'DNI' in base_final.columns and 'DNI' in df_malla_de_turnos.columns:
            base_final['DNI'] = base_final['DNI'].astype(str).str.strip()
            df_malla_de_turnos['DNI'] = df_malla_de_turnos['DNI'].astype(str).str.strip()
            malla_de_turnos_limpio = df_malla_de_turnos[['DNI', 'Turno']].dropna(subset=['DNI']).drop_duplicates(subset=['DNI'])
            base_final = pd.merge(base_final, malla_de_turnos_limpio, how='left', on='DNI')
    except Exception as e:
        print(f"¡ATENCION: No se pudo encontrar los turnos de los agentes. Error: {e}")
        base_final['Turno'] = "Error de cruce"

    # =========================================================================
    # PASO 8: ELIMINACIÓN DE DUPLICADOS
    # =========================================================================
    print("Creando Llaves para eliminar duplicados...")
    try:
        base_final['KEY'] = (
            base_final['Hora'].astype(str).str.strip() + " | " +
            base_final['Usuarios'].astype(str).str.strip() + " | " +
            base_final['Fono'].astype(str).str.strip() + " | " +
            base_final['Tipificacion'].astype(str).str.strip() + " | " +
            base_final['Bucket'].astype(str).str.strip()
        )

        base_final = base_final.sort_values(by='Hora', ascending=True)
        filas_antes = len(base_final)
        base_final = base_final.drop_duplicates(subset=['KEY'], keep='first')
        filas_despues = len(base_final)
        print(f"-> Duplicados eliminados: {filas_antes - filas_despues} filas.")
    except Exception as e:
        print(f"Advertencia: Hubo un problema al quitar duplicados. Error: {e}")

    # =========================================================================
    # PASO 9: EXPORTACIÓN FINAL CON CONTEO Y ACUMULADO MAESTRO
    # =========================================================================
    columnas_finales = [
        "Fecha.", "Hora", "Cola", "Usuarios", "Fono", "Tipificacion", "Identificación de contacto",
        "Origen_Archivo", "Tipo de llamada", "Gestión", "No aplica", "Migracion", "Contacto.",
        "Errores", "Sin tipificar", "Base Cloud", "Bucket", "ANDES", "DNI", "SUPERVISOR",
        "Antiguedad", "Cuartil", "Turno"
    ]

    cols_presentes = [col for col in columnas_finales if col in base_final.columns]
    base_final = base_final[cols_presentes]
    ruta_salida_excel = ruta_salida.replace('.csv', '.xlsx')

    # --- Conteo de bases ---
    print(f"\nBuscando archivos para conteo en: {os.path.basename(ruta_genesys_bases)}...")
    total_genesys_cloud = 0
    total_homepass = 0
    total_genesys_santiago_centro = 0
    fecha_hoy = pd.Timestamp.today().strftime('%d/%m/%Y')
    columna_fecha = 'Fecha_Base'

    try:
        archivos_conteo = glob.glob(os.path.join(ruta_genesys_bases, "*.csv"))
        if not archivos_conteo:
            print("Advertencia: No se encontraron archivos CSV en la carpeta de conteo.")
        else:
            for archivo_c in archivos_conteo:
                nombre_archivo = os.path.basename(archivo_c).upper()

                try:
                    df_temp_c = pd.read_csv(archivo_c, sep=None, engine='python', encoding='utf-8-sig', dtype=str)
                    df_temp_c.columns = df_temp_c.columns.str.strip()

                    if columna_fecha in df_temp_c.columns:
                        filtrado = df_temp_c[df_temp_c[columna_fecha].astype(str).str.contains(fecha_hoy, na=False)]
                    else:
                        filtrado = df_temp_c

                    conteo_actual = len(filtrado)

                    if "CONFIRMACION" in nombre_archivo and "COLA001" in nombre_archivo:
                        total_homepass += conteo_actual
                    elif "BASE GENESYS COLA001" in nombre_archivo:
                        total_genesys_cloud += conteo_actual
                    elif "COLA002" in nombre_archivo:
                        total_genesys_santiago_centro += conteo_actual

                except Exception as e:
                    print(f"  -> Error leyendo el archivo {nombre_archivo}: {e}")

        print(f"  -> Conteo finalizado. Genesys Cloud: {total_genesys_cloud} | HomePass: {total_homepass} | Santiago Centro: {total_genesys_santiago_centro}")

    except Exception as e_conteo:
        print(f"Advertencia: Hubo un problema general en el conteo de bases. Error: {e_conteo}")
        total_genesys_cloud = 0
        total_homepass = 0
        total_genesys_santiago_centro = 0

    df_conteo = pd.DataFrame({
        "Genesys Cloud": [total_genesys_cloud],
        "HomePass": [total_homepass],
        "Santiago Centro": [total_genesys_santiago_centro]
    })

    # --- Guardar archivo Excel ---
    print("\nGuardando información en el archivo Excel final...")
    try:
        if os.path.exists(ruta_acomulado):
            df_acomulado_data = pd.read_csv(ruta_acomulado, sep=';', encoding='utf-8-sig', dtype=str)
        else:
            print(f"Advertencia: No se encontró el archivo en {ruta_acomulado}. Creando pestaña vacía.")
            df_acomulado_data = pd.DataFrame({"Aviso": ["Archivo Acomulado.csv no encontrado en la ruta especificada"]})

        with pd.ExcelWriter(ruta_salida_excel, engine='openpyxl') as writer:
            base_final.to_excel(writer, sheet_name='Base_Consolidada', index=False)
            df_conteo.to_excel(writer, sheet_name='Conteo de bases', index=False)
            df_acomulado_data.to_excel(writer, sheet_name='Acumulado', index=False)

        print("\n" + "="*40)
        print("¡Proceso Terminado Exitosamente!")
        print(f"Archivo Excel Maestro: {ruta_salida_excel}")
        print(f"Registros hoy en Genesys Cloud: {total_genesys_cloud} | Registros en HomePass: {total_homepass} | Registros Santiago Centro: {total_genesys_santiago_centro}")
        print("="*40)

    except Exception as e_excel:
        print(f"Error crítico al escribir el archivo Excel: {e_excel}")


if __name__ == "__main__":
    main()