from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib

app = FastAPI(title="API Controle de Contratos SMS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "contratos.db"

# Função auxiliar para criptografar senhas (SHA-256)
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela de Contratos
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
    
    # Tabela de Usuários para acesso dos servidores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT DEFAULT 'operador'
        )
    ''')
    
    # Cria um usuário administrador padrão se não existir nenhum
    cursor.execute("SELECT count(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nome, usuario, senha, perfil) VALUES (?, ?, ?, ?)",
            ("Administrador HMM", "admin", hash_password("admin123"), "admin")
        )
    
    conn.commit()
    conn.close()

init_db()

# Modelos
class ContratoSchema(BaseModel):
    numero_contrato: str
    empresa: str
    objeto: str
    status: str = "Ativo"

class LoginSchema(BaseModel):
    usuario: str
    senha: str

@app.get("/")
def home():
    return {"status": "API de Contratos Operacional", "versao": "2.0"}

# ROTA DE LOGIN
@app.post("/api/login")
def login(dados: LoginSchema):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    senha_hash = hash_password(dados.senha)
    
    cursor.execute("SELECT id, nome, usuario, perfil FROM usuarios WHERE usuario = ? AND senha = ?", (dados.usuario, senha_hash))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos")
    
    return {
        "mensagem": "Sucesso",
        "usuario": {
            "id": user[0],
            "nome": user[1],
            "usuario": user[2],
            "perfil": user[3]
        }
    }

# ROTA DE LISTAR CONTRATOS
@app.get("/api/contratos")
def listar_contratos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, numero_contrato, empresa, objeto, status FROM contratos ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {"id": r[0], "numero_contrato": r[1], "empresa": r[2], "objeto": r[3], "status": r[4]}
        for r in rows
    ]

# ROTA DE CADASTRAR CONTRATO
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