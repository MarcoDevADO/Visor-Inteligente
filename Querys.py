#Importar librerías necesarias
import psycopg2
from dotenv import load_dotenv
import os
from datetime import datetime
 
# Cargar variables guardadas en el .env
load_dotenv()
URL = os.getenv("URL")

# Clase para manejar la base de datos
class DBManager:
    def __init__(self):
        self.conn = None
        try:
            # Conectamos usando la URL completa de Supabase
            self.conn = psycopg2.connect(URL)
        except psycopg2.Error as e:
            print("Error al conectar a la base de datos:", e)

    def obtener_lotes(self):
        """Devuelve una lista de lotes únicos desde la tabla 'lemon'"""
        lotes = []
        if self.conn:
            try:
                with self.conn.cursor() as cursor:
                    cursor.execute("SELECT DISTINCT lote FROM lemon")
                    lotes = [str(row[0]) for row in cursor.fetchall()]
            except psycopg2.Error as e:
                print("Error al consultar lotes:", e)
        else:
            print("No hay conexión a la base de datos.")
        return lotes
    
    def obtener_validos_y_no_validos_por_lote(self, lote_actual):

        """Devuelve el número de objetos válidos y no válidos para un lote dado"""
        query = """
            SELECT 
                SUM(CASE WHEN valido = TRUE THEN 1 ELSE 0 END) AS total_validos,
                SUM(CASE WHEN valido = FALSE THEN 1 ELSE 0 END) AS total_no_validos
            FROM lemon
            WHERE lote = %s;
        """
        resultado = (0, 0)
        if self.conn:
            try:
                with self.conn.cursor() as cursor:
                    cursor.execute(query, (lote_actual,))
                    resultado = cursor.fetchone()
            except psycopg2.Error as e:
                print("Error al consultar válidos/no válidos:", e)
        return resultado
    
    def insertar_objeto(self, ancho, largo, valido, fecha, lote):
        """Inserta un nuevo objeto en la base de datos con los datos proporcionados"""
        query = """
            INSERT INTO lemon (ancho, largo, valido, fecha, lote)
            VALUES (%s, %s, %s, %s, %s)
        """
        # Convertir fecha a string si es datetime
        if isinstance(fecha, datetime):
            fecha = fecha.isoformat()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (ancho, largo, valido, fecha, lote))
            self.conn.commit()
        except psycopg2.Error as e:
            print("Error al insertar objeto:", e)

    def cerrar_conexion(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()

    def obtener_filas_por_lote(self, lote_actual):
        """Devuelve todas las filas del lote (sin el id) como lista de tuplas:
           (ancho, largo, valido, fecha, lote)
        """
        filas = []
        if not self.conn:
            print("No hay conexión a la base de datos.")
            return filas

        query = """
            SELECT ancho, largo, valido, fecha, lote
            FROM lemon
            WHERE lote = %s
            ORDER BY fecha ASC
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (lote_actual,))
                filas = cursor.fetchall()
        except psycopg2.Error as e:
            print("Error al obtener filas por lote:", e)

        return filas

    def actualizar_nombre_lote(self, lote_viejo, lote_nuevo):
        """
        Cambia el nombre del lote en TODOS los registros que lo usen
        """
        if not self.conn:
            raise Exception("No hay conexión a la base de datos")

        query = """
            UPDATE lemon
            SET lote = %s
            WHERE lote = %s
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (lote_nuevo, lote_viejo))
            self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            print("Error al actualizar lote:", e)
            raise
