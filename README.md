# Sistema de Automatización de Migraciones VTR

Sistema de automatización para la gestión y procesamiento de datos de migraciones VTR, integrando múltiples fuentes de datos (Genesys Cloud, Genesys Engaged y Google Sheets) para generar reportes consolidados.

---

#  Características principales

| Característica | Descripción |
|----------------|-------------|
|  Automatización RPA | Procesamiento automático de datos de migración |
|  Múltiples fuentes | Genesys Cloud, Genesys Engaged y Google Sheets |
|  Procesamiento ETL | Extracción, transformación y carga de datos |
|  Reportes consolidados | Bases de datos unificadas y dashboards |
|  Programación horaria | Ejecución automática en horarios definidos |
|  Interfaz gráfica | PyQt6 con editor de código integrado |
|  Configuración persistente | Rutas y horarios almacenados en AppData |
|  Logs diarios | Registro automático de actividades |

---

#  Estructura del proyecto

```text
RPA_Migracion/
├── main.py
├── interfaz.ui
├── resaltador_sintaxis.py
├── horarios.py
├── tareas_migracion.py
├── Acomulado_Genesys_Cloud.py
├── Base_Genesys_Cloud.py
├── Base_Genesys_Engaged.py
├── Cruce_Genesys_Cloud.py
├── Genesys_Engaged.py
├── logs/
└── modulos/
```

---

#  Estructura en AppData

```text
%APPDATA%/RPA_Migracion/
├── horarios.json
├── rutas_config.json
├── logs/
│   └── rpa_migracion_YYYY-MM-DD.log
└── modulos/
    ├── Acomulado_Genesys_Cloud.py
    ├── Base_Genesys_Cloud.py
    ├── Base_Genesys_Engaged.py
    ├── Cruce_Genesys_Cloud.py
    └── Genesys_Engaged.py
```

---

#  Flujo de trabajo

1. Obtención de datos desde:
   - Genesys Cloud
   - Genesys Engaged
   - Google Sheets

2. Procesamiento ETL mediante:

| Módulo | Archivo generado |
|--------|------------------|
| Acomulado_Genesys_Cloud.py | Acomulado.csv |
| Base_Genesys_Cloud.py | Base_Genesys_Cloud.xlsx |
| Base_Genesys_Engaged.py | Base_Genesys_Engaged.xlsx |
| Cruce_Genesys_Cloud.py | Base_Consolidada_Agentes.xlsx |
| Genesys_Engaged.py | Formulario Engaged.xlsx |

3. Generación de reportes finales.

---

#  Horarios de ejecución

| Hora | Tarea | Días |
|------|-------|------|
| 08:10 | Cruce + Engaged | Lun-Vie |
| 08:50 | Acumulado + Base Cloud | Lun-Sáb |
| 09:10 | Acumulado + Base Cloud | Lun-Sáb |
| 09:10 | Cruce + Engaged | Lun-Vie |
| 10:10 | Cruce + Engaged | Lun-Vie |
| 11:10 | Cruce + Engaged | Lun-Vie |
| 12:10 | Cruce + Engaged | Lun-Vie |
| 13:10 | Cruce + Engaged | Lun-Vie |
| 14:10 | Cruce + Engaged | Lun-Vie |
| 15:10 | Cruce + Engaged | Lun-Sáb |
| 16:10 | Cruce + Engaged | Lun-Vie |
| 17:10 | Cruce + Engaged | Lun-Vie |
| 18:10 | Cruce + Engaged | Lun-Vie |

> Todos los horarios utilizan la zona horaria **America/Bogota**.

---

#  Dependencias

| Librería | Uso |
|----------|-----|
| PyQt6 | Interfaz gráfica |
| pandas | Procesamiento de datos |
| openpyxl | Excel |
| schedule | Programación |
| requests | Descargas |
| zoneinfo | Zona horaria |

## Instalación

```bash
pip install PyQt6 pandas openpyxl schedule requests
```

---

#  Interfaz gráfica

## Consola de salida

- Logs en tiempo real
- Auto-scroll
- Limpieza de consola

## Estado de procesos

- Estado Activo/Inactivo
- Última ejecución
- Duración
- Actualización cada 5 segundos

## Horarios configurados

- Agregar
- Modificar
- Eliminar
- Activar/Desactivar
- Persistencia en JSON

## Rutas de archivos

- Visualización
- Edición
- Explorador de archivos
- Guardado y restauración

## Editor de código

- Resaltado de sintaxis Python
- Carga y guardado
- Persistencia en AppData
- Recarga dinámica

---

#  Configuración

## rutas_config.json

```json
{
  "Acomulado_Genesys_Cloud": {},
  "Base_Genesys_Cloud": {},
  "Cruce_Genesys_Cloud": {},
  "Genesys_Engaged": {}
}
```

## horarios.json

```json
[
  {
    "hora":"08:10",
    "tarea":"cruce_engaged",
    "dias":["lunes","martes","miercoles","jueves","viernes"],
    "activo":true
  }
]
```

---

#  Procesos y archivos generados

| Proceso | Módulo | Archivo |
|---------|--------|---------|
| Acumulado | Acomulado_Genesys_Cloud.py | Acomulado.csv |
| Base Cloud | Base_Genesys_Cloud.py | Base_Genesys_Cloud.xlsx |
| Base Engaged | Base_Genesys_Engaged.py | Base_Genesys_Engaged.xlsx |
| Cruce | Cruce_Genesys_Cloud.py | Base_Consolidada_Agentes.xlsx |
| Engaged | Genesys_Engaged.py | Formulario Engaged.xlsx |

---

#  Tareas disponibles

| Tarea | Acción |
|-------|--------|
| acumulado | Acomulado_Genesys_Cloud.main() |
| base_cloud | Base_Genesys_Cloud.main() |
| cruce | Cruce_Genesys_Cloud.main() |
| engaged | Genesys_Engaged.procesar_automatizacion() |
| cruce_engaged | Cruce + Engaged en paralelo |
| acumulado_base | Acumulado + Base Cloud secuencial |

---

#  Notas importantes

- Configuración persistente en `%APPDATA%/RPA_Migracion/`.
- Los módulos editados permanecen después de actualizar el ejecutable.
- Los logs diarios se almacenan automáticamente.
- Todos los horarios usan la zona horaria **America/Bogota**.
- Los módulos pueden recargarse sin reiniciar la aplicación.

---

#  Licencia

Proyecto privado para uso interno en IBR Latam. Todos los derechos reservados.

---

**Última actualización:** Julio 2026
