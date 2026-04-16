import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g

app = Flask(__name__)
app.secret_key = 'change-moi-en-production-xyz123'

DATABASE = 'coachbus.db'

# --------------------- Base de données ---------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS coachs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifiant TEXT UNIQUE NOT NULL,
                nom TEXT,
                role TEXT DEFAULT 'coach'
            );
            CREATE TABLE IF NOT EXISTS enfants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prenom TEXT NOT NULL,
                age INTEGER,
                allergies TEXT,
                groupe TEXT,
                absent_precoche INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS appels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                bus_num INTEGER NOT NULL,
                coach_id INTEGER NOT NULL,
                termine INTEGER DEFAULT 0,
                heure_validation TEXT,
                FOREIGN KEY (coach_id) REFERENCES coachs(id)
            );
            CREATE TABLE IF NOT EXISTS lignes_appel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appel_id INTEGER NOT NULL,
                enfant_id INTEGER NOT NULL,
                statut TEXT CHECK(statut IN ('Présent', 'Absent')),
                commentaire TEXT,
                FOREIGN KEY (appel_id) REFERENCES appels(id),
                FOREIGN KEY (enfant_id) REFERENCES enfants(id)
            );
        ''')
        # Données de test si tables vides
        cur = db.execute("SELECT COUNT(*) FROM coachs")
        if cur.fetchone()[0] == 0:
            db.executescript('''
                INSERT INTO coachs (identifiant, nom, role) VALUES
                ('julien', 'Julien Coach', 'coach'),
                ('marie', 'Marie Admin', 'admin'),
                ('sophie', 'Sophie Coach', 'coach');
                INSERT INTO enfants (nom, prenom, age, allergies, groupe) VALUES
                ('Dupont', 'Lucas', 8, 'Arachides', 'U9'),
                ('Martin', 'Emma', 9, NULL, 'U11'),
                ('Bernard', 'Léo', 7, 'Lactose', 'U9');
            ''')
        db.commit()

# --------------------- Authentification ---------------------
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Veuillez vous connecter.', 'error')
                return redirect(url_for('login'))
            if role and session.get('role') != role and session.get('role') != 'super-admin':
                flash('Accès non autorisé.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifiant = request.form['identifiant'].strip()
        if identifiant.lower() == 'superadmin':
            session['user_id'] = 0
            session['user_name'] = 'Super Admin'
            session['role'] = 'super-admin'
            return redirect(url_for('dashboard'))
        db = get_db()
        coach = db.execute("SELECT * FROM coachs WHERE identifiant = ?", (identifiant,)).fetchone()
        if coach:
            session['user_id'] = coach['id']
            session['user_name'] = coach['nom']
            session['role'] = coach['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiant inconnu.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --------------------- Dashboard (redirection selon rôle) ---------------------
@app.route('/dashboard')
@login_required()
def dashboard():
    role = session.get('role')
    if role in ('admin', 'super-admin'):
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('coach_select_bus'))

# --------------------- COACH ---------------------
@app.route('/coach/bus')
@login_required(role='coach')
def coach_select_bus():
    return render_template('coach_bus.html')

@app.route('/coach/appel/<int:bus_num>', methods=['GET', 'POST'])
@login_required(role='coach')
def coach_appel(bus_num):
    db = get_db()
    coach_id = session['user_id']
    today = date.today().isoformat()

    # Créer ou récupérer l'appel du jour pour ce bus et ce coach (non terminé)
    appel = db.execute(
        "SELECT * FROM appels WHERE date = ? AND bus_num = ? AND coach_id = ? AND termine = 0",
        (today, bus_num, coach_id)
    ).fetchone()
    if not appel:
        cur = db.execute(
            "INSERT INTO appels (date, bus_num, coach_id) VALUES (?, ?, ?)",
            (today, bus_num, coach_id)
        )
        appel_id = cur.lastrowid
        db.commit()
        appel = db.execute("SELECT * FROM appels WHERE id = ?", (appel_id,)).fetchone()
    else:
        appel_id = appel['id']

    # Charger les enfants
    enfants = db.execute("SELECT * FROM enfants ORDER BY nom, prenom").fetchall()

    if request.method == 'POST':
        # Validation de l'appel
        for enfant in enfants:
            statut = request.form.get(f'statut_{enfant["id"]}')
            commentaire = request.form.get(f'commentaire_{enfant["id"]}', '')
            if statut not in ('Présent', 'Absent'):
                flash(f'Statut manquant pour {enfant["prenom"]} {enfant["nom"]}', 'error')
                return redirect(url_for('coach_appel', bus_num=bus_num))
            # Enregistrer dans lignes_appel
            db.execute(
                "INSERT INTO lignes_appel (appel_id, enfant_id, statut, commentaire) VALUES (?, ?, ?, ?)",
                (appel_id, enfant['id'], statut, commentaire)
            )
        db.execute(
            "UPDATE appels SET termine = 1, heure_validation = ? WHERE id = ?",
            (datetime.now().isoformat(), appel_id)
        )
        db.commit()
        flash('Appel validé avec succès !', 'success')
        return redirect(url_for('coach_select_bus'))

    # Récupérer les statuts déjà saisis pour pré-remplissage
    lignes = db.execute(
        "SELECT enfant_id, statut, commentaire FROM lignes_appel WHERE appel_id = ?",
        (appel_id,)
    ).fetchall()
    statuts = {l['enfant_id']: {'statut': l['statut'], 'commentaire': l['commentaire']} for l in lignes}

    return render_template('coach_appel.html', bus_num=bus_num, enfants=enfants, statuts=statuts,
                           absent_precoche={e['id']: e['absent_precoche'] for e in enfants})

# --------------------- ADMIN ---------------------
@app.route('/admin')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/enfants', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_enfants():
    db = get_db()
    if request.method == 'POST':
        if 'ajouter' in request.form:
            nom = request.form['nom']
            prenom = request.form['prenom']
            age = request.form.get('age')
            allergies = request.form.get('allergies')
            groupe = request.form.get('groupe')
            db.execute(
                "INSERT INTO enfants (nom, prenom, age, allergies, groupe) VALUES (?, ?, ?, ?, ?)",
                (nom, prenom, age, allergies, groupe)
            )
            db.commit()
            flash('Enfant ajouté.', 'success')
        elif 'supprimer' in request.form:
            enfant_id = request.form['supprimer']
            db.execute("DELETE FROM enfants WHERE id = ?", (enfant_id,))
            db.commit()
            flash('Enfant supprimé.', 'success')
        elif 'toggle_absent' in request.form:
            enfant_id = request.form['toggle_absent']
            current = db.execute("SELECT absent_precoche FROM enfants WHERE id = ?", (enfant_id,)).fetchone()
            new_val = 0 if current['absent_precoche'] else 1
            db.execute("UPDATE enfants SET absent_precoche = ? WHERE id = ?", (new_val, enfant_id))
            db.commit()
        return redirect(url_for('admin_enfants'))

    enfants = db.execute("SELECT * FROM enfants ORDER BY nom, prenom").fetchall()
    return render_template('admin_enfants.html', enfants=enfants)

@app.route('/admin/rapports')
@login_required(role='admin')
def admin_rapports():
    db = get_db()
    today = date.today().isoformat()
    appels = db.execute(
        "SELECT a.*, c.nom as coach_nom FROM appels a JOIN coachs c ON a.coach_id = c.id "
        "WHERE a.date = ? AND a.termine = 1 ORDER BY a.heure_validation DESC",
        (today,)
    ).fetchall()
    return render_template('admin_rapports.html', appels=appels, today=today)

@app.route('/admin/rapport/<int:appel_id>')
@login_required(role='admin')
def admin_rapport_detail(appel_id):
    db = get_db()
    appel = db.execute(
        "SELECT a.*, c.nom as coach_nom FROM appels a JOIN coachs c ON a.coach_id = c.id WHERE a.id = ?",
        (appel_id,)
    ).fetchone()
    if not appel:
        flash('Appel introuvable.', 'error')
        return redirect(url_for('admin_rapports'))
    lignes = db.execute(
        "SELECT l.*, e.nom, e.prenom, e.age, e.allergies, e.groupe "
        "FROM lignes_appel l JOIN enfants e ON l.enfant_id = e.id WHERE l.appel_id = ? "
        "ORDER BY l.statut, e.nom",
        (appel_id,)
    ).fetchall()
    return render_template('admin_rapport_detail.html', appel=appel, lignes=lignes)

# --------------------- Lancement ---------------------
if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    else:
        # S'assurer que les tables existent
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)