import sqlite3
from flask import Flask, render_template, request, redirect, url_for
import os
import sys

app = Flask(__name__)
DB_PATH = 'eleves.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS eleves 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         nom TEXT NOT NULL, 
                         absences INTEGER DEFAULT 0)''')

# --- FONCTION CMD POUR AJOUTER DES ELEVES ---
def ajouter_eleve_cmd():
    print("--- AJOUT D'ÉLÈVE ---")
    nom = input("Nom de l'élève : ")
    if nom:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO eleves (nom) VALUES (?)", (nom,))
        print(f"✅ {nom} ajouté avec succès !")
    else:
        print("❌ Nom invalide.")

@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves ORDER BY nom ASC").fetchall()
    return render_template('index.html', eleves=eleves)

@app.route('/toggle_absence/<int:id>')
def toggle_absence(id):
    with sqlite3.connect(DB_PATH) as conn:
        # Alterne entre 0 et 1 absence pour le clic interactif
        conn.execute("UPDATE eleves SET absences = CASE WHEN absences = 0 THEN 1 ELSE 0 END WHERE id = ?", (id,))
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    # On récupère le port donné par Render, sinon 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)