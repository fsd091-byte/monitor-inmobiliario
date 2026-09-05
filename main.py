import os
import requests
import sqlite3
import json
import unicodedata
import re
import sys

from extractor import obtener_pisos_desde_db, obtener_pisos_idealista, obtener_pisos_desde_json
from notificador import enviar_alerta_piso
import gestor_db
import notificador

# 1. Parámetros de filtrado numérico y zonas generales
PRECIO_MIN = 50000
PRECIO_MAX = 975000
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

def quitar_tildes(texto):
    if not texto:
        return ""
    # Convierte a minúsculas y elimina tildes/acentos
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).lower()

def limpiar_total(texto):
    if not texto:
        return ""
    texto_base = quitar_tildes(str(texto))
    # Elimina espacios, guiones y cualquier carácter que no sea letra o número
    return re.sub(r'[^a-z0-9]', '', texto_base)

def procesar_inmueble(item):
    # 1. Extracción de campos clave del diccionario
    item_id = str(item.get('propertyCode', 'N/A'))
    precio = item.get('price', 0)
    superficie = item.get('size', 0)
    habitaciones = item.get('rooms', 0)
    planta = str(item.get('floor', '')).lower().strip()
    zona = str(item.get('zone', '')).lower()
    
    # Extracción de campos de texto específicos y texto global para análisis profundo
    texto_global = str(item).lower()
    subtitulo = str(item.get('subTitle', '')).lower()
    comentario = str(item.get('comment', '')).lower()
    features = str(item.get('features', '')).lower()
    
    # Unificamos todo el texto sospechoso para blindar la búsqueda
    texto_completo = f"{texto_global} {subtitulo} {comentario} {features}".replace("*", " ")

    # =========================================================================
    # 2. FILTROS DE TEXTO CRÍTICOS (Ocupados, alquilados, nuda propiedad, etc.)
    # =========================================================================
    terminos_prohibidos = [
        "nuda propiedad", 
        "alquilada", 
        "alquilado", 
        "ocupada", 
        "ocupado", 
        "okupa", 
        "no visitable",
        "sin posesión",
        "solo inversores", 
        "exclusivamente inversores",
        "rentabilidad"
    ]
    
    for termino in terminos_prohibidos:
        if termino in texto_completo:
            return False, f"Término prohibido estricto: {termino}"

    # =========================================================================
    # 3. FILTRO DE BARRIO / ZONA: Excluir Puente de Vallecas
    # =========================================================================
    if "vallecas" in zona or "puente de vallecas" in zona:
        return False, "Descartado: Barrio Puente de Vallecas excluido"

    # =========================================================================
    # 4. FILTRO DE PLANTA: Quitar bajos / plantas bajas
    # =========================================================================
    if planta in ['bj', 'bajo', '0', 'semisótano', 'ss']:
        return False, "Descartado: Planta baja / bajo no deseado"

    # =========================================================================
    # 5. FILTROS NUMÉRICOS (Precio, superficie, habitaciones)
    # =========================================================================
    if precio < PRECIO_MIN or precio > PRECIO_MAX:
        return False, "Fuera de rango de precio"

    if superficie < SUPERFICIE_MIN:
        return False, "Superficie insuficiente"
        
    if habitaciones < HABITACIONES_MIN:
        return False, "Habitaciones insuficientes"

    # Si supera todos los filtros, se aprueba
    return True, "Cumple todos los filtros"
    
def ejecutar_proceso():

    # 1. Inicializar la base de datos y obtener inmuebles
    gestor_db.inicializar_base_datos()
    resultados_apify = obtener_pisos_desde_json()
    
    inmuebles_aceptados = []

    print("\n" + "="*80)
    print(" 📋 INMUEBLES SELECCIONADOS QUE CUMPLEN TODOS LOS CRITERIOS v2")
    print("="*80)

    for item in resultados_apify:
        
        item_id = str(item.get("id") or item.get("propertyCode") or "")

        # Comprobar en la BD si ya se notificó anteriormente para saltarlo
        if gestor_db.ya_fue_visto(item_id):
            continue
            
        # Evaluar contra las reglas de negocio y filtros
        es_valido, motivo = procesar_inmueble(item)
        if not es_valido:
            # Opcional: puedes descomentar la línea de abajo si quieres ver en consola por qué se descarta cada uno
            # print(f"❌ Descartado ID {item_id}: {motivo}")
            continue
        
        print(f"✅ ¡APROBADO! ID {item_id}")
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
            print("✓ Alerta enviada a tu Telegram con éxito.")
            print(f"  └─ Registro guardado en BD: {item_id}")
        except Exception as e:
            print(f"⚠️ Error enviando notificación para ID {item_id}: {e}")

    print("="*80)
    print(f" Total inmuebles nuevos notificados: {len(inmuebles_aceptados)}")
    print("="*80 + "\n")

if __name__ == "__main__":
    ejecutar_proceso()
