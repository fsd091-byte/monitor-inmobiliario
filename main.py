import os
import requests
import sqlite3
from extractor import obtener_pisos_idealista # O el nombre de tu funcion en extractor.py
from notificador import enviar_alerta_piso      # O el nombre de tu funcion en notificador.py
import extractor
import notificador
import gestor_db
import json
import unicodedata

# print("--- INICIANDO MONITOR INMOBILIARIO ---")

TARGET_LOCATIONS = [
    # Corredor del Henares y Guadalajara
    "alcalá de henares", "alcala de henares",
    "torrejón de ardoz", "torrejon de ardoz",
    "coslada", "san fernando de henares",
    "rivas", "rivas-vaciamadrid",
    "guadalajara", "azuqueca", "azuqueca de henares",
    
    # Sur de Madrid
    "getafe", "móstoles", "mostoles", 
    "fuenlabrada", "alcorcón", "alcorcon", "leganés", "leganes",
    
    # Capitales de provincia cercanas
    "ávila", "avila",
    
    # Valor general de la provincia devuelto por Apify
    "madrid"
]

# Lista de barrios o zonas a excluir (en minúsculas y sin tildes para simplificar)
EXCLUDED_NEIGHBORHOODS = [
    "san cristobal",
    "la canada real", "canada real",
    "el pozo del tio raimundo", "pozo del tio raimundo",
    "entrrevias", "entrevias"
    "villaverde","villaverde"
]

EXCLUDE_KEYWORDS = [
    "ocupado", "okupa", "okupado", "sin posesion", "sin posesión", 
    "nuda propiedad", "subasta", "cesion de remate", "cesión de remate",
    "inversor", "alquilado", "local", "loft", "estudio industrial", "nave"
]



def quitar_tildes(texto):
    if not texto:
        return ""
    # Convierte a minúsculas y elimina tildes/acentos
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).lower()

def procesar_inmueble(item):
    precio = item.get("price")
    planta = str(item.get("floor", "")).lower()
    tiene_ascensor = item.get("hasLift", False)
    
    # Concatenamos título, descripción, zona y la propia URL de Idealista
    texto_completo = quitar_tildes(
        f"{item.get('title', '')} {item.get('description', '')} {item.get('zone', '')} {item.get('url', '')}"
    )

    # 1. Filtro de precio (50k - 175k)
    if isinstance(precio, (int, float)):
        if not (50000 <= precio <= 175000):
            return False, f"Precio fuera de rango ({precio}€)"
    else:
        return False, "Precio no disponible"

    # 2. Filtro de ascensor (plantas 2ª o superiores)
    if planta.isdigit() and int(planta) >= 2 and not tiene_ascensor:
        return False, f"Planta {planta}ª sin ascensor"

    # 3. Filtro de barrios excluidos (busca en todo el contenido)
    for barrio in EXCLUDED_NEIGHBORHOODS:
        if barrio in texto_completo:
            return False, f"Barrio excluido por riesgo ('{barrio}')"

    # 4. Filtro de palabras clave (okupas, subastas, etc.)
    if 'EXCLUDE_KEYWORDS' in globals():
        for kw in EXCLUDE_KEYWORDS:
            if quitar_tildes(kw) in texto_completo:
                return False, f"Aviso de riesgo/okupación ('{kw}')"

    # 5. Filtro de ubicación objetivo
    if 'TARGET_LOCATIONS' in globals() and TARGET_LOCATIONS:
        zona_limpia = quitar_tildes(item.get('zone', ''))
        if zona_limpia != "madrid":
            coincide = any(quitar_tildes(loc) in zona_limpia for loc in TARGET_LOCATIONS)
            if not coincide:
                return False, f"Zona '{item.get('zone')}' no coincide con TARGET_LOCATIONS"

    return True, "Cumple todos los filtros"


def es_propiedad_valida(item):
    piso_id = item.get("id") or item.get("url")
    
    # 1. Filtro de precio
    precio = item.get("price")
    if isinstance(precio, (int, float)):
        if not (50000 <= precio <= 175000):
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
