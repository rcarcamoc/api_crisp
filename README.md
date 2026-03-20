# Scripts de Crisp API para Reportes

Este repositorio contiene tres scripts en Python para descargar y auditar información de Crisp (People, Sessions y Messages) en formato CSV.

## Requisitos

- Python 3.x
- Instalar dependencias:
  ```bash
  pip install crisp-api python-dotenv
  ```

## Configuración

Crea un archivo `.env` en la raíz del proyecto con tus credenciales de Crisp:

```env
CRISP_IDENTIFIER="tu-identificador-de-plugin"
CRISP_KEY="tu-clave-de-plugin"
CRISP_WEBSITE_ID="tu-website-id"
MAX_WORKERS=5
```

- `MAX_WORKERS`: Controla cuántas descargas de mensajes se realizan en paralelo (por defecto 5).

## Scripts Disponibles

### 0. Listar Contactos (People)
Descarga la base de datos completa de contactos y perfiles.
```bash
python listar_contactos.py
```
**Resultado:** `contactos.csv`

### 1. Listar Sesiones Históricas
Descarga la lista de todas las conversaciones con sus metadatos principales.
```bash
python listar_sesiones.py
```
**Resultado:** `sesiones.csv`

### 2. Listar Conversaciones Completo (Auditoría)
Descarga todas las conversaciones e incluye **todos los mensajes** de cada una. Utiliza el sistema de hilos para mayor velocidad.
```bash
python listar_conversaciones.py
```
**Resultado:** `conversaciones_completo.csv`

### 3. Listar Conversaciones de un Usuario
Descarga el historial completo de conversaciones y mensajes de un usuario específico (`people_id` o email).
```bash
python listar_conversaciones_usuario.py <user_id_o_email>
```
**Resultado:** `conversaciones_usuario_<id>.csv`

## Características
- **Paginación automática:** Recorre todos los registros disponibles en la API.
- **Escape de CSV:** Los archivos CSV están configurados con `QUOTE_ALL` para asegurar que el contenido (especialmente los mensajes con saltos de línea) no rompa el formato.
- **Concurrencia:** Usa `ThreadPoolExecutor` para acelerar la descarga de mensajes.
