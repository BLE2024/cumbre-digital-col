# app.py
# Servidor Flask para el registro de asistentes de la Cumbre Digital Col 2026.

import random
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for

app = Flask(__name__)

# Ruta absoluta a la base de datos, siempre en la raíz del proyecto
RUTA_BD = Path(__file__).parent / "evento.db"

# Áreas de interés permitidas en el formulario
AREAS_DISPONIBLES = ["Tecnología", "Marketing", "Negocios", "Emprendimiento"]

# Expresión regular para validar el formato del correo electrónico
PATRON_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def obtener_conexion():
    """Obtiene (o crea) la conexión a SQLite para la petición actual."""
    if "conexion_bd" not in g:
        g.conexion_bd = sqlite3.connect(RUTA_BD)
        g.conexion_bd.row_factory = sqlite3.Row
    return g.conexion_bd


@app.teardown_appcontext
def cerrar_conexion(excepcion=None):
    """Cierra la conexión a la base de datos al finalizar cada petición."""
    conexion = g.pop("conexion_bd", None)
    if conexion is not None:
        conexion.close()


def inicializar_bd():
    """Crea la tabla de asistentes si todavía no existe."""
    conexion = sqlite3.connect(RUTA_BD)
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS asistentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_registro TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            empresa TEXT NOT NULL,
            area TEXT NOT NULL,
            fecha_registro TEXT NOT NULL
        )
        """
    )
    conexion.commit()
    conexion.close()


def generar_numero_registro(conexion):
    """Genera un número de registro único con formato REG-XXXX."""
    while True:
        numero = f"REG-{random.randint(1000, 9999)}"
        existe = conexion.execute(
            "SELECT 1 FROM asistentes WHERE numero_registro = ?", (numero,)
        ).fetchone()
        if not existe:
            return numero


def validar_datos(nombre, email, empresa, area):
    """Valida los campos del formulario y devuelve una lista de errores en español."""
    errores = []

    if not nombre.strip():
        errores.append("El nombre completo es obligatorio.")

    if not email.strip():
        errores.append("El correo electrónico es obligatorio.")
    elif not PATRON_EMAIL.match(email.strip()):
        errores.append("El correo electrónico no tiene un formato válido.")

    if not empresa.strip():
        errores.append("La empresa u organización es obligatoria.")

    if area not in AREAS_DISPONIBLES:
        errores.append("Selecciona un área de interés válida.")

    return errores


@app.route("/")
def index():
    """Muestra el formulario de registro."""
    return render_template("index.html", areas=AREAS_DISPONIBLES, errores=None, datos=None)


@app.route("/registrar", methods=["POST"])
def registrar():
    """Procesa el envío del formulario, valida y guarda al asistente en la base de datos."""
    nombre = request.form.get("nombre", "")
    email = request.form.get("email", "")
    empresa = request.form.get("empresa", "")
    area = request.form.get("area", "")

    errores = validar_datos(nombre, email, empresa, area)

    if errores:
        datos = {"nombre": nombre, "email": email, "empresa": empresa, "area": area}
        return render_template(
            "index.html", areas=AREAS_DISPONIBLES, errores=errores, datos=datos
        ), 400

    conexion = obtener_conexion()
    numero_registro = generar_numero_registro(conexion)
    fecha_registro = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conexion.execute(
        """
        INSERT INTO asistentes (numero_registro, nombre, email, empresa, area, fecha_registro)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (numero_registro, nombre.strip(), email.strip(), empresa.strip(), area, fecha_registro),
    )
    conexion.commit()

    return render_template(
        "confirmacion.html", numero_registro=numero_registro, nombre=nombre.strip()
    )


@app.route("/admin")
def admin():
    """Muestra el panel de administración con la lista de asistentes registrados."""
    conexion = obtener_conexion()
    asistentes = conexion.execute(
        "SELECT * FROM asistentes ORDER BY id DESC"
    ).fetchall()

    conteo_areas = {area: 0 for area in AREAS_DISPONIBLES}
    for asistente in asistentes:
        conteo_areas[asistente["area"]] = conteo_areas.get(asistente["area"], 0) + 1

    return render_template(
        "admin.html",
        asistentes=asistentes,
        total=len(asistentes),
        conteo_areas=conteo_areas,
    )


if __name__ == "__main__":
    inicializar_bd()
    app.run(debug=True)
else:
    # También se inicializa al importar (por ejemplo, bajo un servidor WSGI como gunicorn)
    inicializar_bd()
