import sqlite3
import os
import sys
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request
from flask_mail import Mail, Message
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "coachbus_final_v3"

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
    if not os.path.exists('liste_eleves.txt'):
        print("❌ Fichier liste_eleves.txt introuvable.")
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM eleves")
        with open('liste_eleves.txt', 'r', encoding='utf-8') as f:
            for ligne in f:
                if ';' in ligne:
                    n, p = ligne.strip().split(';')
                    conn.execute("INSERT INTO eleves (nom, prenom) VALUES (?, ?)", (n.upper(), p.capitalize()))
    print("✅ Liste importée et remplacée.")

@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves ORDER BY nom ASC").fetchall()
    total = len(eleves)
    presents = total - sum(1 for e in eleves if e['absences'] == 1)
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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Appel Bus - {date_str}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for e in eleves:
        pdf.cell(100, 10, f"{e['nom']} {e['prenom']}", border=1)
        pdf.cell(50, 10, "ABSENT" if e['absences'] == 1 else "PRESENT", border=1, ln=True)
    
    pdf_file = "appel.pdf"
    pdf.output(pdf_file)

    try:
        msg = Message(f"Appel Bus {date_str}", sender=app.config['MAIL_USERNAME'], recipients=['eliot.thomas.fondriest@gmail.com'])
        msg.body = "Rapport en pièce jointe."
        with app.open_resource(pdf_file) as fp:
            msg.attach(pdf_file, "application/pdf", fp.read())
        mail.send(msg)
        os.remove(pdf_file) # Nettoyage du fichier temporaire
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE eleves SET absences = 0") # REMISE À ZÉRO ICI
        return render_template('success.html')
    except Exception as e:
        return f"Erreur : {e}"

if __name__ == '__main__':
    init_db()
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == 'import': importer_liste_txt()
        elif action == 'clear':
            with sqlite3.connect(DB_PATH) as conn: conn.execute("DELETE FROM eleves")
            print("✅ Base vidée.")
        elif action == 'add':
            n = input("Nom: "); p = input("Prénom: ")
            with sqlite3.connect(DB_PATH) as conn: conn.execute("INSERT INTO eleves (nom, prenom) VALUES (?,?)", (n.upper(), p.capitalize()))
            print(f"✅ {n} ajouté.")
        elif action == 'delete':
            n = input("Nom exact à supprimer: ").upper()
            with sqlite3.connect(DB_PATH) as conn: conn.execute("DELETE FROM eleves WHERE nom=?", (n,))
            print(f"✅ {n} supprimé.")
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))