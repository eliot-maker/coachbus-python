import sqlite3
import os
import sys
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request
from flask_mail import Mail, Message
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "coachbus_secret_2026"

# --- CONFIGURATION MAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'eliot.thomas.fondriest@gmail.com'
app.config['MAIL_PASSWORD'] = 'gbomnyplaffgxxox' 
mail = Mail(app)

DB_PATH = 'eleves.db'

# 1. INITIALISATION DE LA BASE DE DONNÉES
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS eleves 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         nom TEXT NOT NULL, 
                         prenom TEXT NOT NULL,
                         absences INTEGER DEFAULT 0)''')

# 2. FONCTION D'IMPORTATION DEPUIS UN FICHIER TXT
def importer_liste_txt():
    filename = 'liste_eleves.txt'
    if not os.path.exists(filename):
        print(f"❌ Le fichier {filename} est introuvable dans le dossier.")
        return

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            with sqlite3.connect(DB_PATH) as conn:
                for ligne in f:
                    if ';' in ligne:
                        nom, prenom = ligne.strip().split(';')
                        conn.execute("INSERT INTO eleves (nom, prenom) VALUES (?, ?)", (nom.upper(), prenom.capitalize()))
                conn.commit()
        print("✅ Importation terminée avec succès !")
    except Exception as e:
        print(f"❌ Erreur lors de l'import : {e}")

# 3. FONCTION D'AJOUT MANUEL VIA CMD
def ajouter_eleve_cmd():
    print("\n--- AJOUT ÉLÈVE BUS ---")
    nom = input("Nom de famille : ")
    prenom = input("Prénom : ")
    if nom and prenom:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT INTO eleves (nom, prenom) VALUES (?, ?)", (nom.upper(), prenom.capitalize()))
        print(f"✅ {prenom} {nom} ajouté !")

# 4. ROUTES FLASK (SITE WEB)
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
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Rapport d'appel Bus - {date_str}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    
    for e in eleves:
        statut = "ABSENT (X)" if e['absences'] == 1 else "PRESENT"
        pdf.cell(100, 10, f"{e['nom']} {e['prenom']}", border=1)
        pdf.cell(50, 10, statut, border=1, ln=True, align='C')
    
    pdf.output(filename)

    try:
        msg = Message(f"Appel Bus - {date_str}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['eliot.thomas.fondriest@gmail.com']) # Remplace par l'email final si besoin
        msg.body = "Veuillez trouver ci-joint la fiche d'appel du bus."
        with app.open_resource(filename) as fp:
            msg.attach(filename, "application/pdf", fp.read())
        mail.send(msg)
        os.remove(filename)
        return "✅ Mail envoyé avec succès ! <a href='/'>Retour</a>"
    except Exception as e:
        return f"❌ Erreur lors de l'envoi : {e}"

# 5. POINT D'ENTRÉE DU PROGRAMME
if __name__ == '__main__':
    init_db()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'add':
            ajouter_eleve_cmd()
        elif sys.argv[1] == 'import':
            importer_liste_txt()
    else:
        # Configuration pour Render
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)