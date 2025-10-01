from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import hashlib
import os
import re
from datetime import datetime, timedelta
import socket

app = Flask(__name__)
app.secret_key = 'eye_psicol_secret_key_2024'

# CONFIGURACIÓN CORS CORREGIDA - MÁS PERMISIVA
CORS(app,
     supports_credentials=True,
     origins=["http://localhost:63541", "http://127.0.0.1:63541", "http://localhost:5004"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Origin", "Accept"],
     expose_headers=["Content-Type", "Authorization"])

# Configuración de MySQL para Docker - PUERTO 3307
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'eyepsicol_user',
    'password': 'eyepsicol2024',
    'database': 'eyepsicol_db',
    'port': 3307
}

# Middleware para agregar headers CORS manualmente
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:63541', 'http://127.0.0.1:63541']:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Origin,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Manejar requests OPTIONS (preflight)
@app.route('/registro', methods=['OPTIONS'])
@app.route('/login', methods=['OPTIONS'])
@app.route('/contacto', methods=['OPTIONS'])
@app.route('/check-auth', methods=['OPTIONS'])
@app.route('/logout', methods=['OPTIONS'])
def handle_options():
    return '', 200

def get_db_connection():
    """Obtener conexión a MySQL"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        print("✅ Conexión a MySQL exitosa en puerto 3307")
        return conn
    except Error as e:
        print(f"❌ Error conectando a MySQL: {e}")
        return None

def init_db():
    """Inicializar la base de datos con las tablas necesarias"""
    conn = get_db_connection()
    if conn is None:
        print("❌ No se pudo conectar a MySQL")
        return False

    cursor = conn.cursor()

    try:
        # Usar la base de datos (ya existe por Docker)
        cursor.execute("USE eyepsicol_db")

        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT PRIMARY KEY AUTO_INCREMENT,
                nombre VARCHAR(255) NOT NULL,
                usuario VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                contrasena VARCHAR(255) NOT NULL,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de contactos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contactos (
                id INT PRIMARY KEY AUTO_INCREMENT,
                nombre VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                mensaje TEXT NOT NULL,
                fuente VARCHAR(100) NOT NULL DEFAULT 'general',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        print("✅ Base de datos MySQL inicializada correctamente")
        print("✅ Tablas 'usuarios' y 'contactos' creadas/verificadas")
        return True

    except Error as e:
        print(f"❌ Error inicializando base de datos: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

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

# Rutas de la API
@app.route('/')
def index():
    return jsonify({
        'message': 'API EyePsicol funcionando con MySQL',
        'endpoints': {
            'login': '/login (POST)',
            'registro': '/registro (POST)',
            'check-auth': '/check-auth (GET)',
            'logout': '/logout (GET)',
            'contacto': '/contacto (POST)'
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
    if conn is None:
        return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'})

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            'SELECT * FROM usuarios WHERE usuario = %s OR email = %s',
            (usuario, usuario)
        )
        user = cursor.fetchone()

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

    except Error as e:
        return jsonify({'success': False, 'message': f'Error en la base de datos: {str(e)}'})
    finally:
        cursor.close()
        conn.close()

@app.route('/registro', methods=['POST'])
def registro():
    """Endpoint para el registro de nuevos usuarios - ACTUALIZADO"""
    data = request.get_json()
    print(f"📥 Datos recibidos en registro: {data}")

    # Campos requeridos actualizados para el frontend
    required_fields = ['nombre', 'apellido', 'usuario', 'email', 'contrasena']
    for field in required_fields:
        if field not in data or not data[field].strip():
            return jsonify({'success': False, 'message': f'El campo {field} es requerido'})

    nombre = data['nombre'].strip()
    apellido = data['apellido'].strip()
    usuario = data['usuario'].strip()
    email = data['email'].strip().lower()
    contrasena = data['contrasena']

    # Combinar nombre y apellido para la base de datos
    nombre_completo = f"{nombre} {apellido}"

    if len(usuario) < 3:
        return jsonify({'success': False, 'message': 'El usuario debe tener al menos 3 caracteres'})

    if len(contrasena) < 6:
        return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres'})

    if not is_valid_email(email):
        return jsonify({'success': False, 'message': 'El formato del email no es válido'})

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'})

    cursor = conn.cursor(dictionary=True)

    try:
        # Verificar si el usuario o email ya existen
        cursor.execute(
            'SELECT id FROM usuarios WHERE usuario = %s OR email = %s',
            (usuario, email)
        )
        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({'success': False, 'message': 'El usuario o email ya están registrados'})

        hashed_password = hash_password(contrasena)

        # Insertar nuevo usuario con nombre completo
        cursor.execute(
            'INSERT INTO usuarios (nombre, usuario, email, contrasena) VALUES (%s, %s, %s, %s)',
            (nombre_completo, usuario, email, hashed_password)
        )
        conn.commit()

        # Obtener el usuario recién creado
        cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
        new_user = cursor.fetchone()

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

    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Error en el registro: {str(e)}'})
    finally:
        cursor.close()
        conn.close()

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

@app.route('/contacto', methods=['POST'])
def contacto():
    """Endpoint para guardar mensajes de contacto"""
    try:
        data = request.get_json()
        print(f"📥 Datos recibidos en /contacto: {data}")

        if not data or 'name' not in data or 'email' not in data or 'message' not in data:
            return jsonify({'success': False, 'message': 'Todos los campos son requeridos'})

        nombre = data['name'].strip()
        email = data['email'].strip().lower()
        mensaje = data['message'].strip()
        fuente = data.get('fuente', 'general')

        if not nombre or not email or not mensaje:
            return jsonify({'success': False, 'message': 'Todos los campos son requeridos'})

        if not is_valid_email(email):
            return jsonify({'success': False, 'message': 'El formato del email no es válido'})

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Error de conexión a la base de datos'})

        cursor = conn.cursor()

        # Insertar en la tabla contactos
        cursor.execute('''
            INSERT INTO contactos (nombre, email, mensaje, fuente)
            VALUES (%s, %s, %s, %s)
        ''', (nombre, email, mensaje, fuente))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ Mensaje guardado: {nombre}, {email}, fuente: {fuente}")
        return jsonify({'success': True, 'message': 'Mensaje enviado correctamente'})

    except Error as e:
        print(f"❌ Error en /contacto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error en la base de datos: {str(e)}'})
    except Exception as e:
        print(f"❌ Error en /contacto: {str(e)}")
        return jsonify({'success': False, 'message': f'Error en el servidor: {str(e)}'})

if __name__ == '__main__':
    # Verificar que MySQL esté corriendo antes de iniciar
    print("🔍 Verificando conexión a MySQL en puerto 3307...")

    if init_db():
        print(f"🚀 Iniciando servidor EyePsicol con MySQL en puerto 5004...")
        print(f"📧 Endpoint de registro: http://localhost:5004/registro")
        print(f"🔐 Endpoint de login: http://localhost:5004/login")
        print(f"📞 Endpoint de contacto: http://localhost:5004/contacto")
        print(f"🗄️  Base de datos: MySQL en Docker (puerto 3307)")
        print(f"📊 Tablas: usuarios, contactos")
        print(f"🌐 CORS habilitado para: http://localhost:63541")

        # SOLO UNA línea app.run() - con debug=False para evitar reinicios
        app.run(host='0.0.0.0', port=5004, debug=False)
    else:
        print("❌ No se pudo inicializar la base de datos. Verifica que Docker esté ejecutándose.")