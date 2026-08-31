import math
from gestor_db import inicializar_base_datos, ya_fue_visto, guardar_piso_visto
from notificador import enviar_alerta_piso
from extractor import obtener_pisos_idealista

# =====================================================================
# TUS CRITERIOS Y PARÁMETROS FINANCIEROS
# =====================================================================
CAPITAL_PROPIO = 100000          # Tu capital disponible a fin de año (€)
PRECIO_MAXIMO = 175000            # Límite máximo de compra (€)
IMPUESTOS_GASTOS_PCT = 0.10       # 10% ITP (Madrid) + Notaría/Registro/Gestoría
INTERES_HIPOTECA_ANUAL = 0.03     # 3,0% tipo de interés estimado
PLAZO_HIPOTECA_ANOS = 20          # Plazo de amortización en años

# Estimación del precio medio de alquiler por m² según municipios objetivo
PRECIOS_ALQUILER_M2 = {
    "Getafe": 11.5,
    "Móstoles": 10.5,
    "Alcalá de Henares": 10.0,
    "Rivas-Vaciamadrid": 11.0,
    "Guadalajara": 8.5,
    "Por defecto": 10.0
}

def calcular_cuota_hipoteca(prestamo, interes_anual, anos):
    """Calcula la cuota mensual mediante el sistema de amortización francés."""
    if prestamo <= 0:
        return 0.0
    r = interes_anual / 12
    n = anos * 12
    return round(prestamo * (r * math.pow(1 + r, n)) / (math.pow(1 + r, n) - 1), 2)

def analizar_y_evaluar_piso(piso):
    """
    Evalúa la viabilidad financiera de un piso.
    Devuelve un diccionario con los datos analizados si es rentable, o None si no.
    """
    precio = piso.get("price", 0)
    size = piso.get("size", 0)
    zona = piso.get("zone", "Por defecto")
    
    # 1. Filtros duros
    if precio > PRECIO_MAXIMO or size <= 0:
        return None
    
    # Descartar pisos altos sin ascensor
    piso_planta = piso.get("floor", 0)
    tiene_ascensor = piso.get("hasLift", True)
    if not tiene_ascensor and piso_planta > 1:
        return None  # Sin ascensor solo aceptamos bajo o 1º
        
    # 2. Desglose de compra e hipoteca
    gastos_compra = precio * IMPUESTOS_GASTOS_PCT
    inversion_total = precio + gastos_compra
    
    # Préstamo necesario utilizando tus 100.000 € de fondos propios
    prestamo_necesario = max(0, inversion_total - CAPITAL_PROPIO)
    cuota_hipoteca = calcular_cuota_hipoteca(prestamo_necesario, INTERES_HIPOTECA_ANUAL, PLAZO_HIPOTECA_ANOS)
    
    # 3. Estimación de Renta y Cash Flow
    precio_m2_zona = PRECIOS_ALQUILER_M2.get(zona, PRECIOS_ALQUILER_M2["Por defecto"])
    alquiler_estimado = size * precio_m2_zona
    
    # Gastos fijos estimados (IBI, comunidad, seguro impago, mantenimiento ~25% del alquiler)
    gastos_operativos = alquiler_estimado * 0.25
    alquiler_neto = alquiler_estimado - gastos_operativos
    
    # Cash Flow Neto Mensual (Lo que te queda limpio cada mes en el bolsillo)
    cash_flow_mensual = alquiler_neto - cuota_hipoteca
    rentabilidad_bruta = (alquiler_estimado * 12 / precio) * 100

    # 4. Criterio de oportunidad: Cash Flow positivo (>= 150 €/mes) y Rentabilidad Bruta (>= 5,5%)
    if cash_flow_mensual >= 150 and rentabilidad_bruta >= 5.5:
        return {
            "id": piso.get("id"),
            "titulo": piso.get("title", "Piso en venta"),
            "zona": zona,
            "precio": precio,
            "size": size,
            "habitaciones": piso.get("rooms", 2),
            "cuota_hipoteca": cuota_hipoteca,
            "alquiler_estimado": round(alquiler_estimado, 2),
            "cash_flow": round(cash_flow_mensual, 2),
            "rentabilidad_bruta": round(rentabilidad_bruta, 2),
            "url": piso.get("url", "https://www.idealista.com")
        }
    return None


def ejecutar_monitor():
    """Función principal que orquesta la búsqueda, el filtrado y las alertas."""
    print("🚀 === INICIANDO MONITOR INMOBILIARIO ===")
    
    # 1. Asegurar base de datos
    inicializar_base_datos()
    
    # 2. Obtener pisos desde el extractor/Scraper
    pisos_brutos = obtener_pisos_idealista()
    
    if not pisos_brutos:
        print("⚠️ No se han recibido inmuebles en esta ejecución.")
        return

    # 3. Procesar inmuebles
    nuevas_oportunidades = 0
    for piso in pisos_brutos:
        piso_id = piso.get("id")
        
        # Descartar si ya lo vimos anteriormente
        if ya_fue_visto(piso_id):
            continue
            
        # Analizar oportunidad financiera
        analisis = analizar_y_evaluar_piso(piso)
        
        if analisis:
            print(f"🎯 OPORTUNIDAD ENCONTRADA: {analisis['titulo']} ({analisis['precio']} €)")
            # Enviar alerta a Telegram
            enviar_alerta_piso(analisis)
            # Guardar en BD memoria
            guardar_piso_visto(analisis['id'], analisis['titulo'], analisis['precio'], analisis['zona'])
            nuevas_oportunidades += 1
        else:
            # Aunque no sea un chollo, lo guardamos para no volver a analizarlo mañana
            guardar_piso_visto(piso_id, piso.get("title", ""), piso.get("price", 0), piso.get("zone", ""))
            
    print(f"✓ Proceso finalizado. Oportunidades notificados hoy: {nuevas_oportunidades}")

if __name__ == "__main__":
    ejecutar_monitor()