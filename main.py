#nueva app 
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
#import xxhash
import json
import time
import logging
from collections import Counter
# Librerías de LangChain y Chroma para RAG
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db, Usuario
from auth import (
    verificar_password,
    generar_password,
    crear_token,
    obtener_usuario_actual,
    administrador_actual,
    verificar_rate_limit
)
from seguridad_ia import (
    validar_pregunta,
    detectar_prompt_injection,
    validar_pdf,
    validar_salida
)
# ==========================================
# 1. Configuración inicial
# ==========================================
app = FastAPI(title="API RAG con LangChain y FastAPI", version="1.0")

# Variables de entorno para OpenAI (Reemplaza con tu propia API Key)
#os.environ["OPENAI_API_KEY"] = "mi apiKEY Openai"
load_dotenv()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Directorios de trabajo
#UPLOAD_DIR = "C:\\Users\Andres\Documents\phyton\proyecto py\env\data"
#DB_DIR = "C:\\Users\Andres\Documents\phyton\proyecto py\env\database"
CHROMA_DB_DIR = os.getenv(
    "CHROMA_DB_DIR",
    "./database/chroma"
)

UPLOAD_DIR = os.getenv(
    "UPLOAD_DIR",
    "./data"
)

os.makedirs(
    CHROMA_DB_DIR,
    exist_ok=True
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)
embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)
templates = Jinja2Templates(directory="templates")
#UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data")
#DB_DIR = os.getenv("DB_DIR", "./database")
# ==========================================
# CONFIGURACIÓN DE LOGS
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("api_rag")


# ==========================================
# Endpoint /login
# ==========================================
# Modelo Pydantic para la respuesta de la API
class PreguntaRequest(BaseModel):
    pregunta: str
    
@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    username = form_data.username.strip().lower()

    usuario = db.query(Usuario).filter(
        Usuario.username == username
    ).first()

    if not usuario:

        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos"
        )

    if not verificar_password(
        form_data.password,
        usuario.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos"
        )

    token = crear_token(usuario)

    return {
        "access_token": token,
        "token_type": "bearer",
        "rol": usuario.rol
    }




# ==========================================
# 2. Endpoints home
# ==========================================


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        request=request
    )


# ==========================================
# 2. Endpoints
# ==========================================
# Crear Usuarios 

@app.post("/usuarios/")
async def crear_usuario(
    username: str,
    password: str,
    rol: str = "usuario",
    admin: Usuario = Depends(administrador_actual),
    db: Session = Depends(get_db)
):

    # Normalizar nombre de usuario
    username = username.strip().lower()

    # Validar rol
    if rol not in ["admin", "usuario"]:
        raise HTTPException(
            status_code=400,
            detail="Rol inválido"
        )

    # Verificar si el usuario ya existe
    existe = db.query(Usuario).filter(
        Usuario.username == username
    ).first()

    if existe:
        raise HTTPException(
            status_code=400,
            detail="El usuario ya existe"
        )

    # ==========================================
    # DEFINIR LÍMITE SEGÚN EL ROL
    # ==========================================

    if rol == "admin":
        limite = 100
    else:
        limite = 3

    # ==========================================
    # CREAR USUARIO
    # ==========================================

    nuevo_usuario = Usuario(
        username=username,
        password_hash=generar_password(password),
        rol=rol,
        consultas_usadas=0,
        limite_consultas=limite,
        inicio_ventana=0
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {
        "mensaje": "Usuario creado correctamente",
        "usuario": nuevo_usuario.username,
        "rol": nuevo_usuario.rol,
        "limite_consultas": nuevo_usuario.limite_consultas
    }


@app.post("/cargar-documento/")
async def cargar_documento(
    file: UploadFile = File(...),
    usuario: Usuario = Depends(administrador_actual)
):
    """Sube un archivo PDF, lo procesa y lo indexa en la base de datos vectorial."""
    await validar_pdf(file)
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # Guardar el archivo temporalmente
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Cargar el PDF
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        
        # Dividir el texto en fragmentos (chunks)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(docs)
        
        # Crear la base de datos vectorial
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=CHROMA_DB_DIR)
        vectorstore.persist()
        
        return {"mensaje": f"Documento '{file.filename}' procesado e indexado exitosamente."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el documento: {str(e)}")


@app.post("/consultar-ia/")
async def consultar_ia(
    request: PreguntaRequest,
    usuario: Usuario = Depends(verificar_rate_limit)
):
    """Consulta la base de datos vectorial con RAG utilizando el LLM."""

    inicio = time.time()

    pregunta_segura = validar_pregunta(
    request.pregunta
    )

    detectar_prompt_injection(
    pregunta_segura
    )

    if not os.path.exists(CHROMA_DB_DIR):
        raise HTTPException(
            status_code=400,
            detail=(
                "No hay documentos indexados. "
                "Por favor, sube un documento primero."
            )
        )

    try:

        # Cargar base de datos existente
        vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embeddings
        )

        retriever = vectorstore.as_retriever()

        # Plantilla de Prompt
        system_prompt = (
            "Eres un asistente de investigación útil. "
            "SOLO puedes responder utilizando la información "
            "presente en el CONTEXTO.\n"
            "Reglas:\n"
            "1. No utilices conocimientos propios.\n"
            "2. No utilices información aprendida durante el entrenamiento.\n"
            "3. No deduzcas información.\n"
            "4. Si la respuesta no aparece explícitamente en el contexto, "
            "responde únicamente: "
            "'No encontré esa información en los documentos.'\n"
            "5. Nunca inventes información.\n"
            "Responde de manera concisa y clara.\n\n"
            "{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}")
        ])

        # Crear cadena RAG
        question_answer_chain = create_stuff_documents_chain(
            llm,
            prompt
        )

        rag_chain = create_retrieval_chain(
            retriever,
            question_answer_chain
        )

        # Ejecutar consulta
        response = rag_chain.invoke({
            "input": pregunta_segura
        })

        # ==========================================
        # OBSERVABILIDAD - CONSULTA CORRECTA
        # ==========================================
        # Ejecutar la consulta

        response = rag_chain.invoke({
            "input": pregunta_segura
        })

        # Validar la salida generada por el LLM

        respuesta_segura = validar_salida(
            response["answer"]
        )

        # Observabilidad
        metricas["consultas_ia_total"] += 1

        duracion_ms = int(
            (time.time() - inicio) * 1000
        )

        registrar_log(
            evento="consulta_rag",
            usuario=usuario.username,
            endpoint="/consultar-ia/",
            status_code=200,
            duracion_ms=duracion_ms,
            detalle="Consulta procesada correctamente"
        )

        # Recién después devolvemos la respuesta
        return {
            "pregunta": pregunta_segura,
            "respuesta": respuesta_segura
        }

    except Exception:

        # ==========================================
        # OBSERVABILIDAD - ERROR
        # ==========================================

        metricas["errores_ia_total"] += 1

        duracion_ms = int(
            (time.time() - inicio) * 1000
        )

        registrar_log(
            evento="error_consulta_rag",
            usuario=usuario.username,
            endpoint="/consultar-ia/",
            status_code=500,
            duracion_ms=duracion_ms,
            detalle="Error procesando la consulta"
        )

        raise HTTPException(
            status_code=500,
            detail="Error al generar la respuesta."
        )

@app.get("/mi-uso/")
async def mi_uso(
    usuario: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):

    ahora = time.time()

    # Si pasó una hora, reiniciar contador
    if (
        usuario.inicio_ventana == 0
        or ahora - usuario.inicio_ventana >= 3600
    ):
        usuario.inicio_ventana = ahora
        usuario.consultas_usadas = 0

        db.commit()
        db.refresh(usuario)

    disponibles = (
        usuario.limite_consultas
        - usuario.consultas_usadas
    )

    if disponibles < 0:
        disponibles = 0

    return {
        "usuario": usuario.username,
        "rol": usuario.rol,
        "consultas_usadas": usuario.consultas_usadas,
        "limite_consultas": usuario.limite_consultas,
        "consultas_disponibles": disponibles
    }

# ==========================================
# MÉTRICAS
# ==========================================

metricas = Counter()


# ==========================================
# FUNCIÓN PARA LOGS ESTRUCTURADOS
# ==========================================

def registrar_log(
    evento,
    usuario=None,
    endpoint=None,
    status_code=None,
    duracion_ms=None,
    detalle=None
):
    log = {
        "evento": evento,
        "usuario": usuario,
        "endpoint": endpoint,
        "status_code": status_code,
        "duracion_ms": duracion_ms,
        "detalle": detalle
    }

    logger.info(
        json.dumps(
            log,
            ensure_ascii=False
        )
    )
@app.get("/metrics")
async def obtener_metricas(
        usuario: Usuario = Depends(
        administrador_actual
    )
):

    return {
        "consultas_ia_total":
            metricas["consultas_ia_total"],

        "errores_ia_total":
            metricas["errores_ia_total"]
    }