# backend/main.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import sqlite3
import os
import sys
from datetime import datetime, timedelta
import json # Para lidar com as perguntas como JSON
import markdown # Para processar arquivos .md

# Importações para Google Gemini API (você precisará instalá-las)
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv() # Carrega variáveis de ambiente do arquivo .env

# Configuração da API do Gemini
# Certifique-se de que GEMINI_API_KEY está no seu arquivo .env na raiz do projeto
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro') # Ou o modelo que você preferir

app = FastAPI()

# --- Configuração do Banco de Dados SQLite ---
DATABASE_FILE = "revisu_data.db"

def get_db_connection():
    # Conecta-se ao banco de dados SQLite.
    # No modo empacotado, o DB estará na pasta de recursos ou em um local persistente.
    # Por simplicidade em desenvolvimento, vamos usar a pasta do backend.
    db_path = os.path.join(os.path.dirname(__file__), DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row # Permite acessar colunas por nome
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela File
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS File (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL UNIQUE,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            original_content TEXT NOT NULL,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela Topic
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Topic (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            title TEXT,
            summary TEXT NOT NULL,
            questions TEXT NOT NULL, -- Armazenado como JSON string
            next_review_date DATETIME NOT NULL,
            ease_factor REAL DEFAULT 2.5,
            repetitions INTEGER DEFAULT 0,
            last_reviewed DATETIME DEFAULT NULL,
            FOREIGN KEY (file_id) REFERENCES File(id) ON DELETE CASCADE
        )
    """)

    # Tabela Tag
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # Tabela TopicTag (tabela de junção)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TopicTag (
            topic_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (topic_id, tag_id),
            FOREIGN KEY (topic_id) REFERENCES Topic(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES Tag(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()
    print("Banco de dados SQLite inicializado.")

# Inicializa o banco de dados na primeira vez que o aplicativo é iniciado
init_db()

# --- Modelos Pydantic para Requisições e Respostas ---
class ProcessFileRequest(BaseModel):
    file_path: str
    file_name: str
    file_type: str # 'md' ou 'pdf'
    content: str # O conteúdo do arquivo como string

class TopicResponse(BaseModel):
    id: int
    file_id: int
    title: str | None
    summary: str
    questions: list[str] # Lista de strings
    next_review_date: datetime
    ease_factor: float
    repetitions: int
    last_reviewed: datetime | None
    tags: list[str] = [] # Para incluir as tags na resposta

class FileResponse(BaseModel):
    id: int
    file_path: str
    file_name: str
    file_type: str
    processed_at: datetime
    topics: list[TopicResponse] = [] # Para incluir os tópicos relacionados

class TagResponse(BaseModel):
    id: int
    name: str

class ReviewFeedback(BaseModel):
    topic_id: int
    quality: int # 0-5, 0=Esqueci tudo, 5=Perfeito (para SM-2)

# --- Funções de Processamento com Gemini ---

def process_content_with_gemini(content: str):
    try:
        # Novo prompt mais robusto pedindo formato JSON
        prompt = f"""
        Você é um assistente de estudo focado em revisão espaçada.
        Dada a seguinte nota, por favor, gere um JSON com:
        1. Um `titulo` conciso para o tópico da nota.
        2. Um `resumo` detalhado do conteúdo principal.
        3. Uma lista de `tags` (5 a 8 palavras-chave relevantes).
        4. Uma lista de `perguntas` (3 a 5 perguntas de múltipla escolha ou abertas) que ajudem na memorização ativa e revisão espaçada.

        Certifique-se de que a saída seja um JSON válido.

        Conteúdo da Nota:
        {content[:3000]} # Limita o texto para evitar tokens excessivos na API, ajuste se necessário
        """
        
        response = model.generate_content(prompt)
        generated_text = response.text

        # Tenta parsear a resposta como JSON
        try:
            # O Gemini às vezes coloca a resposta JSON dentro de blocos de código markdown ```json ... ```
            # Tentamos extrair isso primeiro.
            if generated_text.strip().startswith('```json') and generated_text.strip().endswith('```'):
                json_str = generated_text.strip()[7:-3].strip()
            else:
                json_str = generated_text.strip()
            
            parsed_data = json.loads(json_str)
            
            # Valida a estrutura esperada do JSON
            summary = parsed_data.get("resumo", "Resumo não encontrado.")
            title = parsed_data.get("titulo", content.split('\n')[0][:50] if content else "Novo Tópico") # Tenta pegar a primeira linha se título faltar
            tags = parsed_data.get("tags", ["geral", "ia"])
            questions = parsed_data.get("perguntas", ["Qual o ponto principal?", "O que você mais aprendeu?"])

            # Garante que questions é uma lista de strings
            if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
                questions = ["Pergunta padrão 1?", "Pergunta padrão 2?"] # Fallback

            # Garante que tags é uma lista de strings
            if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
                tags = ["tag-padrao"] # Fallback

            return {
                "title": title,
                "summary": summary,
                "tags": tags,
                "questions": questions
            }

        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON da resposta do Gemini: {e}")
            print(f"Resposta bruta do Gemini: {generated_text[:500]}...") # Imprime parte da resposta para depuração
            # Fallback para caso o Gemini não retorne JSON válido
            return {
                "title": "Erro na IA - Título Padrão",
                "summary": "Resumo gerado manualmente devido a erro na IA ou formato inválido.",
                "tags": ["erro-ia", "formato-invalido"],
                "questions": ["Por que o JSON falhou?", "Como posso melhorar o prompt?", "O que é JSON?"]
            }
    except Exception as e:
        print(f"Erro geral ao chamar a API do Gemini: {e}")
        return {
            "title": "Erro na IA - Título Padrão",
            "summary": "Resumo gerado manualmente devido a erro geral na API.",
            "tags": ["erro-api", "gemini-falha"],
            "questions": ["Houve um problema de conexão com a IA.", "Verifique sua chave de API.", "Tente novamente mais tarde."]
        }

# --- Lógica de Revisão Espaçada (SM-2 Simplificado) ---
def calculate_next_review(repetitions: int, ease_factor: float, quality: int):
    if quality < 3: # Esqueci ou tive muita dificuldade
        repetitions = 0
        ease_factor = max(1.3, ease_factor - 0.20)
    else:
        repetitions += 1
        ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    if repetitions == 0:
        interval = timedelta(minutes=1) # Ou alguns minutos para revisão imediata
    elif repetitions == 1:
        interval = timedelta(days=1)
    elif repetitions == 2:
        interval = timedelta(days=6)
    else:
        interval = timedelta(days=int(repetitions * ease_factor))

    next_review = datetime.now() + interval
    return next_review, repetitions, ease_factor

# --- Endpoints da API ---

@app.post("/files/process", response_model=FileResponse)
async def process_file(request_data: ProcessFileRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verifica se o arquivo já foi processado para evitar duplicatas
    cursor.execute("SELECT id FROM File WHERE file_path = ?", (request_data.file_path,))
    existing_file = cursor.fetchone()
    if existing_file:
        raise HTTPException(status_code=400, detail="Arquivo já processado.")

    # Insere o arquivo na tabela File
    cursor.execute(
        "INSERT INTO File (file_path, file_name, file_type, original_content) VALUES (?, ?, ?, ?)",
        (request_data.file_path, request_data.file_name, request_data.file_type, request_data.content)
    )
    file_id = cursor.lastrowid

    # Processa o conteúdo com Gemini (mock ou real)
    gemini_result = process_content_with_gemini(request_data.content)
    title = gemini_result["title"] # Agora estamos pegando o título do Gemini
    summary = gemini_result["summary"]
    questions = gemini_result["questions"] # Lista de strings
    tags_to_add = gemini_result["tags"]

    # Define a primeira data de revisão para hoje (ou um curto período)
    # O SM-2 começa com intervalos curtos.
    initial_next_review_date = datetime.now() + timedelta(minutes=5) # Para teste, revise em 5 min

    # Insere o tópico na tabela Topic
    cursor.execute(
        "INSERT INTO Topic (file_id, title, summary, questions, next_review_date, ease_factor, repetitions) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_id, title, summary, json.dumps(questions), initial_next_review_date, 2.5, 0)
    )
    topic_id = cursor.lastrowid

    # Adiciona as tags
    for tag_name in tags_to_add:
        cursor.execute("INSERT OR IGNORE INTO Tag (name) VALUES (?)", (tag_name,))
        cursor.execute("SELECT id FROM Tag WHERE name = ?", (tag_name,))
        tag_id = cursor.fetchone()["id"]
        cursor.execute("INSERT OR IGNORE INTO TopicTag (topic_id, tag_id) VALUES (?, ?)", (topic_id, tag_id))

    conn.commit()
    conn.close()

    # Retorna o arquivo processado com seus tópicos e tags
    return_file = {
        "id": file_id,
        "file_path": request_data.file_path,
        "file_name": request_data.file_name,
        "file_type": request_data.file_type,
        "original_content": request_data.content,
        "processed_at": datetime.now(),
        "topics": [{
            "id": topic_id,
            "file_id": file_id,
            "title": title, # Usando o título gerado pela IA
            "summary": summary,
            "questions": questions,
            "next_review_date": initial_next_review_date,
            "ease_factor": 2.5,
            "repetitions": 0,
            "last_reviewed": None,
            "tags": tags_to_add
        }]
    }
    return FileResponse(**return_file)

@app.get("/files", response_model=list[FileResponse])
async def get_all_files():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM File")
    files_db = cursor.fetchall()

    all_files_response = []
    for file_db in files_db:
        file_data = dict(file_db) # Converte Row para dict
        
        cursor.execute("""
            SELECT t.*, GROUP_CONCAT(tg.name) AS tags_names
            FROM Topic t
            LEFT JOIN TopicTag tt ON t.id = tt.topic_id
            LEFT JOIN Tag tg ON tt.tag_id = tg.id
            WHERE t.file_id = ?
            GROUP BY t.id
        """, (file_data["id"],))
        topics_db = cursor.fetchall()

        topics_response = []
        for topic_db in topics_db:
            topic_data = dict(topic_db)
            topic_data["questions"] = json.loads(topic_data["questions"]) # Deserializa as perguntas
            topic_data["tags"] = topic_data["tags_names"].split(',') if topic_data["tags_names"] else []
            del topic_data["tags_names"] # Remove a coluna extra
            topics_response.append(TopicResponse(**topic_data))
        
        file_data["topics"] = topics_response
        all_files_response.append(FileResponse(**file_data))
    
    conn.close()
    return all_files_response


@app.get("/topics/for-review", response_model=list[TopicResponse])
async def get_topics_for_review():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Seleciona tópicos cuja next_review_date é hoje ou no passado, ordenados para revisão
    cursor.execute("""
        SELECT t.*, GROUP_CONCAT(tg.name) AS tags_names
        FROM Topic t
        LEFT JOIN TopicTag tt ON t.id = tt.topic_id
        LEFT JOIN Tag tg ON tt.tag_id = tg.id
        WHERE t.next_review_date <= CURRENT_TIMESTAMP
        GROUP BY t.id
        ORDER BY t.next_review_date ASC
    """)
    topics_db = cursor.fetchall()
    
    topics_response = []
    for topic_db in topics_db:
        topic_data = dict(topic_db)
        topic_data["questions"] = json.loads(topic_data["questions"])
        topic_data["tags"] = topic_data["tags_names"].split(',') if topic_data["tags_names"] else []
        del topic_data["tags_names"]
        topics_response.append(TopicResponse(**topic_data))
        
    conn.close()
    return topics_response

@app.post("/topics/{topic_id}/review")
async def review_topic(topic_id: int, feedback: ReviewFeedback):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT repetitions, ease_factor FROM Topic WHERE id = ?", (topic_id,))
    topic_data = cursor.fetchone()

    if not topic_data:
        raise HTTPException(status_code=404, detail="Tópico não encontrado.")

    repetitions = topic_data["repetitions"]
    ease_factor = topic_data["ease_factor"]

    new_next_review, new_repetitions, new_ease_factor = calculate_next_review(
        repetitions, ease_factor, feedback.quality
    )

    cursor.execute(
        "UPDATE Topic SET next_review_date = ?, repetitions = ?, ease_factor = ?, last_reviewed = CURRENT_TIMESTAMP WHERE id = ?",
        (new_next_review, new_repetitions, new_ease_factor, topic_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Revisão registrada com sucesso", "next_review": new_next_review}

@app.get("/tags", response_model=list[TagResponse])
async def get_all_tags():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Tag")
    tags_db = cursor.fetchall()
    conn.close()
    return [TagResponse(**dict(tag)) for tag in tags_db]


# --- Ponto de Entrada para Execução com Uvicorn ---
if __name__ == "__main__":
    print("FastAPI backend iniciando com Uvicorn...")
    try:
        # Ao rodar via PyInstaller, ele executará este script.
        # O Uvicorn precisa ser iniciado aqui.
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        print(f"Erro ao iniciar Uvicorn: {e}", file=sys.stderr)
        sys.exit(1) # Sair com código de erro
