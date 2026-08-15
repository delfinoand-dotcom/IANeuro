#nueva app 
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
#import xxhash

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
import os
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db, Usuario
from auth import (
    verificar_password,
    generar_password,
    crear_token,
    obtener_usuario_actual,
    administrador_actual
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
UPLOAD_DIR = "./data"
DB_DIR = "./database"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
#UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data")
#DB_DIR = os.getenv("DB_DIR", "./database")

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

    usuario = db.query(Usuario).filter(
        Usuario.username == form_data.username
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


embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

# ==========================================
# 2. Endpoints home
# ==========================================
templates = Jinja2Templates(directory="templates")

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

    if rol not in ["admin", "usuario"]:

        raise HTTPException(
            status_code=400,
            detail="Rol inválido"
        )

    existe = db.query(Usuario).filter(
        Usuario.username == username
    ).first()

    if existe:

        raise HTTPException(
            status_code=400,
            detail="El usuario ya existe"
        )

    nuevo_usuario = Usuario(
        username=username,
        password_hash=generar_password(password),
        rol=rol
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {
        "mensaje": "Usuario creado correctamente",
        "usuario": nuevo_usuario.username,
        "rol": nuevo_usuario.rol
    }



@app.post("/cargar-documento/")
async def cargar_documento(
    file: UploadFile = File(...),
    usuario: Usuario = Depends(administrador_actual)
):
    """Sube un archivo PDF, lo procesa y lo indexa en la base de datos vectorial."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")

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
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=DB_DIR)
        vectorstore.persist()
        
        return {"mensaje": f"Documento '{file.filename}' procesado e indexado exitosamente."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el documento: {str(e)}")


@app.post("/consultar-ia/")
async def consultar_ia(
        request: PreguntaRequest, 
        usuario: Usuario = Depends(obtener_usuario_actual)
        ):
    """Consulta la base de datos vectorial con RAG utilizando el LLM."""
    if not os.path.exists(DB_DIR):
        raise HTTPException(status_code=400, detail="No hay documentos indexados. Por favor, sube un documento primero.")
    
    try:
        # Cargar base de datos existente
        vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
        retriever = vectorstore.as_retriever()
        
        # Plantilla de Prompt (Instrucciones para el LLM)
        system_prompt = (
            "Eres un asistente de investigación útil. Usa los siguientes fragmentos de contexto recuperados "
            "Eres un asistente que SOLO puede responder utilizando la información presente en el CONTEXTO."
            "Reglas:"
            "1. No utilices conocimientos propios."
            "2. No utilices información aprendida durante el entrenamiento."
            "3. No deduzcas información."
            "4. Si la respuesta no aparece explícitamente en el contexto responde únicamente: "
            "No encontré esa información en los documentos. "
            "5. Nunca inventes información."
            "para responder a la pregunta. Si no sabes la respuesta, di que no la sabes, no inventes información. "
            "Responde de manera concisa y clara.\n\n"
            "{context}"
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        
        # Crear la cadena RAG (Retrieval-Augmented Generation)
        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)
        
        # Ejecutar la consulta
        response = rag_chain.invoke({"input": request.pregunta})
        
        return {
            "pregunta": request.pregunta,
            "respuesta": response["answer"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar la respuesta: {str(e)}")
