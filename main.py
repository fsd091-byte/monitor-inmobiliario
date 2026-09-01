import os
import requests
import sqlite3
from extractor import obtener_pisos_idealista # O el nombre de tu funcion en extractor.py
from notificador import enviar_alerta_piso      # O el nombre de tu funcion en notificador.py
import extractor
import notificador
import gestor_db
import json

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
    # 1. Filtro de tipo de propiedad (viene en 'title')
    tipo = str(item.get("title", "")).lower().strip()
    tipos_validos = ["flat", "piso", "penthouse", "duplex", "atico", "ático", "house", "chalet"]
    if tipo and tipo not in tipos_validos:
        return False

    # 2. Filtro de precio (entre 100k€ y 275k€)
    price = item.get("price")
    if isinstance(price, (int, float)):
        if not (100000 <= price <= 275000):
            return False

    # 3. Filtro de ascensor para plantas altas (ej. floor >= 2)
    floor = str(item.get("floor", "")).lower()
    has_lift = item.get("hasLift", False)
    if floor.isdigit() and int(floor) >= 2 and not has_lift:
        return False

    # 4. Filtro de ubicación (viene en 'zone')
    if 'TARGET_LOCATIONS' in globals() and TARGET_LOCATIONS:
        zone = str(item.get("zone", "")).lower()
        match = any(loc.lower() in zone for loc in TARGET_LOCATIONS)
        if not match:
            return False

    return True

def ejecutar_proceso():
    print("Buscando ofertas en Apify...")
    inmuebles = extractor.obtener_pisos_idealista()
    print(f"Obtenidos {len(inmuebles)} inmuebles en total.")

    # Resto de tu bucle...
    
    validos = 0
    for item in inmuebles:
        
        # IMPRIMIR EL PRIMER ANUNCIO PARA VER SUS CAMPOS REALES
        print("--- ESTRUCTURA DEL PRIMER INMUEBLE ---")
        print(json.dumps(inmuebles[0], indent=2, ensure_ascii=False))
        print("--------------------------------------")
        
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
