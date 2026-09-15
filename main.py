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
PRECIO_MIN = 75000
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
    "Zaragoza",
    
    # Sur de Madrid
    "getafe", "móstoles", "mostoles", 
    "fuenlabrada", "alcorcón", "alcorcon", "leganés", "leganes",
    
    # Capitales de provincia cercanas
    "ávila", "avila","Zaragoza","zaragoza",
    
    # Valor general de la provincia devuelto por Apify
    "madrid"
]

def quitar_tildes(texto):
    if not texto:
        return ""
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto))
        if unicodedata.category(c) != 'Mn'
    ).lower()

def limpiar_total(texto):
    if not texto:
        return ""
    texto_base = quitar_tildes(str(texto))
    return re.sub(r'[^a-z0-9]', '', texto_base)

def procesar_inmueble(item):
    item_id = str(item.get('propertyCode') or item.get('id') or item.get('url', 'N/A'))
    precio = item.get('price', 0)
    superficie = item.get('size', 0)
    habitaciones = int(item.get('rooms', 2))
    baños = int(item.get('bathrooms', item.get('baths', 1)))
    planta = str(item.get('floor', '')).lower().strip()
    zona = str(item.get('zone', '')).lower()
    municipality = str(item.get('municipality', '')).lower()
    province = str(item.get('province', '')).lower()
    tiene_ascensor = item.get('hasLift', True)
    
    # =========================================================================
    # 1. FILTROS NUMÉRICOS GLOBALES Y DE ATRIBUTOS BÁSICOS
    # =========================================================================
    if precio < PRECIO_MIN or precio > PRECIO_MAX:
        return False, "Fuera de rango de precio global"

    if superficie < SUPERFICIE_MIN:
        return False, "Superficie insuficiente"
        
    if habitaciones < HABITACIONES_MIN:
        return False, "Habitaciones insuficientes"

    # =========================================================================
    # 2. FILTROS DE LOCALIZACIÓN
    # =========================================================================
    ubicacion_inmueble = f"{zona} {municipality} {province}".lower()
    
    if not any(loc in ubicacion_inmueble for loc in TARGET_LOCATIONS):
        return False, "Descartado: Fuera de las ubicaciones objetivo"

    # =========================================================================
    # 3. EXTRACCIÓN Y FILTROS DE TEXTO (Términos prohibidos)
    # =========================================================================
    textos_extraidos = []
    for v in item.values():
        if isinstance(v, str) and not v.startswith('http'):
            textos_extraidos.append(v)
        elif isinstance(v, dict):
            for sub_v in v.values():
                if isinstance(sub_v, str) and not sub_v.startswith('http'):
                    textos_extraidos.append(sub_v)
                    
    texto_bruto = " ".join(textos_extraidos).replace("*", " ")
    texto_completo = quitar_tildes(texto_bruto).lower()

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

    zonas_prohibidas = ["san cristobal", "vallecas", "puente de vallecas", "entrevias"]
    if any(z in texto_completo for z in zonas_prohibidas): 
        return False, "Descartado: Zona prohibida detectada en el texto"

    print(f"📄 [APROBADO] ID {item_id} ({len(texto_completo)} chars): {texto_completo[:100]}...")
    return True, "Cumple todos los filtros"
    

def ejecutar_proceso():

    import os
    
    print("📍 Directorio actual de ejecución:", os.getcwd())
    print("📍 Ruta absoluta de la BD que usa gestor_db:", gestor_db.NOMBRE_DB)

    # 1. Inicializar la base de datos y obtener inmuebles
    gestor_db.inicializar_base_datos()
    
    resultados_apify = obtener_pisos_desde_json("pisos_inversion.json")
    
    # Eliminar duplicados exactos dentro del JSON usando un set
    vistos_en_json = set()
    resultados_unicos = []
    for item in resultados_apify:
        p_id = str(item.get("propertyCode") or item.get("id") or item.get("url", ""))
        if p_id and p_id not in vistos_en_json:
            vistos_en_json.add(p_id)
            resultados_unicos.append(item)
    resultados_apify = resultados_unicos

    inmuebles_aceptados = []

    print("\n" + "="*80)
    print(" 📋 INMUEBLES SELECCIONADOS QUE CUMPLEN TODOS LOS CRITERIOS v2")
    print("="*80)

    for item in resultados_apify:
        
        # 1. Extracción unificada y robusta del ID
        item_id = str(item.get("propertyCode") or item.get("id") or item.get("url", ""))

        if not item_id or item_id == 'N/A':
            continue

        # 2. Comprobación crítica PRIMERO: Si ya está en la BD, se descarta al instante
        if gestor_db.ya_fue_visto(item_id):
            continue
            
        # 3. SEGUNDO: Evaluar contra las reglas de negocio y filtros
        es_valido, motivo = procesar_inmueble(item)
        if not es_valido:
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

        print(f"🏠 ID: {item_id} | {precio:,.0f}€ | {superficie} m² | {habitaciones} habs | Planta: {planta} ({ascensor}) | Zona: {zona} | Link: {url}")
         
        # 4. Guardar en BD primero y después enviar la alerta (Sin try/except para ver el error exacto si falla)
        gestor_db.guardar_piso_visto(item_id, titulo, precio, zona)
        enviar_alerta_piso(item)

    print("="*80)
    print(f" Total inmuebles nuevos notificados: {len(inmuebles_aceptados)}")
    print("="*80 + "\n")

if __name__ == "__main__":
    ejecutar_proceso()
