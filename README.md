# Microservicio de Procesamiento de Lenguaje Natural (spaCy + AWS)

Laboratorio I — Procesamiento de Lenguaje Natural — 2026 S02
Universidad Sergio Arboleda

Microservicio NLP construido con **FastAPI** y **spaCy** (`es_core_news_sm`), desplegado en dos
arquitecturas dentro de AWS Academy con el mismo comportamiento funcional en ambas:

- **Despliegue persistente (EC2 / Cloud9)**: proceso `uvicorn` corriendo directamente sobre la instancia.
- **Despliegue serverless (Lambda)**: imagen de contenedor en ECR, ejecutada vía **Lambda Function URL**,
  usando `Mangum` como adaptador ASGI.

## URLs públicas

| Entorno | URL |
|---|---|
| EC2 | `http://54.221.55.237:8080` |
| Lambda (Function URL) | `https://umjdv3obh23eceyk7dxco6rufq0zwgux.lambda-url.us-east-1.on.aws` |

## Estructura del repositorio

```
.
├── common/
│   └── main.py              # Lógica funcional del microservicio (FastAPI), común a ambas arquitecturas
├── ec2/
│   └── (config/servicio systemd o instrucciones de arranque específicas de EC2)
├── lambda/
│   ├── Dockerfile            # Imagen de contenedor para Lambda
│   └── requirements.txt      # Dependencias específicas de la imagen Lambda
├── tests/
│   └── test_4_niveles.py     # Suite de pruebas de caja negra (fácil/medio/difícil/imposible)
└── README.md
```

> La lógica funcional (`main.py`) es la **misma** para ambos despliegues; solo cambian los archivos de
> empaquetado/arranque propios de cada arquitectura (`ec2/` vs `lambda/`), tal como exige la guía.

## Capacidades implementadas

| Capacidad | Endpoint | Método |
|---|---|---|
| Limpieza de texto | `/api/v1/clean` | POST |
| Análisis POS | `/api/v1/pos` | POST |
| Reconocimiento de entidades (NER) | `/api/v1/ner` | POST |
| Visualización de dependencias | `/api/v1/visualize/dep` | POST |
| Vectorización (One-Hot, BoW, TF-IDF) | `/api/v1/vectorize` | POST |

Todos los endpoints reciben `Content-Type: application/json` y devuelven `application/json`,
excepto `/api/v1/visualize/dep`, que devuelve `text/html`.

## Cómo ejecutar el proyecto

### Requisitos previos
- Python 3.12
- pip
- Docker (solo necesario para reconstruir/desplegar la imagen de Lambda)
- Credenciales de AWS Academy configuradas (`aws configure` o variables de entorno) para el despliegue

### Ejecución local (para desarrollo/pruebas)

```bash
pip install fastapi uvicorn mangum spacy --break-system-packages
python -m spacy download es_core_news_sm
uvicorn main:app --host 0.0.0.0 --port 8080
```

El servicio queda disponible en `http://localhost:8080`, con la consola de pruebas interactiva en `/`.

### Despliegue en EC2 (persistente)

1. Copiar `common/main.py` a la instancia EC2.
2. Instalar dependencias (`pip install -r requirements.txt --break-system-packages` y
   `python -m spacy download es_core_news_sm`).
3. Levantar el servicio: `uvicorn main:app --host 0.0.0.0 --port 8080`
   (en producción, ejecutarlo como servicio persistente, ej. con `systemd` o `nohup`).

### Despliegue en Lambda (serverless, vía imagen de contenedor)

```bash
# Variables de la cuenta
export AWS_REGION="us-east-1"
export ACCOUNT_ID="<tu-account-id>"
export REPO_NAME="nlp-fastapi"
export FUNCTION_NAME="nlp-fastapi-image"
export ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"

# Construir y subir la imagen
cd lambda/
docker build --platform linux/amd64 -t "${REPO_NAME}:latest" .
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker tag "${REPO_NAME}:latest" "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

# Crear/actualizar la función Lambda (tipo Imagen)
aws lambda create-function \
  --function-name "${FUNCTION_NAME}" \
  --package-type Image \
  --code ImageUri="${ECR_URI}:latest" \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/LabRole" \
  --timeout 30 --memory-size 1024 --region "${AWS_REGION}"

# Exponer públicamente vía Function URL
aws lambda create-function-url-config --function-name "${FUNCTION_NAME}" \
  --auth-type NONE --region "${AWS_REGION}"
aws lambda add-permission --function-name "${FUNCTION_NAME}" \
  --statement-id FunctionURLAllowPublicAccess --action lambda:InvokeFunctionUrl \
  --principal "*" --function-url-auth-type NONE --region "${AWS_REGION}"
```

### Ejecutar las pruebas de caja negra

```bash
pip install requests --break-system-packages
python3 tests/test_4_niveles.py
```

La suite valida, contra ambos despliegues simultáneamente: las 5 capacidades funcionales, las reglas de
vectorización (incluida verificación matemática exacta de TF-IDF), los 24 casos de entrada inválida de la
sección 9 del enunciado, capacidad (25 documentos de hasta 1000 caracteres en clean/pos/ner, 10 en
vectorize), concurrencia (5 y 20 solicitudes simultáneas), consistencia, statelessness, y paridad
funcional completa entre EC2 y Lambda.

## Declaración de uso de inteligencia artificial generativa

En cumplimiento de la sección 6 de la guía del laboratorio:

- **Herramienta utilizada**: Claude (Anthropic).
- **Propósito**: apoyo en la corrección y robustecimiento del código del microservicio (manejo de
  errores de validación con Pydantic, patrón de excepciones para garantizar respuestas HTTP 4xx
  controladas), diagnóstico y resolución de problemas de despliegue en AWS Academy (errores de memoria al
  actualizar código Lambda, migración de despliegue .zip a imagen de contenedor por límite de tamaño de
  paquete, renovación de credenciales temporales, configuración de Function URL), y diseño de una suite
  de pruebas de caja negra para verificar el cumplimiento del contrato descrito en esta guía.
- **Verificación de resultados**: todo el código generado o modificado con asistencia de IA fue revisado
  manualmente y validado mediante ejecución real de pruebas de caja negra (`tests/test_4_niveles.py`)
  contra ambos despliegues activos, incluyendo verificación matemática independiente de la fórmula TF-IDF
  y comparación de paridad de resultados entre EC2 y Lambda. No se compartieron credenciales, claves de
  acceso, tokens ni información sensible de AWS Academy con la herramienta de IA durante el proceso.

## Notas de seguridad

- No se incluyen credenciales, claves secretas ni tokens de sesión en este repositorio.
- Las credenciales de AWS Academy Learner Lab son temporales y deben configurarse localmente por cada
  integrante del equipo antes de ejecutar los comandos de despliegue.
