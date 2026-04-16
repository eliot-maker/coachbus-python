import sqlite3
import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash
from flask_mail import Mail, Message
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "supersecret"

# --- CONFIGURATION MAIL (À REMPLIR) ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'TON_EMAIL@gmail.com'
app.config['MAIL_PASSWORD'] = 'TON_MOT_DE_PASSE_APPLICATION' # Mot de passe d'application Google
mail = Mail(app)

DB_PATH = 'eleves.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS eleves 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         nom TEXT NOT NULL, 
                         absences INTEGER DEFAULT 0)''')

@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves ORDER BY nom ASC").fetchall()
    return render_template('index.html', eleves=eleves, date=datetime.now().strftime("%d/%m/%Y"))

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
    
    date_str = datetime.now().strftime("%d-%m-%Y")
    filename = f"appel_{date_str}.pdf"
    
    # --- GÉNÉRATION PDF ---
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Fiche d'appel - {date_str}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    
    for e in eleves:
        statut = "X" if e['absences'] == 1 else ""
        pdf.cell(150, 10, f"{e['nom']}", border=1)
        pdf.cell(40, 10, f"Absent: {statut}", border=1, ln=True, align='C')
    
    pdf.output(filename)

    # --- ENVOI MAIL ---
    try:
        msg = Message(f"Fiche d'appel du {date_str}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['DESTINATAIRE@email.com']) # L'adresse qui reçoit le PDF
        msg.body = f"Veuillez trouver ci-joint la fiche d'appel du {date_str}."
        with app.open_resource(filename) as fp:
            msg.attach(filename, "application/pdf", fp.read())
        mail.send(msg)
        os.remove(filename) # Supprime le PDF après envoi
    except Exception as e:
        print(f"Erreur mail: {e}")

    return "Appel envoyé avec succès ! <a href='/'>Retour</a>"

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)