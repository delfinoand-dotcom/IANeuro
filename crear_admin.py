import os

from dotenv import load_dotenv
from database import SessionLocal, Usuario
from auth import generar_password

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    raise RuntimeError(
        "Faltan ADMIN_USERNAME o ADMIN_PASSWORD en el archivo .env"
    )

db = SessionLocal()

usuario_existente = db.query(Usuario).filter(
    Usuario.username == ADMIN_USERNAME
).first()

if usuario_existente:
    print("El administrador ya existe.")
else:

    nuevo_admin = Usuario(
        username=ADMIN_USERNAME,
        password_hash=generar_password(ADMIN_PASSWORD),
        rol="admin"
    )

    db.add(nuevo_admin)
    db.commit()

    print("Administrador creado correctamente.")

db.close()