import os

# ==========================================================
# VARIABLES PARA EL ENTORNO DE TEST
# Deben definirse ANTES de importar main/database/auth
# ==========================================================

os.environ["SECRET_KEY"] = "clave-secreta-exclusiva-para-tests"
os.environ["OPENAI_API_KEY"] = "test-api-key"

# Base SQLite exclusiva para pytest
os.environ["USER_DB_DIR"] = "./database/test"

# Chroma exclusivo para tests
os.environ["CHROMA_DB_DIR"] = "./database/test_chroma"


import pytest

from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from database import (
    SessionLocal,
    Usuario,
    Base,
    engine
)

from auth import (
    generar_password,
    verificar_rate_limit
)


client = TestClient(app)


# ==========================================================
# LIMPIAR BASE ANTES DE CADA TEST
# ==========================================================

@pytest.fixture(autouse=True)
def limpiar_base():

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


# ==========================================================
# FUNCIÓN AUXILIAR PARA CREAR USUARIOS
# ==========================================================

def crear_usuario_test(
    username,
    password,
    rol="usuario",
    limite=20
):

    db = SessionLocal()

    usuario = Usuario(
        username=username.strip().lower(),
        password_hash=generar_password(password),
        rol=rol,
        consultas_usadas=0,
        limite_consultas=limite,
        inicio_ventana=0
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    db.close()


# ==========================================================
# FUNCIÓN AUXILIAR LOGIN
# ==========================================================

def login(username, password):

    return client.post(
        "/login",
        data={
            "username": username,
            "password": password
        }
    )


# ==========================================================
# FUNCIÓN AUXILIAR TOKEN
# ==========================================================

def obtener_token(username, password):

    response = login(
        username,
        password
    )

    assert response.status_code == 200

    return response.json()["access_token"]


# ==========================================================
# TEST 1
# Página principal
# ==========================================================

def test_home():

    response = client.get("/")

    assert response.status_code == 200


# ==========================================================
# TEST 2
# Usuario inexistente
# ==========================================================

def test_login_usuario_inexistente():

    response = login(
        "usuario_inexistente",
        "123456"
    )

    assert response.status_code == 401


# ==========================================================
# TEST 3
# Login correcto
# ==========================================================

def test_login_correcto():

    crear_usuario_test(
        "tomas",
        "Clave123",
        "usuario"
    )

    response = login(
        "tomas",
        "Clave123"
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["rol"] == "usuario"


# ==========================================================
# TEST 4
# Username NO case-sensitive
# ==========================================================

def test_username_no_case_sensitive():

    crear_usuario_test(
        "tomas",
        "Clave123",
        "usuario"
    )

    response = login(
        "TOMAS",
        "Clave123"
    )

    assert response.status_code == 200


# ==========================================================
# TEST 5
# Contraseña SÍ case-sensitive
# ==========================================================

def test_password_case_sensitive():

    crear_usuario_test(
        "pedro",
        "ClaveABC",
        "usuario"
    )

    response = login(
        "pedro",
        "claveabc"
    )

    assert response.status_code == 401


# ==========================================================
# TEST 6
# Consulta sin autenticación
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
# TEST 7
# Subir documento sin login
# ==========================================================

def test_subir_documento_sin_login():

    response = client.post(
        "/cargar-documento/",
        files={
            "file": (
                "prueba.pdf",
                b"contenido prueba",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 401


# ==========================================================
# TEST 8
# Usuario común NO puede subir documentos
# ==========================================================

def test_usuario_no_puede_subir_documento():

    crear_usuario_test(
        "usuario_normal",
        "Clave123",
        "usuario"
    )

    token = obtener_token(
        "usuario_normal",
        "Clave123"
    )

    response = client.post(
        "/cargar-documento/",
        headers={
            "Authorization":
                f"Bearer {token}"
        },
        files={
            "file": (
                "prueba.pdf",
                b"contenido prueba",
                "application/pdf"
            )
        }
    )

    assert response.status_code == 403


# ==========================================================
# TEST 9
# Endpoint de consumo
# ==========================================================

def test_mi_uso():

    crear_usuario_test(
        "usuario_uso",
        "Clave123",
        "usuario",
        limite=20
    )

    token = obtener_token(
        "usuario_uso",
        "Clave123"
    )

    response = client.get(
        "/mi-uso/",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["usuario"] == "usuario_uso"

    assert data["consultas_usadas"] == 0

    assert data["limite_consultas"] == 20

    assert data["consultas_disponibles"] == 20


# ==========================================================
# TEST 10
# RATE LIMIT persistente
# Sin llamar realmente a OpenAI
# ==========================================================

def test_rate_limit():

    crear_usuario_test(
        "limitado",
        "Clave123",
        "usuario",
        limite=2
    )

    db = SessionLocal()

    usuario = db.query(Usuario).filter(
        Usuario.username == "limitado"
    ).first()


    # Consulta 1
    verificar_rate_limit(
        usuario=usuario,
        db=db
    )

    db.refresh(usuario)

    assert usuario.consultas_usadas == 1


    # Consulta 2
    verificar_rate_limit(
        usuario=usuario,
        db=db
    )

    db.refresh(usuario)

    assert usuario.consultas_usadas == 2


    # Consulta 3 debe bloquearse
    with pytest.raises(HTTPException) as error:

        verificar_rate_limit(
            usuario=usuario,
            db=db
        )


    assert error.value.status_code == 429

    db.close()