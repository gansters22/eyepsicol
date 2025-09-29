from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash
import os
from dotenv import load_dotenv
from datetime import datetime
import secrets

load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave-temporal-para-pruebas-123'
CORS(app, supports_credentials=True, origins=["http://localhost:8000"])

def get_db_connection():
    try:
        return mysql.connector.connect(
            host='localhost',
            database='eyepsicol_db',
            user='root',
            password='',
            autocommit=True
        )
    except Error as e:
        print("Error de base de datos:", e)
        return None

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        usuario = data.get('usuario')
        contrasena = data.get('contrasena')
        
        if not usuario or not contrasena:
            return jsonify({'success': False, 'message': 'Usuario y contraseña requeridos'}), 400
        
        connection = get_db_connection()
        if not connection:
            return jsonify({'success': False, 'message': 'Error de base de datos'}), 500
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE usuario = %s", (usuario,))
        user = cursor.fetchone()
        
        if user and user['contrasena'] and check_password_hash(user['contrasena'], contrasena):
            session['user_id'] = user['id']
            session['usuario'] = user['usuario']
            session['nombre'] = user['nombre']
            
            return jsonify({
                'success': True, 
                'message': '¡Login exitoso!',
                'user': {
                    'id': user['id'],
                    'usuario': user['usuario'],
                    'nombre': user['nombre']
                }
            }), 200
        else:
            return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Error del servidor'}), 500
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK', 'message': 'Servidor funcionando'}), 200

if __name__ == '__main__':
    print("🚀 Servidor iniciado en http://localhost:5000")
    print("📊 Prueba con usuario: admin, contraseña: 1234")
    app.run(debug=True, port=5000, host='0.0.0.0')
