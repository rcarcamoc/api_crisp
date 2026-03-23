import os
import csv
import time
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

BASE_URL = "https://api.crisp.chat/v1"

def get_auth():
    """Obtiene el objeto de autenticación Basic para requests."""
    identifier = os.getenv("CRISP_IDENTIFIER")
    key = os.getenv("CRISP_KEY")
    if not identifier or not key:
        logger.error("Las variables de entorno CRISP_IDENTIFIER y CRISP_KEY no están configuradas.")
        raise ValueError("CRISP_IDENTIFIER and CRISP_KEY environment variables must be set")
    return HTTPBasicAuth(identifier, key)

def get_headers():
    """Obtiene las cabeceras necesarias para la API de Crisp."""
    return {
        "X-Crisp-Tier": "plugin",
        "Content-Type": "application/json"
    }

def get_website_id():
    """Obtiene el website_id de las variables de entorno."""
    website_id = os.getenv("CRISP_WEBSITE_ID")
    if not website_id:
        logger.error("La variable de entorno CRISP_WEBSITE_ID no está configurada.")
        raise ValueError("CRISP_WEBSITE_ID environment variable must be set")
    return website_id

def get_max_workers():
    """Obtiene el número de hilos configurados, por defecto 5."""
    try:
        return int(os.getenv("MAX_WORKERS", 5))
    except (ValueError, TypeError):
        return 5

def export_to_csv(filename, data, fieldnames):
    """Exporta una lista de diccionarios a un archivo CSV escapado correctamente."""
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        logger.info(f"Datos exportados exitosamente a {filename}")
    except Exception as e:
        logger.error(f"Error al exportar a CSV: {e}")

def get_conversation_metadata(conv):
    """Extrae los metadatos relevantes de una conversación."""
    meta = conv.get("meta", {})
    return {
        "session_id": conv.get("session_id"),
        "people_id": conv.get("people_id"),
        "state": conv.get("state"),
        "created_at": conv.get("created_at"),
        "updated_at": conv.get("updated_at"),
        "meta_nickname": meta.get("nickname", ""),
        "meta_origin": meta.get("origin", ""),
        "meta_phone": meta.get("phone", ""),
        "meta_segments": ",".join(meta.get("segments", [])) if isinstance(meta.get("segments"), list) else "",
        "meta_email": meta.get("email", ""),
        "meta_address": meta.get("address", ""),
        "meta_ip": meta.get("ip", ""),
        "meta_subject": meta.get("subject", "")
    }

def fetch_all_conversations(website_id):
    """Descarga todas las conversaciones usando el endpoint directamente."""
    all_conversations = []
    page = 1
    auth = get_auth()
    headers = get_headers()

    while True:
        logger.info(f"Descargando conversaciones - Página {page}...")
        url = f"{BASE_URL}/website/{website_id}/conversations/{page}"
        try:
            response = requests.get(url, auth=auth, headers=headers)
            response.raise_for_status()
            data = response.json()

            # La API de Crisp devuelve un objeto con {"error": false, "reason": "...", "data": [...]}
            conversations = data.get("data", [])

            if not conversations:
                break

            all_conversations.extend(conversations)
            page += 1
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error al obtener conversaciones en página {page}: {e}")
            break
    return all_conversations

def fetch_messages_for_conversation(website_id, session_id):
    """Obtiene los mensajes de una conversación específica manejando paginación histórica."""
    all_messages = []
    timestamp_before = None
    auth = get_auth()
    headers = get_headers()

    try:
        while True:
            url = f"{BASE_URL}/website/{website_id}/conversation/{session_id}/messages"
            params = {}
            if timestamp_before:
                params["timestamp_before"] = timestamp_before

            response = requests.get(url, auth=auth, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            messages = data.get("data", [])

            if not messages:
                break

            all_messages.extend(messages)

            # Si hay menos de 30 mensajes, es probable que hayamos llegado al final (el límite por defecto suele ser 40)
            if len(messages) < 30:
                break

            # Usar el timestamp del mensaje más antiguo recibido (el último de la lista) para pedir los anteriores
            # Los mensajes vienen del más nuevo al más viejo
            new_timestamp = messages[-1].get("timestamp")
            if new_timestamp == timestamp_before:
                break
            timestamp_before = new_timestamp

        all_messages.sort(key=lambda x: x.get("timestamp", 0))
        return all_messages
    except Exception as e:
        logger.error(f"Error al obtener mensajes para {session_id}: {e}")
        return all_messages

def run_with_workers(func, items, *args):
    """Ejecuta una función en paralelo para una lista de ítems."""
    max_workers = get_max_workers()
    results = []
    logger.info(f"Iniciando procesamiento con {max_workers} workers...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {executor.submit(func, item, *args): item for item in items}
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            try:
                result = future.result()
                if result:
                    if isinstance(result, list):
                        results.extend(result)
                    else:
                        results.append(result)
            except Exception as e:
                logger.error(f"Error procesando ítem {item}: {e}")
    return results

def resolve_people_id(website_id, user_id_or_email):
    """Resuelve un email a un people_id llamando al endpoint de perfil."""
    if "@" in user_id_or_email:
        try:
            logger.info(f"Resolviendo email {user_id_or_email} a people_id...")
            url = f"{BASE_URL}/website/{website_id}/people/profile/{user_id_or_email}"
            response = requests.get(url, auth=get_auth(), headers=get_headers())
            response.raise_for_status()
            data = response.json()
            profile = data.get("data", {})
            return profile.get("people_id")
        except Exception as e:
            logger.error(f"No se pudo encontrar el perfil para {user_id_or_email}: {e}")
            return None
    return user_id_or_email
