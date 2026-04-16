from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    # Liste d'élèves pour l'exemple
    # On peut ajouter un champ 'absent' ou 'alerte' pour le style
    eleves = [
        {"nom": "ALBERT Tressy", "absences": ""},
        {"nom": "ALVES Ines", "absences": ""},
        {"nom": "ALVES Lea", "absences": ""},
        {"nom": "BALMES Clémence", "absences": ""},
        {"nom": "BAYNAT Lilian", "absences": ""},
        {"nom": "LAVAYSSE Firmin", "absences": "1", "alerte": True},
        {"nom": "ROBIN Lana", "absences": ""},
    ]
    return render_template('index.html', eleves=eleves)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)