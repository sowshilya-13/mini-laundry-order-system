from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)

GARMENT_PRICES = {
    "Shirt": 50,
    "Pants": 70,
    "Saree": 150,
    "Coat": 200,
    "Kurta": 80
}

STATUSES = ["RECEIVED", "PROCESSING", "READY", "DELIVERED"]


# ---------- DATABASE ----------

def init_db():
    conn = sqlite3.connect("laundry.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE,
            customer_name TEXT,
            phone TEXT,
            garment TEXT,
            quantity INTEGER,
            price INTEGER,
            total_amount INTEGER,
            status TEXT,
            created_at TEXT,
            estimated_delivery TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect("laundry.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------- ROUTES ----------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/create", methods=["GET", "POST"])
def create_order():
    if request.method == "POST":
        customer_name = request.form["customer_name"]
        phone = request.form["phone"]
        garment = request.form["garment"]
        quantity = int(request.form["quantity"])

        price = GARMENT_PRICES[garment]
        total_amount = price * quantity

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        order_id = "ORD" + str(count + 1).zfill(3)

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        estimated_delivery = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO orders (
                order_id, customer_name, phone, garment, quantity,
                price, total_amount, status, created_at, estimated_delivery
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, customer_name, phone, garment, quantity,
            price, total_amount, "RECEIVED", created_at, estimated_delivery
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("view_orders"))

    return render_template("create_order.html", garment_prices=GARMENT_PRICES)


@app.route("/orders")
def view_orders():
    status_filter = request.args.get("status", "")
    search = request.args.get("search", "")

    conn = get_db_connection()

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if search:
        query += """
            AND (
                LOWER(customer_name) LIKE ?
                OR phone LIKE ?
                OR LOWER(garment) LIKE ?
            )
        """
        search_value = f"%{search.lower()}%"
        params.extend([search_value, search_value, search_value])

    query += " ORDER BY id DESC"

    orders = conn.execute(query, params).fetchall()
    conn.close()

    return render_template(
        "orders.html",
        orders=orders,
        statuses=STATUSES,
        selected_status=status_filter,
        search=search
    )


@app.route("/update-status/<order_id>", methods=["POST"])
def update_status(order_id):
    new_status = request.form["status"]

    conn = get_db_connection()
    conn.execute(
        "UPDATE orders SET status = ? WHERE order_id = ?",
        (new_status, order_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("view_orders"))


# ---------- DELETE ROUTE (NEW) ----------

@app.route("/delete/<order_id>", methods=["POST"])
def delete_order(order_id):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM orders WHERE order_id = ?",
        (order_id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("view_orders"))


@app.route("/dashboard")
def dashboard():
    conn = get_db_connection()

    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM orders"
    ).fetchone()[0]

    status_count = {}
    for status in STATUSES:
        count = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = ?",
            (status,)
        ).fetchone()[0]
        status_count[status] = count

    conn.close()

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        total_revenue=total_revenue,
        status_count=status_count
    )


# ---------- RUN ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)