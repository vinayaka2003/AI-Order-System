from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
import re

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# DATABASE
# =========================

def init_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # =========================
    # INVENTORY TABLE
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE,
        quantity INTEGER
    )
    """)

    # =========================
    # ORDERS TABLE
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        quantity INTEGER,
        status TEXT,
        delivery_time TEXT
    )
    """)

    # =========================
    # SAFE DATABASE UPGRADES
    # =========================

    columns_to_add = [

        ("material", "TEXT"),
        ("deadline", "TEXT"),
        ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")

    ]

    cursor.execute("PRAGMA table_info(orders)")

    existing_columns = [
        column[1]
        for column in cursor.fetchall()
    ]

    for column_name, column_type in columns_to_add:

        if column_name not in existing_columns:

            cursor.execute(f"""
            ALTER TABLE orders
            ADD COLUMN {column_name} {column_type}
            """)

    # =========================
    # QUALITY NOTES TABLE
    # =========================

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quality_notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        note TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # =========================
    # INSERT INVENTORY
    # =========================

    cursor.execute("SELECT COUNT(*) FROM inventory")

    count = cursor.fetchone()[0]

    if count == 0:

        items = [
            ("banana", 50),
            ("apple", 30),
            ("mango", 20),
            ("orange", 40)
        ]

        cursor.executemany("""
        INSERT INTO inventory(item_name, quantity)
        VALUES(?,?)
        """, items)

    conn.commit()
    conn.close()

init_db()

# =========================
# HOME
# =========================

@app.route("/")
def home():
    return redirect("/login")

# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin123":

            session["logged_in"] = True

            return redirect("/dashboard")

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if not session.get("logged_in"):
        return redirect("/login")

    return render_template("index.html")

# =========================
# CHAT API
# =========================

@app.route("/chat", methods=["POST"])
def chat():

    if not session.get("logged_in"):

        return jsonify({
            "reply": "Unauthorized"
        }), 401

    data = request.get_json()

    message = data.get("message", "").lower().strip()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # =========================================
    # STATUS UPDATE
    # =========================================

    status_match = re.search(
        r'order\s+(\d+)\s+(?:to|is)\s+(pending|review|accepted|completed)',
        message
    )

    if status_match:

        order_id = status_match.group(1)
        new_status = status_match.group(2).title()

        cursor.execute("""
        UPDATE orders
        SET status=?
        WHERE id=?
        """, (new_status, order_id))

        conn.commit()
        conn.close()

        return jsonify({
            "reply": f"""
            ✅ Order Updated Successfully<br><br>

            🆔 Order ID: #{order_id}<br>
            📌 New Status: {new_status}
            """
        })

    # =========================================
    # QUALITY NOTES
    # =========================================

    note_match = re.search(
        r'note\s+for\s+order\s+(\d+)\s*:\s*(.+)',
        message
    )

    if note_match:

        order_id = note_match.group(1)
        note = note_match.group(2)

        cursor.execute("""
        INSERT INTO quality_notes(order_id,note)
        VALUES(?,?)
        """, (order_id, note))

        conn.commit()
        conn.close()

        return jsonify({
            "reply": f"""
            📝 Quality Note Added<br><br>

            🆔 Order ID: #{order_id}<br>
            🗒️ Note: {note}
            """
        })

    # =========================================
    # DELIVERY TIME
    # =========================================

    time_match = re.search(
        r'(\d{1,2}:\d{2}\s?(am|pm))',
        message
    )

    delivery_time = (
        time_match.group()
        if time_match
        else "Immediate"
    )

    # =========================================
    # MATERIAL
    # =========================================

    material_match = re.search(
        r'(steel|aluminum|copper|plastic)',
        message
    )

    material = (
        material_match.group().title()
        if material_match
        else "General"
    )

    # =========================================
    # DEADLINE
    # =========================================

    deadline_match = re.search(
        r'(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        message
    )

    deadline = (
        deadline_match.group().title()
        if deadline_match
        else "Not Specified"
    )

    # =========================================
    # CREATE ORDER
    # =========================================

    matches = re.findall(
        r'(\d+)\s+(banana|apple|mango|orange)s?',
        message
    )

    if not matches:

        conn.close()

        return jsonify({
            "reply": """
            ❌ No valid command found<br><br>

            Examples:<br><br>

            ✅ Create Orders<br>
            • I want 2 bananas<br>
            • 3 apples tomorrow<br>
            • 5 mangoes at 5:30 pm<br><br>

            ✅ Update Status<br>
            • order 1 to accepted<br>
            • order 2 is completed<br><br>

            ✅ Add Notes<br>
            • note for order 1: scratches found
            """
        })

    response_text = ""

    for match in matches:

        quantity = int(match[0])
        item_name = match[1]

        cursor.execute("""
        SELECT quantity
        FROM inventory
        WHERE item_name=?
        """, (item_name,))

        result = cursor.fetchone()

        if result:

            available = result[0]

            if available >= quantity:

                remaining = available - quantity

                # UPDATE INVENTORY

                cursor.execute("""
                UPDATE inventory
                SET quantity=?
                WHERE item_name=?
                """, (remaining, item_name))

                # CREATE ORDER

                cursor.execute("""
                INSERT INTO orders(
                    item_name,
                    quantity,
                    status,
                    delivery_time,
                    material,
                    deadline
                )
                VALUES(?,?,?,?,?,?)
                """, (
                    item_name,
                    quantity,
                    "Pending",
                    delivery_time,
                    material,
                    deadline
                ))

                order_id = cursor.lastrowid

                response_text += f"""
                ✅ Order Created Successfully<br><br>

                🆔 Order ID: #{order_id}<br>
                📦 Item: {item_name}<br>
                🔢 Quantity: {quantity}<br>
                🏗️ Material: {material}<br>
                📅 Deadline: {deadline}<br>
                📉 Remaining Stock: {remaining}<br>
                📌 Status: Pending<br>
                ⏰ Delivery Time: {delivery_time}<br><br>
                """

            else:

                response_text += f"""
                ❌ Not enough stock for {item_name}<br><br>
                """

    conn.commit()
    conn.close()

    return jsonify({
        "reply": response_text
    })

# =========================
# GET ORDERS
# =========================

@app.route("/orders")
def orders():

    if not session.get("logged_in"):

        return jsonify({
            "orders": []
        })

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        item_name,
        quantity,
        status,
        delivery_time,
        COALESCE(material, 'General'),
        COALESCE(deadline, 'Not Specified'),
        COALESCE(created_at, 'N/A')
    FROM orders
    ORDER BY id DESC
    """)

    orders = cursor.fetchall()

    final_orders = []

    for order in orders:

        order_id = order[0]

        cursor.execute("""
        SELECT note
        FROM quality_notes
        WHERE order_id=?
        ORDER BY id DESC
        LIMIT 1
        """, (order_id,))

        note_result = cursor.fetchone()

        latest_note = (
            note_result[0]
            if note_result
            else "No Notes"
        )

        final_orders.append({
            "id": order[0],
            "item_name": order[1],
            "quantity": order[2],
            "status": order[3],
            "delivery_time": order[4],
            "material": order[5],
            "deadline": order[6],
            "created_at": order[7],
            "latest_note": latest_note
        })

    conn.close()

    return jsonify({
        "orders": final_orders
    })

# =========================
# CLEAR DATABASE
# =========================

@app.route("/clear")
def clear():

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM orders
    """)

    cursor.execute("""
    DELETE FROM quality_notes
    """)

    cursor.execute("""
    DELETE FROM sqlite_sequence
    WHERE name='orders'
    """)

    cursor.execute("""
    DELETE FROM sqlite_sequence
    WHERE name='quality_notes'
    """)

    conn.commit()

    conn.close()

    return """
    ✅ Database Cleared Successfully<br><br>

    Orders Removed<br>
    Notes Removed<br>
    IDs Reset
    """

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.pop("logged_in", None)

    return redirect("/login")

# =========================
# RUN APP
# =========================

if __name__ == "__main__":

    app.run(
        debug=True
    )