import os
from apify_client import ApifyClient

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")

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
