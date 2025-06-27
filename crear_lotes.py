import sqlite3

# Ruta a tu base de datos
db_path = "C:/Users/Admin/Desktop/Kardex_Foods/database/kardex.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Agregar la columna fecha si no existe
try:
    cursor.execute("ALTER TABLE lotes ADD COLUMN fecha TEXT")
    print("✅ Columna 'fecha' agregada correctamente.")
except sqlite3.OperationalError as e:
    print(f"⚠️ Ya existe o hubo un problema: {e}")

conn.commit()
conn.close()
