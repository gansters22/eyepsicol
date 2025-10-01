import requests
import json

url = "http://localhost:5002/contacto"
data = {
    "name": "Test User",
    "email": "test@test.com",
    "message": "Mensaje de prueba desde Python"
}

response = requests.post(url, json=data)
print("Status Code:", response.status_code)
print("Response:", response.json())