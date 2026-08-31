from gestor_db import inicializar_base_datos, ya_fue_visto, guardar_piso_visto

# 1. Creamos la base de datos
inicializar_base_datos()

# ID de prueba (por ejemplo, el ID que nos daría el anuncio de Idealista)
id_prueba = "idealista-12345"

# 2. Comprobamos si existe (debería decir False)
print(f"¿Existe el piso {id_prueba} en BD?:", ya_fue_visto(id_prueba))

# 3. Guardamos el piso de prueba
print("Guardando piso en BD...")
guardar_piso_visto(
    id_anuncio=id_prueba,
    titulo="Piso 3 hab con ascensor",
    precio=165000,
    zona="Getafe"
)

# 4. Volvemos a comprobar (debería decir True)
print(f"¿Existe el piso {id_prueba} en BD ahora?:", ya_fue_visto(id_prueba))