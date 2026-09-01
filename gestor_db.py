import sqlite3
from datetime import datetime

NOMBRE_DB = "inmuebles.db"

def obtener_conexion():
    """Crea y devuelve la conexión a la base de datos."""
    return sqlite3.connect(NOMBRE_DB)

def inicializar_base_datos():
    """
    Crea la base de datos y la tabla 'pisos_vistos' si no existen.
    Se ejecuta al iniciar el programa.
    """
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pisos_vistos (
                id_anuncio TEXT PRIMARY KEY,
                titulo TEXT,
                precio INTEGER,
                zona TEXT,
                fecha_guardado TEXT
            )
        """)
        conexion.commit()
    print("✓ Base de datos conectada e inicializada correctamente.")

def ya_fue_visto(id_anuncio):
    """
    Verifica si un id_anuncio ya está registrado.
    Devuelve True si ya existe, False si es un anuncio nuevo.
    """
    """
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT 1 FROM pisos_vistos WHERE id_anuncio = ?", (id_anuncio,))
        resultado = cursor.fetchone()
    return resultado is not None
    """
    return False

def guardar_piso_visto(id_anuncio, titulo, precio, zona):
    """
    Registra un anuncio en la base de datos para no volver a notificarlo.
    """
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO pisos_vistos (id_anuncio, titulo, precio, zona, fecha_guardado)
            VALUES (?, ?, ?, ?, ?)
        """, (id_anuncio, titulo, precio, zona, fecha_actual))
        conexion.commit()
    print(f"  └─ Registro guardado en BD: {id_anuncio}")
