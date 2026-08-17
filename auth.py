
import os
from datetime import datetime, timedelta, timezone

import time
from collections import defaultdict
from fastapi import HTTPException

import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_db, Usuario

#==========================================
#Configuración
#==========================================

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
    "No se ha configurado SECRET_KEY en el archivo .env"
    )

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

#==========================================
#Configuración de contraseñas
#==========================================

password_hash = PasswordHash.recommended()

#==========================================
#Configuración OAuth2
#==========================================

oauth2_scheme = OAuth2PasswordBearer(
tokenUrl="/login"
)

#==========================================
#Verificar contraseña
#==========================================

def verificar_password(
    password,
    password_hash_db
    ):
    return password_hash.verify(
    password,
    password_hash_db
    )

#==========================================
#Generar contraseña
#==========================================

def generar_password(password):
    return password_hash.hash(password)

#==========================================
#Crear JWT
#==========================================

def crear_token(usuario):

    expiracion = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    datos = {
        "sub": usuario.username,
        "rol": usuario.rol,
        "exp": expiracion
    }

    return jwt.encode(
        datos,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
#==========================================
#Obtener usuario autenticado
#==========================================

def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido",
        headers={
            "WWW-Authenticate": "Bearer"
        }
    )

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if username is None:
            raise credenciales_invalidas

    except jwt.PyJWTError:

        raise credenciales_invalidas


    usuario = db.query(Usuario).filter(
        Usuario.username == username
    ).first()


    if usuario is None:

        raise credenciales_invalidas


    return usuario
#==========================================
#Verificar administrador
#==========================================

def administrador_actual(
usuario: Usuario = Depends(
obtener_usuario_actual
)
):

    if usuario.rol != "admin":

        raise HTTPException(
        status_code=403,
        detail="No tiene permisos de administrador"
    )

    return usuario

# ==========================================
# RATE LIMIT PERSISTENTE
# ==========================================

VENTANA_SEGUNDOS = 3600


def verificar_rate_limit(
    usuario: Usuario = Depends(
        obtener_usuario_actual
    ),
    db: Session = Depends(get_db)
):

    ahora = time.time()


    # ======================================
    # Iniciar una nueva ventana
    # ======================================

    if (
        usuario.inicio_ventana == 0
        or
        ahora - usuario.inicio_ventana
        >= VENTANA_SEGUNDOS
    ):

        usuario.inicio_ventana = ahora

        usuario.consultas_usadas = 0


    # ======================================
    # Comprobar límite
    # ======================================

    if (
        usuario.consultas_usadas
        >= usuario.limite_consultas
    ):

        tiempo_transcurrido = (
            ahora
            - usuario.inicio_ventana
        )

        tiempo_restante = int(
            VENTANA_SEGUNDOS
            - tiempo_transcurrido
        )

        if tiempo_restante < 1:
            tiempo_restante = 1


        raise HTTPException(

            status_code=429,

            detail=(
                "Has alcanzado el límite de "
                f"{usuario.limite_consultas} "
                "consultas por hora."
            ),

            headers={
                "Retry-After":
                    str(tiempo_restante)
            }
        )


    # ======================================
    # Registrar consulta
    # ======================================

    usuario.consultas_usadas += 1


    db.commit()

    db.refresh(usuario)


    print(
        "RATE LIMIT -> "
        f"usuario={usuario.username}, "
        f"consultas="
        f"{usuario.consultas_usadas}/"
        f"{usuario.limite_consultas}"
    )


    return usuario
