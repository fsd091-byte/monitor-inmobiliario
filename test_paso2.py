from gestor_db import inicializar_base_datos, ya_fue_visto, guardar_piso_visto

# 1. Aseguramos que la BD está inicializada
inicializar_base_datos()

# 2. Lista simulada de pisos devueltos por la extracción
pisos_obtenidos = [
    {
        "id": "idealista-2001",
        "title": "Piso 3 hab con ascensor en Getafe",
        "price": 165000,
        "zone": "Getafe"
    },
    {
        "id": "idealista-12345",  # Este ID ya se guardó en la prueba del Paso 1
        "title": "Piso que ya teníamos registrado",
        "price": 150000,
        "zone": "Móstoles"
    }
]

# 3. Procesamos los anuncios descartando repetidos
print("\n--- PROCESANDO ANUNCIOS ENCONTRADOS ---")
for piso in pisos_obtenidos:
    piso_id = piso["id"]
    
    if ya_fue_visto(piso_id):
        print(f"⏩ [IGNORADO] El piso '{piso['title']}' ({piso_id}) ya estaba en la BD.")
    else:
        print(f"🆕 [NUEVO PISO] '{piso['title']}' por {piso['price']:,} € en {piso['zone']}")
        guardar_piso_visto(piso_id, piso['title'], piso['price'], piso['zone'])