import pandas as pd
import glob
import os
from datetime import datetime, timedelta


hoy = datetime.now()
mes_pasado_fecha = hoy.replace(day=1) - timedelta(days=6)
meses_espanol = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

anio_pasado = mes_pasado_fecha.strftime('%Y')
num_mes = mes_pasado_fecha.strftime('%m')
nombre_mes = meses_espanol[mes_pasado_fecha.month]
carpeta_mes_pasado = f"{num_mes}. {nombre_mes}"


ruta_base = r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\09. Bases Genesys\01. Contact_List'
ruta_salida = r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Cloud.xlsx'
ruta_cargue_actual = os.path.join(ruta_base, 'Cargue Actual')
ruta_historico_mes_pasado = os.path.join(
ruta_base, 'Historico', anio_pasado, carpeta_mes_pasado)
ruta_bases_cloud = r'C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Cloud Bases'

columnas_expandidas = [
    'inin-outbound-id',
    'vCampaignEffectiveDate',
    'RUT_PERSONA',
    'FONO_CONTACTO',
    'Fono1',
    'Segment_of_Origin'
]

print("Buscando archivos en todas las rutas...")
print(f" -> Actual: {ruta_cargue_actual}")
print(f" -> Histórico: {ruta_historico_mes_pasado}")
print(f" -> Cloud Bases: {ruta_bases_cloud}")

archivos_actual = glob.glob(os.path.join(ruta_cargue_actual, "*.csv"))
archivos_historico = glob.glob(
    os.path.join(ruta_historico_mes_pasado, "*.csv"))
archivos_cloud = glob.glob(os.path.join(ruta_bases_cloud, "*.csv"))
archivos_csv = archivos_actual + archivos_historico + archivos_cloud

if not archivos_csv:
    print("\n❌ No se encontraron archivos CSV en ninguna de las rutas.")
else:
    print(
        f"\n✅ Se encontraron {len(archivos_csv)} archivos en total. Iniciando consolidación...")
    lista_tablas = []

    for archivo in archivos_csv:
        try:
            try:
                datos = pd.read_csv(
                    archivo, sep=',', encoding='utf-8-sig', dtype=str, on_bad_lines='skip')
                if len(datos.columns) == 1:
                    raise ValueError("Probable separador punto y coma")
            except:
                # Intento con Punto y Coma
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

            # Limpieza de fonos
            for col_fono in ['FONO_CONTACTO', 'Fono1']:
                if col_fono in datos.columns:
                    datos[col_fono] = datos[col_fono].apply(lambda x: str(
                        x).strip()[-9:] if pd.notna(x) and str(x).strip() != "" else None)

            lista_tablas.append(datos)
            print(f"✔️ Cargado: {os.path.basename(archivo)}")

        except Exception as e:
            print(f"❌ Error en {os.path.basename(archivo)}: {e}")

    if lista_tablas:
        df_final = pd.concat(lista_tablas, ignore_index=True)

        print("Limpiando caracteres especiales (Mojibake)...")
        diccionario_caracteres = {
            'Ã¡': 'á', 'Ã©': 'é', 'Ã\xad': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
            'Ã±': 'ñ', 'Ã‘': 'Ñ', 'Â°': '°', 'Â': ''
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

        print(f"\n--- ÉXITO: Archivo guardado con {len(df_final)} filas ---")
        print(f"Ruta: {ruta_salida}")
    else:
        print("\nError: No se procesó ninguna información.")
