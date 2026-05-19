from flask import Flask, render_template, request, redirect, url_for, session
import csv

app = Flask(__name__)
app.secret_key = "your_secret_key"  # session ke liye zaroori

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
    try:
        with open("inventory.csv", "r") as f:
            reader = csv.DictReader(f)
            max_id = 0
            for row in reader:
                pid = int(row["ID"])
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
    except FileNotFoundError:
        pass

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

# --- Login System ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # simple static login check
        if username == "admin" and password == "1234":
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Protected Routes ---
@app.route("/")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    load_inventory()
    return render_template("index.html", inventory=inventory)

@app.route("/add", methods=["POST"])
def add():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    name = request.form["name"]
    qty = int(request.form["qty"])
    category = request.form.get("category", "General")
    company = request.form.get("company", "Unknown")
    price = float(request.form.get("price", 0.0))
    add_product(name, qty, category, company, price)
    return render_template("success.html", product=name, qty=qty)

@app.route("/remove", methods=["POST"])
def remove():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    pid = request.form["id"]
    remove_product(pid)
    return render_template("remove.html", product_id=pid)

@app.route("/search", methods=["POST"])
def search():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    query = request.form["query"].strip().lower()
    load_inventory()
    results = []
    recommendations = []

    for pid, data in inventory.items():
        if query == str(pid) or query in data["name"].lower() or query in data["company"].lower():
            results.append((pid, data))

    if not results:
        for pid, data in inventory.items():
            if query[:3] in data["name"].lower() or query[:3] in data["company"].lower():
                recommendations.append((pid, data))

    return render_template("search.html", results=results, recommendations=recommendations, query=query)

if __name__ == "__main__":
    app.run(debug=True)
