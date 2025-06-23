import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.services import (
    calculate_next_review,
    process_content_with_gemini,
    process_new_file,
)

from src.services import (
    _format_file_data_to_response,
    _format_topic_data_to_response
)

from src.models import TopicResponse, FileResponse

def test_calculate_next_review_quality_5_initial():
    repetitions = 0
    ease_factor = 2.5
    quality = 5

    with patch('src.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 5, 27, 10, 0, 0)
        mock_datetime.timedelta = timedelta
        mock_datetime.fromisoformat = datetime.fromisoformat

        next_review, new_repetitions, new_ease_factor = calculate_next_review(
            repetitions, ease_factor, quality
        )

        assert new_repetitions == 1
        assert abs(new_ease_factor - 2.6) < 0.001
        assert next_review == datetime(2025, 5, 27, 10, 0, 0) + timedelta(days=1)


def test_calculate_next_review_quality_5_second_review():
    repetitions = 1
    ease_factor = 2.5
    quality = 5

    with patch('src.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 5, 27, 10, 0, 0)
        mock_datetime.timedelta = timedelta
        mock_datetime.fromisoformat = datetime.fromisoformat

        next_review, new_repetitions, new_ease_factor = calculate_next_review(
            repetitions, ease_factor, quality
        )

        assert new_repetitions == 2
        assert abs(new_ease_factor - 2.6) < 0.001
        assert next_review == datetime(2025, 5, 27, 10, 0, 0) + timedelta(days=6)

def test_calculate_next_review_quality_5_subsequent_reviews():
    repetitions = 2
    ease_factor = 2.5
    quality = 5

    with patch('src.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 5, 27, 10, 0, 0)
        mock_datetime.timedelta = timedelta
        mock_datetime.fromisoformat = datetime.fromisoformat

        next_review, new_repetitions, new_ease_factor = calculate_next_review(
            repetitions, ease_factor, quality
        )
        assert new_repetitions == 3
        assert abs(new_ease_factor - 2.6) < 0.001
        assert next_review == datetime(2025, 5, 27, 10, 0, 0) + timedelta(days=7)

def test_calculate_next_review_quality_less_than_3():
    repetitions = 3
    ease_factor = 2.6
    quality = 2

    with patch('src.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 5, 27, 10, 0, 0)
        mock_datetime.timedelta = timedelta
        mock_datetime.fromisoformat = datetime.fromisoformat

        next_review, new_repetitions, new_ease_factor = calculate_next_review(
            repetitions, ease_factor, quality
        )
        assert new_repetitions == 0
        assert abs(new_ease_factor - max(1.3, ease_factor - 0.20)) < 0.001
        assert next_review == datetime(2025, 5, 27, 10, 0, 0) + timedelta(minutes=1)

def test_calculate_next_review_edge_case_ease_factor_min():
    repetitions = 1
    ease_factor = 1.4
    quality = 0

    with patch('src.services.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 5, 27, 10, 0, 0)
        mock_datetime.timedelta = timedelta
        mock_datetime.fromisoformat = datetime.fromisoformat

        next_review, new_repetitions, new_ease_factor = calculate_next_review(
            repetitions, ease_factor, quality
        )
        assert new_repetitions == 0
        assert abs(new_ease_factor - 1.3) < 0.001
        assert next_review == datetime(2025, 5, 27, 10, 0, 0) + timedelta(minutes=1)

@patch('src.services.model')
def test_process_content_with_gemini_success(mock_gemini_model):
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "titulo": "Título de Teste",
        "resumo": "Este é um resumo de teste.",
        "tags": ["teste", "python", "gemini"],
        "perguntas": ["P1?", "P2?"]
    })
    mock_gemini_model.generate_content.return_value = mock_response

    content = "Conteúdo de teste para a IA."
    result = process_content_with_gemini(content)

    mock_gemini_model.generate_content.assert_called_once()

    assert result["title"] == "Título de Teste"
    assert result["summary"] == "Este é um resumo de teste."
    assert result["tags"] == ["teste", "python", "gemini"]
    assert result["questions"] == ["P1?", "P2?"]


@patch('src.services.model')
def test_process_content_with_gemini_invalid_json(mock_gemini_model):
    mock_response = MagicMock()
    mock_response.text = "Isso não é um JSON válido."
    mock_gemini_model.generate_content.return_value = mock_response

    content = "Conteúdo de teste."
    result = process_content_with_gemini(content)

    assert result["title"] == "Erro na IA - Título Padrão"
    assert "Resumo gerado manualmente" in result["summary"]
    assert "erro-ia" in result["tags"]

@patch('src.services.model')
def test_process_content_with_gemini_api_error(mock_gemini_model):
    mock_gemini_model.generate_content.side_effect = Exception("Erro de conexão simulado")

    content = "Conteúdo de teste."
    result = process_content_with_gemini(content)

    assert result["title"] == "Erro na IA - Título Padrão"
    assert result["summary"] == "Resumo gerado manualmente devido a erro geral na API."
    assert "erro-api" in result["tags"]

def test_format_topic_data_to_response_valid():
    topic_data = {
        "id": 1,
        "file_id": 101,
        "title": "Introdução ao Python",
        "summary": "Fundamentos da linguagem Python.",
        "questions": '["O que é Python?", "Para que serve Python?"]',
        "next_review_date": datetime(2025, 5, 28).isoformat(),
        "ease_factor": 2.5,
        "repetitions": 1,
        "last_reviewed": datetime(2025, 5, 27).isoformat(),
        "tags_names": "programacao,python,iniciante"
    }

    response = _format_topic_data_to_response(topic_data)

    assert isinstance(response, TopicResponse)
    assert response.id == 1
    assert response.title == "Introdução ao Python"
    assert response.questions == ["O que é Python?", "Para que serve Python?"]
    assert response.tags == ["programacao", "python", "iniciante"]
    assert response.next_review_date == datetime(2025, 5, 28)

def test_format_topic_data_to_response_invalid_questions():
    topic_data = {
        "id": 2,
        "file_id": 102,
        "title": "Tópico com erro",
        "summary": "Erro de perguntas.",
        "questions": "não-json",
        "next_review_date": datetime(2025, 5, 29).isoformat(),
        "ease_factor": 2.5,
        "repetitions": 0,
        "last_reviewed": None,
        "tags_names": "erro,teste"
    }

    response = _format_topic_data_to_response(topic_data)

    assert "Erro ao carregar perguntas" in response.questions[0]

def test_format_file_data_to_response():
    file_data = {
        "id": 201,
        "file_path": "/path/to/note.md",
        "file_name": "note.md",
        "file_type": "md",
        "processed_at": datetime(2025, 5, 27, 9, 0, 0).isoformat(),
        "topics": [
            {
                "id": 3,
                "file_id": 201,
                "title": "Subtópico 1",
                "summary": "Resumo subtópico 1.",
                "questions": '["Q1?", "Q2?"]',
                "next_review_date": datetime(2025, 5, 29).isoformat(),
                "ease_factor": 2.5,
                "repetitions": 0,
                "last_reviewed": None,
                "tags_names": "subtopico,teste"
            }
        ]
    }

    response = _format_file_data_to_response(file_data)

    assert isinstance(response, FileResponse)
    assert response.id == 201
    assert response.file_name == "note.md"
    assert len(response.topics) == 1
    assert response.topics[0].title == "Subtópico 1"
    assert response.processed_at == datetime(2025, 5, 27, 9, 0, 0)

@pytest.mark.asyncio
@patch('src.services.insert_file')
@patch('src.services.process_content_with_gemini')
@patch('src.services.insert_topic')
@patch('src.services.get_or_create_tag')
@patch('src.services.link_topic_to_tag')
@patch('src.services.get_file_by_id_db')
@patch('src.services._format_file_data_to_response')
async def test_process_new_file_success(
    mock_format_file,
    mock_get_file_by_id,
    mock_link_topic_tag,
    mock_get_or_create_tag,
    mock_insert_topic,
    mock_process_gemini,
    mock_insert_file
):
    mock_insert_file.return_value = 1
    mock_process_gemini.return_value = {
        "title": "Título IA", "summary": "Resumo IA",
        "questions": ["Q1"], "tags": ["tag1", "tag2"]
    }
    mock_insert_topic.return_value = 101
    mock_get_or_create_tag.side_effect = [1, 2]
    mock_get_file_by_id.return_value = {"id": 1, "topics": []}
    mock_format_file.return_value = MagicMock(spec=FileResponse)

    file_name = "test.md"
    file_type = "md"
    content = "Conteúdo do arquivo."

    from src.services import process_new_file
    result = await process_new_file(file_name, file_type, content)

    mock_insert_file.assert_called_once_with(file_name, file_name, file_type, content)
    mock_process_gemini.assert_called_once_with(content)
    mock_insert_topic.assert_called_once_with(
        file_id=1,
        title="Título IA",
        summary="Resumo IA",
        questions_json=json.dumps(["Q1"]),
        next_review_date=mock_insert_topic.call_args.kwargs['next_review_date'],
        ease_factor=2.5,
        repetitions=0,
        last_reviewed=None
    )

    mock_get_or_create_tag.assert_any_call("tag1")
    mock_get_or_create_tag.assert_any_call("tag2")
    mock_link_topic_tag.assert_any_call(101, 1)
    mock_link_topic_tag.assert_any_call(101, 2)
    mock_get_file_by_id.assert_called_once_with(1)
    mock_format_file.assert_called_once()

    assert result is not None
    assert isinstance(result, MagicMock)
