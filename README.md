# NLP Processing Microservice API (FastAPI + AWS)

Microservicio de Procesamiento de Lenguaje Natural (NLP) de alto rendimiento construido con **FastAPI**, **spaCy** y **scikit-learn**. Desplegado de forma paralela en la nube utilizando arquitectura con servidor (**AWS EC2**) y arquitectura Serverless (**AWS Lambda**).

---

## Arquitectura y Despliegue

La solución cuenta con paridad de entorno y persistencia en dos infraestructuras distintas de AWS:

| Entorno | Tipo | URL Base |
| :--- | :--- | :--- |
| **AWS EC2** | Servidor persistente (Port 8000) | `http://54.204.206.244:8000` |
| **AWS Lambda** | Serverless / Function URL | `https://uwsq72qscaqkmjsljbpqfxab7a0xwkkr.lambda-url.us-east-1.on.aws` |

---

## Endpoints Disponibles

### 1. Limpieza de Texto (`/api/v1/clean`)
Normaliza y remueve ruido del texto (símbolos, URLs, formato).
* **Método:** `POST`
* **Payload:** `{"text": "Texto a limpiar..."}` o `{"text": ["Texto 1", "Texto 2"]}`

### 2. Etiquetado Gramatical (`/api/v1/pos`)
Realiza extracción de Part-of-Speech Tagging utilizando modelos de spaCy.
* **Método:** `POST`
* **Payload:** `{"text": "El perro corre rápido."}`

### 3. Reconocimiento de Entidades (`/api/v1/ner`)
Identifica organizaciones, personas, lugares y fechas en el texto.
* **Método:** `POST`
* **Payload:** `{"text": "Carlos trabaja en Amazon en la ciudad de Seattle."}`

### 4. Vectorización TF-IDF (`/api/v1/vectorize`)
Calcula la matriz dispersa de representación numérica TF-IDF para lotes de documentos.
* **Método:** `POST`
* **Payload:** `{"documents": ["Documento uno", "Documento dos"]}`

### 5. Visualización Sintáctica (`/api/v1/visualize/dep`)
Genera la estructura en árbol de dependencias sintácticas.
* **Método:** `POST`
* **Payload:** `{"text": "FastAPI procesa la solicitud asíncrona."}`

---

## Validación de Contrato y Manejo de Errores

Las solicitudes que incumplan el contrato (ausencia de campos obligatorios, valores `null`, tipos incorrectos, listas vacías, elementos no string o textos vacíos) producen una respuesta controlada con código **HTTP 4xx**, rechazando el lote completo sin emitir resultados parciales

---

## Declaración de Uso de Inteligencia Artificial

Durante el desarrollo de este laboratorio se emplearon herramientas de Inteligencia Artificial Generativa como asistencia para la estructuración del código base, la optimización de los algoritmos de vectorización matemática y la resolución de incidencias de despliegue en AWS
* **Verificación:** Todo el código generado por IA fue rigurosamente auditado, probado y contrastado de manera manual contra las pruebas funcionales, de paridad, concurrencia y rendimiento establecidas en la guía oficial de la Universidad Sergio Arboleda
