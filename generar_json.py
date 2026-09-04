import json

# Cargamos directamente el archivo descargado de Apify
with open('apify_export.json', 'r', encoding='utf-8') as f:
    bruto = json.load(f)

lista_pisos = []
for item in bruto:
    # Apify suele guardar el identificador en 'propertyCode' o sacarlo de la URL
    property_code = item.get("propertyCode") or item.get("id") or "sin-codigo"
    
    # Si viene en formato texto largo, intentamos extraer los números si los hay
    if property_code != "sin-codigo" and "-" in str(property_code):
        property_code = str(property_code).split("-")[-1]

    piso = {
        "propertyCode": str(property_code),
        "price": item.get("price"),
        "title": item.get("title") or item.get("heading"),
        "zone": item.get("municipality") or item.get("neighborhood") or "Zona",
        "size": item.get("size") or 80,
        "rooms": item.get("rooms") or 3,
        "floor": item.get("floor") or "2",
        "hasLift": item.get("hasLift", True),
        "url": f"https://www.idealista.com/inmueble/{property_code}/"
    }
    lista_pisos.append(piso)

# Guardamos el resultado limpio listo para el bot
with open('pisos_prueba.json', 'w', encoding='utf-8') as f:
    json.dump(lista_pisos, f, ensure_ascii=False, indent=4)

print(f"¡Procesados {len(lista_pisos)} pisos reales con éxito!")