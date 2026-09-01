import os
import requests
import sqlite3

# --- LISTA DE MUNICIPIOS OBJETIVO ---
TARGET_LOCATIONS = [
    # Sur / Suroeste de Madrid
    "Fuenlabrada", "Getafe", "Móstoles", "Alcorcón", "Pinto", "Parla",
    # Corredor del Henares (Madrid)
    "San Fernando de Henares", "Coslada", "Torrejón de Ardoz", 
    "Alcalá de Henares", "Ajalvir", "Loeches", "Meco",
    # Corredor del Henares / Guadalajara
    "Azuqueca de Henares", "Alovera", "Guadalajara"
]

# --- PALABRAS CLAVE A EXCLUIR EN TÍTULO / DESCRIPCIÓN ---
EXCLUDE_KEYWORDS = [
    "ocupado", "okupa", "okupado", "sin posesion", "sin posesión", 
    "nuda propiedad", "subasta", "cesion de remate", "cesión de remate",
    "inversor", "alquilado", "local", "loft", "estudio industrial", "nave"
]

def es_propiedad_valida(item):
    """Aplica las reglas de filtrado sobre cada inmueble encontrado."""
    
    # 1. Filtro de Tipo de Propiedad (Solo Pisos)
    property_type = item.get("propertyType", "").lower()
    if property_type not in ["flat", "penthouse", "duplex"]:
        return False

    # 2. Filtro de Precio (entre 100.000 € y 175.000 €)
    price = item.get("price", 0)
    if not (10000 <= price <= 375000):
        return False

    # 3. Filtro de Habitaciones (mínimo 1)
    rooms = item.get("rooms", 0)
    if rooms < 1:
        return False

    # 4. Filtro de Ascensor (Obligatorio a partir de 2ª planta; opcional en Bajo/1º)
    floor = item.get("floor", "")
    has_lift = item.get("hasLift", False)
    
    # Si la planta es numérica (2º o superior) y no tiene ascensor, se descarta
    try:
        floor_num = int(floor)
        if floor_num >= 2 and not has_lift:
            return False
    except ValueError:
        # En el caso de "bj" (bajo), "en" (entreplanta), "st" (sótano) o "1", no exige ascensor
        pass

    # 5. Filtro de Exclusión de Palabras Clave (Ocupados, Nuda Propiedad, Locales, etc.)
    title = item.get("title", "").lower()
    description = item.get("description", "").lower()
    full_text = f"{title} {description}"

    for kw in EXCLUDE_KEYWORDS:
        if kw in full_text:
            return False

    # 6. Filtro de Ubicación
    municipality = item.get("municipality", "")
    if municipality not in TARGET_LOCATIONS:
        # Si la API devuelve la ubicación en 'address' o 'town'
        address = item.get("address", "")
        if not any(loc.lower() in address.lower() or loc.lower() in municipality.lower() for loc in TARGET_LOCATIONS):
            return False

    return True

# --- INSTRUCCIONES DE USO ---
# Integra esta función 'es_propiedad_valida(item)' dentro de tu bucle de procesamiento
# de resultados de la API antes de guardar en SQLite o enviar la alerta por Telegram.
