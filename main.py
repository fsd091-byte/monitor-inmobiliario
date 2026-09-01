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
    piso_id = item.get("id") or item.get("url")
    
    # 1. Filtro de precio
    precio = item.get("price")
    if isinstance(precio, (int, float)):
        if not (100000 <= precio <= 275000):
            print(f"  └─ Descartado ID {piso_id}: Precio fuera de rango ({precio}€)")
            return False

    # 2. Filtro de ascensor
    planta = str(item.get("floor", "")).lower()
    tiene_ascensor = item.get("hasLift", False)
    if planta.isdigit() and int(planta) >= 2 and not tiene_ascensor:
        print(f"  └─ Descartado ID {piso_id}: Planta {planta} sin ascensor")
        return False

    # 3. Palabras clave a excluir
    title = str(item.get("title", "")).lower()
    description = str(item.get("description", "")).lower()
    full_text = f"{title} {description}"

    if 'EXCLUDE_KEYWORDS' in globals() and EXCLUDE_KEYWORDS:
        for kw in EXCLUDE_KEYWORDS:
            if kw.lower() in full_text:
                print(f"  └─ Descartado ID {piso_id}: Palabra excluida '{kw}'")
                return False

    # 4. Filtro de ubicación
    if 'TARGET_LOCATIONS' in globals() and TARGET_LOCATIONS:
        zona = str(item.get("zone", "")).lower()
        if zona and zona != "madrid":
            coincide = any(loc.lower() in zona for loc in TARGET_LOCATIONS)
            if not coincide:
                return False

    return True

def ejecutar_proceso():
    print("--- INICIANDO MONITOR INMOBILIARIO ---")
    inmuebles = extractor.obtener_pisos_idealista()
    print(f"Obtenidos {len(inmuebles)} inmuebles en total.\n")

    validos = 0
    for item in inmuebles:
        piso_id = item.get("id") or item.get("url")
        es_valido, motivo = procesar_inmueble(item)
        
        if es_valido:
            validos += 1
            if not gestor_db.ya_fue_visto(piso_id):
                try:
                    notificador.enviar_alerta_piso(item)
                    print(f"✓ Alerta enviada a tu Telegram con éxito para ID {piso_id}.")
                except Exception as e:
                    print(f"   └─ ⚠️ Error al enviar Telegram: {e}")
                
                # Envolver la persistencia en DB para evitar que falle el script
                try:
                    gestor_db.guardar_visto(piso_id)
                except Exception as e:
                    print(f"   └─ ⚠️ Error al guardar en la BD ({piso_id}): {e}")
            else:
                print(f"ℹ️ El inmueble {piso_id} ya fue notificado previamente.")
        else:
            print(f"❌ DESCARTADO {piso_id}: {motivo}")

    print(f"\n--- RESUMEN: {validos} de {len(inmuebles)} inmuebles pasaron los filtros ---")


if __name__ == "__main__":
    ejecutar_proceso()
