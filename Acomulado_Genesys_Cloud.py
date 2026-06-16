import pandas as pd
import glob
import os
import warnings
import json
import sys

# Silenciar advertencias de excel
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


# =============================================================================
# FUNCION PARA CARGAR RUTAS DESDE JSON
# =============================================================================

def obtener_ruta_config():
    """Obtiene la ruta donde se guarda la configuración en AppData/Roaming"""
    app_data = os.getenv('APPDATA')
    config_dir = os.path.join(app_data, 'RPA_Migracion')
    return os.path.join(config_dir, 'rutas_config.json')


def cargar_rutas_modulo():
    """Carga las rutas del módulo Acomulado_Genesys_Cloud desde el JSON"""
    ruta_config = obtener_ruta_config()
    if os.path.exists(ruta_config):
        try:
            with open(ruta_config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if 'Acomulado_Genesys_Cloud' in config:
                return config['Acomulado_Genesys_Cloud']
        except:
            pass
    # Si no existe, usar rutas por defecto
    return {
        'ruta_carpeta': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\09. Bases Genesys\02. Interacciones\Historico\2026',
        'ruta_salida': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Acomulado.csv',
        'ruta_dotacion': r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Dotacion VTR Operaciones.xlsx'
    }


# Cargar rutas desde JSON
_RUTAS = cargar_rutas_modulo()

# Asignar variables globales
ruta_carpeta = _RUTAS['ruta_carpeta']
ruta_salida = _RUTAS['ruta_salida']
ruta_dotacion = _RUTAS['ruta_dotacion']


# =============================================================================
# FUNCIONES DE EXTRACCION Y LIMPIEZA
# =============================================================================

def extraer_tipificacion(conclusion):
    if pd.isna(conclusion) or str(conclusion).strip() == "":
        return None
    partes = [parte.strip() for parte in str(conclusion).split(";")]
    if len(partes) >= 2:
        return partes[1]
    return conclusion


def crear_agente_inicial(texto):
    if pd.isna(texto) or str(texto).strip() == "":
        return ""
    
    texto_str = str(texto).strip()
    
    if ";" in texto_str:
        texto_str = texto_str.split(";")[0].strip()
        
    if "_" in texto_str:
        partes = texto_str.split("_")
        if len(partes) >= 2:
            return partes[-2].strip()
            
    return texto_str


# =============================================================================
# DICCIONARIOS DE REEMPLAZOS
# =============================================================================

reemplazos_nombres = {
    "Diana Carolina Llorente  Almanza": "Diana Carolina Llorente Almanza",
    "Angie Nicole Abril Marino": "Angie Nicole Abril Mariño",
    "ANDRÉS FELIPE ZIZOU BARRIOS BERMÚDEZ": "Andres Felipe Zizou Barrios Bermudez",
    "Andrés Felipe Zizou Barrios Bermúdez": "Andres Felipe Zizou Barrios Bermudez",
    "Andrã%89S Felipe Zizou Barrios Bermã%9ADez": "Andres Felipe Zizou Barrios Bermudez",
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

diccionario_mojibake = {
    '\xc3\xa1': 'a', '\xc3\xa9': 'e', '\xc3\xad': 'i', '\xc3\xb3': 'o', '\xc3\xba': 'u', 
    '\xc3\xb1': 'n', '\xc3\x91': 'N', '\xc3\xa3': 'a', '\xc3\xa3S': 'es', '\xc3\xa3N': 'n', '\xc2\x94': ''
}

columnas_expandidas = [
    "Usuarios", "Fecha", "Hora", "Fono", "Dirección", "DNIS", "Cola", "Conclusión", "Identificación de contacto"
]


# =============================================================================
# PROCESO PRINCIPAL
# =============================================================================

def main():
    """Funcion principal que ejecuta todo el proceso de Acumulado Genesys Cloud"""

    archivos_csv = glob.glob(os.path.join(ruta_carpeta, "**", "*.csv"), recursive=True)

    if not archivos_csv:
        print("No se encontraron archivos CSV en la ruta especificada. Revisa la ruta o las subcarpetas.")
        return

    print(f"Se encontraron {len(archivos_csv)} archivos. Iniciando unión...")

    lista_tablas = []

    for archivo in archivos_csv:
        try:
            datos = pd.read_csv(archivo, sep=';', encoding='utf-8-sig', dtype=str)
            datos.columns = datos.columns.str.strip()
            datos = datos.rename(columns=correccion_columnas)
            cols_presentes = [col for col in columnas_expandidas if col in datos.columns]
            datos = datos[cols_presentes]
            datos['Origen_Archivo'] = os.path.basename(archivo)
            lista_tablas.append(datos)
            print(f"Cargado: {os.path.basename(archivo)}")

        except Exception:
            try:
                datos = pd.read_csv(archivo, sep=';', encoding='latin1', dtype=str)
                datos.columns = datos.columns.str.strip()
                datos = datos.rename(columns=correccion_columnas) 
                cols_presentes = [col for col in columnas_expandidas if col in datos.columns]
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

    # --- Limpieza Profunda de Usuarios ---
    if "Usuarios" in base_final.columns:
        base_final['Usuarios'] = base_final['Usuarios'].apply(crear_agente_inicial)
        base_final["Usuarios"] = base_final["Usuarios"].replace(reemplazos_nombres)
        
        for mal, bien in diccionario_mojibake.items():
            base_final["Usuarios"] = base_final["Usuarios"].str.replace(mal, bien, regex=False)
        
        base_final["Usuarios"] = base_final["Usuarios"].str.replace(r'\s+', ' ', regex=True).str.strip().str.title()
        base_final["Usuarios"] = base_final["Usuarios"].replace(reemplazos_nombres)

        # --- Cruce con Dotación (Supervisor) ---
        try:
            df_dot_aux = pd.read_excel(ruta_dotacion, sheet_name='DOTACION', dtype=str)
            df_dot_aux['NOMBRE COMPLETO'] = df_dot_aux['NOMBRE COMPLETO'].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip().str.title()
            dot_limpia_aux = df_dot_aux[['NOMBRE COMPLETO', 'SUPERVISOR']].dropna(subset=['NOMBRE COMPLETO']).drop_duplicates(subset=['NOMBRE COMPLETO'])
            base_final = pd.merge(base_final, dot_limpia_aux, how='left', left_on='Usuarios', right_on='NOMBRE COMPLETO')
        except Exception as error_dot:
            print(f"Advertencia - No se cruzó Dotación: {error_dot}")
            base_final['SUPERVISOR'] = "-"

    # --- Limpieza de Conclusión y Tipificación ---
    if "Conclusión" in base_final.columns:
        base_final['Conclusión'] = base_final['Conclusión'].str.replace("ININ-OUTBOUND-CAMPAIGN-FORCED-OFF; ", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace("ININ-OUTBOUND-TRANSFERRED-TO-QUEUE; ", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace("ININ-OUTBOUND-", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace("ININ-", "", regex=False)
        base_final['Conclusión'] = base_final['Conclusión'].str.replace(" - SOP", "", regex=False)
        base_final['Tipificacion'] = base_final['Conclusión'].apply(extraer_tipificacion)
    
    # --- Mapeo de Colas a Bases ---
    if "Cola" in base_final.columns:
        diccionario_colas = {
            "COLA_OPERACIONES_MIGRACION_IBR_COLOMBIA_Q001": "Genesys Cloud",
            "COLA_OPERACIONES_CONFIRMACION_IBR_COLOMBIA_Q001": "HomePass",
            "COLA_OPERACIONES_MIGRACION_IBR_COLOMBIA_Q002": "Santiago Centro",
            "COLA_OPERACIONES_MIGRACION_IBR_COLOMBIA_Q003": "Base Infactible"
        }
        base_final['Base Cloud'] = base_final['Cola'].map(diccionario_colas).fillna("-")

    # --- Filtro Específico de Migraciones ---
    if "Tipificacion" in base_final.columns:
        base_final = base_final[base_final['Tipificacion'].str.contains(r"ACEPTA AGENDA - MIGRACION|ACEPTA REINGRESO MIGRACION", case=False, na=False, regex=True)]

    # --- Separación, Formato y FILTRO ESTRICTO DE FECHAS ---
    if "Fecha" in base_final.columns:
        base_final['Fecha'] = base_final['Fecha'].astype(str)
        partes = base_final['Fecha'].str.split(' ', n=1, expand=True)
        
        base_final['Fecha'] = partes[0]
        base_final['Hora'] = partes[1].fillna("00:00")
        base_final['Hora'] = pd.to_datetime(base_final['Hora'], format='%H:%M', errors='coerce').dt.strftime('%H:%M').fillna("00:00")

        base_final['Fecha_Temp'] = pd.to_datetime(base_final['Fecha'], dayfirst=True, errors='coerce')
        
        hoy_chile = pd.Timestamp.now(tz='America/Santiago').tz_localize(None).normalize() 
        inicio_este_mes = hoy_chile.replace(day=1)
        fecha_limite_inferior = inicio_este_mes - pd.Timedelta(days=10)
        inicio_siguiente_mes = (inicio_este_mes + pd.Timedelta(days=32)).replace(day=1)
        fecha_limite_superior = inicio_siguiente_mes - pd.Timedelta(days=1)
        
        print("\n" + "-"*40)
        print("Aplicando Filtro Estricto de Fechas:")
        print(f"-> Desde: {fecha_limite_inferior.strftime('%d/%m/%Y')}")
        print(f"-> Hasta: {fecha_limite_superior.strftime('%d/%m/%Y')} (Fin de este mes)")
        print("-"  *40)
        
        filtro_fechas = (base_final['Fecha_Temp'] >= fecha_limite_inferior) & (base_final['Fecha_Temp'] <= fecha_limite_superior)
        base_final = base_final[filtro_fechas]
        base_final = base_final.drop(columns=['Fecha_Temp'])

    # --- Ordenamiento y Exportación Final ---
    columnas_finales = [
        "Fecha",
        "Hora",
        "Cola",
        "Usuarios",
        "Fono",
        "Tipificacion",
        "Identificación de contacto",
        "Base Cloud",
        "Origen_Archivo",
        "SUPERVISOR"
    ]
    
    cols_presentes = [col for col in columnas_finales if col in base_final.columns]
    base_final = base_final[cols_presentes]
    
    base_final.to_csv(
        ruta_salida,
        index=False,
        sep=';',              
        encoding='utf-8-sig'
    )

    print("\n" + "="*30)
    print(f"¡Hecho! Archivo creado con {len(base_final)} filas.")
    print(f"Ubicación: {ruta_salida}")


if __name__ == "__main__":
    main()