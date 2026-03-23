from crisp_utils import (
    get_website_id, export_to_csv, logger, BASE_URL, get_auth, get_headers
)
import time
import requests

def fetch_all_people(website_id):
    """Descarga todos los perfiles de personas (contactos) usando endpoint directo."""
    all_people = []
    page = 1
    auth = get_auth()
    headers = get_headers()

    while True:
        logger.info(f"Descargando contactos (People) - Página {page}...")
        url = f"{BASE_URL}/website/{website_id}/people/profiles/{page}"
        try:
            response = requests.get(url, auth=auth, headers=headers)
            response.raise_for_status()
            data = response.json()
            people = data.get("data", [])

            if not people:
                break
            all_people.extend(people)
            page += 1
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error al obtener contactos en página {page}: {e}")
            break
    return all_people

def main():
    try:
        website_id = get_website_id()

        logger.info("Iniciando descarga de contactos (People)...")
        people_list = fetch_all_people(website_id)

        if not people_list:
            logger.info("No se encontraron contactos.")
            return

        processed_data = []
        for p in people_list:
            person = p.get("person", {})
            geolocation = person.get("geolocation", {})
            processed_data.append({
                "people_id": p.get("people_id"),
                "email": p.get("email"),
                "nickname": person.get("nickname", ""),
                "phone": person.get("phone", ""),
                "address": person.get("address", ""),
                "description": person.get("description", ""),
                "website": person.get("website", ""),
                "segments": ",".join(p.get("segments", [])) if isinstance(p.get("segments"), list) else "",
                "country": geolocation.get("country", ""),
                "city": geolocation.get("city", ""),
                "created_at": p.get("created_at"),
                "updated_at": p.get("updated_at")
            })

        fieldnames = [
            "people_id", "email", "nickname", "phone", "address",
            "description", "website", "segments", "country", "city",
            "created_at", "updated_at"
        ]

        export_to_csv("contactos.csv", processed_data, fieldnames)

    except Exception as e:
        logger.error(f"Error en script de contactos: {e}")

if __name__ == "__main__":
    main()
