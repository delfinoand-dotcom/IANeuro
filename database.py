import os

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float
)

from sqlalchemy.orm import (
    declarative_base,
    sessionmaker
)


# ==========================================
# Directorio de base de datos
# ==========================================

USER_DB_DIR = os.getenv(
    "USER_DB_DIR",
    "./database/usuarios"
)

os.makedirs(
    USER_DB_DIR,
    exist_ok=True
)

DATABASE_URL = (
    f"sqlite:///{USER_DB_DIR}/usuarios.db"
)


# ==========================================
# SQLAlchemy
# ==========================================

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


# ==========================================
# Modelo Usuario
# ==========================================

class Usuario(Base):

    __tablename__ = "usuarios"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    rol = Column(
        String,
        nullable=False,
        default="usuario"
    )

    # Cantidad utilizada en la ventana actual
    consultas_usadas = Column(
        Integer,
        nullable=False,
        default=0
    )

    # Máximo permitido por hora
    limite_consultas = Column(
        Integer,
        nullable=False,
        default=20
    )

    # Momento en que comenzó la ventana
    # guardado como timestamp Unix
    inicio_ventana = Column(
        Float,
        nullable=False,
        default=0.0
    )


# Crear tablas
Base.metadata.create_all(
    bind=engine
)


# ==========================================
# Dependencia FastAPI
# ==========================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()