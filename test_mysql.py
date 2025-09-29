import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="carlos",        # 👈 el usuario que creaste
    password="12345",     # 👈 la clave que pusiste
    database="testdb"     # 👈 la base que creaste
)

print("✅ Conexión exitosa a MySQL!")

cursor = conn.cursor()
cursor.execute("SHOW DATABASES;")

print("📂 Bases de datos disponibles:")
for db in cursor:
    print(" -", db[0])

cursor.close()
conn.close()

