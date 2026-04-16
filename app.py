import sqlite3, os, sys
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request
from flask_mail import Mail, Message
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "coachbus_expert_v1"

# --- CONFIG MAIL ---
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
                         nom TEXT NOT NULL, prenom TEXT NOT NULL, bus TEXT NOT NULL,
                         present_aller INTEGER DEFAULT 0,
                         present_retour INTEGER DEFAULT 0)''')

@app.route('/')
def selection_bus():
    return render_template('selection.html')

@app.route('/bus/<type_bus>')
def liste_bus(type_bus):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves WHERE bus = ? ORDER BY nom ASC", (type_bus,)).fetchall()
    p_aller = sum(1 for e in eleves if e['present_aller'] == 1)
    p_retour = sum(1 for e in eleves if e['present_retour'] == 1)
    return render_template('index.html', eleves=eleves, bus=type_bus, total=len(eleves), p_aller=p_aller, p_retour=p_retour)

@app.route('/toggle/<int:id>/<bus>/<int:colonne>')
def toggle_presence(id, bus, colonne):
    col = "present_aller" if colonne == 1 else "present_retour"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"UPDATE eleves SET {col} = 1 - {col} WHERE id = ?", (id,))
    return redirect(url_for('liste_bus', type_bus=bus))

@app.route('/terminer/<bus>/<type_appel>')
def terminer_appel(bus, type_appel):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        eleves = conn.execute("SELECT * FROM eleves WHERE bus = ? ORDER BY nom ASC", (bus,)).fetchall()
    
    date_str = datetime.now().strftime("%d-%m-%Y %H:%M")
    pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 14)
    titre = f"RAPPORT {type_appel.upper()} - {bus.upper()} - {date_str}"
    pdf.cell(200, 10, titre, ln=True, align='C'); pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 10, "Eleve", 1); pdf.cell(40, 10, "ALLER", 1); pdf.cell(40, 10, "RETOUR", 1, ln=True)
    pdf.set_font("Arial", size=10)
    for e in eleves:
        pdf.cell(80, 10, f"{e['nom']} {e['prenom']}", 1)
        pdf.cell(40, 10, "OK" if e['present_aller'] == 1 else "ABSENT", 1)
        pdf.cell(40, 10, "OK" if e['present_retour'] == 1 else "ABSENT", 1, ln=True)
    
    filename = f"appel_{bus}_{type_appel}.pdf"
    pdf.output(filename)

    try:
        msg = Message(titre, sender=app.config['MAIL_USERNAME'], recipients=['eliot.thomas.fondriest@gmail.com'])
        msg.body = f"Rapport de transport pour le trajet du {type_appel}."
        with app.open_resource(filename) as fp: msg.attach(filename, "application/pdf", fp.read())
        mail.send(msg); os.remove(filename)
        
        if type_appel == "retour":
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("UPDATE eleves SET present_aller = 0, present_retour = 0 WHERE bus = ?", (bus,))
        return render_template('success.html')
    except Exception as e: return f"Erreur : {e}"

if __name__ == '__main__':
    init_db()
    if len(sys.argv) > 1 and sys.argv[1] == 'import':
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM eleves")
            for f, b in [('bus1.txt','bus1'),('bus2.txt','bus2'),('minibus.txt','minibus')]:
                if os.path.exists(f):
                    with open(f, 'r', encoding='utf-8') as file:
                        for l in file:
                            if ';' in l:
                                n, p = l.strip().split(';')
                                conn.execute("INSERT INTO eleves (nom, prenom, bus) VALUES (?,?,?)", (n.upper(), p.capitalize(), b))
        print("✅ Importation terminée.")
    else:
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))