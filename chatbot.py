from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import sys

app = Flask(__name__)
# Configuración CORS más permisiva
CORS(app, origins=["http://localhost", "http://127.0.0.1", "http://192.168.1.81", "*"])

# CONFIGURACIÓN
MODEL = "llama3.2:1b"
OLLAMA_URL = "http://localhost:11434/api/generate"

print("🚀 Iniciando Eyebot Chatbot...")
print(f"📦 Modelo: {MODEL}")
print("🔍 Verificando servicios...")


def verificar_ollama():
    """Verifica si Ollama está disponible"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama conectado")
            return True
        return False
    except Exception as e:
        print(f"❌ Ollama no disponible: {e}")
        return False


def generar_respuesta(pregunta):
    """Genera respuesta inteligente con fallbacks"""

    # RESPUESTAS RÁPIDAS MEJORADAS
    respuestas_rapidas = {
        "hola": "¡Hola! Soy Eyebot, tu psicólogo virtual. ¿En qué puedo ayudarte hoy? 😊",
        "que eres": "Soy Eyebot, especialista en salud mental. Te ayudo con relajación, estrés, ansiedad y bienestar emocional.",
        "ansiedad": "🤗 **Para la ansiedad:**\n• Respiración 4-7-8\n• Mindfulness 5min\n• Ejercicio suave\n• Hablar con alguien",
        "estres": "💆‍♂️ **Manejo de estrés:**\n• Organiza tu tiempo\n• Pausas activas\n• Ejercicio regular\n• Límites saludables",
        "dormir": "😴 **Mejor sueño:**\n• Horarios fijos\n• Ambiente oscuro\n• Sin pantallas 1h antes\n• Lectura ligera",
        "depresion": "🤗 **Depresión:** Busca apoyo profesional. Mientras:\n• Mantén rutinas\n• Contacto social\n• Ejercicio suave",
        "novia me dejó": "💔 **Ruptura amorosa:**\n• Permítete sentir\n• Habla con amigos\n• Mantén rutinas\n• Ejercicio ayuda",
        "triste": "😔 **Tristeza:**\n• Habla con alguien\n• Escribe sentimientos\n• Sal a caminar\n• Música que te guste",
        "estoisismo": "🏛️ **Estoicismo:** Enfócate en lo controlable, acepta lo que no. Muy útil para salud mental!",
        "futbol": "⚽ **Fútbol:** Excelente para salud mental - ejercicio, equipo, libera estrés.",
        "cr7": "⚽ **Cristiano Ronaldo:** Ejemplo de disciplina y mentalidad deportiva.",
        "troya": "🏛️ **Troya:** Ciudad antigua - representa perseverancia.",
        "gracias": "¡De nada! 💙 Cuida tu mente como cuidas tu cuerpo.",
        "adios": "¡Hasta luego! Cuídate mucho 😊"
    }

    pregunta_lower = pregunta.lower().strip()

    # Buscar en respuestas rápidas primero
    for clave, respuesta in respuestas_rapidas.items():
        if clave in pregunta_lower:
            print(f"⚡ Respuesta rápida: '{clave}'")
            return respuesta

    # Intentar con Ollama si está disponible
    if verificar_ollama():
        try:
            prompt = f"Eres psicólogo. Responde breve y útil en español: {pregunta}"
            payload = {
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,
                    "top_p": 0.8
                }
            }

            print(f"🤖 Consultando {MODEL}: {pregunta[:30]}...")
            response = requests.post(OLLAMA_URL, json=payload, timeout=15)

            if response.status_code == 200:
                data = response.json()
                respuesta = data.get("response", "").strip()
                if respuesta:
                    return respuesta
                else:
                    return "¿Podrías reformular tu pregunta? No la entendí completamente."
            else:
                return "El servicio está ocupado. Intenta con una pregunta más breve."

        except requests.exceptions.Timeout:
            return "La respuesta está tardando. Intenta con preguntas más específicas."
        except Exception as e:
            print(f"💥 Error Ollama: {e}")
            return "Problema técnico. Puedo ayudarte con temas de salud mental."

    # Fallback final
    return "¡Hola! 😊 Puedo ayudarte con: ansiedad, estrés, sueño, relaciones o bienestar emocional. ¿Qué te interesa?"


@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400

        mensaje = data.get('mensaje', '').strip()
        user_id = data.get('user_id', 'default')

        print(f"💬 Mensaje recibido: {mensaje}")

        if not mensaje:
            return jsonify({'error': 'Mensaje vacío'}), 400

        respuesta = generar_respuesta(mensaje)

        return jsonify({
            'respuesta': respuesta,
            'user_id': user_id,
            'status': 'success',
            'model': MODEL
        })

    except Exception as e:
        print(f"🔥 Error en /api/chat: {e}")
        return jsonify({
            'respuesta': '¡Hola! Estoy aquí para ayudarte 😊 ¿En qué puedo asistirte?',
            'status': 'success'
        })


@app.route('/api/health', methods=['GET'])
def health_check():
    ollama_ok = verificar_ollama()
    return jsonify({
        'status': 'ok',
        'ollama': 'connected' if ollama_ok else 'disconnected',
        'model': MODEL,
        'message': 'Servidor funcionando correctamente'
    })


@app.route('/')
def index():
    return jsonify({
        'message': 'Eyebot Chatbot API',
        'version': '1.0',
        'endpoints': ['/api/chat', '/api/health']
    })


if __name__ == '__main__':
    # Verificar Ollama al inicio
    ollama_status = verificar_ollama()

    print("🌐 Servidor listo en http://localhost:8005")
    print("📞 Endpoints disponibles:")
    print("   POST /api/chat")
    print("   GET  /api/health")
    print("   GET  /")
    print("\n⚡ Ejecutando servidor...")

    try:
        app.run(debug=True, port=8005, host='0.0.0.0', use_reloader=False)
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
    except Exception as e:
        print(f"💥 Error iniciando servidor: {e}")