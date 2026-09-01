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
    # 1. Filtro de tipo de propiedad (acepta variaciones en ingles y espanol)
    prop_type = str(item.get("propertyType", "")).lower()
    if prop_type and prop_type not in ["flat", "penthouse", "duplex", "atico", "ático", "homes"]:
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

    if hasattr(config, 'EXCLUDE_KEYWORDS'):
        for kw in config.EXCLUDE_KEYWORDS:
            if kw.lower() in full_text:
                return False

    # 4. Comprobación flexible de ubicación
    if hasattr(config, 'TARGET_LOCATIONS') and config.TARGET_LOCATIONS:
        # Construye un texto general con todos los campos de ubicacion que manda Apify
        location_text = f"{item.get('municipality', '')} {item.get('address', '')} {item.get('locationName', '')} {item.get('district', '')}".lower()
        
        # Comprueba si algun municipio objetivo esta contenido en la cadena
        match = any(loc.lower() in location_text for loc in config.TARGET_LOCATIONS)
        if not match:
            return False

    return True


def ejecutar_proceso():
    print("Buscando ofertas en Apify...")
    inmuebles = extractor.obtener_pisos_idealista()
    print(f"Obtenidos {len(inmuebles)} inmuebles en total.")

    validos = 0
    for item in inmuebles:
        if es_propiedad_valida(item):
            validos += 1
            piso_id = item.get("propertyCode") or item.get("id")
            print(f"✅ Piso válido encontrado: {piso_id}")
            if not gestor_db.ya_fue_visto(piso_id):
                print(f"Enviando alerta Telegram para: {piso_id}")
                notificador.enviar_telegram(item)
                gestor_db.guardar_visto(piso_id)

    print(f"--- TOTAL VALIDOS TRAS FILTROS: {validos} ---")

if __name__ == "__main__":
    ejecutar_proceso()
