import os
import json
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from dotenv import load_dotenv

from src.db import (
    insert_topic,
    insert_file,
    get_or_create_tag,
    link_topic_to_tag,
    get_file_by_id_db,
    get_all_files_db,
    get_topics_for_review_db,
    get_topic_review_data_db,
    update_topic_review_data_db,
    get_all_tags_db
)
from src.models import FileResponse, TopicResponse, TagResponse

load_dotenv()

# Configuração da API Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')

def process_content_with_gemini(content: str) -> Dict[str, Any]:
    """
    Usa a IA para gerar título, resumo, perguntas e tags de um texto.
    """
    try:
        prompt = f"""Gere JSON apenas com o seguinte modelo:
            {{
                "titulo": "título conciso",
                "resumo": "resumo em 2-3 frases",
                "tags": ["tag1", "tag2", "tag3"],
                "perguntas": ["pergunta1?", "pergunta2?", "pergunta3?"]
            }}

            Contexto: Idioma em português. Nota do usuário limitada por segurança. Revisão rápida e concisa.

            Propósito: Revisão espaçada, baseando-se na nota fornecida e preenchendo o JSON de acordo.

            Com a seguinte nota: {content[:2000]}
            """

        response = model.generate_content(prompt)
        generated_text = response.text

        try:
            json_str = generated_text.strip()
            if json_str.startswith('```'):
                json_str = json_str.split('\n', 1)[1].rsplit('\n', 1)[0]

            parsed_data = json.loads(json_str)

            return {
                "title": parsed_data.get("titulo", content.split('\n')[0][:50] if content else "Novo Tópico"),
                "summary": parsed_data.get("resumo", "Resumo não disponível."),
                "tags": parsed_data.get("tags", ["geral"])[:3],
                "questions": parsed_data.get("perguntas", ["Revise o conteúdo."])[:5]
            }

        except json.JSONDecodeError as e:
            print(f"JSON inválido: {e}")
            return {
                "title": "Título Manual",
                "summary": "Erro no processamento.",
                "tags": ["erro"],
                "questions": ["Revisar nota?"]
            }

    except Exception as e:
        print(f"Erro API: {e}")
        return {
            "title": "Erro",
            "summary": "Falha na API.",
            "tags": ["erro-api"],
            "questions": ["Tentar novamente?"]
        }

def calculate_next_review(repetitions: int, ease_factor: float, quality: int) -> Tuple[datetime, int, float]:
    """
    Calcula a próxima data de revisão, fator de facilidade e repetições
    usando o algoritmo SM-2 (SuperMemo 2).
    """

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

async def process_new_file(file_name: str | None, file_type: str, original_content: str) -> FileResponse:
    """
    Orquestra o processamento de um novo arquivo:
    1. Salva o arquivo no DB.
    2. Processa o conteúdo com a IA.
    3. Salva os tópicos e tags no DB.
    4. Retorna o FileResponse completo.
    """

    file_id = insert_file(file_name, file_name, file_type, original_content)

    gemini_result = process_content_with_gemini(original_content)
    title = gemini_result["title"]
    summary = gemini_result["summary"]
    questions = gemini_result["questions"]
    tags_to_add = gemini_result["tags"]

    initial_next_review_date = datetime.now() + timedelta(minutes=5)

    topic_id = insert_topic(
        file_id=file_id,
        title=title,
        summary=summary,
        questions_json=json.dumps(questions),
        next_review_date=initial_next_review_date.isoformat(),
        ease_factor=2.5,
        repetitions=0,
        last_reviewed=None
    )

    for tag_name in tags_to_add:
        tag_id = get_or_create_tag(tag_name)
        link_topic_to_tag(topic_id, tag_id)

    file_data = get_file_by_id_db(file_id)
    if not file_data:
        raise Exception("Arquivo não encontrado após o processamento.")

    return _format_file_data_to_response(file_data)

def get_all_files_service(limit: Optional[int] = None) -> List[FileResponse]:
    """
    Busca todos os arquivos processados (opcionalmente limitado) e os formata.
    """

    files_db_data = get_all_files_db(limit)

    return [_format_file_data_to_response(file_data) for file_data in files_db_data]

def get_file_details_service(file_id: int) -> Optional[FileResponse]:
    """
    Busca os detalhes de um arquivo específico e os formata.
    """

    file_db_data = get_file_by_id_db(file_id)
    if file_db_data:
        return _format_file_data_to_response(file_db_data)

    return None

def get_topics_for_review_service() -> List[TopicResponse]:
    """
    Retorna a lista de tópicos prontos para revisão, formatados.
    """

    topics_db_data = get_topics_for_review_db()

    return [_format_topic_data_to_response(topic_data) for topic_data in topics_db_data]

def review_topic_service(topic_id: int, quality: int) -> Dict[str, Any]:
    """
    Registra o feedback de revisão para um tópico e recalcula a próxima data.
    """

    topic_current_data = get_topic_review_data_db(topic_id)

    if not topic_current_data:
        raise ValueError("Tópico não encontrado.")

    repetitions = topic_current_data["repetitions"]
    ease_factor = topic_current_data["ease_factor"]

    new_next_review, new_repetitions, new_ease_factor = calculate_next_review(
        repetitions, ease_factor, quality
    )

    update_topic_review_data_db(
        topic_id,
        new_next_review.isoformat(),
        new_repetitions,
        new_ease_factor,
        datetime.now().isoformat()
    )
    return {"message": "Revisão registrada com sucesso", "next_review": new_next_review.isoformat()}

def get_all_tags_service() -> List[TagResponse]:
    """
    Retorna a lista de todas as tags, formatadas.
    """

    tags_db_data = get_all_tags_db()

    return [TagResponse(**tag_data) for tag_data in tags_db_data]

def _format_topic_data_to_response(topic_data: Dict[str, Any]) -> TopicResponse:
    """Formata um dicionário de dados de tópico do DB para TopicResponse."""

    try:
        questions_list = json.loads(topic_data["questions"])
    except (json.JSONDecodeError, TypeError):
        questions_list = ["Erro ao carregar perguntas ou formato inválido."]

    tags_list = []

    if topic_data.get("tags_names"):
        # Garante que tags_names é uma string antes de splitar
        if isinstance(topic_data["tags_names"], str):
            tags_list = topic_data["tags_names"].split(',')
        else:
            print(f"Aviso: tags_names não é string para o tópico {topic_data['id']}: {topic_data['tags_names']}")


    return TopicResponse(
        id=topic_data["id"],
        file_id=topic_data["file_id"],
        title=topic_data["title"],
        summary=topic_data["summary"],
        questions=questions_list,
        next_review_date=datetime.fromisoformat(topic_data["next_review_date"]),
        ease_factor=topic_data["ease_factor"],
        repetitions=topic_data["repetitions"],
        last_reviewed=datetime.fromisoformat(topic_data["last_reviewed"]) if topic_data["last_reviewed"] else None,
        tags=tags_list
    )

def _format_file_data_to_response(file_data: Dict[str, Any]) -> FileResponse:
    """Formata um dicionário de dados de arquivo do DB para FileResponse."""

    topics_response = []

    for topic_db_data in file_data.get("topics", []):
        topics_response.append(_format_topic_data_to_response(topic_db_data))

    return FileResponse(
        id=file_data["id"],
        file_path=file_data["file_path"],
        file_name=file_data["file_name"],
        file_type=file_data["file_type"],
        processed_at=datetime.fromisoformat(file_data["processed_at"]) if isinstance(file_data["processed_at"], str) else file_data["processed_at"],
        topics=topics_response
    )
