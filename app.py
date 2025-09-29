from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import hashlib
import os
import re
from datetime import datetime, timedelta
import socket

app = Flask(__name__)
app.secret_key = 'eye_psicol_secret_key_2024'
CORS(app, supports_credentials=True)

# Configuración de la base de datos
DATABASE = 'eyepsicol.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializar la base de datos con las tablas necesarias"""
    conn = get_db_connection()

    # Tabla de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")


def hash_password(password):
    """Hashear la contraseña usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    """Verificar si la contraseña coincide con el hash"""
    return hash_password(password) == hashed


def is_valid_email(email):
    """Validar formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def find_available_port(start_port=5000, max_attempts=10):
    """Encontrar un puerto disponible"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return start_port  # Fallback al puerto inicial


# Rutas de la API
@app.route('/')
def index():
    return jsonify({
        'message': 'API EyePsicol funcionando',
        'endpoints': {
            'login': '/login (POST)',
            'registro': '/registro (POST)',
            'check-auth': '/check-auth (GET)',
            'logout': '/logout (GET)'
        }
    })


@app.route('/login', methods=['POST'])
def login():
    """Endpoint para el login de usuarios"""
    data = request.get_json()

    if not data or 'usuario' not in data or 'contrasena' not in data:
        return jsonify({'success': False, 'message': 'Datos incompletos'})

    usuario = data['usuario'].strip()
    contrasena = data['contrasena']

    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM usuarios WHERE usuario = ? OR email = ?',
        (usuario, usuario)
    ).fetchone()
    conn.close()

    if user and verify_password(contrasena, user['contrasena']):
        session['user_id'] = user['id']
        session['user_nombre'] = user['nombre']
        session['user_usuario'] = user['usuario']
        session['user_email'] = user['email']

        return jsonify({
            'success': True,
            'message': 'Login exitoso',
            'user': {
                'id': user['id'],
                'nombre': user['nombre'],
                'usuario': user['usuario'],
                'email': user['email']
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos'})


@app.route('/registro', methods=['POST'])
def registro():
    """Endpoint para el registro de nuevos usuarios"""
    data = request.get_json()

    required_fields = ['nombre', 'usuario', 'email', 'contrasena']
    for field in required_fields:
        if field not in data or not data[field].strip():
            return jsonify({'success': False, 'message': f'El campo {field} es requerido'})

    nombre = data['nombre'].strip()
    usuario = data['usuario'].strip()
    email = data['email'].strip().lower()
    contrasena = data['contrasena']

    if len(usuario) < 3:
        return jsonify({'success': False, 'message': 'El usuario debe tener al menos 3 caracteres'})

    if len(contrasena) < 6:
        return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres'})

    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'El formato del email no es válido'})

    conn = get_db_connection()

    existing_user = conn.execute(
        'SELECT id FROM usuarios WHERE usuario = ? OR email = ?',
        (usuario, email)
    ).fetchone()

    if existing_user:
        conn.close()
        return jsonify({'success': False, 'message': 'El usuario o email ya están registrados'})

    hashed_password = hash_password(contrasena)

    try:
        conn.execute(
            'INSERT INTO usuarios (nombre, usuario, email, contrasena) VALUES (?, ?, ?, ?)',
            (nombre, usuario, email, hashed_password)
        )
        conn.commit()

        new_user = conn.execute(
            'SELECT * FROM usuarios WHERE usuario = ?', (usuario,)
        ).fetchone()
        conn.close()

        session['user_id'] = new_user['id']
        session['user_nombre'] = new_user['nombre']
        session['user_usuario'] = new_user['usuario']
        session['user_email'] = new_user['email']

        return jsonify({
            'success': True,
            'message': 'Registro exitoso',
            'user': {
                'id': new_user['id'],
                'nombre': new_user['nombre'],
                'usuario': new_user['usuario'],
                'email': new_user['email']
            }
        })

    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': f'Error en el registro: {str(e)}'})


@app.route('/check-auth', methods=['GET'])
def check_auth():
    """Verificar si el usuario está autenticado"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'nombre': session['user_nombre'],
                'usuario': session['user_usuario'],
                'email': session['user_email']
            }
        })
    else:
        return jsonify({'authenticated': False})


@app.route('/logout', methods=['GET'])
def logout():
    """Cerrar sesión"""
    session.clear()
    return jsonify({'success': True, 'message': 'Sesión cerrada correctamente'})


@app.route('/login/google')
def google_login():
    return jsonify({'success': False, 'message': 'Login con Google no está disponible'})


if __name__ == '__main__':
    init_db()

    # Encontrar puerto disponible
    port = find_available_port(5002)

    print(f"🚀 Iniciando servidor EyePsicol en puerto {port}...")
    print(f"📧 Endpoint de registro: http://localhost:{port}/registro")
    print(f"🔐 Endpoint de login: http://localhost:{port}/login")

    app.run(debug=True, port=port, host='0.0.0.0')