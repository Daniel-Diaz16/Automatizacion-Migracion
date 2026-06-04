import os
import glob
import pandas as pd
import logging

# Configuración de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

RUTA_BASES = r"C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Genesys Engaged Bases"
RUTA_SALIDA = r"C:\Users\User\Grupo de Servicios Integrales Chile S.A\Mildred Casas - VTR Operaciones\02.Migracion\10.Corte Migracion\Base_Genesys_Engaged.xlsx"

def procesar_engadged_eficiente():
    archivos = glob.glob(os.path.join(RUTA_BASES, "*.rsl"))
    lista_df = []

    for archivo in archivos:
        logging.info(f"Procesando: {os.path.basename(archivo)}")
        
        # 1. Leemos el archivo | como delimitador
        df = pd.read_csv(archivo, sep='|', encoding='latin-1', dtype=str, on_bad_lines='skip')
        
        # 2. Lógica de limpieza dinámica
        # Obtenemos la primera fila como referencia para los nombres
        primera_fila = df.iloc[0]
        
        # Extraemos lo que está antes del '=' para los nombres y lo que está después para los datos
        nuevos_nombres = [str(val).split('=')[0] for val in primera_fila]
        
        # Renombramos las columnas
        df.columns = nuevos_nombres
        
        def limpiar_celda(x):
            # Convertimos a string primero para evitar errores
            s = str(x)
            if '=' in s:
                return s.split('=', 1)[1]
            return s

        # Aplicamos la limpieza a todo el DataFrame
        df = df.map(limpiar_celda)
        
        # ¡ESTA ES LA LÍNEA QUE FALTABA! Guardamos el dataframe limpio en la lista
        lista_df.append(df)

    # 3. Consolidar todo
    if lista_df:
        logging.info("Consolidando archivos y preparando para guardar...")
        final_df = pd.concat(lista_df, ignore_index=True)
        
        # Eliminamos filas que sean iguales al encabezado (si quedaron restos)
        final_df = final_df[final_df.iloc[:, 0] != final_df.columns[0]]
        
        # Guardamos en Excel
        final_df.to_excel(RUTA_SALIDA, index=False)
        logging.info(f"¡Proceso finalizado con éxito! Guardado en: {RUTA_SALIDA}")
    else:
        # Si la lista está vacía, ahora nos avisará
        logging.warning("No se procesó ningún archivo o la carpeta está vacía.")

if __name__ == "__main__":
    procesar_engadged_eficiente()