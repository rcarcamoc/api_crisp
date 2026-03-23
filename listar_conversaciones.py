import requests
import sys
from crisp_utils import (
    get_website_id, fetch_all_conversations,
    get_conversation_metadata, fetch_messages_for_conversation,
    run_with_workers, export_to_csv, logger, BASE_URL, get_auth, get_headers
)

# ==============================================================================
# CONFIGURACIÓN DE FILTROS
# ==============================================================================
# Si deseas filtrar, escribe el valor entre las comillas. Si no, déjalo vacío "".
# Ejemplo: FILTER_PHONE = "56994549279"
FILTER_PHONE = ""

# Ejemplo: FILTER_SESSION_ID = "session_c5f584da-b843-4d11-ba6d-26034c8a4a34"
FILTER_SESSION_ID = ""
# ==============================================================================

def process_conversation_with_messages(conv, website_id):
    """Función para el worker: obtiene metadatos y mensajes de una conversación."""
    session_id = conv.get("session_id")
    metadata = get_conversation_metadata(conv)

    # Obtener mensajes
    messages = fetch_messages_for_conversation(website_id, session_id)

    # Si no hay mensajes, devolvemos solo la entrada de metadatos con contenido vacío
    if not messages:
        metadata["message_from"] = ""
        metadata["message_content"] = ""
        metadata["message_timestamp"] = ""
        metadata["message_type"] = ""
        metadata["message_fingerprint"] = ""
        return [metadata]

    # Crear una fila por cada mensaje vinculada a los metadatos de la sesión
    rows = []
    for msg in messages:
        row = metadata.copy()
        row["message_from"] = msg.get("from", "")
        row["message_content"] = msg.get("content", "")
        row["message_timestamp"] = msg.get("timestamp", "")
        row["message_type"] = msg.get("type", "")
        row["message_fingerprint"] = msg.get("fingerprint", "")
        rows.append(row)

    return rows

def main():
    try:
        website_id = get_website_id()
        conversations = []

        # 1. Prioridad: Filtrar por una sesión específica definida en la variable
        if FILTER_SESSION_ID:
            logger.info(f"Obteniendo metadatos para la sesión definida: {FILTER_SESSION_ID}")
            url = f"{BASE_URL}/website/{website_id}/conversation/{FILTER_SESSION_ID}"
            response = requests.get(url, auth=get_auth(), headers=get_headers())
            response.raise_for_status()
            conv_data = response.json().get("data", {})
            if conv_data:
                conversations = [conv_data]
            else:
                logger.error(f"No se encontró la sesión {FILTER_SESSION_ID}")
                return
        else:
            # 2. Obtener todas y filtrar por teléfono si la variable está definida
            logger.info("Obteniendo lista de conversaciones...")
            conversations = fetch_all_conversations(website_id)

            if FILTER_PHONE:
                logger.info(f"Filtrando conversaciones por el teléfono definido: {FILTER_PHONE}")
                conversations = [
                    c for c in conversations
                    if c.get("meta", {}).get("phone") == FILTER_PHONE
                ]
                logger.info(f"Conversaciones encontradas tras filtrar por teléfono: {len(conversations)}")

        if not conversations:
            logger.info("No hay conversaciones que coincidan con los criterios (revisa las variables FILTER_ en el script).")
            return

        logger.info(f"Procesando {len(conversations)} conversaciones con mensajes...")

        # Usar workers para descargar mensajes en paralelo
        all_rows = run_with_workers(process_conversation_with_messages, conversations, website_id)

        fieldnames = [
            "session_id", "people_id", "state", "created_at", "updated_at",
            "meta_nickname", "meta_origin", "meta_phone", "meta_segments",
            "meta_email", "meta_address", "meta_ip", "meta_subject",
            "message_from", "message_type", "message_timestamp", "message_fingerprint", "message_content"
        ]

        # Generar nombre de archivo
        filename = "conversaciones_filtrado.csv" if (FILTER_PHONE or FILTER_SESSION_ID) else "conversaciones_completo.csv"
        export_to_csv(filename, all_rows, fieldnames)

    except Exception as e:
        logger.error(f"Error en el proceso de exportación: {e}")

if __name__ == "__main__":
    main()
