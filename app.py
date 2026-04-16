import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request
from flask_mail import Mail, Message
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "coachbus_secret"

# --- CONFIGURATION MAIL (À REMPLIR) ---
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
    
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    filename = f"appel_bus.pdf"
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Rapport d'appel Bus - {date_str}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    
    for e in eleves:
        statut = "ABSENT" if e['absences'] == 1 else "PRESENT"
        pdf.cell(100, 10, f"{e['nom'].upper()} {e['prenom']}", border=1)
        pdf.cell(50, 10, statut, border=1, ln=True, align='C')
    
    pdf.output(filename)

    try:
        msg = Message(f"Appel Bus terminé - {date_str}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['eliot.thomas.fondriest@email.com'])
        msg.body = f"L'appel du bus est terminé. Voici la liste en pièce jointe."
        with app.open_resource(filename) as fp:
            msg.attach(filename, "application/pdf", fp.read())
        mail.send(msg)
        os.remove(filename)
    except Exception as e:
        print(f"Erreur: {e}")

    return "Appel envoyé ! <a href='/'>Retour au bus</a>"

# Fonction CMD pour ajouter des élèves
def ajouter_eleve_cmd():
    print("\n--- AJOUT ÉLÈVE BUS ---")
    nom = input("Nom de famille : ")
    prenom = input("Prénom : ")
    if nom and prenom:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO eleves (nom, prenom) VALUES (?, ?)", (nom, prenom))
        print(f"✅ {prenom} {nom} ajouté !")

if __name__ == '__main__':
    init_db()
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'add':
        ajouter_eleve_cmd()
    else:
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)