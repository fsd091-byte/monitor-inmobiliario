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

# 1. Parámetros de filtrado

PRECIO_MIN = 50000
PRECIO_MAX = 175000
SUPERFICIE_MIN = 45.0
HABITACIONES_MIN = 2

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
    precio = item.get("price")
    planta = str(item.get("floor", "")).lower()
    tiene_ascensor = item.get("hasLift", False)
    
    habitaciones = item.get("rooms") or item.get("roomsCount") or item.get("bedrooms", 0)
    superficie = item.get("size") or item.get("builtArea") or item.get("sizeM2") or item.get("surface", 0)
    zona = item.get("zone") or item.get("municipality") or "Madrid"

    texto_completo = quitar_tildes(str(item))

    # 1. Filtro de precio (50k - 175k)
    if isinstance(precio, (int, float)):
        if not (PRECIO_MIN <= precio <= PRECIO_MAX):
            return False, "Precio fuera de rango"
    else:
        return False, "Precio no disponible"

    # 2. Filtro de superficie mínima (45 m²)
    try:
        superficie_val = float(superficie) if superficie is not None else 0
        if superficie_val < SUPERFICIE_MIN:
            return False, "Superficie insuficiente"
    except (ValueError, TypeError):
        pass

    # 3. Filtro de habitaciones (mínimo 2)
    try:
        hab_val = int(habitaciones) if habitaciones is not None else 0
        if hab_val < HABITACIONES_MIN:
            return False, "Habitaciones insuficientes"
    except (ValueError, TypeError):
        pass

    # 4. Filtro de ascensor (plantas 2ª o superiores)
    if planta.isdigit() and int(planta) >= 2 and not tiene_ascensor:
        return False, "Planta alta sin ascensor"

    # 5. Filtro de barrios excluidos
    for barrio in EXCLUDED_NEIGHBORHOODS:
        if barrio in texto_completo:
            return False, f"Barrio excluido ({barrio})"

    # 6. Filtro de palabras clave (nuda propiedad, okupas, subastas, etc.)
    for kw in EXCLUDE_KEYWORDS:
        if kw in texto_completo:
            return False, f"Término prohibido ({kw})"

    # 7. Ubicación objetivo
    if 'TARGET_LOCATIONS' in globals() and TARGET_LOCATIONS:
        zona_limpia = quitar_tildes(zona)
        if zona_limpia != "madrid":
            coincide = any(quitar_tildes(loc) in zona_limpia for loc in TARGET_LOCATIONS)
            if not coincide:
                return False, "Zona no objetivo"

    return True, "Cumple filtros"
    
    

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

    resultados_apify = obtener_pisos_idealista()  # Usa el nombre exacto de tu función de Apify
    
    inmuebles_aceptados = []

    print("\n" + "="*80)
    print(" 📋 INMUEBLES SELECCIONADOS QUE CUMPLEN TODOS LOS CRITERIOS")
    print("="*80)

    for item in resultados_apify:
        es_valido, motivo = procesar_inmueble(item)
        
        if es_valido:
            inmuebles_aceptados.append(item)
            
            # Extraemos atributos clave para el log limpio
            item_id = item.get("id") or item.get("propertyCode") or "Sin-ID"
            precio = item.get("price", 0)
            superficie = item.get("size") or item.get("builtArea") or item.get("sizeM2") or 0
            habitaciones = item.get("rooms") or item.get("roomsCount") or item.get("bedrooms", 0)
            planta = item.get("floor", "N/A")
            ascensor = "Con ascensor" if item.get("hasLift") else "Sin ascensor"
            zona = item.get("zone") or item.get("municipality") or "Madrid"
            url = item.get("url") or item.get("link") or "Sin URL"

            # Imprime 1 sola línea por piso aceptado
            print(f"🏠 ID: {item_id} | {precio:,.0f}€ | {superficie} m² | {habitaciones} habs | Planta: {planta} ({ascensor}) | Zona: {zona} | Link: {url}")

    print("="*80)
    print(f" Total inmuebles filtrados listos para notificar: {len(inmuebles_aceptados)}")
    print("="*80 + "\n")

def ejecutar_proceso():
    # 1. Cargar base de datos e inmuebles desde Apify
    db = gestor_db()  # O como se llame tu instancia/clase de base de datos
    resultados_apify = obtener_pisos_idealista()  # Ajusta el nombre si tu función se llama diferente

    inmuebles_aceptados = []

    print("\n" + "="*80)
    print(" 📋 INMUEBLES SELECCIONADOS QUE CUMPLEN TODOS LOS CRITERIOS")
    print("="*80)

    for item in resultados_apify:
        es_valido, motivo = procesar_inmueble(item)
        
        if es_valido:
            item_id = str(item.get("id") or item.get("propertyCode") or "")
            
            # Comprobar en la BD si ya se notificó anteriormente
            if db.existe(item_id):
                continue

            inmuebles_aceptados.append(item)
            
            # Formateo de atributos para el log limpio
            precio = item.get("price", 0)
            superficie = item.get("size") or item.get("builtArea") or item.get("sizeM2") or 0
            habitaciones = item.get("rooms") or item.get("roomsCount") or item.get("bedrooms", 0)
            planta = item.get("floor", "N/A")
            ascensor = "Con ascensor" if item.get("hasLift") else "Sin ascensor"
            zona = item.get("zone") or item.get("municipality") or "Madrid"
            url = item.get("url") or item.get("link") or "Sin URL"

            # Imprime 1 sola línea por piso aceptado en la consola
            print(f"🏠 ID: {item_id} | {precio:,.0f}€ | {superficie} m² | {habitaciones} habs | Planta: {planta} ({ascensor}) | Zona: {zona} | Link: {url}")

            # 2. Enviar notificación por Telegram y guardar en BD
            try:
                enviar_notificacion_telegram(item)  # Ajusta al nombre de tu función de Telegram
                db.guardar(item_id)
            except Exception as e:
                print(f"⚠️ Error enviando notificación para ID {item_id}: {e}")

    print("="*80)
    print(f" Total inmuebles nuevos notificados: {len(inmuebles_aceptados)}")
    print("="*80 + "\n")


if __name__ == "__main__":
    ejecutar_proceso()
