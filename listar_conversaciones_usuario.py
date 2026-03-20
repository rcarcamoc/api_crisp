import sys
from crisp_utils import (
    get_crisp_client, get_website_id, get_conversation_metadata,
    fetch_messages_for_conversation, export_to_csv, logger, resolve_people_id
)

def fetch_user_conversations(client, website_id, people_id):
    """Descarga todas las conversaciones vinculadas a un people_id."""
    all_conversations = []
    page = 1
    while True:
        logger.info(f"Descargando conversaciones del usuario {people_id} - Página {page}...")
        try:
            # Corregido: el método es get_people_conversations
            session_ids = client.website.get_people_conversations(website_id, people_id, page)
            if not session_ids:
                break
            all_conversations.extend(session_ids)
            page += 1
        except Exception as e:
            logger.error(f"Error al obtener conversaciones del usuario: {e}")
            break
    return all_conversations

def main():
    if len(sys.argv) < 2:
        print("Uso: python listar_conversaciones_usuario.py <user_id_o_email>")
        return

    input_user = sys.argv[1]

    try:
        client = get_crisp_client()
        website_id = get_website_id()

        # Resolver ID si se pasó un email
        people_id = resolve_people_id(client, website_id, input_user)
        if not people_id:
            logger.error(f"No se pudo resolver el identificador para: {input_user}")
            return

        logger.info(f"Buscando conversaciones para el people_id: {people_id}")
        session_ids = fetch_user_conversations(client, website_id, people_id)

        if not session_ids:
            logger.info(f"No se encontraron conversaciones para el usuario {people_id}")
            return

        logger.info(f"Se encontraron {len(session_ids)} conversaciones. Descargando mensajes...")

        all_rows = []
        for session_id in session_ids:
            try:
                conv = client.website.get_conversation(website_id, session_id)
                metadata = get_conversation_metadata(conv)

                messages = fetch_messages_for_conversation(client, website_id, session_id)

                if not messages:
                    row = metadata.copy()
                    row.update({"message_from": "", "message_content": "", "message_timestamp": "", "message_type": "", "message_fingerprint": ""})
                    all_rows.append(row)
                else:
                    for msg in messages:
                        row = metadata.copy()
                        row.update({
                            "message_from": msg.get("from", ""),
                            "message_content": msg.get("content", ""),
                            "message_timestamp": msg.get("timestamp", ""),
                            "message_type": msg.get("type", ""),
                            "message_fingerprint": msg.get("fingerprint", "")
                        })
                        all_rows.append(row)
            except Exception as e:
                logger.error(f"Error procesando sesión {session_id}: {e}")

        fieldnames = [
            "session_id", "people_id", "state", "created_at", "updated_at",
            "meta_nickname", "meta_origin", "meta_phone", "meta_segments",
            "meta_email", "meta_address", "meta_ip", "meta_subject",
            "message_from", "message_type", "message_timestamp", "message_fingerprint", "message_content"
        ]

        filename = f"conversaciones_usuario_{people_id}.csv"
        export_to_csv(filename, all_rows, fieldnames)

    except Exception as e:
        logger.error(f"Error en script de usuario: {e}")

if __name__ == "__main__":
    main()
