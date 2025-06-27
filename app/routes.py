from flask import Blueprint, render_template, request, redirect, url_for, send_file
from .db import get_db
import io
import openpyxl
from datetime import datetime

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
            db.execute("""
                INSERT INTO productos (sku, nombre, categoria, codigo_ean)
                VALUES (?, ?, ?, ?)
            """, (sku, nombre, categoria, codigo_ean))

            db.execute("""
                INSERT INTO stock (sku, cantidad)
                VALUES (?, 0)
            """, (sku,))

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

# Entrada de inventario con número de lote
@main.route("/entrada", methods=["GET", "POST"])
def registrar_entrada():
    db = get_db()

    if request.method == "POST":
        codigo = request.form["codigo"]
        cantidad = int(request.form["cantidad"])
        lote = request.form.get("lote")
        observacion = request.form.get("observacion")
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not lote:
            return "❌ Debes ingresar un número de lote."

        try:
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

            db.execute("""
                UPDATE stock SET cantidad = cantidad + ?
                WHERE sku = ?
            """, (cantidad_total, sku))

            db.execute("""
                INSERT INTO movimientos (sku, tipo, cantidad, observacion)
                VALUES (?, 'ENTRADA', ?, ?)
            """, (sku, cantidad_total, observacion))

            db.execute("""
                INSERT INTO lotes (sku, lote, cantidad, fecha)
                VALUES (?, ?, ?, ?)
            """, (sku, lote, cantidad_total, fecha))

            db.commit()
            return redirect(url_for('main.index'))

        except Exception as e:
            return f"Error: {e}"

    return render_template("entrada.html")

# Salida de inventario
@main.route("/salida", methods=["GET", "POST"])
def registrar_salida():
    db = get_db()
    codigo = request.values.get("codigo")
    lotes = []
    sku = None

    if codigo:
        empaque = db.execute("""
            SELECT codigo_ean, unidades_por_empaque
            FROM empaques
            WHERE dun14 = ?
        """, (codigo,)).fetchone()

        if empaque:
            producto = db.execute("""
                SELECT sku FROM productos WHERE codigo_ean = ?
            """, (empaque["codigo_ean"],)).fetchone()
            if producto:
                sku = producto["sku"]
                multiplicador = empaque["unidades_por_empaque"]
            else:
                return f"❌ No se encontró SKU para EAN {empaque['codigo_ean']}"
        else:
            producto = db.execute("""
                SELECT sku FROM productos WHERE sku = ?
            """, (codigo,)).fetchone()
            if producto:
                sku = producto["sku"]
                multiplicador = 1
            else:
                return f"❌ No se encontró el producto con SKU {codigo}"

        if request.method == "GET":
            lotes = db.execute("""
                SELECT lote, cantidad FROM lotes
                WHERE sku = ? AND cantidad > 0
                ORDER BY fecha ASC
            """, (sku,)).fetchall()
            return render_template("salida.html", codigo=codigo, lotes=lotes, sku=sku)

        elif request.method == "POST":
            cantidad = int(request.form["cantidad"])
            lote = request.form["lote"]
            observacion = request.form.get("observacion")
            cantidad_total = cantidad * multiplicador

            stock = db.execute("SELECT cantidad FROM stock WHERE sku = ?", (sku,)).fetchone()
            if not stock or stock["cantidad"] < cantidad_total:
                return f"❌ Stock insuficiente. Disponible: {stock['cantidad'] if stock else 0}"

            if lote == "SIN_LOTE":
                db.execute("""
                    UPDATE stock SET cantidad = cantidad - ?
                    WHERE sku = ?
                """, (cantidad_total, sku))
                db.execute("""
                    INSERT INTO movimientos (sku, tipo, cantidad, observacion)
                    VALUES (?, 'SALIDA', ?, ?)
                """, (sku, cantidad_total, observacion))
                db.commit()
                return redirect(url_for('main.index'))

            lote_data = db.execute("""
                SELECT cantidad FROM lotes
                WHERE sku = ? AND lote = ?
            """, (sku, lote)).fetchone()

            if not lote_data or lote_data["cantidad"] < cantidad_total:
                return f"❌ Stock insuficiente en lote {lote}. Disponible: {lote_data['cantidad'] if lote_data else 0}"

            db.execute("""
                UPDATE stock SET cantidad = cantidad - ?
                WHERE sku = ?
            """, (cantidad_total, sku))
            db.execute("""
                INSERT INTO movimientos (sku, tipo, cantidad, observacion)
                VALUES (?, 'SALIDA', ?, ?)
            """, (sku, cantidad_total, observacion))
            db.execute("""
                UPDATE lotes SET cantidad = cantidad - ?
                WHERE sku = ? AND lote = ?
            """, (cantidad_total, sku, lote))
            db.commit()
            return redirect(url_for('main.index'))

    return render_template("salida.html", codigo=codigo, lotes=lotes, sku=sku)

# Ver Kardex
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

# Consulta de stock
@main.route("/consulta", methods=["GET"])
def consultar_stock():
    db = get_db()
    sku = request.args.get("sku")
    resultados = []

    base_query = """
        SELECT p.sku, p.nombre, p.categoria, s.cantidad,
               p.codigo_ean, e.dun14, e.unidades_por_empaque
        FROM productos p
        JOIN stock s ON p.sku = s.sku
        LEFT JOIN empaques e ON p.codigo_ean = e.codigo_ean
    """

    if sku:
        resultados = db.execute(base_query + " WHERE p.sku = ?", (sku,)).fetchall()
    else:
        resultados = db.execute(base_query + " ORDER BY p.nombre").fetchall()

    return render_template("consulta.html", resultados=resultados, sku=sku)

# Exportar stock
@main.route("/exportar_stock")
def exportar_stock():
    db = get_db()
    resultados = db.execute("""
        SELECT p.sku, p.nombre, p.categoria, s.cantidad,
               p.codigo_ean, e.dun14, e.unidades_por_empaque
        FROM productos p
        JOIN stock s ON p.sku = s.sku
        LEFT JOIN empaques e ON p.codigo_ean = e.codigo_ean
        ORDER BY p.nombre
    """).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stock"

    headers = ["SKU", "Nombre", "Categoría", "Stock", "EAN", "DUN14", "Unidades x Caja"]
    ws.append(headers)

    for r in resultados:
        ws.append([
            r["sku"], r["nombre"], r["categoria"], r["cantidad"],
            r["codigo_ean"], r["dun14"], r["unidades_por_empaque"]
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="stock_kardex.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Ver productos
@main.route("/productos", methods=["GET"])
def gestionar_productos():
    db = get_db()
    productos = db.execute("""
        SELECT p.sku, p.nombre, p.categoria, p.codigo_ean,
               e.dun14, e.unidades_por_empaque
        FROM productos p
        LEFT JOIN empaques e ON p.codigo_ean = e.codigo_ean
        ORDER BY p.nombre
    """).fetchall()
    return render_template("productos.html", productos=productos)

@main.route("/eliminar_producto/<sku>", methods=["POST"])
def eliminar_producto(sku):
    db = get_db()
    try:
        db.execute("DELETE FROM lotes WHERE sku = ?", (sku,))
        db.execute("DELETE FROM stock WHERE sku = ?", (sku,))
        db.execute("DELETE FROM movimientos WHERE sku = ?", (sku,))
        db.execute("DELETE FROM productos WHERE sku = ?", (sku,))
        db.commit()
        return redirect(url_for('main.gestionar_productos'))
    except Exception as e:
        return f"Error al eliminar: {e}"

# Ver lotes
@main.route("/lotes", methods=["GET"])
def ver_lotes():
    db = get_db()
    sku = request.args.get("sku")
    if sku:
        lotes = db.execute("""
            SELECT rowid AS id, sku, lote, cantidad, fecha
            FROM lotes
            WHERE sku = ?
            ORDER BY fecha ASC
        """, (sku,)).fetchall()
    else:
        lotes = db.execute("""
            SELECT rowid AS id, sku, lote, cantidad, fecha
            FROM lotes
            ORDER BY sku, fecha ASC
        """).fetchall()

    return render_template("lotes.html", lotes=lotes, sku=sku)

# Eliminar lote si cantidad = 0
@main.route("/eliminar_lote/<int:rowid>", methods=["POST"])
def eliminar_lote(rowid):
    db = get_db()
    lote = db.execute("SELECT cantidad FROM lotes WHERE rowid = ?", (rowid,)).fetchone()
    if lote and lote["cantidad"] == 0:
        db.execute("DELETE FROM lotes WHERE rowid = ?", (rowid,))
        db.commit()
    return redirect(url_for('main.ver_lotes'))

# Exportar lotes
@main.route("/exportar_lotes")
def exportar_lotes():
    db = get_db()
    resultados = db.execute("""
        SELECT sku, lote, cantidad, fecha
        FROM lotes
        ORDER BY sku, fecha ASC
    """).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lotes"

    headers = ["SKU", "Lote", "Cantidad", "Fecha"]
    ws.append(headers)

    for r in resultados:
        ws.append([r["sku"], r["lote"], r["cantidad"], r["fecha"]])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="lotes_kardex.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
