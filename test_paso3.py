from notificador import enviar_alerta_piso

# Datos simulados de un chollo para verificar el formato
piso_ejemplo = {
    "titulo": "Piso 3 hab con ascensor en Getafe Centro",
    "zona": "Getafe",
    "size": 75,
    "habitaciones": 3,
    "precio": 165000,
    "cuota_hipoteca": 395,
    "alquiler_estimado": 850,
    "cash_flow": 242,
    "rentabilidad_bruta": 6.18,
    "url": "https://www.idealista.com"
}

print("Enviando mensaje de prueba a Telegram...")
enviar_alerta_piso(piso_ejemplo)