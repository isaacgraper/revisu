import uvicorn
import sqlite3
import os
import sys
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

import google.generativeai as genai
from typing import Optional

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')

app = FastAPI()

# CORS Middleware
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração do Banco de Dados
DATABASE_FILE = "revisu_data.db"

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS File (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            original_content TEXT NOT NULL,
            processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Tag (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

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

init_db()

"""

Classes para as entendidas do banco de dados local.

"""
class TopicResponse(BaseModel):
    id: int
    file_id: int
    title: str | None
    summary: str
    questions: list[str]
    next_review_date: datetime
    ease_factor: float
    repetitions: int
    last_reviewed: datetime | None
    tags: list[str] = []

class FileResponse(BaseModel):
    id: int
    file_path: str
    file_name: str
    file_type: str
    processed_at: datetime
    topics: list[TopicResponse] = []

class TagResponse(BaseModel):
    id: int
    name: str

class ReviewFeedback(BaseModel):
    topic_id: int
    quality: int

"""

Processa o conteúdo usando a API do Google Gemini para extrair título,
resumo, perguntas e tags.

"""
def process_content_with_gemini(content: str):
    try:
        prompt = f"""
        Você é um assistente de estudo focado em revisão espaçada.
        Dada a seguinte nota, por favor, gere um JSON com:
        1. Um `titulo` conciso para o tópico da nota.
        2. Um `resumo` detalhado do conteúdo principal.
        3. Uma lista de `tags` (5 a 8 palavras-chave relevantes).
        4. Uma lista de `perguntas` (3 a 5 perguntas de múltipla escolha ou abertas) que ajudem na memorização ativa e revisão espaçada.

        Certifique-se de que a saída seja um JSON válido.

        Conteúdo da Nota:
        {content[:3000]}
        """

        response = model.generate_content(prompt)
        generated_text = response.text

        try:
            if generated_text.strip().startswith('```json') and generated_text.strip().endswith('```'):
                json_str = generated_text.strip()[7:-3].strip()
            else:
                json_str = generated_text.strip()

            parsed_data = json.loads(json_str)

            summary = parsed_data.get("resumo", "Resumo não encontrado.")
            title = parsed_data.get("titulo", content.split('\n')[0][:50] if content else "Novo Tópico")

            raw_questions = parsed_data.get("perguntas", [])
            questions: list[str] = []
            if isinstance(raw_questions, list) and all(isinstance(q, str) for q in raw_questions):
                questions = raw_questions
            elif isinstance(raw_questions, str):
                questions = [q.strip() for q in raw_questions.split('\n') if q.strip()]
            else:
                questions = ["Por favor, reformule sua nota para gerar perguntas.", "Não foi possível extrair perguntas."]

            raw_tags = parsed_data.get("tags", [])
            tags: list[str] = []
            if isinstance(raw_tags, list) and all(isinstance(t, str) for t in raw_tags):
                tags = raw_tags
            elif isinstance(raw_tags, str):
                tags = [t.strip() for t in raw_tags.split(',') if t.strip()]
            else:
                tags = ["sem-tags", "geral"]

            return {
                "title": title,
                "summary": summary,
                "tags": tags,
                "questions": questions
            }

        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON da resposta do Gemini: {e}")
            print(f"Resposta bruta do Gemini: {generated_text[:500]}...")
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

"""

Calcula a próxima data de revisão, fator de facilidade e repetições
usando o algoritmo SM-2 (SuperMemo 2).

"""
def calculate_next_review(repetitions: int, ease_factor: float, quality: int):
    if quality < 3:
        repetitions = 0
        ease_factor = max(1.3, ease_factor - 0.20)
    else:
        repetitions += 1
        ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

    if repetitions == 0:
        interval = timedelta(minutes=1)
    elif repetitions == 1:
        interval = timedelta(days=1)
    elif repetitions == 2:
        interval = timedelta(days=6)
    else:
        interval = timedelta(days=int(repetitions * ease_factor))

    next_review = datetime.now() + interval
    return next_review, repetitions, ease_factor

"""

Processa um arquivo enviado, extrai informações usando IA e as armazena no banco de dados.
Retorna os dados do arquivo processado, incluindo os tópicos gerados.

"""
@app.post("/files/process", response_model=FileResponse)
async def process_file(file: UploadFile = File(...), file_type: str = Form(...)):
    conn = get_db_connection()
    cursor = conn.cursor()

    content_bytes = await file.read()
    original_content = content_bytes.decode("utf-8")

    file_name_to_save = file.filename
    file_path_to_save = file.filename

    cursor.execute(
        "INSERT INTO File (file_path, file_name, file_type, original_content) VALUES (?, ?, ?, ?)",
        (file_path_to_save, file_name_to_save, file_type, original_content)
    )
    file_id = cursor.lastrowid

    gemini_result = process_content_with_gemini(original_content)
    title = gemini_result["title"]
    summary = gemini_result["summary"]
    questions = gemini_result["questions"]
    tags_to_add = gemini_result["tags"]

    initial_next_review_date = datetime.now() + timedelta(minutes=5)

    cursor.execute(
        "INSERT INTO Topic (file_id, title, summary, questions, next_review_date, ease_factor, repetitions) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_id, title, summary, json.dumps(questions), initial_next_review_date, 2.5, 0)
    )
    topic_id = cursor.lastrowid

    for tag_name in tags_to_add:
        cursor.execute("INSERT OR IGNORE INTO Tag (name) VALUES (?)", (tag_name,))
        cursor.execute("SELECT id FROM Tag WHERE name = ?", (tag_name,))
        tag_id = cursor.fetchone()["id"]
        cursor.execute("INSERT OR IGNORE INTO TopicTag (topic_id, tag_id) VALUES (?, ?)", (topic_id, tag_id))

    conn.commit()
    conn.close()

    return_file = {
        "id": file_id,
        "file_path": file_path_to_save,
        "file_name": file_name_to_save,
        "file_type": file_type,
        "processed_at": datetime.now(),
        "topics": [{
            "id": topic_id,
            "file_id": file_id,
            "title": title,
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

"""

Retorna uma lista de todos os arquivos processados e seus tópicos associados.

"""
@app.get("/files", response_model=list[FileResponse])
async def get_all_files(limit: Optional[int] = None):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM File ORDER BY processed_at DESC"

    if limit is not None:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    files_db = cursor.fetchall()

    files_response = []
    for file_db in files_db:
        file_data = dict(file_db)

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
            topic_data["questions"] = json.loads(topic_data["questions"])
            topic_data["tags"] = topic_data["tags_names"].split(',') if topic_data["tags_names"] else []
            del topic_data["tags_names"]
            topics_response.append(TopicResponse(**topic_data))

        file_data["topics"] = topics_response
        files_response.append(FileResponse(**file_data))

    conn.close()
    return files_response

"""

Retorna os detalhes de um arquivo específico, incluindo seus tópicos, pelo ID.

"""
@app.get("/files/{file_id}", response_model=FileResponse)
async def get_file_by_id(file_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM File WHERE id = ?", (file_id,))
    file_db = cursor.fetchone()

    if not file_db:
        conn.close()
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    file_data = dict(file_db)

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
        try:
            topic_data["questions"] = json.loads(topic_data["questions"])
        except json.JSONDecodeError:
            print(f"Aviso: Não foi possível decodificar JSON para perguntas do tópico {topic_data['id']}. Conteúdo: {topic_data['questions']}")
            topic_data["questions"] = ["Erro ao carregar perguntas."]

        topic_data["tags"] = topic_data["tags_names"].split(',') if topic_data["tags_names"] else []
        del topic_data["tags_names"]

        topics_response.append(TopicResponse(**topic_data))

    file_data["topics"] = topics_response
    conn.close()
    return FileResponse(**file_data)

"""

Retorna uma lista de tópicos que estão prontos para revisão,
baseado na `next_review_date`.

"""
@app.get("/topics/for-review", response_model=list[TopicResponse])
async def get_topics_for_review():

    conn = get_db_connection()
    cursor = conn.cursor()

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

"""

Registra o feedback de revisão para um tópico e recalcula a próxima data de revisão.

"""
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

"""

Retorna uma lista de todas as tags existentes.

"""
@app.get("/tags", response_model=list[TagResponse])
async def get_all_tags():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Tag")
    tags_db = cursor.fetchall()
    conn.close()
    return [TagResponse(**dict(tag)) for tag in tags_db]

if __name__ == "__main__":
    print("Initializing FastAPI backend with Uvicorn...")
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        print(f"Error initializing Uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
