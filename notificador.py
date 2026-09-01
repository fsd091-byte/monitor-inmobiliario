import requests

# Configuración de tu Telegram
TELEGRAM_BOT_TOKEN = "8700550988:AAGqA6JXjJKhVz17B_kgaVMEygRW2PJxuo4"
TELEGRAM_CHAT_ID = "1371718984"

def enviar_alerta_piso(piso_analizado):
    """
    Envía un mensaje formateado a tu Telegram con el desglose de la oportunidad.
    """
    zona = piso_analizado.get('zone') or piso_analizado.get('zona') or 'No especificada'
    
    mensaje = (
        f"🎯 *¡OPORTUNIDAD INMOBILIARIA DETECTADA!*\n\n"
        f"📍 *Zona:* {piso_analizado.get('zone') or piso_analizado.get('zona') or 'No especificada'}\n"
        f"🏠 *Título:* {piso_analizado['titulo']}\n"
        f"📐 *Tamaño:* {piso_analizado['size']} m² | {piso_analizado['habitaciones']} hab.\n\n"
        f"💰 *Precio Venta:* {piso_analizado['precio']:,} €\n"
        f"🏦 *Hipoteca Est. (20 años):* ~{piso_analizado['cuota_hipoteca']} €/mes\n"
        f"🔑 *Alquiler Estimado:* ~{piso_analizado['alquiler_estimado']} €/mes\n"
        f"💵 *Cash Flow Neto Est.:* +{piso_analizado['cash_flow']} €/mes\n"
        f"📊 *Rentabilidad Bruta:* {piso_analizado['rentabilidad_bruta']}%\n\n"
        f"🔗 [Ver Anuncio en el Portal]({piso_analizado['url']})"
    )
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✓ Alerta enviada a tu Telegram con éxito.")
        else:
            print(f"❌ Error al enviar a Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Error de conexión al notificar: {e}")
