import sqlite3
import os
import sys
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request
from flask_mail import Mail, Message
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "coachbus_pro_final_2026"

# --- CONFIGURATION MAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'eliot.thomas.fondriest@gmail.com'
app.config['MAIL_PASSWORD'] = 'gbomnyplaffgxxox' 
mail = Mail(app)

DB_PATH = 'eleves.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS eleves 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         nom TEXT NOT NULL, 
                         prenom TEXT NOT NULL,
                         absences INTEGER DEFAULT 0)''')

def importer_liste_txt():
    filename = 'liste_eleves.txt'
    if not os.path.exists(filename):
        print(f"❌ Fichier {filename} manquant.")
        return
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM eleves") # On vide avant d'importer
                for ligne in f:
                    if ';' in ligne:
                        nom, prenom = ligne.strip().split(';')
                        conn.execute("INSERT INTO eleves (nom, prenom) VALUES (?, ?)", (nom.upper(), prenom.capitalize()))
                conn.commit()
        print("✅ Liste remplacée avec succès !")
    except Exception as e:
        print(f"❌ Erreur : {e}")

def vider_base_donnees():
    confirm = input("⚠️ Supprimer TOUS les élèves ? (oui/non) : ")
    if confirm.lower() == 'oui':
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM eleves")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='eleves'")
        print("✅ Base vidée.")

def supprimer_un_eleve():
    nom = input("Nom de famille à supprimer : ").upper()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM eleves WHERE nom = ?", (nom,))
        if cursor.rowcount > 0: print(f"✅ {nom} supprimé.")
        else: print("❌ Non trouvé.")

@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves ORDER BY nom ASC").fetchall()
    total = len(eleves)
    absents = sum(1 for e in eleves if e['absences'] == 1)
    presents = total - absents
    return render_template('index.html', eleves=eleves, total=total, presents=presents)

@app.route('/toggle/<int:id>')
def toggle_absence(id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE eleves SET absences = 1 - absences WHERE id = ?", (id,))
    return redirect(url_for('index'))

@app.route('/terminer_appel')
def terminer_appel():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves ORDER BY nom ASC").fetchall()
    
    date_str = datetime.now().strftime("%d-%m-%Y %H:%M")
    filename = "appel_bus.pdf"
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Rapport d'appel Bus - {date_str}", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=12)
    for e in eleves:
        statut = "ABSENT (X)" if e['absences'] == 1 else "PRESENT"
        pdf.cell(100, 10, f"{e['nom']} {e['prenom']}", border=1)
        pdf.cell(50, 10, statut, border=1, ln=True, align='C')
    pdf.output(filename)

    try:
        msg = Message(f"Appel Bus - {date_str}", sender=app.config['MAIL_USERNAME'], recipients=['eliot.thomas.fondriest@gmail.com'])
        msg.body = "Rapport d'appel ci-joint."
        with app.open_resource(filename) as fp: msg.attach(filename, "application/pdf", fp.read())
        mail.send(msg); os.remove(filename)
        with sqlite3.connect(DB_PATH) as conn: conn.execute("UPDATE eleves SET absences = 0")
        return render_template('success.html')
    except Exception as e: return f"Erreur : {e}"

if __name__ == '__main__':
    init_db()
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == 'import': importer_liste_txt()
        elif action == 'clear': vider_base_donnees()
        elif action == 'delete': supprimer_un_eleve()
        elif action == 'add': 
            nom = input("Nom : "); prenom = input("Prénom : ")
            with sqlite3.connect(DB_PATH) as conn: conn.execute("INSERT INTO eleves (nom, prenom) VALUES (?, ?)", (nom.upper(), prenom.capitalize()))
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))