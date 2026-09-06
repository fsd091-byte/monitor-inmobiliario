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
    
    # Sur de Madrid
    "getafe", "móstoles", "mostoles", 
    "fuenlabrada", "alcorcón", "alcorcon", "leganés", "leganes",
    
    # Capitales de provincia cercanas
    "ávila", "avila","Zaragoza","zaragoza"
    
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
    item_id = str(item.get('propertyCode') or item.get('id') or 'N/A')
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
    # 2. FILTROS DE LOCALIZACIÓN Y TECTOS DE PRECIO ESPECÍFICOS POR ZONA
    # - Ávila: < 100.000 €
    # - Guadalajara / Azuqueca: < 160.000 €
    # - Zaragoza: < 140.000 €
    # =========================================================================
    ubicacion_inmueble = f"{zona} {municipality} {province}".lower()
    
    if any(loc in ubicacion_inmueble for loc in ["ávila", "avila"]):
        if precio >= 100000:
            return False, "Descartado: Ávila con precio >= 100.000€"
    elif any(loc in ubicacion_inmueble for loc in ["guadalajara", "azuqueca"]):
        if precio >= 160000:
            return False, "Descartado: Guadalajara con precio >= 160.000€"
    elif "zaragoza" in ubicacion_inmueble:
        if precio >= 140000:
            return False, "Descartado: Zaragoza con precio >= 140.000€"

    # Validar que pertenezca a las zonas objetivo generales
    if not any(loc in ubicacion_inmueble for loc in TARGET_LOCATIONS):
        return False, "Descartado: Fuera de las ubicaciones objetivo"

    # =========================================================================
    # 3. REGLAS DE HABITACIONES, PRECIO GENERAL Y BAÑOS
    # - 2 habitaciones o menos: Máximo 150.000 €
    # - 3 habitaciones o más: Hasta los 175.000 € (o el límite zonal menor)
    # - Más de 2 habitaciones: Exigir mínimo 2 baños
    # =========================================================================
    if habitaciones <= 2 and precio > 150000:
        return False, "Descartado: <= 2 habitaciones y precio > 150.000€"

    if habitaciones > 2 and baños < 2:
        return False, "Descartado: > 2 habitaciones pero menos de 2 baños"

    # =========================================================================
    # 4. FILTRO DE PLANTA Y ASCENSOR
    # - Descartar bajos / semisótanos siempre
    # - Sin ascensor: Solo se permite el primer piso
    # =========================================================================
    if planta in ['bj', 'bajo', '0', 'semisótano', 'ss']:
        return False, "Descartado: Planta baja / bajo no deseado"

    plantas_primer_piso = ['1', '1º', 'primero']
    if not tiene_ascensor and planta not in plantas_primer_piso:
        return False, "Descartado: Sin ascensor y no es un primer piso"

    # =========================================================================
    # 5. EXTRACCIÓN Y FILTROS DE TEXTO (Términos prohibidos y zonas excluidas)
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

    zonas_prohibidas = ["san cristobal", "vallecas", "puente de vallecas", "villaverde", "entrevias"]
    if any(z in texto_completo for z in zonas_prohibidas): 
        return False, "Descartado: Zona prohibida detectada en el texto"

    print(f"📄 [APROBADO] ID {item_id} ({len(texto_completo)} chars): {texto_completo[:100]}...")
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
        #if gestor_db.ya_fue_visto(item_id):
        #    continue
            
        # Evaluar contra las reglas de negocio y filtros
        es_valido, motivo = procesar_inmueble(item)
        if not es_valido:
            # Traza de descartados comentada para mantener la consola limpia
            # print(f"❌ Descartado ID {item_id}: {motivo}")
            continue
        
        print(f"✅ ¡APROBADO! ID {item_id}")
        inmuebles_aceptados.append(item)
        
        # Extraemos atributos y la descripción completa para traza
        precio = item.get("price", 0)
        superficie = item.get("size") or item.get("builtArea") or item.get("sizeM2") or 0
        habitaciones = item.get("rooms") or item.get("roomsCount") or item.get("bedrooms", 0)
        planta = item.get("floor", "N/A")
        ascensor = "Con ascensor" if item.get("hasLift") else "Sin ascensor"
        zona = item.get("zone") or item.get("municipality") or "Madrid"
        descripcion_completa = item.get("description", "Sin descripción")
        url = item.get("url") or item.get("link") or "Sin URL"

        print(f"🏠 ID: {item_id} | {precio:,.0f}€ | {superficie} m² | {habitaciones} habs | Planta: {planta} ({ascensor}) | Zona: {zona}")
        print(f"📄 Descripción analizada: {descripcion_completa[:150]}...")
        print(f"🔗 Link: {url}")
         
        # 2. Enviar notificación por Telegram y guardar en BD
        try:
            enviar_alerta_piso(item)
            gestor_db.guardar_piso_visto(item_id, item.get("title", "Sin título"), precio, zona)
            print("✓ Alerta enviada a tu Telegram con éxito.")
            print(f"  └─ Registro guardado en BD: {item_id}\n")
        except Exception as e:
            print(f"⚠️ Error enviando notificación para ID {item_id}: {e}\n")

    print("="*80)
    print(f" Total inmuebles nuevos notificados: {len(inmuebles_aceptados)}")
    print("="*80 + "\n")

def ejecutar_proceso():

    # 1. Inicializar la base de datos y obtener inmuebles
    gestor_db.inicializar_base_datos()
    
    # Leemos directamente del JSON específico de Guadalajara para jugar con los datos reales
    resultados_apify = obtener_pisos_desde_json("pisos_inversion.json")
    
    inmuebles_aceptados = []
    # ... resto de tu lógica de filtros y envío a Telegram

    print("\n" + "="*80)
    print(" 📋 INMUEBLES SELECCIONADOS QUE CUMPLEN TODOS LOS CRITERIOS v2")
    print("="*80)

    for item in resultados_apify:
        
        item_id = str(item.get("id") or item.get("propertyCode") or "")

        # Comprobar en la BD si ya se notificó anteriormente para saltarlo
        #if gestor_db.ya_fue_visto(item_id):
        #    continue
            
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
