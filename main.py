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

HABITACIONES_MIN = 2
SUPERFICIE_MIN = 45.0  # metros cuadrados mínimos

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
    "ocupado", "okupado", "sin posesion", "sin posesión",
    "proindiviso", "subasta", "cesion de remate", "cesión de remate",
    "nuda propiedad", "nuda-propiedad", "nudapropiedad",
    "renta antigua", "sin cedula", "sin cédula"
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
    item_id = item.get("id") or item.get("propertyCode") or "Sin-ID"
    precio = item.get("price")
    planta = str(item.get("floor", "")).lower()
    tiene_ascensor = item.get("hasLift", False)
    
    habitaciones = item.get("rooms") or item.get("roomsCount") or item.get("bedrooms", 0)
    superficie = item.get("size") or item.get("builtArea") or item.get("sizeM2") or item.get("surface", 0)
    zona = item.get("zone") or item.get("municipality") or "Madrid"

    # Convertimos todo el objeto JSON a texto plano limpio para escaneo exhaustivo
    texto_completo = quitar_tildes(str(item))

    # 1. Filtro de precio
    if isinstance(precio, (int, float)):
        if not (PRECIO_MIN <= precio <= PRECIO_MAX):
            return False, f"❌ {item_id} | {precio}€ | {superficie}m² | {habitaciones}hab | {zona} -> Precio fuera de rango"
    else:
        return False, f"❌ {item_id} | Sin precio | {zona} -> Precio no disponible"

    # 2. Filtro de superficie mínima
    try:
        superficie_val = float(superficie) if superficie is not None else 0
        if superficie_val < SUPERFICIE_MIN:
            return False, f"❌ {item_id} | {precio}€ | {superficie_val}m² | {habitaciones}hab | {zona} -> Superficie < {SUPERFICIE_MIN}m²"
    except (ValueError, TypeError):
        pass

    # 3. Filtro de habitaciones mínimas
    try:
        hab_val = int(habitaciones) if habitaciones is not None else 0
        if hab_val < HABITACIONES_MIN:
            return False, f"❌ {item_id} | {precio}€ | {superficie}m² | {hab_val}hab | {zona} -> Habitaciones < {HABITACIONES_MIN}"
    except (ValueError, TypeError):
        pass

    # 4. Filtro de ascensor (2ª planta o superior)
    if planta.isdigit() and int(planta) >= 2 and not tiene_ascensor:
        return False, f"❌ {item_id} | {precio}€ | Planta {planta} | {zona} -> Planta alta sin ascensor"

    # 5. Filtro de barrios excluidos
    for barrio in EXCLUDED_NEIGHBORHOODS:
        if barrio in texto_completo:
            return False, f"❌ {item_id} | {precio}€ | {zona} -> Barrio excluido ('{barrio}')"

    # 6. Filtro de palabras clave (nuda propiedad, okupas, subastas, etc.)
    for kw in EXCLUDE_KEYWORDS:
        if kw in texto_completo:
            return False, f"❌ {item_id} | {precio}€ | {zona} -> Término prohibido ('{kw}')"

    # 7. Filtro de ubicación objetivo
    if 'TARGET_LOCATIONS' in globals() and TARGET_LOCATIONS:
        zona_limpia = quitar_tildes(zona)
        if zona_limpia != "madrid":
            coincide = any(quitar_tildes(loc) in zona_limpia for loc in TARGET_LOCATIONS)
            if not coincide:
                return False, f"❌ {item_id} | {precio}€ | {zona} -> Zona no objetivo"

    return True, f"✅ {item_id} | {precio}€ | {superficie}m² | {habitaciones}hab | {zona} -> ACEPTADO"
    
    

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
