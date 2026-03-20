from crisp_utils import (
    get_crisp_client, get_website_id, fetch_all_conversations,
    get_conversation_metadata, export_to_csv, logger
)

def main():
    try:
        client = get_crisp_client()
        website_id = get_website_id()

        logger.info("Iniciando descarga de todas las sesiones (conversaciones)...")
        conversations = fetch_all_conversations(client, website_id)

        if not conversations:
            logger.info("No se encontraron conversaciones.")
            return

        logger.info(f"Se encontraron {len(conversations)} conversaciones. Procesando metadatos...")

        processed_data = [get_conversation_metadata(c) for c in conversations]

        fieldnames = [
            "session_id", "people_id", "state", "created_at", "updated_at",
            "meta_nickname", "meta_origin", "meta_phone", "meta_segments",
            "meta_email", "meta_address", "meta_ip", "meta_subject"
        ]

        export_to_csv("sesiones.csv", processed_data, fieldnames)

    except Exception as e:
        logger.error(f"Ocurrió un error en el script: {e}")

if __name__ == "__main__":
    main()
