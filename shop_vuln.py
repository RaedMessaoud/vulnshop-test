from flask import Flask, request, render_template_string, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "shop.db"

# ── init DB ──────────────────────────────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB) as con:
        cur = con.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                role     TEXT DEFAULT 'user'
            );
            CREATE TABLE IF NOT EXISTS products (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 10
            );
            INSERT OR IGNORE INTO users (id, username, password, role)
                VALUES (1, 'admin', 'admin123', 'admin'),
                       (2, 'alice', 'alice123', 'user');
            INSERT OR IGNORE INTO products (id, name, price, stock)
                VALUES (1, 'Laptop',      999.99, 5),
                       (2, 'Souris USB',   19.99, 20),
                       (3, 'Clavier',      49.99, 15),
                       (4, 'Ecran 27"',   299.99, 8);
        """)
        con.commit()

# ── templates ────────────────────────────────────────────────────────────────
BASE = """
<!DOCTYPE html>
<html>
<head>
  <title>VulnShop</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
    h1   { color: #c0392b; }
    nav  { background: #2c3e50; padding: 10px; border-radius: 6px; margin-bottom: 20px; }
    nav a{ color: white; margin-right: 15px; text-decoration: none; }
    .card{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,.1); }
    input, button { padding: 8px 12px; margin: 5px 0; border-radius: 4px; border: 1px solid #ccc; }
    button { background: #c0392b; color: white; border: none; cursor: pointer; }
    .warn { background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 12px; margin: 10px 0; color: #856404; }
    .err  { color: red; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; }
    th, td{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
    th    { background: #2c3e50; color: white; }
  </style>
</head>
<body>
<h1>🛒 VulnShop</h1>
<nav>
  <a href="/">Accueil</a>
  <a href="/products">Produits</a>
  <a href="/search">Recherche</a>
  {% if session.get('user') %}
    <a href="/profile">Profil ({{ session['user'] }})</a>
    <a href="/logout">Déconnexion</a>
  {% else %}
    <a href="/login">Connexion</a>
  {% endif %}
</nav>
{% block content %}{% endblock %}
</body>
</html>
"""

LOGIN_TMPL = BASE.replace("{% block content %}{% endblock %}", """
<div class="card">
  <h2>Connexion</h2>
  <div class="warn">
    ⚠️ <strong>Hint SQLi :</strong> essaie <code>' OR '1'='1</code> comme mot de passe
  </div>
  {% if error %}<p class="err">{{ error }}</p>{% endif %}
  <form method="POST">
    <input name="username" placeholder="Nom d'utilisateur" required><br>
    <input name="password" type="password" placeholder="Mot de passe" required><br>
    <button type="submit">Se connecter</button>
  </form>
</div>
""")

PRODUCTS_TMPL = BASE.replace("{% block content %}{% endblock %}", """
<div class="card">
  <h2>Nos produits</h2>
  <table>
    <tr><th>ID</th><th>Nom</th><th>Prix</th><th>Stock</th></tr>
    {% for p in products %}
    <tr><td>{{ p[0] }}</td><td>{{ p[1] }}</td><td>{{ p[2] }} €</td><td>{{ p[3] }}</td></tr>
    {% endfor %}
  </table>
</div>
""")

SEARCH_TMPL = BASE.replace("{% block content %}{% endblock %}", """
<div class="card">
  <h2>Recherche de produit</h2>
  <div class="warn">
    ⚠️ <strong>Hint SQLi :</strong> essaie <code>' UNION SELECT id,username,password,role FROM users--</code>
  </div>
  <form method="GET">
    <input name="q" placeholder="Nom du produit..." value="{{ query }}">
    <button type="submit">Rechercher</button>
  </form>
  {% if results is not none %}
  <table style="margin-top:15px">
    <tr><th>ID</th><th>Nom</th><th>Prix</th><th>Stock</th></tr>
    {% for r in results %}
    <tr><td>{{ r[0] }}</td><td>{{ r[1] }}</td><td>{{ r[2] }}</td><td>{{ r[3] }}</td></tr>
    {% endfor %}
  </table>
  {% if not results %}<p>Aucun résultat.</p>{% endif %}
  {% endif %}
</div>
""")

PROFILE_TMPL = BASE.replace("{% block content %}{% endblock %}", """
<div class="card">
  <h2>Profil</h2>
  <p><strong>Connecté en tant que :</strong> {{ session['user'] }}</p>
  <p><strong>Rôle :</strong> {{ session.get('role','user') }}</p>
</div>
""")

HOME_TMPL = BASE.replace("{% block content %}{% endblock %}", """
<div class="card">
  <h2>Bienvenue sur VulnShop</h2>
  <p>Application Flask <strong>volontairement vulnérable</strong> à l'injection SQL.</p>
  <div class="warn">
    ⚠️ <strong>Usage éducatif uniquement.</strong> Ne jamais déployer en production.
  </div>
  <h3>Vulnérabilités présentes</h3>
  <ul>
    <li><strong>/login</strong> — Bypass d'authentification par SQLi</li>
    <li><strong>/search</strong> — Extraction de données via UNION SQLi</li>
  </ul>
</div>
""")

# ── routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template_string(HOME_TMPL)

@app.route("/products")
def products():
    with sqlite3.connect(DB) as con:
        rows = con.execute("SELECT * FROM products").fetchall()
    return render_template_string(PRODUCTS_TMPL, products=rows)

# ❌ VULNÉRABILITÉ 1 : Login bypass via SQLi
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # ⚠️ REQUÊTE NON SÉCURISÉE — concaténation directe !
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        with sqlite3.connect(DB) as con:
            user = con.execute(query).fetchone()
        if user:
            session["user"] = user[1]
            session["role"] = user[3]
            return redirect(url_for("profile"))
        else:
            error = "Identifiants incorrects"
    return render_template_string(LOGIN_TMPL, error=error)

# ❌ VULNÉRABILITÉ 2 : UNION-based SQLi dans la recherche
@app.route("/search")
def search():
    q = request.args.get("q", "")
    results = None
    if q:
        # ⚠️ REQUÊTE NON SÉCURISÉE — concaténation directe !
        query = f"SELECT * FROM products WHERE name LIKE '%{q}%'"
        try:
            with sqlite3.connect(DB) as con:
                results = con.execute(query).fetchall()
        except Exception as e:
            results = [("ERREUR", str(e), "", "")]
    return render_template_string(SEARCH_TMPL, query=q, results=results)

@app.route("/profile")
def profile():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template_string(PROFILE_TMPL)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# ── run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("\n✅ VulnShop démarré sur http://127.0.0.1:5000\n")
    app.run(debug=True)
