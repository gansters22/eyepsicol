#!/bin/bash

cd ~/proyectos/intento\ 3mil/EyePsicol-2.3/EyePsyco/

echo "🧪 INICIANDO PRUEBAS DE FORMULARIOS"
echo "====================================="

# Ver estado inicial
echo "1. Estado inicial de la base de datos:"
sqlite3 eyepsicol.db "SELECT COUNT(*) as total_contactos FROM contactos;"
sqlite3 eyepsicol.db "SELECT fuente, COUNT(*) FROM contactos GROUP BY fuente;"

echo ""
echo "2. Probando endpoints con curl..."
# Probar mindfulness
curl -s -X POST http://localhost:5002/contacto \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Automatizado Mindfulness", "email": "auto@mindfulness.com", "message": "Test automatizado", "fuente": "mindfulness"}' | grep -o '"success":[^,]*'

# Probar tips
curl -s -X POST http://localhost:5002/contacto \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Automatizado Tips", "email": "auto@tips.com", "message": "Test automatizado", "fuente": "tips"}' | grep -o '"success":[^,]*'

# Probar videos
curl -s -X POST http://localhost:5002/contacto \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Automatizado Videos", "email": "auto@videos.com", "message": "Test automatizado", "fuente": "videos"}' | grep -o '"success":[^,]*'

echo ""
echo "3. Estado final de la base de datos:"
sqlite3 eyepsicol.db "SELECT id, nombre, email, fuente FROM contactos ORDER BY id DESC LIMIT 5;"

echo ""
echo "4. Resumen por fuentes:"
sqlite3 eyepsicol.db "SELECT fuente, COUNT(*) as total FROM contactos GROUP BY fuente;"

echo ""
echo "✅ Pruebas completadas"
