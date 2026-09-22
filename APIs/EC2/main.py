import re
import math
from typing import Any, List

import spacy
from spacy import displacy

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError

from pydantic import BaseModel, field_validator

from mangum import Mangum

# ------------------------------------------------------------------------------
# 1. Carga del Modelo spaCy
# ------------------------------------------------------------------------------
try:
    nlp = spacy.load("es_core_news_sm")
except Exception as e:
    raise RuntimeError(f"Error al cargar el modelo es_core_news_sm: {e}")

app = FastAPI(
    title="Dashboard API NLP",
    version="1.0.1",
    description="API de NLP con interfaz gráfica e interoperabilidad ajustada a la guía"
)

# Middleware para interceptar solicitudes con Content-Type inválido en Lambda/EC2
@app.middleware("http")
async def validate_content_type_middleware(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH"] and request.url.path.startswith("/api/v1/"):
        content_type = request.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Content-Type debe ser application/json."}
            )
    return await call_next(request)

# ------------------------------------------------------------------------------
# 2. Manejo Global de Errores para Garantizar HTTP 400 / 500 controlados
# ------------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # FIX: se extrae el mensaje real del validador en vez de un texto genérico fijo.
    # Los validadores ahora lanzan ValueError (patrón idiomático de Pydantic v2),
    # que FastAPI envuelve automáticamente en RequestValidationError.
    errors = exc.errors()
    detail = "Entrada inválida o formato incorrecto."
    if errors:
        msg = errors[0].get("msg", detail)
        # Pydantic v2 antepone "Value error, " a los mensajes lanzados con ValueError
        detail = msg.replace("Value error, ", "")
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detail})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# FIX: handler genérico para cualquier excepción no controlada (p. ej. errores internos
# de spaCy con entradas extremas). Evita que Lambda/uvicorn devuelvan un traceback crudo
# y garantiza siempre una respuesta JSON, aunque el código de estado siga siendo 5xx.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Error interno del servidor."}
    )

# ------------------------------------------------------------------------------
# 3. Modelos de Datos (Pydantic) y Validadores Strict
# ------------------------------------------------------------------------------
# FIX: los validadores ahora lanzan ValueError en lugar de HTTPException.
# Es el patrón soportado oficialmente por Pydantic v2 dentro de field_validator;
# HTTPException lanzada ahí dependía de que Starlette la interceptara "por fuera"
# del ciclo de validación, lo cual no está garantizado entre versiones.
def validate_single_text_str(v: Any) -> str:
    if v is None or not isinstance(v, str):
        raise ValueError("El texto debe ser una cadena de caracteres.")
    if not v.strip():
        raise ValueError("El texto no puede estar vacío ni contener solo espacios.")
    return v

def validate_text_batch_input(v: Any) -> List[str]:
    if v is None:
        raise ValueError("El campo 'text' no puede ser nulo.")

    if isinstance(v, str):
        if not v.strip():
            raise ValueError("El texto no puede estar vacío ni contener solo espacios.")
        return [v]
    elif isinstance(v, list):
        if len(v) == 0:
            raise ValueError("La lista de textos no puede estar vacía.")
        texts = []
        for item in v:
            if item is None or not isinstance(item, str):
                raise ValueError("Todos los elementos deben ser cadenas de texto.")
            if not item.strip():
                raise ValueError("Ningún texto puede estar vacío o contener solo espacios.")
            texts.append(item)
        return texts
    else:
        raise ValueError("El campo 'text' debe ser string o una lista de strings.")

class BatchTextRequest(BaseModel):
    text: Any

    @field_validator("text")
    @classmethod
    def check_text(cls, v):
        return validate_text_batch_input(v)

class VisualizeDepRequest(BaseModel):
    text: Any

    @field_validator("text")
    @classmethod
    def check_single_text(cls, v):
        if isinstance(v, list):
            raise ValueError("visualize/dep solo procesa un único documento, no un lote.")
        return validate_single_text_str(v)

class VectorizeRequest(BaseModel):
    documents: Any

    @field_validator("documents")
    @classmethod
    def check_documents(cls, v):
        if v is None or not isinstance(v, list):
            raise ValueError("'documents' debe ser una lista de cadenas de texto.")
        if len(v) < 2:
            raise ValueError("Se requieren al menos 2 documentos para vectorizar.")

        for doc in v:
            if doc is None or not isinstance(doc, str):
                raise ValueError("Todos los documentos deben ser cadenas de texto.")
            if not doc.strip():
                raise ValueError("Los documentos no pueden estar vacíos ni contener solo espacios.")
        return v

# ------------------------------------------------------------------------------
# 4. Helper de Limpieza
# ------------------------------------------------------------------------------
def clean_single_text_tokens(text: str) -> List[str]:
    doc = nlp(text)
    tokens = []
    for token in doc:
        if token.is_stop or token.is_punct:
            continue
        cleaned_tok = token.text.strip().lower()
        if cleaned_tok:
            tokens.append(cleaned_tok)
    return tokens

def clean_single_text(text: str) -> str:
    tokens = clean_single_text_tokens(text)
    cleaned = " ".join(tokens)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# ------------------------------------------------------------------------------
# 5. Interfaz Gráfica Dashboard (Ruta Raíz /)
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def read_root():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard API NLP</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f3f4f8; margin: 0; padding: 40px; color: #333; }
            .container { max-width: 800px; margin: 0 auto; }
            .card { background-color: #ffffff; border-radius: 8px; padding: 32px 40px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 24px; }
            h1 { font-size: 26px; color: #1e3a60; margin-top: 0; margin-bottom: 10px; }
            p { font-size: 15px; margin: 8px 0; color: #4a5568; }
            .badge { display: inline-block; background-color: #e6fffa; color: #234e52; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 14px; }
            textarea { width: 100%; height: 100px; border: 1px solid #cbd5e0; border-radius: 6px; padding: 10px; box-sizing: border-box; font-size: 14px; margin-top: 10px; }
            .btn-group { margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap; }
            button { background-color: #3182ce; color: white; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; }
            button:hover { background-color: #2b6cb0; }
            #output-container { margin-top: 20px; background-color: #f7fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 15px; max-height: 400px; overflow-y: auto; }
            pre { margin: 0; font-family: monospace; white-space: pre-wrap; word-break: break-all; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>Dashboard API NLP</h1>
                <p>Estado del servicio: <span class="badge">OK</span></p>
            </div>
            <div class="card">
                <h2>Consola de Pruebas Interactiva</h2>
                <textarea id="inputText" placeholder="Escribe tu texto aquí..."></textarea>
                <div class="btn-group">
                    <button onclick="executeApi('/api/v1/clean')">Limpiar Texto</button>
                    <button onclick="executeApi('/api/v1/pos')">Análisis POS</button>
                    <button onclick="executeApi('/api/v1/ner')">Reconocimiento NER</button>
                    <button onclick="executeDepVis()">Visualizar Dependencias</button>
                    <button onclick="executeVectorize()">Vectorizar</button>
                </div>
                <div id="output-container">
                    <strong>Resultado:</strong>
                    <div id="outputContent"><p style="color: #a0aec0;">Los resultados aparecerán aquí...</p></div>
                </div>
            </div>
        </div>
        <script>
            async function executeApi(endpoint) {
                const rawText = document.getElementById("inputText").value;
                const lines = rawText.split('\\n').filter(l => l.trim() !== "");
                const payload = { text: lines.length > 1 ? lines : rawText };
                try {
                    const res = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                    const data = await res.json();
                    document.getElementById("outputContent").innerHTML = "<pre>" + JSON.stringify(data, null, 2) + "</pre>";
                } catch (err) {
                    document.getElementById("outputContent").innerHTML = "<pre style='color:red;'>Error: " + err + "</pre>";
                }
            }
            async function executeDepVis() {
                const text = document.getElementById("inputText").value;
                try {
                    const res = await fetch('/api/v1/visualize/dep', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text }) });
                    if (!res.ok) {
                        const errData = await res.json();
                        document.getElementById("outputContent").innerHTML = "<pre style='color:red;'>" + JSON.stringify(errData, null, 2) + "</pre>";
                        return;
                    }
                    const html = await res.text();
                    document.getElementById("outputContent").innerHTML = html;
                } catch (err) {
                    document.getElementById("outputContent").innerHTML = "<pre style='color:red;'>Error: " + err + "</pre>";
                }
            }
            async function executeVectorize() {
                const rawText = document.getElementById("inputText").value;
                const docs = rawText.split('\\n').filter(l => l.trim() !== "");
                try {
                    const res = await fetch('/api/v1/vectorize', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ documents: docs }) });
                    const data = await res.json();
                    document.getElementById("outputContent").innerHTML = "<pre>" + JSON.stringify(data, null, 2) + "</pre>";
                } catch (err) {
                    document.getElementById("outputContent").innerHTML = "<pre style='color:red;'>Error: " + err + "</pre>";
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# ------------------------------------------------------------------------------
# 6. Endpoints de la API (/api/v1/...)
# ------------------------------------------------------------------------------

# Endpoint 1: Limpieza de texto (/api/v1/clean)
@app.post("/api/v1/clean")
def clean_text_endpoint(payload: BatchTextRequest):
    # FIX: el validador de BatchTextRequest siempre normaliza `text` a List[str],
    # sin importar si llegó string o lista. Por lo tanto `payload.text` NUNCA es un
    # string en este punto; se elimina la rama muerta que comprobaba
    # `isinstance(payload.text, str)` y se retorna siempre una lista, tal como
    # exige el contrato ("cleaned_text: lista de strings, incluso para entrada individual").
    texts: List[str] = payload.text
    cleaned_list = [clean_single_text(t) for t in texts]
    return {"cleaned_text": cleaned_list}

# Endpoint 2: Análisis POS (/api/v1/pos)
@app.post("/api/v1/pos")
def pos_endpoint(payload: BatchTextRequest):
    texts: List[str] = payload.text
    results = []

    for doc_nlp in nlp.pipe(texts):
        doc_tokens = []
        for token in doc_nlp:
            doc_tokens.append({
                "text": token.text,
                "pos": token.pos_,
                "lemma": token.lemma_
            })
        # FIX: el contrato exige results[i].tokens (objeto con clave "tokens"),
        # no la lista de tokens directamente. Antes se hacía
        # results.append(doc_tokens), lo cual dejaba results[i] como una lista
        # cruda sin la clave "tokens" -> el validador del contrato nunca la
        # encontraba y todo el endpoint se reportaba como fallido.
        results.append({"tokens": doc_tokens})

    return {"results": results}

# Endpoint 3: Reconocimiento de Entidades Nombradas (/api/v1/ner)
@app.post("/api/v1/ner")
def ner_endpoint(payload: BatchTextRequest):
    texts: List[str] = payload.text
    results = []

    for doc_nlp in nlp.pipe(texts):
        doc_entities = []
        for ent in doc_nlp.ents:
            doc_entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        # FIX: mismo problema que en /api/v1/pos. El contrato exige
        # results[i].entities (objeto con clave "entities"), no la lista de
        # entidades directamente.
        results.append({"entities": doc_entities})

    return {"results": results}

# Endpoint 4: Visualización de Dependencias (/api/v1/visualize/dep)
@app.post("/api/v1/visualize/dep", response_class=HTMLResponse)
def visualize_dep_endpoint(payload: VisualizeDepRequest):
    text: str = payload.text
    doc = nlp(text)
    svg_content = displacy.render(doc, style="dep", jupyter=False)

    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Visualización de Dependencias</title>
</head>
<body>
    <div style="width: 100%; overflow-x: auto;">
        {svg_content}
    </div>
</body>
</html>"""
    return HTMLResponse(content=full_html, status_code=200)

# Endpoint 5: Vectorización (/api/v1/vectorize)
@app.post("/api/v1/vectorize")
def vectorize_endpoint(payload: VectorizeRequest):
    documents: List[str] = payload.documents

    docs_tokens = [clean_single_text_tokens(doc) for doc in documents]

    vocab_set = set()
    for tokens in docs_tokens:
        for t in tokens:
            vocab_set.add(t)

    vocabulary = sorted(vocab_set)
    vocab_map = {word: idx for idx, word in enumerate(vocabulary)}
    V = len(vocabulary)
    N = len(documents)

    bag_of_words = []
    for tokens in docs_tokens:
        row = [0] * V
        for t in tokens:
            if t in vocab_map:
                row[vocab_map[t]] += 1
        bag_of_words.append(row)

    one_hot = []
    for tokens in docs_tokens:
        doc_matrix = []
        for t in tokens:
            if t in vocab_map:
                vec = [0] * V
                vec[vocab_map[t]] = 1
                doc_matrix.append(vec)
        one_hot.append(doc_matrix)

    idf_values = []
    for term in vocabulary:
        n_t = sum(1 for tokens in docs_tokens if term in tokens)
        idf_t = math.log((N + 1.0) / (n_t + 1.0)) + 1.0
        idf_values.append(idf_t)

    tf_idf = []
    for i in range(N):
        row = []
        for j in range(V):
            tf = bag_of_words[i][j]
            val = tf * idf_values[j]
            row.append(round(val, 4))
        tf_idf.append(row)

    return {
        "vocabulary": vocabulary,
        "one_hot": one_hot,
        "bag_of_words": bag_of_words,
        "tf_idf": tf_idf
    }

# ------------------------------------------------------------------------------
# 7. Adaptador Handler para AWS Lambda
# ------------------------------------------------------------------------------
handler = Mangum(app)
