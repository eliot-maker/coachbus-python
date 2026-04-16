import sqlite3
import os
import sys
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request
from flask_mail import Mail, Message
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "coachbus_multi_v1"

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
                         bus TEXT NOT NULL,
                         present INTEGER DEFAULT 0)''')

# --- ROUTES ---

@app.route('/')
def selection_bus():
    return render_template('selection.html')

@app.route('/bus/<type_bus>')
def liste_bus(type_bus):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves WHERE bus = ? ORDER BY nom ASC", (type_bus,)).fetchall()
    
    total = len(eleves)
    presents = sum(1 for e in eleves if e['present'] == 1)
    return render_template('index.html', eleves=eleves, total=total, presents=presents, bus=type_bus)

@app.route('/toggle/<int:id>/<bus>')
def toggle_presence(id, bus):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE eleves SET present = 1 - present WHERE id = ?", (id,))
    return redirect(url_for('liste_bus', type_bus=bus))

@app.route('/terminer/<bus>')
def terminer_appel(bus):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves WHERE bus = ? ORDER BY nom ASC", (bus,)).fetchall()
    
    date_str = datetime.now().strftime("%d-%m-%Y %H:%M")
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, f"Rapport Appel - {bus.upper()} - {date_str}", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", size=12)
    
    for e in eleves:
        statut = "PRESENT" if e['present'] == 1 else "ABSENT (!!!)"
        pdf.cell(100, 10, f"{e['nom']} {e['prenom']}", border=1)
        pdf.cell(50, 10, statut, border=1, ln=True)
    
    filename = f"appel_{bus}.pdf"
    pdf.output(filename)

    try:
        msg = Message(f"Appel {bus.upper()} - {date_str}", sender=app.config['MAIL_USERNAME'], recipients=['eliot.thomas.fondriest@gmail.com'])
        msg.body = f"Voici le rapport d'appel pour le {bus}."
        with app.open_resource(filename) as fp: msg.attach(filename, "application/pdf", fp.read())
        mail.send(msg); os.remove(filename)
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE eleves SET present = 0 WHERE bus = ?", (bus,))
        return render_template('success.html')
    except Exception as e: return f"Erreur : {e}"

# --- COMMANDES CMD ---
if __name__ == '__main__':
    init_db()
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == 'import':
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("DELETE FROM eleves")
                for f_name, b_type in [('bus1.txt','bus1'), ('bus2.txt','bus2'), ('minibus.txt','minibus')]:
                    if os.path.exists(f_name):
                        with open(f_name, 'r', encoding='utf-8') as f:
                            for l in f:
                                if ';' in l:
                                    n, p = l.strip().split(';')
                                    conn.execute("INSERT INTO eleves (nom, prenom, bus) VALUES (?,?,?)", (n.upper(), p.capitalize(), b_type))
            print("✅ Importation des 3 listes terminée.")
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))