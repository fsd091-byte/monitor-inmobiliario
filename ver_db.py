import sqlite3

conexion = sqlite3.connect('inmuebles.db')
cursor = conexion.cursor()

# Consultamos la tabla real que sí existe: 'pisos_vistos'
cursor.execute("SELECT * FROM pisos_vistos LIMIT 1;")
print("Columnas:", [description[0] for description in cursor.description])
print("Ejemplo de fila:", cursor.fetchone())

conexion.close()