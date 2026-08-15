import os

# Evitar que los tests utilicen una API Key real
os.environ["OPENAI_API_KEY"] = "test-api-key"

from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, Usuario
from auth import generar_password


client = TestClient(app)


# ==========================================================
# TEST 1 - Página principal
# ==========================================================

def test_home():

    response = client.get("/")

    assert response.status_code == 200


# ==========================================================
# TEST 2 - Login con usuario inexistente
# ==========================================================

def test_login_usuario_inexistente():

    response = client.post(
        "/login",
        data={
            "username": "usuario_que_no_existe",
            "password": "123456"
        }
    )

    assert response.status_code == 401


# ==========================================================
# TEST 3 - Login correcto
# ==========================================================

def test_login_correcto():

    db = SessionLocal()

    usuario = db.query(Usuario).filter(
        Usuario.username == "testusuario"
    ).first()

    if not usuario:

        usuario = Usuario(
            username="testusuario",
            password_hash=generar_password("123456"),
            rol="usuario"
        )

        db.add(usuario)
        db.commit()

    db.close()


    response = client.post(
        "/login",
        data={
            "username": "testusuario",
            "password": "123456"
        }
    )


    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data

    assert data["token_type"] == "bearer"

    assert data["rol"] == "usuario"


# ==========================================================
# TEST 4 - Consulta sin autenticación
# ==========================================================

def test_consulta_sin_login():

    response = client.post(
        "/consultar-ia/",
        json={
            "pregunta": "Pregunta de prueba"
        }
    )

    assert response.status_code == 401


# ==========================================================
# TEST 5 - Subir documento sin autenticación
# ==========================================================

def test_subir_documento_sin_login():

    response = client.post(
        "/cargar-documento/",
        files={
            "file": (
                "prueba.pdf",
                b"contenido de prueba",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 401