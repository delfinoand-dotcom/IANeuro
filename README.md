# API RAG con FastAPI, ChromaDB y seguridad

API desarrollada en Python con **FastAPI**, **LangChain**, **ChromaDB** y un modelo LLM de OpenAI.

El sistema implementa una arquitectura **RAG (Retrieval-Augmented Generation)** que permite cargar documentos PDF, almacenarlos en una base vectorial y realizar consultas utilizando exclusivamente el contexto recuperado de dichos documentos.

Además, incorpora autenticación, autorización por roles, rate limiting, observabilidad, modelo de amenazas STRIDE y mitigaciones específicas de seguridad para IA.

---

## 1. Arquitectura general

El sistema utiliza dos bases de datos con responsabilidades diferentes:

### SQLite

Utilizada para almacenar:

- usuarios;
- contraseñas hasheadas;
- roles;
- límites de consultas;
- consultas utilizadas;
- ventana temporal del rate limiting.

### ChromaDB

Utilizada como base de datos vectorial del sistema RAG.

Almacena:

- fragmentos de los documentos;
- embeddings;
- metadatos;
- información necesaria para realizar búsquedas semánticas.

Flujo general:

Usuario  
→ FastAPI  
→ Autenticación JWT  
→ Autorización / Rate limiting  
→ Validación de seguridad  
→ ChromaDB  
→ Recuperación de contexto  
→ LLM  
→ Validación de salida  
→ Respuesta

---

## 2. Funcionalidades

La API permite:

- iniciar sesión;
- autenticarse mediante JWT;
- utilizar roles `admin` y `usuario`;
- crear usuarios desde una cuenta administrativa;
- cargar documentos PDF;
- indexar documentos en ChromaDB;
- consultar el sistema RAG;
- controlar el número de consultas por usuario;
- consultar el consumo disponible;
- registrar logs estructurados;
- obtener métricas básicas;
- validar entradas y salidas del sistema de IA.

---

## 3. Roles

### Administrador

Puede:

- iniciar sesión;
- crear usuarios;
- cargar documentos;
- realizar consultas al RAG;
- acceder a métricas administrativas.

### Usuario

Puede:

- iniciar sesión;
- consultar el RAG;
- consultar su consumo.

No puede realizar operaciones administrativas como cargar documentos o crear usuarios.

Los permisos son verificados en el backend y no dependen únicamente de la interfaz web.

---

## 4. RAG

Los documentos PDF son procesados y divididos en fragmentos.

Posteriormente se generan embeddings que son almacenados en **ChromaDB**.

Cuando un usuario realiza una pregunta:

1. se valida la entrada;
2. se realiza una búsqueda semántica en ChromaDB;
3. se recuperan los fragmentos relevantes;
4. esos fragmentos son enviados como contexto al LLM;
5. el modelo genera una respuesta;
6. la salida es validada antes de ser enviada al usuario.

El prompt del sistema indica al modelo que debe responder utilizando únicamente la información disponible en el contexto recuperado.

---

## 5. Autenticación y autorización

La aplicación utiliza autenticación mediante **JSON Web Tokens (JWT)**.

Las contraseñas no se almacenan en texto plano, sino mediante hash.

Los endpoints protegidos verifican:

- identidad del usuario;
- validez del token;
- rol;
- permisos necesarios.

---

## 6. Rate limiting

El sistema incorpora control de consumo por usuario.

Cada usuario dispone de un número máximo de consultas dentro de una ventana temporal de una hora.

Cuando se supera el límite, la API responde:

`HTTP 429 - Too Many Requests`

El estado del consumo se almacena en SQLite.

El endpoint:

`GET /mi-uso/`

permite conocer:

- consultas utilizadas;
- límite;
- consultas disponibles.

---

## 7. Observabilidad

La API implementa observabilidad básica mediante:

### Logs estructurados

Se registran datos como:

- evento;
- usuario;
- endpoint;
- código HTTP;
- duración de la operación.

Ejemplo:

```json
{
  "evento": "consulta_rag",
  "usuario": "usuario1",
  "endpoint": "/consultar-ia/",
  "status_code": 200,
  "duracion_ms": 842,
  "detalle": "Consulta procesada correctamente"
}
```

### Métricas

El sistema mantiene métricas básicas como:

- consultas IA procesadas;
- errores durante las consultas.

El acceso a las métricas está restringido a administradores.

---

## 8. Seguridad para IA

El módulo `seguridad_ia.py` incorpora controles específicos para sistemas basados en LLM.

### Validación de entradas

Se controlan:

- preguntas vacías;
- longitud máxima;
- caracteres de control;
- entradas excesivas o malformadas.

### Prompt Injection

Se implementa un guardrail heurístico para detectar patrones relacionados con intentos de:

- ignorar instrucciones anteriores;
- revelar el prompt del sistema;
- evitar las reglas;
- asumir privilegios administrativos;
- utilizar información externa.

### Validación de documentos

Antes de aceptar un PDF se verifica:

- tipo MIME;
- extensión `.pdf`;
- tamaño máximo;
- firma básica `%PDF`.

### Validación de salida

Antes de devolver una respuesta se aplican controles para:

- respuestas vacías;
- respuestas excesivamente largas;
- posibles API Keys;
- Bearer tokens;
- variables sensibles como `SECRET_KEY`.

---

## 9. Modelo de amenazas STRIDE

El proyecto incluye:

`STRIDE.md`

El documento analiza las siguientes categorías:

- **S — Spoofing:** suplantación de identidad.
- **T — Tampering:** manipulación.
- **R — Repudiation:** repudio.
- **I — Information Disclosure:** divulgación de información.
- **D — Denial of Service:** denegación de servicio.
- **E — Elevation of Privilege:** elevación de privilegios.

También documenta las mitigaciones implementadas y los riesgos residuales.

---

## 10. Estructura del proyecto

```text
proyecto/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── database/
│   ├── usuarios/
│   └── chroma/
│
├── templates/
│   └── index.html
│
├── tests/
│   ├── test_main.py
│   └── test_seguridad_ia.py
│
├── .env
├── .env.example
├── .gitignore
├── auth.py
├── crear_admin.py
├── database.py
├── main.py
├── pytest.ini
├── requirements.txt
├── seguridad_ia.py
├── STRIDE.md
└── README.md
```

El archivo `.env` y las bases de datos no deben publicarse en el repositorio.

---

## 11. Instalación

Clonar el repositorio:

```bash
git clone https://github.com/delfinoand-dotcom/IANeuro.git
```

Entrar al proyecto y crear un entorno virtual:

```bash
python -m venv venv
```

En Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Instalar dependencias:

```bash
python -m pip install -r requirements.txt
```

---

## 12. Variables de entorno

Crear un archivo `.env` tomando como referencia `.env.example`.

Ejemplo:

```env
OPENAI_API_KEY=TU_API_KEY
SECRET_KEY=TU_SECRET_KEY

USER_DB_DIR=./database/usuarios
CHROMA_DB_DIR=./database/chroma
UPLOAD_DIR=./data
```

**Nunca publicar el archivo `.env` ni claves reales en GitHub.**

---

## 13. Crear administrador

Ejecutar:

```bash
python crear_admin.py
```

Esto crea el usuario administrador inicial en SQLite.

---

## 14. Ejecutar la API

Con el entorno virtual activado:

```bash
python -m uvicorn main:app --reload
```

La aplicación quedará disponible localmente en el puerto configurado por Uvicorn.

---

## 15. Swagger

FastAPI proporciona documentación interactiva mediante Swagger.

Con la API ejecutándose localmente:

`http://127.0.0.1:8000/docs`

Swagger permite probar los endpoints y verificar los controles de autenticación y autorización.

Los endpoints protegidos continúan requiriendo las credenciales o token correspondiente.

---

## 16. Tests automatizados

El proyecto utiliza **pytest**.

Ejecutar:

```bash
python -m pytest -v
```

Actualmente la suite contiene:

- 10 tests de autenticación, autorización y rate limiting;
- 16 tests de seguridad específica para IA.

Resultado esperado:

```text
26 passed
```

Entre otras cosas, los tests verifican:

- login;
- roles;
- acceso no autorizado;
- rate limiting;
- validación de preguntas;
- prompt injection básico;
- filtrado de información sensible;
- validación de PDFs;
- archivos falsos;
- límite de tamaño de archivos.

---

## 17. Integración continua

El proyecto utiliza **GitHub Actions**.

El workflow se encuentra en:

`.github/workflows/ci.yml`

Ante un `push` o `pull_request` sobre la rama `main`, el pipeline:

1. descarga el código;
2. configura Python;
3. instala las dependencias;
4. ejecuta automáticamente pytest.

Esto permite verificar que los controles principales continúan funcionando después de realizar modificaciones.

---

## 18. Consideraciones de seguridad

Las mitigaciones implementadas reducen riesgos, pero no garantizan seguridad absoluta.

Entre los riesgos residuales se encuentran:

- técnicas avanzadas de prompt injection;
- instrucciones maliciosas dentro de documentos;
- robo de JWT;
- ataques de fuerza bruta;
- PDFs especialmente diseñados contra el parser;
- patrones de información sensible no contemplados por los filtros.

Para un entorno productivo serían necesarios controles adicionales.

---

## 19. Tecnologías utilizadas

- Python
- FastAPI
- Uvicorn
- LangChain
- ChromaDB
- OpenAI
- SQLite
- SQLAlchemy
- JWT
- Pytest
- GitHub Actions

---

## 20. Estado de pruebas

Última ejecución local:

**26 tests superados correctamente.**

La suite valida controles funcionales y de seguridad de la API.

## 21. Persistencia e incorporación incremental de conocimiento

El sistema RAG utiliza ChromaDB como base de datos vectorial persistente.

La incorporación de documentos es incremental: cuando un administrador
carga un nuevo documento, sus fragmentos y embeddings se agregan a la
colección existente sin eliminar los documentos previamente indexados.

Por lo tanto, la base de conocimiento disponible para el sistema RAG
puede crecer progresivamente a medida que se incorporan nuevos documentos.

Es importante aclarar que este mecanismo no implica un reentrenamiento
del modelo de lenguaje. El LLM no modifica sus parámetros ni "aprende"
los documentos cargados. La información se conserva en ChromaDB y es
recuperada dinámicamente mediante RAG al realizar cada consulta.

En la implementación actual, la eliminación de un archivo PDF original
no elimina automáticamente la información que ya fue indexada en
ChromaDB.