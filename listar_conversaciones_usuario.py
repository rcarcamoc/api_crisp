import sys
from crisp_utils import (
    get_website_id, get_conversation_metadata,
    fetch_messages_for_conversation, export_to_csv, logger, resolve_people_id,
    BASE_URL, get_auth, get_headers
)
import requests

def fetch_user_conversations(website_id, people_id):
    """Descarga todas las conversaciones vinculadas a un people_id usando endpoint directo."""
    all_conversations = []
    page = 1
    auth = get_auth()
    headers = get_headers()

    while True:
        logger.info(f"Descargando conversaciones del usuario {people_id} - Página {page}...")
        url = f"{BASE_URL}/website/{website_id}/people/conversations/{people_id}/list/{page}"
        try:
            response = requests.get(url, auth=auth, headers=headers)
            if response.status_code != 200:
                try:
                    error_info = response.json()
                    reason = error_info.get("reason", "No reason provided")
                except:
                    reason = response.text
                logger.error(f"Error {response.status_code} al obtener conversaciones: {reason}")
                break

            data = response.json()
            session_ids = data.get("data", [])

            if not session_ids:
                break
            all_conversations.extend(session_ids)
            page += 1
        except Exception as e:
            logger.error(f"Error inesperado al obtener conversaciones del usuario: {e}")
            break
    return all_conversations

def main():
    if len(sys.argv) < 2:
        print("Uso: python listar_conversaciones_usuario.py <user_id_o_email>")
        return

    input_user = sys.argv[1]

    try:
        website_id = get_website_id()

        # Resolver ID si se pasó un email
        people_id = resolve_people_id(website_id, input_user)
        if not people_id:
            logger.error(f"No se pudo resolver el identificador para: {input_user}")
            return

        logger.info(f"Buscando conversaciones para el people_id: {people_id}")
        session_ids = fetch_user_conversations(website_id, people_id)

        if not session_ids:
            logger.info(f"No se encontraron conversaciones para el usuario {people_id}")
            return

        logger.info(f"Se encontraron {len(session_ids)} conversaciones. Descargando mensajes...")

        logger.info(f"Se encontraron {len(session_ids)} conversaciones. Procesando mensajes con hilos...")

        # Función auxiliar para procesar cada sesión en el worker
        def process_session(session_id):
            try:
                # Obtener la conversación para metadatos
                url_conv = f"{BASE_URL}/website/{website_id}/conversation/{session_id}"
                resp_conv = requests.get(url_conv, auth=get_auth(), headers=get_headers())
                resp_conv.raise_for_status()
                conv = resp_conv.json().get("data", {})

                metadata = get_conversation_metadata(conv)
                messages = fetch_messages_for_conversation(website_id, session_id)

                rows = []
                if not messages:
                    row = metadata.copy()
                    row.update({"message_from": "", "message_content": "", "message_timestamp": "", "message_type": "", "message_fingerprint": ""})
                    rows.append(row)
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
                        rows.append(row)
                return rows
            except Exception as e:
                logger.error(f"Error procesando sesión {session_id}: {e}")
                return []

        # Usar workers para descargar mensajes en paralelo
        from crisp_utils import run_with_workers
        all_rows = run_with_workers(process_session, session_ids)

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
