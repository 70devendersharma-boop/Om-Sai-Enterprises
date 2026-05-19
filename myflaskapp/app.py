from flask import Flask, render_template, request, redirect, url_for, session
import csv, os

app = Flask(__name__)
app.secret_key = "supersecretkey"

inventory = {}
next_id = 1

# --- Inventory Functions ---
def save_inventory():
    with open("inventory.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Product", "Quantity", "Category", "Company", "Price"])
        for pid, data in inventory.items():
            writer.writerow([pid, data["name"], data["qty"], data["category"], data["company"], data["price"]])

def load_inventory():
    global next_id
    inventory.clear()
    if not os.path.exists("inventory.csv"):
        return
    with open("inventory.csv", "r") as f:
        reader = csv.DictReader(f)
        max_id = 0
        for row in reader:
            try:
                pid = int(row.get("ID", max_id + 1))
            except ValueError:
                pid = max_id + 1
            inventory[pid] = {
                "name": row["Product"],
                "qty": int(row["Quantity"]),
                "category": row["Category"],
                "company": row["Company"],
                "price": float(row["Price"])
            }
            if pid > max_id:
                max_id = pid
        next_id = max_id + 1

def add_product(name, quantity, category="General", company="Unknown", price=0.0):
    global next_id
    inventory[next_id] = {"name": name, "qty": quantity, "category": category, "company": company, "price": price}
    next_id += 1
    save_inventory()

def remove_product(pid):
    pid = int(pid)
    if pid in inventory:
        del inventory[pid]
        save_inventory()

# --- Root Redirect ---
@app.route("/")
def root():
    return redirect(url_for("shop"))

# --- Admin Login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "admin" and password == "1234":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("shop"))

# --- Orders Helper ---
def load_orders():
    orders = []
    if not os.path.exists("orders.csv"):
        return orders
    with open("orders.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 5:
                orders.append({
                    "customer": row[0],
                    "email": row[1],
                    "address": row[2],
                    "cart": eval(row[3]),
                    "total": float(row[4])
                })
    return orders

# --- Admin Dashboard ---
@app.route("/admin")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("login"))
    load_inventory()
    customers = load_customers()
    orders = load_orders()   # ✅ show orders directly
    return render_template("index.html", inventory=inventory, customers=customers, orders=orders)

@app.route("/approve_customer/<username>")
def approve_customer(username):
    if not session.get("admin"):
        return redirect(url_for("login"))
    customers = load_customers()
    if username in customers:
        customers[username]["status"] = "active"
        with open("customers.csv", "w", newline="") as f:
            writer = csv.writer(f)
            for uname, data in customers.items():
                writer.writerow([uname, data["password"], data["email"], data["address"], data["status"]])
    return redirect(url_for("admin_dashboard"))

@app.route("/reject_customer/<username>")
def reject_customer(username):
    if not session.get("admin"):
        return redirect(url_for("login"))
    customers = load_customers()
    if username in customers:
        del customers[username]
        with open("customers.csv", "w", newline="") as f:
            writer = csv.writer(f)
            for uname, data in customers.items():
                writer.writerow([uname, data["password"], data["email"], data["address"], data["status"]])
    return redirect(url_for("admin_dashboard"))

# --- Billing (Admin only, multi-product) ---
@app.route("/billing", methods=["GET", "POST"])
def billing():
    if not session.get("admin"):
        return redirect(url_for("login"))
    if request.method == "POST":
        items = []
        grand_total = 0
        product_names = request.form.getlist("name")
        quantities = request.form.getlist("qty")
        prices = request.form.getlist("price")

        for i in range(len(product_names)):
            pname = product_names[i].strip()
            if pname:
                qty = int(quantities[i])
                price = float(prices[i])
                total = qty * price
                grand_total += total
                items.append({"name": pname, "qty": qty, "price": price, "total": total})

                # update inventory
                for pid, data in inventory.items():
                    if data["name"].lower() == pname.lower():
                        if data["qty"] >= qty:
                            data["qty"] -= qty
                            save_inventory()
                        break

        return render_template("billing.html", items=items, grand_total=grand_total)
    return render_template("billing_form.html")

@app.route("/confirm_billing/<customer>")
def confirm_billing(customer):
    if not session.get("admin"):
        return redirect(url_for("login"))
    all_orders = load_orders()
    cust_orders = [o for o in all_orders if o["customer"].lower() == customer.lower()]
    if not cust_orders:
        return redirect(url_for("admin_dashboard"))
    order = cust_orders[-1]
    items = order["cart"]
    grand_total = order["total"]
    return render_template("billing.html", items=items, grand_total=grand_total)

# --- Customer Accounts ---
def save_customer(username, password, email, address, status="pending"):
    with open("customers.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([username, password, email, address, status])

def load_customers():
    customers = {}
    if not os.path.exists("customers.csv"):
        return customers
    with open("customers.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 5:
                customers[row[0]] = {
                    "password": row[1],
                    "email": row[2],
                    "address": row[3],
                    "status": row[4]
                }
    return customers

@app.route("/customer_signup", methods=["GET", "POST"])
def customer_signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        address = request.form["address"]
        save_customer(username, password, email, address)
        return redirect(url_for("customer_login"))
    return render_template("customer_signup.html")

@app.route("/customer_login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        customers = load_customers()
        if username in customers and customers[username]["password"] == password:
            if customers[username]["status"] == "active":
                session["customer"] = username
                return redirect(url_for("shop"))
            elif customers[username]["status"] == "rejected":
                return render_template("customer_login.html", error="Your account was rejected by admin")
            else:
                return render_template("customer_login.html", error="Account pending admin approval")
        else:
            return render_template("customer_login.html", error="Invalid credentials")
    return render_template("customer_login.html")

@app.route("/customer_logout")
def customer_logout():
    session.pop("customer", None)
    return redirect(url_for("shop"))

# --- Customer Shopping ---
@app.route("/shop")
def shop():
    load_inventory()
    return render_template("shop.html", inventory=inventory)

@app.route("/add_to_cart/<int:pid>")
def add_to_cart(pid):
    load_inventory()
    product = inventory.get(pid)
    if not product:
        return redirect(url_for("shop"))
    cart = session.get("cart", [])
    for item in cart:
        if item["id"] == pid:
            item["qty"] += 1
            break
    else:
        cart.append({
            "id": pid,
            "name": product["name"],
            "qty": 1,
            "price": product["price"]
        })
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    cart = session.get("cart", [])
    total = sum(item["qty"] * item["price"] for item in cart)
    return render_template("cart.html", cart=cart, total=total)

@app.route("/checkout")
def checkout():
    if "customer" not in session:
        return redirect(url_for("customer_login"))
    cart = session.get("cart", [])
    total = sum(item["qty"] * item["price"] for item in cart)
    customers = load_customers()
    cust = customers.get(session["customer"], {})
    with open("orders.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([session["customer"], cust.get("email",""), cust.get("address",""), cart, total])
    session["cart"] = []
    return render_template("checkout.html", total=total, customer=session["customer"], email=cust.get("email"), address=cust.get("address"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
