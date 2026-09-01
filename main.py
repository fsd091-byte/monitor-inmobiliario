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
