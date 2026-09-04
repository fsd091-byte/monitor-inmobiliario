import os
from apify_client import ApifyClient
import sqlite3

def obtener_pisos_desde_db(db_path="inmuebles.db"):
    """
    Lee todos los inmuebles guardados históricamente en la base de datos
    detectando automáticamente el nombre de la tabla.
    """
    print(f"🗄️ [MODO OFFLINE DB] Leyendo inmuebles desde la base de datos '{db_path}'...")
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
        cursor = conn.cursor()
        
        # Buscar automáticamente el nombre de la tabla en la base de datos
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()
        
        if not tablas:
            print("⚠️ No se encontraron tablas en la base de datos.")
            conn.close()
            return []
            
        # Selecciona la primera tabla que encuentre
        nombre_tabla = tablas[0]['name']
        print(f"📂 Tabla detectada automáticamente: '{nombre_tabla}'")
        
        cursor.execute(f"SELECT * FROM {nombre_tabla}")
        filas = cursor.fetchall()
        
        pisos = [dict(fila) for fila in filas]
        conn.close()
        
        print(f"✓ {len(pisos)} pisos cargados desde la base de datos para pruebas.")
        return pisos
    except Exception as e:
        print(f"⚠️ Error al leer la base de datos: {e}")
        return []
        
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")

""" conexion real

def obtener_pisos_idealista():
    
    client = ApifyClient(APIFY_TOKEN)
    
    run_input = {
        "location": "Madrid",
        "operation": "sale",
        "propertyType": "homes",
        "minPrice": "50000",
        "maxPrice": "175000",
        "maxItems": 100
    }

    print("🔍 Conectando con Apify para buscar inmuebles en Madrid...")
    
    try:
        run = client.actor("igolaizola/idealista-scraper").call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else run.default_dataset_id
        items_raw = list(client.dataset(dataset_id).iterate_items())
        
        pisos_normalizados = []
        for item in items_raw:
            piso_id = str(item.get("propertyCode") or item.get("id") or item.get("url", ""))
            if not piso_id:
                continue
                
            pisos_normalizados.append({
                "id": piso_id,
                "title": item.get("title") or item.get("propertyType", "Piso en venta"),
                "zone": item.get("municipality") or item.get("district") or item.get("address", "Madrid"),
                "price": float(item.get("price", 0)),
                "size": float(item.get("size", 0) or item.get("constructedArea", 0)),
                "rooms": int(item.get("rooms", 2)),
                "hasLift": item.get("hasLift", True),
                "floor": item.get("floor", 1),
                "url": item.get("url") or item.get("link", "https://www.idealista.com")
            })
            
        print(f"✓ Se han obtenido {len(pisos_normalizados)} anuncios procesados.")
        return pisos_normalizados
    except Exception as e:
        print(f"❌ Error al procesar datos de Apify: {e}")
        return []
"""

import json

def obtener_pisos_idealista():
    """
    Función temporal en modo offline para depurar con los datos reales guardados.
    """
    print("📁 [MODO OFFLINE] Leyendo inmuebles desde 'pisos_prueba.json'...")
    try:
        with open("pisos_prueba.json", "r", encoding="utf-8") as f:
            pisos = json.load(f)
            print(f"✓ {len(pisos)} pisos cargados correctamente para pruebas.")
            return pisos
    except FileNotFoundError:
        print("⚠️ No se encontró el archivo 'pisos_prueba.json'.")
        return []
