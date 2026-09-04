import os
import requests
import sqlite3
from extractor import obtener_pisos_idealista 
from notificador import enviar_alerta_piso
import extractor
import notificador
import gestor_db
import json
import unicodedata
from extractor import obtener_pisos_desde_db, obtener_pisos_idealista

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
    "entrrevias", "entrevias",
    "villaverde"
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


import re

def limpiar_total(texto):
    if not texto:
        return ""
    # Quita tildes y pasa a minúsculas
    texto_base = ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).lower()
    # Elimina espacios, guiones y cualquier carácter que no sea letra o número
    return re.sub(r'[^a-z0-9]', '', texto_base)

import sys

def procesar_inmueble(item):
    precio = item.get("price")
    planta = str(item.get("floor", "")).lower()
    tiene_ascensor = item.get("hasLift", False)
    
    habitaciones = item.get("rooms") or item.get("roomsCount") or item.get("bedrooms", 0)
    superficie = item.get("size") or item.get("builtArea") or item.get("sizeM2") or item.get("surface", 0)
    zona = item.get("zone") or item.get("municipality") or "Madrid"

    features = item.get("features", [])
    tags = item.get("tags", [])
    sub_type = item.get("subType", "")
    property_type = item.get("propertyType", "")
    
    item_id_actual = str(item.get("id") or item.get("propertyCode") or "")

    # CHIVATO FORZADO: Si coincide con el piso o queremos ver los IDs que pasan
    if item_id_actual == "11219507":
        print(f"\n[CHIVATO ENCONTRADO] ID 11219507 detectado:", flush=True)
        print(f" - Features: {features}", flush=True)
        print(f" - Tags: {tags}", flush=True)
        print(f" - SubType: {sub_type}", flush=True)
        print(f" - Objeto completo: {item}\n", flush=True)

    texto_completo = limpiar_total(f"{str(item)} {str(features)} {str(tags)} {sub_type} {property_type}")

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
        if limpiar_total(barrio) in texto_completo:
            return False, f"Barrio excluido ({barrio})"

    # 6. Filtro de palabras clave
    for kw in EXCLUDE_KEYWORDS:
        if limpiar_total(kw) in texto_completo:
            return False, f"Término prohibido ({kw})"

    # 7. Ubicación objetivo
    if 'TARGET_LOCATIONS' in globals() and TARGET_LOCATIONS:
        zona_limpia = quitar_tildes(zona)
        if zona_limpia != "madrid":
            coincide = any(quitar_tildes(loc) in zona_limpia for loc in TARGET_LOCATIONS)
            if not coincide:
                return False, "Zona no objetivo"

    return True, "Cumple filtros"




def ejecutar_proceso():
    # 1. Inicializar la base de datos y obtener inmuebles de Apify
    gestor_db.inicializar_base_datos()
    # resultados_apify = obtener_pisos_idealista()
    # Usa esto mientras estemos probando con la base de datos histórica:
    resultados_apify = obtener_pisos_desde_db()

    inmuebles_aceptados = []

    print("\n" + "="*80)
    print(" 📋 INMUEBLES SELECCIONADOS QUE CUMPLEN TODOS LOS CRITERIOS v2")
    print("="*80)

    for item in resultados_apify:

        es_valido, motivo = procesar_inmueble(item)
        
        if not es_valido:
            print(f"❌ Descartado ID {item.get('id', 'N/A')}: {motivo}")
            continue
            
        print(f"✅ ¡APROBADO! ID {item.get('id', 'N/A')}")
        inmuebles_aceptados.append(item)
        
        if es_valido:
            item_id = str(item.get("id") or item.get("propertyCode") or "")   
            

       
            
            # Comprobar en la BD si ya se notificó anteriormente
            # if gestor_db.ya_fue_visto(item_id):
            #    continue

            inmuebles_aceptados.append(item)
            
            # Extraer atributos para el log y la BD
            precio = item.get("price", 0)
            superficie = item.get("size") or item.get("builtArea") or item.get("sizeM2") or 0
            habitaciones = item.get("rooms") or item.get("roomsCount") or item.get("bedrooms", 0)
            planta = item.get("floor", "N/A")
            ascensor = "Con ascensor" if item.get("hasLift") else "Sin ascensor"
            zona = item.get("zone") or item.get("municipality") or "Madrid"
            titulo = item.get("title", "Sin título")
            url = item.get("url") or item.get("link") or "Sin URL"

            # Imprime 1 sola línea por piso aceptado en la consola
            print(f"🏠 ID: {item_id} | {precio:,.0f}€ | {superficie} m² | {habitaciones} habs | Planta: {planta} ({ascensor}) | Zona: {zona} | Link: {url}")
           
                  
            # 2. Enviar notificación por Telegram y guardar en BD
            try:
                enviar_alerta_piso(item)
                gestor_db.guardar_piso_visto(item_id, titulo, precio, zona)
            except Exception as e:
                print(f"⚠️ Error enviando notificación para ID {item_id}: {e}")

    print("="*80)
    print(f" Total inmuebles nuevos notificados: {len(inmuebles_aceptados)}")
    print("="*80 + "\n")


if __name__ == "__main__":
    ejecutar_proceso()
