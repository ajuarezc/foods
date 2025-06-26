import sqlite3

def crear_base_datos():
    conn = sqlite3.connect('database/kardex.db')
    cursor = conn.cursor()

    # Crear tabla productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            sku TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            categoria TEXT,
            codigo_ean TEXT UNIQUE NOT NULL
        )
    """)

    # Crear tabla stock
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            sku TEXT PRIMARY KEY,
            cantidad INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sku) REFERENCES productos(sku)
        )
    """)

    # Crear tabla movimientos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            tipo TEXT CHECK(tipo IN ('ENTRADA', 'SALIDA')) NOT NULL,
            cantidad INTEGER NOT NULL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            observacion TEXT,
            FOREIGN KEY (sku) REFERENCES productos(sku)
        )
    """)

    # Crear tabla empaques (DUN14)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS empaques (
            dun14 TEXT PRIMARY KEY,
            codigo_ean TEXT NOT NULL,
            unidades_por_empaque INTEGER NOT NULL,
            FOREIGN KEY (codigo_ean) REFERENCES productos(codigo_ean)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Base de datos creada correctamente.")


if __name__ == "__main__":
    crear_base_datos()
