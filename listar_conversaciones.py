from crisp_utils import (
    get_crisp_client, get_website_id, fetch_all_conversations,
    get_conversation_metadata, fetch_messages_for_conversation,
    run_with_workers, export_to_csv, logger
)

def process_conversation_with_messages(conv, client, website_id):
    """Función para el worker: obtiene metadatos y mensajes de una conversación."""
    session_id = conv.get("session_id")
    metadata = get_conversation_metadata(conv)

    # Obtener mensajes
    messages = fetch_messages_for_conversation(client, website_id, session_id)

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
        client = get_crisp_client()
        website_id = get_website_id()

        logger.info("Obteniendo lista de conversaciones para auditoría completa...")
        conversations = fetch_all_conversations(client, website_id)

        if not conversations:
            logger.info("No hay conversaciones para procesar.")
            return

        logger.info(f"Procesando {len(conversations)} conversaciones con mensajes...")

        # Usar workers para descargar mensajes en paralelo
        all_rows = run_with_workers(process_conversation_with_messages, conversations, client, website_id)

        fieldnames = [
            "session_id", "people_id", "state", "created_at", "updated_at",
            "meta_nickname", "meta_origin", "meta_phone", "meta_segments",
            "meta_email", "meta_address", "meta_ip", "meta_subject",
            "message_from", "message_type", "message_timestamp", "message_fingerprint", "message_content"
        ]

        export_to_csv("conversaciones_completo.csv", all_rows, fieldnames)

    except Exception as e:
        logger.error(f"Error en auditoría completa: {e}")

if __name__ == "__main__":
    main()
