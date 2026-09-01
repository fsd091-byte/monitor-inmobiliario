import os
import requests
import sqlite3
from extractor import obtener_pisos_idealista # O el nombre de tu funcion en extractor.py
from notificador import enviar_telegram      # O el nombre de tu funcion en notificador.py
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
    property_type = item.get("propertyType", "").lower()
    if property_type not in ["flat", "penthouse", "duplex"]:
        return False

    price = item.get("price", 0)
    if not (100000 <= price <= 275000):  # Prueba con 275k
        return False

    rooms = item.get("rooms", 0)
    if rooms < 1:
        return False

    floor = item.get("floor", "")
    has_lift = item.get("hasLift", False)
    try:
        floor_num = int(floor)
        if floor_num >= 2 and not has_lift:
            return False
    except ValueError:
        pass

    title = item.get("title", "").lower()
    description = item.get("description", "").lower()
    full_text = f"{title} {description}"

    for kw in EXCLUDE_KEYWORDS:
        if kw in full_text:
            return False

    return True

def ejecutar_proceso():
    print("Buscando ofertas en Apify de la funcion obtener_pisos_idealista()...")
    inmuebles = obtener_pisos_idealista() # Llama a la funcion de tu extractor.py
    print(f"Obtenidos {len(inmuebles)} inmuebles en total.")

    for item in inmuebles:
        if es_propiedad_valida(item):
            piso_id = item.get("propertyCode") or item.get("id")
            
            # Comprobacion de vistos
            if not gestor_db.ya_fue_visto(piso_id):
                print(f"Enviando alerta para inmueble: {piso_id}")
                enviar_telegram(item)
                gestor_db.guardar_visto(piso_id)

if __name__ == "__main__":
    ejecutar_proceso()
