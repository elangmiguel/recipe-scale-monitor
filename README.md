
# Monitor de Recetas con Báscula Inteligente

Aplicación que combina un recetario digital con una báscula conectada, dando retroalimentación visual en tiempo real mientras se pesan los ingredientes de una receta.

## ¿Qué hace?

- Muestra un listado de recetas almacenadas en una base de datos PostgreSQL.
- Al seleccionar una receta, despliega sus ingredientes con cantidad y unidad de medida.
- Recibe lecturas de peso enviadas por un sensor (ESP32 + celda de carga) y las compara en tiempo real contra la cantidad requerida de cada ingrediente.
- Indica visualmente (color e indicador circular) si la cantidad pesada ya alcanzó lo requerido por la receta.
- Incluye un gráfico radial que muestra el peso actual sobre el total esperado.

## Arquitectura

```
[Sensor de peso / ESP32] → [API FastAPI] → [PostgreSQL]
                                 ↓
                        [Frontend HTML/JS]
```

- **Backend:** FastAPI + psycopg2, expone endpoints REST para recetas, ingredientes y lecturas de sensor.
- **Base de datos:** PostgreSQL, con tablas para recetas, ingredientes, medidas y lecturas.
- **Frontend:** HTML/CSS/JS sin framework, consulta la API vía `fetch` y actualiza la interfaz cada segundo.

## Requisitos

- Python 3.10+
- PostgreSQL
- Un navegador moderno para el frontend

## Instalación

```bash
git clone https://github.com/TU_USUARIO/recipe-scale-monitor.git
cd recipe-scale-monitor
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install fastapi uvicorn psycopg2-binary python-dotenv pydantic
```

## Configuración

Este proyecto usa variables de entorno para las credenciales de la base de datos. Crea un archivo `.env` en la raíz (nunca lo subas al repositorio):

```
DB_HOST=localhost
DB_NAME=recetario
DB_USER=recetario
DB_PASSWORD=tu_password_aqui
```

Y en `main.py`, reemplaza los valores fijos por lectura desde entorno, por ejemplo:

```python
import os
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASWD = os.getenv("DB_PASSWORD")
```

## Ejecutar el backend

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Ejecutar el frontend

El archivo `html/index.html` puede servirse con cualquier servidor estático simple:

```bash
cd html
python -m http.server 8080
```

Ajusta la constante `API_BASE` dentro del `<script>` de `index.html` para que apunte a la IP donde corre tu backend.

## Endpoints principales

| Método | Ruta                              | Descripción                          |
|--------|------------------------------------|---------------------------------------|
| GET    | `/recetas`                         | Lista todas las recetas               |
| GET    | `/recetas/{id}/ingredientes`       | Ingredientes de una receta específica |
| GET    | `/sensores/{sensor_id}/ultima`     | Última lectura registrada del sensor  |
| POST   | `/sensor/insert/lectura`           | Registra una nueva lectura de peso    |

## Hardware utilizado

- Microcontrolador ESP32
- Celda de carga con módulo HX711
- Conexión Wi-Fi a la red local donde corre el backend

> Nota: la IP definida en `API_BASE` del frontend corresponde a la red local del laboratorio donde se desarrolló el proyecto. Para reproducirlo en otro entorno, ajusta esa IP y las reglas de CORS en el backend.

## Estado del proyecto

Proyecto académico. Pendiente: mover credenciales a variables de entorno, limpiar definiciones duplicadas de modelos en `main.py`.