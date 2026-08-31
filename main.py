import os
import requests
from extractor import obtener_pisos_idealista

# Configuración de variables de entorno (Secrets de GitHub)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

def enviar_mensaje_telegram(mensaje):
    """Envia una notificacion por mensaje de Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Advertencia: No se han configurado las credenciales de Telegram.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Notificación enviada a Telegram con éxito.")
    except Exception as e:
        print(f"❌ Error al enviar mensaje a Telegram: {e}")

def analizar_y_evaluar_piso(piso):
    """Analiza las características del inmueble y determina si es una oportunidad."""
    precio = piso.get("price", 0)
    superficie = piso.get("size", 0)
    piso_planta = piso.get("floor", "0")
    tiene_ascensor = piso.get("hasLift", False)
    
    # Conversión segura de planta a int
    try:
        planta_num = int(piso_planta)
    except (ValueError, TypeError):
        planta_num = 0

    # Conversión segura de precio y superficie
    try:
        precio_num = float(precio)
    except (ValueError, TypeError):
        precio_num = 0.0

    try:
        superficie_num = float(superficie)
    except (ValueError, TypeError):
        superficie_num = 0.0

    # Descartar pisos altos sin ascensor (Sin ascensor solo aceptamos bajo o 1º)
    if not tiene_ascensor and planta_num > 1:
        return False, "Piso alto sin ascensor"

    # Cálculo de precio por metro cuadrado
    if superficie_num > 0:
        precio_m2 = precio_num / superficie_num
    else:
        precio_m2 = 0

    # Criterio de oportunidad
    es_oportunidad = precio_num > 0 and precio_m2 > 0 and precio_m2 < 3000
    
    razon = f"Precio/m²: {precio_m2:.2f} €/m²" if es_oportunidad else "No cumple criterios de precio"
    return es_oportunidad, razon

def ejecutar_monitor():
    """Flujo principal del monitor de inmuebles."""
    print("🚀 === INICIANDO MONITOR INMOBILIARIO ===")
    print("🔍 Conectando con Apify para buscar inmuebles en Madrid...")
    
    pisos = obtener_pisos_idealista()
    print(f"✓ Se han obtenido {len(pisos)} anuncios procesados.")

    oportunidades = []

    for piso in pisos:
        es_oportunidad, razon = analizar_y_evaluar_piso(piso)
        if es_oportunidad:
            oportunidades.append((piso, razon))

    print(f"🎯 Se han encontrado {len(oportunidades)} oportunidades.")

    if oportunidades:
        mensaje = f"<b>🏢 Monitor Inmobiliario - Oportunidades ({len(oportunidades)})</b>\n\n"
        for idx, (piso, razon) in enumerate(oportunidades[:5], 1):
            titulo = piso.get("propertyTitle", "Inmueble sin título")
            precio = piso.get("price", "N/A")
            url = piso.get("url", "#")
            mensaje += f"{idx}. <b>{titulo}</b>\n💰 Precio: {precio} €\n📊 {razon}\n🔗 <a href='{url}'>Ver anuncio</a>\n\n"
        
        enviar_mensaje_telegram(mensaje)
    else:
        enviar_mensaje_telegram("ℹ️ <b>Monitor Inmobiliario:</b> Ejecución completada. No se encontraron nuevas oportunidades hoy.")

if __name__ == "__main__":
    ejecutar_monitor()
