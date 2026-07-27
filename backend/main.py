from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

app = FastAPI(title="API Controle de Contratos SMS")

# Libera o acesso para o seu GitHub Pages (Front-End) conectar na API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "contratos.db"

# Inicializa o banco de dados SQLite
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_contrato TEXT NOT NULL,
            empresa TEXT NOT NULL,
            objeto TEXT,
            status TEXT DEFAULT 'Ativo',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Modelo de dados
class ContratoSchema(BaseModel):
    numero_contrato: str
    empresa: str
    objeto: str
    status: str = "Ativo"

@app.get("/")
def home():
    return {"status": "API de Contratos Operacional"}

# Rota para LISTAR todos os contratos
@app.get("/api/contratos")
def listar_contratos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero_contrato, empresa, objeto, status FROM contratos")
    rows = cursor.fetchall()
    conn.close()
    
    contratos = []
    for row in rows:
        contratos.append({
            "id": row[0],
            "numero_contrato": row[1],
            "empresa": row[2],
            "objeto": row[3],
            "status": row[4]
        })
    return contratos

# Rota para CADASTRAR um novo contrato
@app.post("/api/contratos")
def criar_contrato(contrato: ContratoSchema):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO contratos (numero_contrato, empresa, objeto, status) VALUES (?, ?, ?, ?)",
        (contrato.numero_contrato, contrato.empresa, contrato.objeto, contrato.status)
    )
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return {"mensagem": "Contrato salvo com sucesso!", "id": novo_id}