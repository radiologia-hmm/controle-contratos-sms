from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from datetime import datetime

app = FastAPI(title="API Controle de Contratos - SMS DMAC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE = "contratos_dmac.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                nome TEXT NOT NULL,
                perfil TEXT NOT NULL,
                categoria_vinculada TEXT
            )
        """)
        
        cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha, nome, perfil, categoria_vinculada) VALUES (1, 'denisval', '123456', 'Denisval Rodrigues', 'Coordenador de Diagnóstico por Imagem', 'Diagnóstico por Imagem')")
        cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha, nome, perfil, categoria_vinculada) VALUES (2, 'luana', '123456', 'Luana', 'Diretora DMAC', 'TODAS')")
        cursor.execute("INSERT OR REPLACE INTO usuarios (id, usuario, senha, nome, perfil, categoria_vinculada) VALUES (3, 'admin', '123456', 'Administrador do Sistema', 'Administrador Geral', 'TODAS')")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contratos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_contrato TEXT UNIQUE NOT NULL,
                empresa TEXT NOT NULL,
                objeto TEXT NOT NULL,
                categoria TEXT NOT NULL,
                valor_total REAL NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE NOT NULL,
                status TEXT DEFAULT 'Ativo'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aditivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contrato_id INTEGER NOT NULL,
                valor_aditivo REAL NOT NULL,
                data_aditivo DATE NOT NULL,
                observacao TEXT,
                FOREIGN KEY (contrato_id) REFERENCES contratos (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS despesas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contrato_id INTEGER NOT NULL,
                mes_referencia TEXT NOT NULL,
                tipo_lancamento TEXT NOT NULL,
                qtd_exames INTEGER DEFAULT 0,
                valor_unitario REAL DEFAULT 0,
                valor_total_mes REAL NOT NULL,
                data_lancamento DATE NOT NULL,
                FOREIGN KEY (contrato_id) REFERENCES contratos (id)
            )
        """)
        conn.commit()

init_db()

class LoginSchema(BaseModel):
    usuario: str
    senha: str

class ContratoSchema(BaseModel):
    numero_contrato: str
    empresa: str
    objeto: str
    categoria: str
    valor_total: float
    data_inicio: str
    data_fim: str

class AditivoSchema(BaseModel):
    contrato_id: int
    valor_aditivo: float
    observacao: str

class DespesaSchema(BaseModel):
    contrato_id: int
    mes_referencia: str
    tipo_lancamento: str
    qtd_exames: Optional[int] = 0
    valor_unitario: Optional[float] = 0
    valor_total_mes: float

@app.post("/api/login")
def login(dados: LoginSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (dados.usuario, dados.senha))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {
        "status": "sucesso", 
        "usuario": {
            "id": user["id"],
            "nome": user["nome"], 
            "perfil": user["perfil"],
            "categoria_vinculada": user["categoria_vinculada"]
        }
    }

@app.get("/api/contratos")
def listar_contratos(categoria: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    if categoria and categoria != 'TODAS':
        cursor.execute("SELECT * FROM contratos WHERE categoria = ?", (categoria,))
    else:
        cursor.execute("SELECT * FROM contratos")
        
    contratos = [dict(row) for row in cursor.fetchall()]
    hoje = datetime.now()

    for c in contratos:
        cursor.execute("SELECT SUM(valor_total_mes) as total_exec FROM despesas WHERE contrato_id = ?", (c["id"],))
        res_desp = cursor.fetchone()
        c["total_executado"] = res_desp["total_exec"] if res_desp["total_exec"] else 0.0
        
        c["pct_financeiro"] = round((c["total_executado"] / c["valor_total"]) * 100, 2) if c["valor_total"] > 0 else 0
        c["alerta_financeiro"] = c["pct_financeiro"] >= 70.0

        d_inicio = datetime.strptime(c["data_inicio"], "%Y-%m-%d")
        d_fim = datetime.strptime(c["data_fim"], "%Y-%m-%d")
        dias_totais = (d_fim - d_inicio).days
        dias_decorridos = (hoje - d_inicio).days
        
        if dias_totais > 0:
            pct_tempo = round((dias_decorridos / dias_totais) * 100, 2)
            c["pct_tempo"] = min(max(pct_tempo, 0), 100)
        else:
            c["pct_tempo"] = 0
            
        c["alerta_tempo"] = c["pct_tempo"] >= 70.0

    return contratos

@app.post("/api/contratos")
def criar_contrato(c: ContratoSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contratos (numero_contrato, empresa, objeto, categoria, valor_total, data_inicio, data_fim)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (c.numero_contrato, c.empresa, c.objeto, c.categoria, c.valor_total, c.data_inicio, c.data_fim))
    conn.commit()
    return {"status": "sucesso"}

@app.put("/api/contratos/{contrato_id}")
def editar_contrato(contrato_id: int, c: ContratoSchema):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE contratos 
        SET numero_contrato = ?, empresa = ?, objeto = ?, categoria = ?, valor_total = ?, data_inicio = ?, data_fim = ?
        WHERE id = ?
    """, (c.numero_contrato, c.empresa, c.objeto, c.categoria, c.valor_total, c.data_inicio, c.data_fim, contrato_id))
    conn.commit()
    return {"status": "sucesso"}

@app.post("/api/aditivos")
def adicionar_aditivo(a: AditivoSchema):
    conn = get_db()
    cursor = conn.cursor()
    hoje = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO aditivos (contrato_id, valor_aditivo, data_aditivo, observacao)
        VALUES (?, ?, ?, ?)
    """, (a.contrato_id, a.valor_aditivo, hoje, a.observacao))
    cursor.execute("""
        UPDATE contratos SET valor_total = valor_total + ? WHERE id = ?
    """, (a.valor_aditivo, a.contrato_id))
    conn.commit()
    return {"status": "sucesso"}

@app.post("/api/despesas")
def lancar_despesa(d: DespesaSchema):
    conn = get_db()
    cursor = conn.cursor()
    hoje = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        INSERT INTO despesas (contrato_id, mes_referencia, tipo_lancamento, qtd_exames, valor_unitario, valor_total_mes, data_lancamento)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (d.contrato_id, d.mes_referencia, d.tipo_lancamento, d.qtd_exames, d.valor_unitario, d.valor_total_mes, hoje))
    conn.commit()
    return {"status": "sucesso"}