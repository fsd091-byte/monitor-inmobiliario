import os
import requests
import sqlite3
from extractor import obtener_pisos_idealista # O el nombre de tu funcion en extractor.py
from notificador import enviar_alerta_piso      # O el nombre de tu funcion en notificador.py
import extractor
import notificador
import gestor_db

print("--- INICIANDO MONITOR INMOBILIARIO ---")

TARGET_LOCATIONS = [
    "Fuenlabrada", "Getafe", "Móstoles", "Alcorcón", "Pinto", "Parla",
    "San Fernando de Henares", "Coslada", "Torrejón de Ardoz", 
    "Alcalá de Henares", "Ajalvir", "Loeches", "Meco",
    "Azuqueca de Henares", "Alovera", "Guadalajara"
]

EXCLUDE_KEYWORDS = [
    "ocupado", "okupa", "okupado", "sin posesion", "sin posesión", 
    "nuda propiedad", "subasta", "cesion de remate", "cesión de remate",
    "inversor", "alquilado", "local", "loft", "estudio industrial", "nave"
]


def es_propiedad_valida(item):
    # 1. Filtro de tipo de propiedad
    prop_type = str(item.get("propertyType", "")).lower()
    if prop_type and prop_type not in ["flat", "penthouse", "duplex", "piso", "atico", "ático", "homes"]:
        return False

    # 2. Filtro de precio (convierte texto a número si es necesario)
    price = item.get("price")
    if isinstance(price, str):
        try:
            price = float(price.replace(".", "").replace("€", "").strip())
        except ValueError:
            price = None
            
    if price and not (100000 <= price <= 275000):
        return False

    # 3. Palabras clave a excluir
    title = str(item.get("title", "")).lower()
    description = str(item.get("description", "")).lower()
    full_text = f"{title} {description}"

    if 'EXCLUDE_KEYWORDS' in globals():
        for kw in EXCLUDE_KEYWORDS:
            if kw.lower() in full_text:
                return False

    # 4. Comprobación flexible de ubicación
    if 'TARGET_LOCATIONS' in globals() and TARGET_LOCATIONS:
        location_text = f"{item.get('municipality', '')} {item.get('address', '')} {item.get('locationName', '')} {item.get('district', '')}".lower()
        match = any(loc.lower() in location_text for loc in TARGET_LOCATIONS)
        if not match:
            return False

    return True


def ejecutar_proceso():
    print("Buscando ofertas en Apify...")
    inmuebles = extractor.obtener_pisos_idealista()
    print(f"Obtenidos {len(inmuebles)} inmuebles en total.")

    validos = 0
    for item in inmuebles:
        # Imprime la ubicacion detectada para ver como viene de Apify
        muni = item.get("municipality") or item.get("locationName") or item.get("address")
        precio = item.get("price")
        
        if es_propiedad_valida(item):
            validos += 1
            piso_id = item.get("propertyCode") or item.get("id")
            print(f"✅ VÁLIDO: {piso_id} - {muni} - {precio}€")
            notificador.enviar_telegram(item)
            gestor_db.guardar_visto(piso_id)
        else:
            print(f"❌ Descartado: {muni} | Precio: {precio}€ | Tipo: {item.get('propertyType')}")

    print(f"--- TOTAL VALIDOS TRAS FILTROS: {validos} ---")

    print(f"--- TOTAL VALIDOS TRAS FILTROS: {validos} ---")

if __name__ == "__main__":
    ejecutar_proceso()
