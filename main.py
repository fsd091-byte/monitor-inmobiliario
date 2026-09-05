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
from extractor import obtener_pisos_desde_json, obtener_pisos_idealista

# 1. Parámetros de filtrado
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
    "San Cristóbal",
    
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
    "ocupado", "okupado", "sin posesion", "sin posesión", "Ocupada ilegalmente","Ocupada","OCUPADO",
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
    # 1. Extracción de campos clave del diccionario
    item_id = str(item.get('propertyCode', 'N/A'))
    precio = item.get('price', 0)
    superficie = item.get('size', 0)
    habitaciones = item.get('rooms', 0)
    planta = str(item.get('floor', '')).lower().strip()
    tiene_ascensor = item.get('hasLift', False)
    zona = str(item.get('zone', '')).lower()
    
    # Texto global para búsqueda de términos prohibidos (títulos, descripciones, subtítulos, etc.)
    texto_global = str(item).lower()

    # =========================================================================
    # 2. FILTROS DE TEXTO CRÍTICOS (Nuda propiedad, alquilada, ocupada, inversores)
    # =========================================================================
    terminos_prohibidos = [
        "nuda propiedad", 
        "alquilada", 
        "alquilado", 
        "ocupada", 
        "ocupado", 
        "okupa", 
        "solo inversores", 
        "exclusivamente inversores",
        "rentabilidad"
    ]
    
    for termino in terminos_prohibidos:
        if termino in texto_global:
            return False, f"Término prohibido estricto: {termino}"

    # =========================================================================
    # 3. FILTRO DE BARRIO: Excluir Puente de Vallecas
    # =========================================================================
    if "vallecas" in zona or "puente de vallecas" in zona:
        return False, "Descartado: Barrio Puente de Vallecas excluido"

    # =========================================================================
    # 4. FILTRO DE PLANTA: Quitar bajos / plantas bajas (si aplica)
    # =========================================================================
    # Si 'planta' es 'bj', 'bajo' o '0', lo descartamos con esta regla:
    if planta in ['bj', 'bajo', '0', 'semisótano', 'ss']:
        return False, "Descartado: Planta baja / bajo no deseado"

    # =========================================================================
    # 5. TUS OTROS FILTROS NUMÉRICOS (Precio, superficie, habitaciones, etc.)
    # =========================================================================
    # Ejemplo de validaciones estándar (ajústalas a tus límites de siempre):
    if superficie < 45:
        return False, "Superficie insuficiente"
        
    if habitaciones < 2:
        return False, "Habitaciones insuficientes"

    # Si pasa todas las murallas, se aprueba
    return True, "Cumple todos los filtros"
    
    
def ejecutar_proceso():



    # 1. Inicializar la base de datos y obtener inmuebles de Apify
    gestor_db.inicializar_base_datos()
    
    resultados_apify = obtener_pisos_desde_json()
    
    print("TIPO DE DATO:", type(resultados_apify[0]))
    print("EJEMPLO PLANO:", str(resultados_apify[0])[:200])

    inmuebles_aceptados = []

    print("\n" + "="*80)
    print(" 📋 INMUEBLES SELECCIONADOS QUE CUMPLEN TODOS LOS CRITERIOS v2")
    print("="*80)

    for item in resultados_apify:
        
        if item in ["112201296", "112195107"]:
            print(f"🔍 [CHIVATO TEXTO {item_id_actual}]: {texto_bruto_global[:400]}...")

        if item == "112201296":
            print(f"🚨 [INSPECCIÓN FORENSE 112201296]: {item}")  
    
        es_valido, motivo = procesar_inmueble(item)
        
        if not es_valido:
            print(f"❌ Descartado ID {item.get('id', 'N/A')}: {motivo}")
            continue
            
        item_id = str(item.get("id") or item.get("propertyCode") or "")

        # Comprobar en la BD si ya se notificó anteriormente para saltarlo
        if gestor_db.ya_fue_visto(item_id):
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
        except Exception as e:
            print(f"⚠️ Error enviando notificación para ID {item_id}: {e}")

    print("="*80)
    print(f" Total inmuebles nuevos notificados: {len(inmuebles_aceptados)}")
    print("="*80 + "\n")
    

if __name__ == "__main__":
    ejecutar_proceso()
