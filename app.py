from flask import Flask, render_template, request, redirect, url_for, Response
import sqlite3
import csv
from io import StringIO

app = Flask(__name__)

DATABASE = "inventory.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)

    # New History Table for Audit Logging
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            product_name TEXT NOT NULL,
            details TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

@app.route("/")
def dashboard():

    search = request.args.get("search", "").strip()

    conn = get_db()

    if search:
        products = conn.execute("""
            SELECT * FROM products
            WHERE name LIKE ?
               OR category LIKE ?
            ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%"
        )).fetchall()
    else:
        products = conn.execute("""
            SELECT * FROM products
            ORDER BY id DESC
        """).fetchall()

    total_products = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    total_stock = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM products"
    ).fetchone()[0]

    low_stock = conn.execute(
        "SELECT COUNT(*) FROM products WHERE quantity <= 5"
    ).fetchone()[0]

    inventory_value = conn.execute(
        "SELECT COALESCE(SUM(quantity * price), 0) FROM products"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        products=products,
        total_products=total_products,
        total_stock=total_stock,
        low_stock=low_stock,
        inventory_value=inventory_value,
        search=search
    )


@app.route("/products")
def products():
    search = request.args.get("search", "").strip()

    conn = get_db()

    if search:
        products = conn.execute("""
            SELECT * FROM products
            WHERE name LIKE ?
               OR category LIKE ?
            ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%"
        )).fetchall()
    else:
        products = conn.execute("""
            SELECT * FROM products
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    return render_template(
        "products.html",
        products=products,
        search=search
    )


@app.route("/reports")
def reports():
    conn = get_db()

    total_products = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    total_stock = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM products"
    ).fetchone()[0]

    inventory_value = conn.execute(
        "SELECT COALESCE(SUM(quantity * price), 0) FROM products"
    ).fetchone()[0]

    low_stock = conn.execute(
        "SELECT COUNT(*) FROM products WHERE quantity > 0 AND quantity <= 5"
    ).fetchone()[0]

    out_of_stock = conn.execute(
        "SELECT COUNT(*) FROM products WHERE quantity = 0"
    ).fetchone()[0]

    categories = conn.execute("""
        SELECT
            category,
            COUNT(*) AS product_count,
            COALESCE(SUM(quantity), 0) AS stock,
            COALESCE(SUM(quantity * price), 0) AS value
        FROM products
        GROUP BY category
        ORDER BY value DESC
    """).fetchall()

    recent_activity = conn.execute("""
        SELECT * FROM history ORDER BY timestamp DESC LIMIT 10
    """).fetchall()

    conn.close()

    return render_template(
        "reports.html",
        total_products=total_products,
        total_stock=total_stock,
        inventory_value=inventory_value,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        categories=categories,
        recent_activity=recent_activity
    )


@app.route("/add-product", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        price = request.form["price"]

        conn = get_db()
        conn.execute("""
            INSERT INTO products (name, category, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (name, category, quantity, price))
        
        # Log to history
        conn.execute("""
            INSERT INTO history (action, product_name, details)
            VALUES (?, ?, ?)
        """, ("CREATED", name, f"Added {quantity} units at ${price} each."))

        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    return render_template("add_product.html")

@app.route("/delete-product/<int:id>", methods=["POST"])
def delete_product(id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (id,)).fetchone()
    
    if product:
        conn.execute("DELETE FROM products WHERE id = ?", (id,))
        # Log to history
        conn.execute("""
            INSERT INTO history (action, product_name, details)
            VALUES (?, ?, ?)
        """, ("DELETED", product["name"], "Product removed from inventory."))
        
        conn.commit()
    
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/edit-product/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (id,)
    ).fetchone()

    if product is None:
        conn.close()
        return "Product not found", 404

    if request.method == "POST":

        name = request.form["name"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        price = request.form["price"]

        conn.execute("""
            UPDATE products
            SET name = ?, category = ?, quantity = ?, price = ?
            WHERE id = ?
        """, (name, category, quantity, price, id))

        conn.commit()
        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()

    return render_template(
        "edit_product.html",
        product=product
    )

@app.route("/settings")
def settings():
    return render_template("settings.html")




@app.route('/adjust-stock/<int:id>/<action>', methods=['POST'])
def adjust_stock(id, action):
    # Fetch product, update quantity (+1 or -1), and log the activity
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    
    if product:
        current_qty = product['quantity']
        new_qty = current_qty + 1 if action == 'increase' else max(0, current_qty - 1)
        
        db.execute('UPDATE products SET quantity = ? WHERE id = ?', (new_qty, id))
        db.commit()
        
    return redirect(request.referrer or url_for('index'))



@app.route("/export-csv")
def export_csv():
    conn = get_db()
    products = conn.execute("SELECT * FROM products ORDER BY id ASC").fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Category', 'Quantity', 'Price'])

    for product in products:
        cw.writerow([product['id'], product['name'], product['category'], product['quantity'], product['price']])

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=inventory_report.csv"}
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)



if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

    