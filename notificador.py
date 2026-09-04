import requests

# Configuración de tu Telegram
TELEGRAM_BOT_TOKEN = "8700550988:AAGqA6JXjJKhVz17B_kgaVMEygRW2PJxuo4"
TELEGRAM_CHAT_ID = "1371718984"

def enviar_alerta_piso(piso_analizado):
    # Recuperación segura de campos usando nombres en inglés (Apify) y español como respaldo
    titulo = piso_analizado.get('title') or piso_analizado.get('titulo') or 'Inmueble'
    zona = piso_analizado.get('zone') or piso_analizado.get('zona') or 'No especificada'
    precio = piso_analizado.get('price', 'N/A')
    tamano = piso_analizado.get('size', 'N/A')
    habitaciones = piso_analizado.get('rooms', 'N/A')
    planta = piso_analizado.get('floor', 'N/A')
    url_inmueble = piso_analizado.get('url', '')  # <--- Usamos un nombre único

    mensaje = (
        f"🏠 *{titulo}*\n\n"
        f"📍 *Zona:* {zona}\n"
        f"💰 *Precio:* {precio} €\n"
        f"📐 *Superficie:* {tamano} m²\n"
        f"🛏 *Habitaciones:* {habitaciones}\n"
        f"🏢 *Planta:* {planta}\n\n"
        f"🔗 [Ver en Idealista]({url_inmueble})"  # <--- Apuntamos a la variable correcta
    )
    
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"  # <--- Variable separada para la API
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(telegram_url, json=payload)  # <--- Usamos la variable de Telegram
        if response.status_code == 200:
            print("✓ Alerta enviada a tu Telegram con éxito.")
        else:
            print(f"❌ Error al enviar a Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Error de conexión al notificar: {e}")
        
