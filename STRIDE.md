# Modelo de amenazas STRIDE - API RAG

## 1. Alcance del sistema

El sistema está compuesto por:

- API desarrollada con FastAPI.
- Autenticación mediante JWT.
- Roles `admin` y `usuario`.
- Base de usuarios en SQLite.
- Base vectorial ChromaDB para RAG.
- Carga de documentos PDF restringida a administradores.
- Consultas al modelo mediante RAG.
- Rate limiting persistente por usuario.
- Logs estructurados y métricas básicas.
- Variables sensibles almacenadas en `.env`.

---

## 2. S - Spoofing (Suplantación de identidad)

### Amenaza

Un atacante podría intentar hacerse pasar por otro usuario mediante:

- credenciales robadas;
- contraseñas débiles;
- reutilización de un JWT;
- intento de acceso con usuario inexistente.

### Mitigaciones implementadas

- autenticación mediante usuario y contraseña;
- contraseñas almacenadas mediante hash;
- uso de JWT firmado con `SECRET_KEY`;
- expiración de los tokens;
- validación del JWT en endpoints protegidos;
- normalización del nombre de usuario;
- contraseña sensible a mayúsculas y minúsculas.

### Evidencias

Tests asociados:

- `test_login_usuario_inexistente`
- `test_login_correcto`
- `test_username_no_case_sensitive`
- `test_password_case_sensitive`

---

## 3. T - Tampering (Manipulación)

### Amenaza

Un usuario podría intentar:

- modificar información sin autorización;
- subir documentos PDF sin permisos;
- crear usuarios;
- alterar datos de la base de usuarios;
- modificar el conocimiento almacenado en ChromaDB.

### Mitigaciones implementadas

- `/cargar-documento/` requiere rol `admin`;
- `/usuarios/` requiere rol `admin`;
- validación de roles en el backend;
- acceso a SQLite mediante SQLAlchemy;
- separación entre base de usuarios y base ChromaDB;
- los permisos no dependen únicamente del frontend.

### Evidencias

- `test_usuario_no_puede_subir_documento`
- respuesta HTTP `403 Forbidden` para usuarios sin privilegios.

---

## 4. R - Repudiation (Repudio)

### Amenaza

Un usuario podría negar haber realizado una acción o una consulta.

### Mitigaciones implementadas

El sistema incorpora logs estructurados que registran:

- evento;
- usuario;
- endpoint;
- código de estado;
- duración de la operación.

Ejemplo:

```json
{
  "evento": "consulta",
  "usuario": "pepe",
  "endpoint": "/consultar-ia/",
  "status_code": 200,
  "duracion_ms": 842,
  "detalle": "Consulta procesada correctamente"
}
```
---

## 5. I - Information Disclosure (Divulgación de información)

### Amenaza

El sistema podría exponer información sensible como:

- API Key del proveedor LLM;
- `SECRET_KEY` utilizada para JWT;
- contraseñas de usuarios;
- tokens de autenticación;
- información interna contenida en excepciones;
- información sensible generada accidentalmente por el LLM.

### Mitigaciones implementadas

- variables sensibles almacenadas en `.env`;
- `.env` excluido del repositorio mediante `.gitignore`;
- contraseñas almacenadas mediante hash;
- mensajes de error controlados;
- filtrado de posibles datos sensibles en las respuestas del LLM;
- endpoint `/metrics` restringido al administrador.

---

## 6. D - Denial of Service (Denegación de servicio)

### Amenaza

Un usuario podría realizar una cantidad excesiva de consultas provocando:

- consumo excesivo de recursos;
- aumento del costo del servicio LLM;
- degradación del rendimiento;
- saturación de la API.

### Mitigaciones implementadas

- rate limiting por usuario;
- límite de consultas configurable;
- persistencia del consumo en SQLite;
- respuesta HTTP `429 Too Many Requests`;
- contador de consultas utilizadas y disponibles.

### Evidencias

- `test_rate_limit`;
- endpoint `/mi-uso/`.

---

## 7. E - Elevation of Privilege (Elevación de privilegios)

### Amenaza

Un usuario con rol normal podría intentar obtener privilegios administrativos para:

- crear otros usuarios;
- cargar documentos;
- modificar el conocimiento almacenado;
- acceder a funciones administrativas.

### Mitigaciones implementadas

- roles `admin` y `usuario`;
- validación de autorización en el backend;
- dependencia `administrador_actual`;
- endpoints administrativos protegidos;
- respuesta HTTP `403 Forbidden` ante accesos no autorizados.

### Evidencias

- `test_usuario_no_puede_subir_documento`.

---

## 8. Mitigaciones específicas de seguridad para IA

El sistema incorpora controles adicionales orientados a los riesgos propios
de aplicaciones basadas en LLM y RAG.

### Validación de entradas

La función `validar_pregunta()` permite:

- rechazar preguntas vacías;
- limitar la longitud máxima de las consultas;
- rechazar caracteres de control no permitidos;
- evitar entradas excesivas o malformadas.

### Protección frente a Prompt Injection

La función `detectar_prompt_injection()` implementa un guardrail básico
antes de enviar la consulta al LLM.

Se buscan patrones relacionados con intentos de:

- ignorar las instrucciones anteriores;
- revelar el prompt del sistema;
- evitar las reglas establecidas;
- asumir privilegios administrativos;
- forzar el uso de información externa.

Las consultas detectadas son rechazadas antes de llegar al LLM.

Esta protección es heurística y reduce el riesgo, pero no garantiza la
detección de todos los ataques de prompt injection.

### Validación de documentos

Antes de incorporar un PDF al sistema RAG se comprueba:

- tipo MIME;
- extensión `.pdf`;
- tamaño máximo permitido;
- firma básica `%PDF`.

Esto reduce el riesgo de procesar archivos que intenten hacerse pasar por PDF.

### Validación de salidas

La función `validar_salida()` procesa la respuesta antes de enviarla al usuario.

Se aplican controles para:

- detectar respuestas vacías;
- limitar la longitud de la respuesta;
- ocultar posibles API Keys;
- ocultar tokens;
- ocultar variables sensibles como `SECRET_KEY`.

### Flujo de seguridad de IA

Pregunta del usuario
→ Validación de entrada
→ Detección de Prompt Injection
→ RAG / ChromaDB
→ LLM
→ Validación de salida
→ Respuesta al usuario

---

## 9. Riesgos residuales

A pesar de las mitigaciones implementadas, permanecen riesgos como:

- robo de tokens JWT;
- ataques de fuerza bruta contra el login;
- técnicas avanzadas de prompt injection;
- instrucciones maliciosas contenidas dentro de documentos;
- archivos PDF especialmente diseñados para atacar al parser;
- fuga de información no reconocida por los filtros;
- consumo elevado de recursos mediante entradas especialmente diseñadas.

Estos riesgos podrían requerir controles adicionales en un entorno de producción.

---

## 10. Conclusión

El análisis STRIDE permitió identificar amenazas relacionadas con
suplantación de identidad, manipulación, repudio, divulgación de información,
denegación de servicio y elevación de privilegios.

La API implementa controles como autenticación JWT, autorización mediante
roles, hashing de contraseñas, rate limiting, logs estructurados, métricas,
validación de archivos y mecanismos específicos de seguridad para IA.

Las mitigaciones específicas para el sistema RAG incluyen validación de
entradas, detección básica de prompt injection y validación de las respuestas
generadas por el LLM.