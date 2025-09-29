from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
from business_info import info
import time
import subprocess
import os

app = Flask(__name__)
CORS(app)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma2:2b"

# Contador de intentos fallidos
ollama_fail_count = 0
MAX_RETRIES = 3


def reiniciar_ollama():
    """Intenta reiniciar Ollama si falla múltiples veces"""
    global ollama_fail_count
    try:
        print("🔄 Intentando reiniciar Ollama...")
        # Detener Ollama
        subprocess.run(["pkill", "-f", "ollama"], timeout=10)
        time.sleep(2)
        # Iniciar Ollama en segundo plano
        subprocess.Popen(["ollama", "serve"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        time.sleep(5)  # Esperar a que inicie
        ollama_fail_count = 0
        print("✅ Ollama reiniciado")
        return True
    except Exception as e:
        print(f"❌ Error reiniciando Ollama: {e}")
        return False


def verificar_ollama():
    """Verifica si Ollama está disponible con timeout corto"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        return response.status_code == 200
    except:
        return False


def generar_respuesta(pregunta, contexto=""):
    """
    Versión con reconexión automática y fallback
    """
    global ollama_fail_count

    # Verificar conexión con Ollama
    if not verificar_ollama():
        print("❌ Ollama no responde, intentando reconectar...")
        if ollama_fail_count < MAX_RETRIES:
            if reiniciar_ollama():
                return generar_respuesta(pregunta, contexto)  # Reintentar
        else:
            return "🔧 El servicio está experimentando problemas técnicos. Por favor, intenta en unos minutos."

    # Si es una pregunta simple, responder directamente
    preguntas_simples = {
        "cuantos balones de oro tiene cr7": "Cristiano Ronaldo tiene 5 Balones de Oro en su carrera.",
        "balones de oro cristiano ronaldo": "Cristiano Ronaldo ha ganado 5 Balones de Oro.",
        "cr7 balones de oro": "CR7 tiene 5 Balones de Oro."
    }

    pregunta_lower = pregunta.lower().strip()
    if pregunta_lower in preguntas_simples:
        return preguntas_simples[pregunta_lower]

    prompt = f"""
    Eres Eyebot, un psicólogo virtual especializado en salud mental. Responde de manera empática y profesional EN ESPAÑOL.

    CONTEXTO OPCIONAL (solo si es relevante para psicología):
    {info}

    CONVERSACIÓN PREVIA:
    {contexto}

    PREGUNTA ACTUAL: {pregunta}

    RESPUESTA (enfócate en psicología y salud mental, sé natural):
    """

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 200,  # Más corto para mayor estabilidad
            "temperature": 0.7,
            "top_p": 0.8,
        }
    }

    try:
        print(f"📤 Enviando a Ollama: {pregunta[:30]}...")
        start_time = time.time()

        response = requests.post(OLLAMA_URL, json=payload, timeout=30)

        if response.status_code != 200:
            ollama_fail_count += 1
            print(f"❌ Error HTTP {response.status_code}")
            return f"Error temporal del servicio (código {response.status_code}). Intenta de nuevo."

        data = response.json()
        respuesta = data.get("response", "").strip()

        # Reiniciar contador si fue exitoso
        ollama_fail_count = 0

        end_time = time.time()
        print(f"✅ Respuesta en {end_time - start_time:.1f}s")

        return respuesta if respuesta else "No pude generar una respuesta adecuada. ¿Podrías reformular tu pregunta?"

    except requests.exceptions.Timeout:
        ollama_fail_count += 1
        print("⏰ Timeout con Ollama")
        return "El servicio está respondiendo lentamente. Intenta con una pregunta más breve."

    except requests.exceptions.ConnectionError:
        ollama_fail_count += 1
        print("🔌 Error de conexión con Ollama")
        if ollama_fail_count >= MAX_RETRIES:
            return "El servicio de IA no está disponible temporalmente. Estamos trabajando para solucionarlo."
        return "Problema de conexión temporal. Intenta de nuevo."

    except Exception as e:
        ollama_fail_count += 1
        print(f"💥 Error: {e}")
        return "Error inesperado. Por favor, intenta más tarde."


# Almacenamiento de conversaciones
conversaciones = {}


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id', 'default')
        mensaje = data.get('mensaje', '').strip()

        print(f"📩 Chat request: {user_id} - '{mensaje}'")

        if not mensaje:
            return jsonify({'error': 'Mensaje vacío'}), 400

        # Manejar contexto
        if user_id not in conversaciones:
            conversaciones[user_id] = ""

        contexto = conversaciones[user_id]

        # Generar respuesta
        respuesta = generar_respuesta(mensaje, contexto)

        # Actualizar contexto
        conversaciones[user_id] += f"Usuario: {mensaje}\nAsistente: {respuesta}\n"
        if len(conversaciones[user_id]) > 1000:
            conversaciones[user_id] = conversaciones[user_id][-800:]

        return jsonify({
            'respuesta': respuesta,
            'user_id': user_id,
            'status': 'success'
        })

    except Exception as e:
        print(f"🔥 Error en chat: {e}")
        return jsonify({
            'respuesta': 'Error interno del servidor. Intenta de nuevo.',
            'status': 'error'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    status = "connected" if verificar_ollama() else "disconnected"
    return jsonify({
        'status': 'ok',
        'ollama': status,
        'fail_count': ollama_fail_count,
        'users_activos': len(conversaciones)
    })


# Endpoint para forzar reinicio de Ollama
@app.route('/api/restart-ollama', methods=['POST'])
def restart_ollama():
    success = reiniciar_ollama()
    return jsonify({'success': success, 'message': 'Ollama reiniciado' if success else 'Error al reiniciar'})


if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask mejorado...")

    # Verificar estado inicial
    if verificar_ollama():
        print("✅ Ollama conectado al inicio")
    else:
        print("⚠️ Ollama no disponible al inicio")

    app.run(debug=True, port=8000, host='0.0.0.0')