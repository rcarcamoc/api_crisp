import requests
import csv
import sys
import os
from datetime import datetime, timedelta, timezone
import base64
import time

# --- CONFIGURACIÓN ---
# Se recomienda usar variables de entorno para mayor seguridad.
IDENTIFIER = os.environ.get("CRISP_IDENTIFIER", "73d66b40-d037-4689-adec-17111cef35b5")
KEY = os.environ.get("CRISP_KEY", "faaea935eaa869ef5906ca67cd25f6751873871c48c5e0fe46848c4e6ac14306")
WEBSITE_ID = os.environ.get("CRISP_WEBSITE_ID", "448e0792-3836-49a2-8631-72693b9487e0")
BASE_URL = "https://api.crisp.chat/v1"

# --- AUTENTICACIÓN ---
auth_str = f"{IDENTIFIER}:{KEY}"
encoded_auth = base64.b64encode(auth_str.encode("ascii")).decode("ascii")
HEADERS = {
    "Authorization": f"Basic {encoded_auth}",
    "X-Crisp-Tier": "plugin",
    "Content-Type": "application/json"
}

# Caché para nombres de operadores
OPERATOR_CACHE = {}

def get_iso_date(days_ago=0):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

def fetch_conversations(start_date, end_date):
    conversations = []
    page = 1
    while True:
        url = f"{BASE_URL}/website/{WEBSITE_ID}/conversations/{page}"
        params = {
            "filter_date_start": start_date,
            "filter_date_end": end_date
        }
        print(f"Obteniendo conversaciones - Página {page}...")
        sys.stdout.flush()
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        except requests.exceptions.Timeout:
            print(f"Timeout en página {page}")
            break

        if response.status_code not in [200, 206]:
            print(f"Error fetching conversations: {response.status_code} - {response.text}")
            break

        resp_json = response.json()
        data = resp_json.get("data", [])
        print(f"Conversaciones en esta página: {len(data)}")
        if not data:
            break

        conversations.extend(data)
        page += 1
        if page > 500: break
        time.sleep(0.1)

    return conversations

def fetch_meta(session_id):
    url = f"{BASE_URL}/website/{WEBSITE_ID}/conversation/{session_id}/meta"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
    except requests.exceptions.Timeout:
        return {}
    if response.status_code != 200:
        return {}
    return response.json().get("data", {})

def fetch_messages(session_id):
    messages = []
    timestamp_before = None
    while True:
        url = f"{BASE_URL}/website/{WEBSITE_ID}/conversation/{session_id}/messages"
        params = {}
        if timestamp_before:
            params["timestamp_before"] = timestamp_before

        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=30)
        except requests.exceptions.Timeout:
            break
        if response.status_code not in [200, 206]:
            break

        data = response.json().get("data", [])
        if not data:
            break

        messages.extend(data)
        earliest_ts = data[-1].get("timestamp")
        if timestamp_before == earliest_ts:
            break
        timestamp_before = earliest_ts
        if len(data) < 20:
            break
        time.sleep(0.05)

    return messages

def get_operator_name(user_id):
    if not user_id:
        return "Sin asignar"
    if user_id in OPERATOR_CACHE:
        return OPERATOR_CACHE[user_id]

    url = f"{BASE_URL}/website/{WEBSITE_ID}/operator/{user_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json().get("data", {})
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            name = f"{first_name} {last_name}".strip() or user_id
            OPERATOR_CACHE[user_id] = name
            return name
    except:
        pass
    return user_id

def calculate_metrics(messages, state, updated_at_ts):
    sorted_msgs = sorted(messages, key=lambda x: x.get("timestamp", 0))

    first_user_ts = None
    first_op_ts = None
    last_op_ts = None

    for msg in sorted_msgs:
        sender = msg.get("from")
        ts = msg.get("timestamp")

        if not first_user_ts and sender in ["user", "website"]:
            first_user_ts = ts

        if sender == "operator":
            if not first_op_ts:
                first_op_ts = ts
            last_op_ts = ts

    # First Response Time
    frt = "N/A"
    if first_user_ts and first_op_ts:
        frt = round((first_op_ts - first_user_ts) / (1000 * 60), 2)

    # Resolution Time
    res_time = "Sin atención"
    if first_op_ts:
        end_ts = updated_at_ts if state == "resolved" else last_op_ts
        res_time = round((end_ts - first_op_ts) / (1000 * 60), 2)
        if state != "resolved":
            res_time = f"{res_time} (En proceso)"

    return frt, res_time

def format_timestamp(ts):
    if ts:
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    return ""

def main():
    print("Iniciando script de reporte final...")
    sys.stdout.flush()
    date_start = get_iso_date(7)
    date_end = get_iso_date(0)

    conversations = fetch_conversations(date_start, date_end)
    total_convs = len(conversations)
    print(f"Total de conversaciones encontradas: {total_convs}")

    all_conversations_data = []
    all_messages_data = []
    all_custom_keys = set()

    for i, conv in enumerate(conversations):
        sid = conv.get("session_id")
        print(f"[{i+1}/{total_convs}] Procesando: {sid}")
        sys.stdout.flush()

        meta = fetch_meta(sid) or conv.get("meta", {})
        device = meta.get("device", {})
        geo = device.get("geolocation", {})
        assigned = conv.get("assigned", {}) or {}
        unread = conv.get("unread", {}) or {}

        user_id = assigned.get("user_id")
        user_name = get_operator_name(user_id)

        segments = ", ".join(meta.get("segments", []))
        custom_data = meta.get("data", {})
        for key in custom_data.keys():
            all_custom_keys.add(key)

        messages = fetch_messages(sid)
        frt, res_time = calculate_metrics(messages, conv.get("state"), conv.get("updated_at"))

        conv_row = {
            "session_id": sid,
            "created_at": format_timestamp(conv.get("created_at")),
            "updated_at": format_timestamp(conv.get("updated_at")),
            "state": conv.get("state"),
            "assigned_user_id": user_id or "Sin asignar",
            "assigned_user_name": user_name,
            "email": meta.get("email", ""),
            "nickname": meta.get("nickname", ""),
            "country": geo.get("country", ""),
            "last_message": conv.get("last_message", ""),
            "unread_operator": unread.get("operator", 0),
            "canal": meta.get("origin", ""),
            "segments": segments,
            "first_response_time_minutes": frt,
            "resolution_time_minutes": res_time
        }
        for key, value in custom_data.items():
            conv_row[f"data_{key}"] = value

        all_conversations_data.append(conv_row)

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, dict):
                content = content.get("text") or content.get("value") or str(content)

            all_messages_data.append([
                sid, format_timestamp(msg.get("timestamp")), content, msg.get("from"), msg.get("type")
            ])

        if (i + 1) % 20 == 0:
            time.sleep(0.5)

    # Escribir CSV
    custom_cols = sorted([f"data_{k}" for k in all_custom_keys])
    fieldnames = [
        "session_id", "created_at", "updated_at", "state", "assigned_user_id",
        "assigned_user_name", "email", "nickname", "country", "last_message",
        "unread_operator", "canal", "segments", "first_response_time_minutes",
        "resolution_time_minutes"
    ] + custom_cols

    with open('reporte_conversaciones_final.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_conversations_data:
            for col in custom_cols:
                if col not in row: row[col] = ""
            writer.writerow(row)

    with open('reporte_mensajes_final.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["session_id", "fecha", "mensaje", "de", "tipo"])
        writer.writerows(all_messages_data)

    print(f"Finalizado. Reportes: reporte_conversaciones_final.csv y reporte_mensajes_final.csv")

if __name__ == "__main__":
    main()
