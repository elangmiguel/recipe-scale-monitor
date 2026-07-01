from fastapi import FastAPI, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Generator, Tuple
from pydantic import BaseModel, Field

# --- Configuración de conexión a la base de datos ---
DB_HOST = "192.168.56.1"
DB_NAME = "recetario"
DB_USER = "recetario"
DB_PASWD = "123456"

# --- Inicialización de FastAPI ---
app = FastAPI()

# --- Middleware CORS ---
allowed_origins = [
    "http://localhost:8000",
    "http://localhost:8080",
    "http://10.147.17.1:8000",
    "http://10.147.17.2:8000",
    "http://10.147.17.3:8000",
    "http://10.147.17.4:8000",
    "http://10.147.17.5:8000",
    "http://10.147.17.6:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- Dependencia para conexión a base de datos ---
def get_db() -> Generator[Tuple[psycopg2.extensions.connection, RealDictCursor], None, None]:
    conn = psycopg2.connect(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASWD,
        host=DB_HOST,
        port=5432
    )
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()

# --- Modelos de datos ---
# Modelo básico de una receta
class Receta(BaseModel):
    id: int
    nombre: str

# Modelo de ingrediente con los campos requeridos por el cliente
class Ingrediente(BaseModel):
    id: int
    nombre: str
    cantidad: float
    unidad: str
    orden: int

# Modelo para registrar lecturas de peso desde ESP32
class Lectura(BaseModel):
    sensor_id: int
    valor: float


# --- Ruta raíz ---
@app.get("/")
async def root():
    return {"message": "API funcionando correctamente"}

# --- Ruta para obtener ingredientes por receta ---
@app.get(
    "/recetas/{receta_id}/ingredientes",
    response_model=List[Ingrediente],
    tags=["Recetas"]
)
def obtener_ingredientes(receta_id: int, db: Tuple = Depends(get_db)):
    conn, cursor = db
    cursor.execute("""
        SELECT 
            i.id,
            i.nombre,
            ri.cantidad AS cantidad,
            m.simbolo AS unidad,
            ri.orden
        FROM receta_ingrediente ri
        JOIN ingrediente i ON ri.ingrediente_id = i.id
        JOIN medida m ON ri.medida_id = m.id
        WHERE ri.receta_id = %s
        ORDER BY ri.orden;
    """, (receta_id,))
    return cursor.fetchall()


@app.get(
    "/recetas",
    response_model=List[Receta],
    tags=["Recetas"]
)
def listar_recetas(db: Tuple = Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT id, nombre FROM receta ORDER BY nombre;")
    return cursor.fetchall()

@app.get(
    "/sensores/{sensor_id}/ultima",
    tags=["Sensores"]
)
def obtener_ultima_lectura(sensor_id: int, db: Tuple = Depends(get_db)):
    conn, cursor = db
    cursor.execute("""
        SELECT l.valor, l.fecha
        FROM lectura l
        WHERE l.sensor_id = %s
        ORDER BY l.fecha DESC
        LIMIT 1;
    """, (sensor_id,))
    lectura = cursor.fetchone()
    if not lectura:
        raise HTTPException(status_code=404, detail="No se encontró lectura")

    return lectura


# --- Ruta para insertar lecturas del sensor---
class LecturaInput(BaseModel):
    sensor_id: int
    valor: float

DBConnection = Tuple[psycopg2.extensions.connection, RealDictCursor]

# Modelo de datos de entrada
class LecturaInput(BaseModel):
    sensor_id: int = Field(..., description="ID del sensor que envía la lectura")
    valor: float = Field(..., description="Valor leído por el sensor")
    fecha: Optional[str] = Field(None, description="Fecha y hora en formato ISO 8601 (opcional)")

@app.post("/sensor/insert/lectura", tags=["application/json"])
async def insert_lectura(
    lectura: LecturaInput,
    db: DBConnection = Depends(get_db)
):
    conn, cursor = db

    # Validar o generar la fecha
    try:
        fecha_final = datetime.fromisoformat(lectura.fecha).isoformat() if lectura.fecha else datetime.now().isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use ISO 8601.")

    try:
        cursor.execute("""
            INSERT INTO lectura (sensor_id, valor, fecha)
            VALUES (%s, %s, %s)
        """, (lectura.sensor_id, lectura.valor, fecha_final))
        conn.commit()
        return {
            "message": "Lectura insertada correctamente",
            "datos_insertados": {
                "sensor_id": lectura.sensor_id,
                "valor": lectura.valor,
                "fecha": fecha_final
            }
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))








class Dispositivo(BaseModel):
    id: int
    latitud: Optional[float]
    longitud: Optional[float]
    nombre: Optional[str]

class Ingrediente(BaseModel):
    id: int
    nombre: str

class Medida(BaseModel):
    id: int
    nombre: str
    simbolo: Optional[str]

class Receta(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]

class RecetaIngrediente(BaseModel):
    id: int
    receta_id: int
    ingrediente_id: int
    cantidad: float
    medida_id: int
    orden: Optional[int]

class Sensor(BaseModel):
    id: int
    dispositivo_id: int
    referencia: str
    descripcion: Optional[str]

class Lectura(BaseModel):
    id: int
    fecha: datetime
    valor: float
    sensor_id: int


# ----------------------------------------
# RUTAS CRUD CON FORMULARIO Y TAGS
# ----------------------------------------

# ----------------- Dispositivo -----------------

@app.post("/dispositivos/", tags=["dispositivos"])
def create_dispositivo(
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None),
    nombre: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "INSERT INTO public.dispositivo (latitud, longitud, nombre) VALUES (%s, %s, %s) RETURNING id",
        (latitud, longitud, nombre)
    )
    id = cursor.fetchone()["id"]
    conn.commit()
    return {"id": id, "latitud": latitud, "longitud": longitud, "nombre": nombre}

@app.get("/dispositivos/", response_model=List[Dispositivo], tags=["dispositivos"])
def read_dispositivos(db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.dispositivo ORDER BY id")
    resultados = cursor.fetchall()
    return resultados

@app.get("/dispositivos/{id}", response_model=Dispositivo, tags=["dispositivos"])
def read_dispositivo(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.dispositivo WHERE id = %s", (id,))
    dispositivo = cursor.fetchone()
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return dispositivo

@app.put("/dispositivos/{id}", tags=["dispositivos"])
def update_dispositivo(
    id: int,
    latitud: Optional[float] = Form(None),
    longitud: Optional[float] = Form(None),
    nombre: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    # Leer datos actuales para validar existencia
    cursor.execute("SELECT * FROM public.dispositivo WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    # Actualizar sólo los campos recibidos
    cursor.execute(
        """
        UPDATE public.dispositivo SET
            latitud = COALESCE(%s, latitud),
            longitud = COALESCE(%s, longitud),
            nombre = COALESCE(%s, nombre)
        WHERE id = %s
        """,
        (latitud, longitud, nombre, id)
    )
    conn.commit()
    return {"mensaje": "Dispositivo actualizado"}

@app.delete("/dispositivos/{id}", tags=["dispositivos"])
def delete_dispositivo(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.dispositivo WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    cursor.execute("DELETE FROM public.dispositivo WHERE id = %s", (id,))
    conn.commit()
    return {"mensaje": "Dispositivo eliminado"}


# ----------------- Ingrediente -----------------

@app.post("/ingredientes/", tags=["ingredientes"])
def create_ingrediente(
    nombre: str = Form(...),
    db=Depends(get_db)
):
    conn, cursor = db
    try:
        cursor.execute("INSERT INTO public.ingrediente (nombre) VALUES (%s) RETURNING id", (nombre,))
        id = cursor.fetchone()["id"]
        conn.commit()
        return {"id": id, "nombre": nombre}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Nombre de ingrediente ya existe")

@app.get("/ingredientes/", response_model=List[Ingrediente], tags=["ingredientes"])
def read_ingredientes(db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.ingrediente ORDER BY id")
    return cursor.fetchall()

@app.get("/ingredientes/{id}", response_model=Ingrediente, tags=["ingredientes"])
def read_ingrediente(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.ingrediente WHERE id = %s", (id,))
    ingrediente = cursor.fetchone()
    if not ingrediente:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return ingrediente

@app.put("/ingredientes/{id}", tags=["ingredientes"])
def update_ingrediente(
    id: int,
    nombre: str = Form(...),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.ingrediente WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    try:
        cursor.execute("UPDATE public.ingrediente SET nombre = %s WHERE id = %s", (nombre, id))
        conn.commit()
        return {"mensaje": "Ingrediente actualizado"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Nombre de ingrediente ya existe")

@app.delete("/ingredientes/{id}", tags=["ingredientes"])
def delete_ingrediente(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.ingrediente WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    cursor.execute("DELETE FROM public.ingrediente WHERE id = %s", (id,))
    conn.commit()
    return {"mensaje": "Ingrediente eliminado"}


# ----------------- Medida -----------------

@app.post("/medidas/", tags=["medidas"])
def create_medida(
    nombre: str = Form(...),
    simbolo: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    try:
        cursor.execute("INSERT INTO public.medida (nombre, simbolo) VALUES (%s, %s) RETURNING id", (nombre, simbolo))
        id = cursor.fetchone()["id"]
        conn.commit()
        return {"id": id, "nombre": nombre, "simbolo": simbolo}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Nombre de medida ya existe")

@app.get("/medidas/", response_model=List[Medida], tags=["medidas"])
def read_medidas(db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.medida ORDER BY id")
    return cursor.fetchall()

@app.get("/medidas/{id}", response_model=Medida, tags=["medidas"])
def read_medida(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.medida WHERE id = %s", (id,))
    medida = cursor.fetchone()
    if not medida:
        raise HTTPException(status_code=404, detail="Medida no encontrada")
    return medida

@app.put("/medidas/{id}", tags=["medidas"])
def update_medida(
    id: int,
    nombre: str = Form(...),
    simbolo: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.medida WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Medida no encontrada")
    try:
        cursor.execute("UPDATE public.medida SET nombre = %s, simbolo = %s WHERE id = %s", (nombre, simbolo, id))
        conn.commit()
        return {"mensaje": "Medida actualizada"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Nombre de medida ya existe")

@app.delete("/medidas/{id}", tags=["medidas"])
def delete_medida(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.medida WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Medida no encontrada")
    cursor.execute("DELETE FROM public.medida WHERE id = %s", (id,))
    conn.commit()
    return {"mensaje": "Medida eliminada"}


# ----------------- Receta -----------------

@app.post("/recetas/", tags=["recetas"])
def create_receta(
    nombre: str = Form(...),
    descripcion: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    try:
        cursor.execute("INSERT INTO public.receta (nombre, descripcion) VALUES (%s, %s) RETURNING id", (nombre, descripcion))
        id = cursor.fetchone()["id"]
        conn.commit()
        return {"id": id, "nombre": nombre, "descripcion": descripcion}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Nombre de receta ya existe")

@app.get("/recetas/", response_model=List[Receta], tags=["recetas"])
def read_recetas(db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta ORDER BY id")
    return cursor.fetchall()

@app.get("/recetas/{id}", response_model=Receta, tags=["recetas"])
def read_receta(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta WHERE id = %s", (id,))
    receta = cursor.fetchone()
    if not receta:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return receta

@app.put("/recetas/{id}", tags=["recetas"])
def update_receta(
    id: int,
    nombre: str = Form(...),
    descripcion: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    try:
        cursor.execute("UPDATE public.receta SET nombre = %s, descripcion = %s WHERE id = %s", (nombre, descripcion, id))
        conn.commit()
        return {"mensaje": "Receta actualizada"}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Nombre de receta ya existe")

@app.delete("/recetas/{id}", tags=["recetas"])
def delete_receta(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    cursor.execute("DELETE FROM public.receta WHERE id = %s", (id,))
    conn.commit()
    return {"mensaje": "Receta eliminada"}


# ----------------- Receta Ingrediente -----------------

@app.post("/receta_ingredientes/", tags=["receta_ingredientes"])
def create_receta_ingrediente(
    receta_id: int = Form(...),
    ingrediente_id: int = Form(...),
    cantidad: float = Form(...),
    medida_id: int = Form(...),
    orden: Optional[int] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "INSERT INTO public.receta_ingrediente (receta_id, ingrediente_id, cantidad, medida_id, orden) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (receta_id, ingrediente_id, cantidad, medida_id, orden)
    )
    id = cursor.fetchone()["id"]
    conn.commit()
    return {
        "id": id,
        "receta_id": receta_id,
        "ingrediente_id": ingrediente_id,
        "cantidad": cantidad,
        "medida_id": medida_id,
        "orden": orden,
    }

@app.get("/receta_ingredientes/", response_model=List[RecetaIngrediente], tags=["receta_ingredientes"])
def read_receta_ingredientes(db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta_ingrediente ORDER BY id")
    return cursor.fetchall()

@app.get("/receta_ingredientes/{id}", response_model=RecetaIngrediente, tags=["receta_ingredientes"])
def read_receta_ingrediente(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta_ingrediente WHERE id = %s", (id,))
    ri = cursor.fetchone()
    if not ri:
        raise HTTPException(status_code=404, detail="Receta Ingrediente no encontrado")
    return ri

@app.put("/receta_ingredientes/{id}", tags=["receta_ingredientes"])
def update_receta_ingrediente(
    id: int,
    receta_id: int = Form(...),
    ingrediente_id: int = Form(...),
    cantidad: float = Form(...),
    medida_id: int = Form(...),
    orden: Optional[int] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta_ingrediente WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Receta Ingrediente no encontrado")
    cursor.execute(
        """
        UPDATE public.receta_ingrediente SET
            receta_id = %s,
            ingrediente_id = %s,
            cantidad = %s,
            medida_id = %s,
            orden = %s
        WHERE id = %s
        """,
        (receta_id, ingrediente_id, cantidad, medida_id, orden, id)
    )
    conn.commit()
    return {"mensaje": "Receta Ingrediente actualizado"}

@app.delete("/receta_ingredientes/{id}", tags=["receta_ingredientes"])
def delete_receta_ingrediente(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.receta_ingrediente WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Receta Ingrediente no encontrado")
    cursor.execute("DELETE FROM public.receta_ingrediente WHERE id = %s", (id,))
    conn.commit()
    return {"mensaje": "Receta Ingrediente eliminado"}


# ----------------- Sensor -----------------

@app.post("/sensores/", tags=["sensores"])
def create_sensor(
    dispositivo_id: int = Form(...),
    referencia: str = Form(...),
    descripcion: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "INSERT INTO public.sensor (dispositivo_id, referencia, descripcion) VALUES (%s, %s, %s) RETURNING id",
        (dispositivo_id, referencia, descripcion)
    )
    id = cursor.fetchone()["id"]
    conn.commit()
    return {"id": id, "dispositivo_id": dispositivo_id, "referencia": referencia, "descripcion": descripcion}

@app.get("/sensores/", response_model=List[Sensor], tags=["sensores"])
def read_sensores(db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.sensor ORDER BY id")
    return cursor.fetchall()

@app.get("/sensores/{id}", response_model=Sensor, tags=["sensores"])
def read_sensor(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.sensor WHERE id = %s", (id,))
    sensor = cursor.fetchone()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    return sensor

@app.put("/sensores/{id}", tags=["sensores"])
def update_sensor(
    id: int,
    dispositivo_id: int = Form(...),
    referencia: str = Form(...),
    descripcion: Optional[str] = Form(None),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.sensor WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    cursor.execute(
        "UPDATE public.sensor SET dispositivo_id = %s, referencia = %s, descripcion = %s WHERE id = %s",
        (dispositivo_id, referencia, descripcion, id)
    )
    conn.commit()
    return {"mensaje": "Sensor actualizado"}

@app.delete("/sensores/{id}", tags=["sensores"])
def delete_sensor(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.sensor WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Sensor no encontrado")
    cursor.execute("DELETE FROM public.sensor WHERE id = %s", (id,))
    conn.commit()
    return {"mensaje": "Sensor eliminado"}


# ----------------- Lectura -----------------

@app.post("/lecturas/", tags=["lecturas"])
def create_lectura(
    fecha: datetime = Form(...),
    valor: float = Form(...),
    sensor_id: int = Form(...),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute(
        "INSERT INTO public.lectura (fecha, valor, sensor_id) VALUES (%s, %s, %s) RETURNING id",
        (fecha, valor, sensor_id)
    )
    id = cursor.fetchone()["id"]
    conn.commit()
    return {"id": id, "fecha": fecha, "valor": valor, "sensor_id": sensor_id}

@app.get("/lecturas/", response_model=List[Lectura], tags=["lecturas"])
def read_lecturas(db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.lectura ORDER BY id")
    return cursor.fetchall()

@app.get("/lecturas/{id}", response_model=Lectura, tags=["lecturas"])
def read_lectura(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.lectura WHERE id = %s", (id,))
    lectura = cursor.fetchone()
    if not lectura:
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    return lectura

@app.put("/lecturas/{id}", tags=["lecturas"])
def update_lectura(
    id: int,
    fecha: datetime = Form(...),
    valor: float = Form(...),
    sensor_id: int = Form(...),
    db=Depends(get_db)
):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.lectura WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    cursor.execute(
        "UPDATE public.lectura SET fecha = %s, valor = %s, sensor_id = %s WHERE id = %s",
        (fecha, valor, sensor_id, id)
    )
    conn.commit()
    return {"mensaje": "Lectura actualizada"}

@app.delete("/lecturas/{id}", tags=["lecturas"])
def delete_lectura(id: int, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM public.lectura WHERE id = %s", (id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Lectura no encontrada")
    cursor.execute("DELETE FROM public.lectura WHERE id = %s", (id,))
    conn.commit()
    return {"mensaje": "Lectura eliminada"}



