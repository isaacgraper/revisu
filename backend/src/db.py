import sqlite3
import os
from typing import List, Dict, Any, Optional

DATABASE_FILE = "revisu_data.db"

def get_db_connection():
    """Obtém uma conexão com o banco de dados."""

    db_path = os.path.join(os.path.dirname(__file__), DATABASE_FILE)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    return conn

def init_db():
    """Inicializa o esquema do banco de dados se não existir."""

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

    print("INFO: Database SQLite initialized.")

def insert_file(
    file_path: str | None,
    file_name: str | None,
    file_type: str,
    original_content: str
    ) -> int | None:
    """Insere um novo arquivo no DB e retorna seu ID."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO File (file_path, file_name, file_type, original_content) VALUES (?, ?, ?, ?)",
        (file_path, file_name, file_type, original_content)
    )
    file_id = cursor.lastrowid
    conn.commit()

    conn.close()

    return file_id

def insert_topic(
    file_id: int | None,
    title: Optional[str],
    summary: str,
    questions_json: str,
    next_review_date: str,
    ease_factor: float,
    repetitions: int,
    last_reviewed: Optional[str] = None
) -> int | None:
    """Insere um novo tópico no DB e retorna seu ID."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO Topic (file_id, title, summary, questions, next_review_date, ease_factor, repetitions, last_reviewed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (file_id, title, summary, questions_json, next_review_date, ease_factor, repetitions, last_reviewed)
    )

    topic_id = cursor.lastrowid
    conn.commit()

    conn.close()

    return topic_id

def get_or_create_tag(tag_name: str) -> int:
    """Busca um tag existente ou cria um novo, retornando seu ID."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("INSERT OR IGNORE INTO Tag (name) VALUES (?)", (tag_name,))
    conn.commit()

    cursor.execute("SELECT id FROM Tag WHERE name = ?", (tag_name,))
    tag_id = cursor.fetchone()["id"]

    conn.close()

    return tag_id

def link_topic_to_tag(topic_id: int | None, tag_id: int):
    """Associa um tópico a uma tag."""

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT OR IGNORE INTO TopicTag (topic_id, tag_id) VALUES (?, ?)", # Usar IGNORE para evitar duplicatas
            (topic_id, tag_id),
        )
        conn.commit()
    finally:
        conn.close()

def get_all_files_db(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Busca todos os arquivos do DB, com seus tópicos e tags."""

    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM File ORDER BY processed_at DESC"
    if limit is not None:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    files_db = cursor.fetchall()

    conn.close()

    all_files_data = []
    for file_row in files_db:
        file_data = dict(file_row)
        file_data["topics"] = get_topics_for_file_db(file_data["id"])
        all_files_data.append(file_data)

    return all_files_data

def get_file_by_id_db(file_id: int | None) -> Optional[Dict[str, Any]]:
    """Busca um arquivo específico (com tópicos e tags) pelo ID do DB."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM File WHERE id = ?", (file_id,))
    file_data = cursor.fetchone()

    conn.close()

    if file_data:
        file_dict = dict(file_data)
        file_dict["topics"] = get_topics_for_file_db(file_dict["id"])
        return file_dict

    return None

def get_topics_for_file_db(file_id: int) -> List[Dict[str, Any]]:
    """Busca todos os tópicos e suas tags para um dado file_id."""

    conn = get_db_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.*, GROUP_CONCAT(tg.name) AS tags_names
        FROM Topic t
        LEFT JOIN TopicTag tt ON t.id = tt.topic_id
        LEFT JOIN Tag tg ON tt.tag_id = tg.id
        WHERE t.file_id = ?
        GROUP BY t.id
        ORDER BY t.id
    """, (file_id,))
    topics_db = cursor.fetchall()

    conn.close()

    return [dict(topic_row) for topic_row in topics_db]

def get_topics_for_review_db() -> List[Dict[str, Any]]:
    """Retorna tópicos prontos para revisão do DB."""

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

    conn.close()

    return [dict(topic_row) for topic_row in topics_db]

def get_topic_review_data_db(topic_id: int) -> Optional[Dict[str, Any]]:
    """Busca dados de revisão de um tópico específico."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT repetitions, ease_factor FROM Topic WHERE id = ?", (topic_id,))
    data = cursor.fetchone()

    conn.close()

    return dict(data) if data else None

def update_topic_review_data_db(topic_id: int, next_review_date: str, repetitions: int, ease_factor: float, last_reviewed: str):
    """Atualiza os dados de revisão de um tópico no DB."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE Topic SET next_review_date = ?, repetitions = ?, ease_factor = ?, last_reviewed = ? WHERE id = ?",
        (next_review_date, repetitions, ease_factor, last_reviewed, topic_id)
    )

    conn.commit()

    conn.close()

def get_all_tags_db() -> List[Dict[str, Any]]:
    """Retorna todas as tags do DB."""

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Tag")

    tags_db = cursor.fetchall()

    conn.close()

    return [dict(tag) for tag in tags_db]
