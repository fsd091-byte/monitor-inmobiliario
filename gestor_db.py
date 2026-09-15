import os
import sqlite3
from datetime import datetime

# --- SOLUCIÓN: Ruta absoluta basada en la ubicación del script ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOMBRE_DB = os.path.join(BASE_DIR, "inmuebles.db")
# -----------------------------------------------------------------

def obtener_conexion():
    """Crea y devuelve la conexión a la base de datos."""
    return sqlite3.connect(NOMBRE_DB)

# Resto de tus funciones de gestor_db...

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
    with obtener_conexion() as conexion:
        cursor = conexion.cursor()
        cursor.execute("SELECT 1 FROM pisos_vistos WHERE id_anuncio = ?", (id_anuncio,))
        resultado = cursor.fetchone()
    
    print(f"DEBUG DB -> ID {id_anuncio} ya_fue_visto: {resultado is not None}")
    return resultado is not None


def guardar_piso_visto(id_anuncio, titulo, precio, zona):
    """
    Registra un anuncio en la base de datos de forma persistente.
    """
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("""
        INSERT OR IGNORE INTO pisos_vistos (id_anuncio, titulo, precio, zona, fecha_guardado)
        VALUES (?, ?, ?, ?, ?)
    """, (str(id_anuncio), titulo, precio, zona, fecha_actual))
    
    conexion.commit()
    conexion.close()
    print(f"  └─ Registro guardado en BD: {id_anuncio}")

def ya_fue_visto(id_anuncio):
    """
    Comprueba si un anuncio ya está registrado en la base de datos.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT 1 FROM pisos_vistos WHERE id_anuncio = ?", (str(id_anuncio),))
    resultado = cursor.fetchone()
    
    conexion.close()
    
    visto = resultado is not None
    print(f"DEBUG DB -> ID {id_anuncio} ya_fue_visto: {visto}")
    return visto
    
