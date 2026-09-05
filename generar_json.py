import json

# Cargamos el archivo descargado de Apify
with open('apify_export.json', 'r', encoding='utf-8') as f:
    bruto = json.load(f)

lista_pisos = []
for item in bruto:
    property_code = item.get("propertyCode") or item.get("id") or "sin-codigo"
    if property_code != "sin-codigo" and "-" in str(property_code):
        property_code = str(property_code).split("-")[-1]

    # Capturamos correctamente el título y la descripción del JSON original
    titulo_real = item.get("title") or item.get("heading") or item.get("description") or ""

    piso = {
        "propertyCode": str(property_code),
        "price": item.get("price"),
        "title": titulo_real,
        "description": item.get("description") or "",
        "zone": item.get("municipality") or item.get("neighborhood") or "Madrid",
        "size": item.get("size") or item.get("builtArea") or 80,
        "rooms": item.get("rooms") or item.get("roomsCount") or 3,
        "floor": str(item.get("floor") or "2"),
        "hasLift": item.get("hasLift", True),
        "url": f"https://www.idealista.com/inmueble/{property_code}/"
    }
    lista_pisos.append(piso)

with open('pisos_prueba.json', 'w', encoding='utf-8') as f:
    json.dump(lista_pisos, f, ensure_ascii=False, indent=4)

print(f"¡Procesados {len(lista_pisos)} pisos con título y descripción reales!")