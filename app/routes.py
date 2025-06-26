from flask import Blueprint, render_template, request, redirect, url_for
from .db import get_db

main = Blueprint('main', __name__)

# Página de inicio
@main.route("/")
def index():
    return render_template("index.html")

# Crear producto
@main.route("/crear", methods=["GET", "POST"])
def crear_producto():
    db = get_db()
    if request.method == "POST":
        sku = request.form["sku"]
        nombre = request.form["nombre"]
        categoria = request.form["categoria"]
        codigo_ean = request.form["codigo_ean"]
        dun14 = request.form.get("dun14")
        unidades = request.form.get("unidades_por_empaque")

        try:
            # Insertar en productos
            db.execute("""
                INSERT INTO productos (sku, nombre, categoria, codigo_ean)
                VALUES (?, ?, ?, ?)
            """, (sku, nombre, categoria, codigo_ean))

            # Insertar en stock con 0 por defecto
            db.execute("""
                INSERT INTO stock (sku, cantidad)
                VALUES (?, 0)
            """, (sku,))

            # Insertar en empaques si corresponde
            if dun14 and unidades:
                db.execute("""
                    INSERT INTO empaques (dun14, codigo_ean, unidades_por_empaque)
                    VALUES (?, ?, ?)
                """, (dun14, codigo_ean, int(unidades)))

            db.commit()
            return redirect(url_for('main.index'))

        except Exception as e:
            return f"Error: {e}"

    return render_template("crear.html")

# Entrada de inventario
@main.route("/entrada", methods=["GET", "POST"])
def registrar_entrada():
    db = get_db()

    if request.method == "POST":
        codigo = request.form["codigo"]
        cantidad = int(request.form["cantidad"])
        observacion = request.form.get("observacion")

        try:
            # Ver si es DUN14
            empaque = db.execute("""
                SELECT codigo_ean, unidades_por_empaque
                FROM empaques
                WHERE dun14 = ?
            """, (codigo,)).fetchone()

            if empaque:
                ean = empaque["codigo_ean"]
                unidades = empaque["unidades_por_empaque"]
                cantidad_total = cantidad * unidades
                producto = db.execute("""
                    SELECT sku FROM productos WHERE codigo_ean = ?
                """, (ean,)).fetchone()
                if not producto:
                    return f"❌ No se encontró SKU asociado al EAN {ean}"
                sku = producto["sku"]
            else:
                producto = db.execute("""
                    SELECT sku FROM productos WHERE sku = ?
                """, (codigo,)).fetchone()
                if not producto:
                    return f"❌ No se encontró el producto con SKU {codigo}"
                sku = producto["sku"]
                cantidad_total = cantidad

            # Actualizar stock
            db.execute("""
                UPDATE stock SET cantidad = cantidad + ?
                WHERE sku = ?
            """, (cantidad_total, sku))

            # Registrar movimiento
            db.execute("""
                INSERT INTO movimientos (sku, tipo, cantidad, observacion)
                VALUES (?, 'ENTRADA', ?, ?)
            """, (sku, cantidad_total, observacion))

            db.commit()
            return redirect(url_for('main.index'))

        except Exception as e:
            return f"Error: {e}"

    return render_template("entrada.html")

# Salida de inventario
@main.route("/salida", methods=["GET", "POST"])
def registrar_salida():
    db = get_db()

    if request.method == "POST":
        codigo = request.form["codigo"]
        cantidad = int(request.form["cantidad"])
        observacion = request.form.get("observacion")

        try:
            # Ver si es DUN14
            empaque = db.execute("""
                SELECT codigo_ean, unidades_por_empaque
                FROM empaques
                WHERE dun14 = ?
            """, (codigo,)).fetchone()

            if empaque:
                ean = empaque["codigo_ean"]
                unidades = empaque["unidades_por_empaque"]
                cantidad_total = cantidad * unidades
                producto = db.execute("""
                    SELECT sku FROM productos WHERE codigo_ean = ?
                """, (ean,)).fetchone()
                if not producto:
                    return f"❌ No se encontró SKU asociado al EAN {ean}"
                sku = producto["sku"]
            else:
                producto = db.execute("""
                    SELECT sku FROM productos WHERE sku = ?
                """, (codigo,)).fetchone()
                if not producto:
                    return f"❌ No se encontró el producto con SKU {codigo}"
                sku = producto["sku"]
                cantidad_total = cantidad

            # Verificar stock disponible
            stock = db.execute("""
                SELECT cantidad FROM stock WHERE sku = ?
            """, (sku,)).fetchone()

            if not stock or stock["cantidad"] < cantidad_total:
                return f"❌ Stock insuficiente. Disponible: {stock['cantidad'] if stock else 0}"

            # Descontar stock
            db.execute("""
                UPDATE stock SET cantidad = cantidad - ?
                WHERE sku = ?
            """, (cantidad_total, sku))

            # Registrar movimiento
            db.execute("""
                INSERT INTO movimientos (sku, tipo, cantidad, observacion)
                VALUES (?, 'SALIDA', ?, ?)
            """, (sku, cantidad_total, observacion))

            db.commit()
            return redirect(url_for('main.index'))

        except Exception as e:
            return f"Error: {e}"

    return render_template("salida.html")
@main.route("/kardex", methods=["GET"])
def ver_kardex():
    db = get_db()
    sku = request.args.get("sku")
    movimientos = []

    if sku:
        movimientos = db.execute("""
            SELECT fecha, tipo, cantidad, observacion
            FROM movimientos
            WHERE sku = ?
            ORDER BY fecha DESC
        """, (sku,)).fetchall()

    return render_template("kardex.html", sku=sku, movimientos=movimientos)
@main.route("/consulta", methods=["GET"])
def consultar_stock():
    db = get_db()
    sku = request.args.get("sku")
    resultados = []

    if sku:
        resultados = db.execute("""
            SELECT p.sku, p.nombre, p.categoria, s.cantidad
            FROM productos p
            JOIN stock s ON p.sku = s.sku
            WHERE p.sku = ?
        """, (sku,)).fetchall()
    else:
        resultados = db.execute("""
            SELECT p.sku, p.nombre, p.categoria, s.cantidad
            FROM productos p
            JOIN stock s ON p.sku = s.sku
            ORDER BY p.nombre
        """).fetchall()

    return render_template("consulta.html", resultados=resultados, sku=sku)
