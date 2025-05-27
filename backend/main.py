import uvicorn
import sys

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Form
)

from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from src.db import init_db
from src.models import (
    FileResponse,
    TopicResponse,
    TagResponse,
    ReviewFeedback
)

from src.services import (
    process_new_file,
    get_all_files_service,
    get_file_details_service,
    get_topics_for_review_service,
    review_topic_service,
    get_all_tags_service
)

app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.post("/files/process", response_model=FileResponse)
async def process_file(file: UploadFile = File(...), file_type: str = Form(...)):
    """
    Processa um arquivo enviado, extrai tópicos e os salva no banco de dados.
    """
    try:
        content = await file.read()
        original_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400, detail="Não foi possível decodificar o arquivo. Certifique-se de que é um arquivo de texto válido (UTF-8)."
        )

    processed_file_response = await process_new_file(
        file_name=file.filename,
        file_type=file_type,
        original_content=original_content
    )
    return processed_file_response

@app.get("/files", response_model=List[FileResponse])
async def get_all_files_api(limit: Optional[int] = None):
    """
    Retorna todos os arquivos processados, opcionalmente limitado.
    """
    files_data = get_all_files_service(limit=limit)
    return files_data

@app.get("/files/{file_id}", response_model=FileResponse)
async def get_file_by_id_api(file_id: int):
    """
    Retorna os detalhes de um arquivo específico, incluindo seus tópicos, pelo ID.
    """
    file_data = get_file_details_service(file_id)
    if not file_data:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return file_data

@app.get("/topics/for-review", response_model=List[TopicResponse])
async def get_topics_for_review_endpoint():
    """
    Endpoint que retorna uma lista de tópicos que estão prontos para revisão,
    baseado na `next_review_date`.
    """

    return get_topics_for_review_service()

@app.post("/topics/{topic_id}/review")
async def review_topic_endpoint(topic_id: int, feedback: ReviewFeedback):
    """
    Endpoint que registra o feedback de revisão para um tópico e recalcula a próxima data de revisão.
    """

    try:
        result = review_topic_service(topic_id, feedback.quality)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar revisão: {e}")

@app.get("/tags", response_model=List[TagResponse])
async def get_all_tags_endpoint():
    """
    Endpoint que retorna uma lista de todas as tags existentes.
    """
    return get_all_tags_service()

if __name__ == "__main__":
    print("Initializing FastAPI backend with Uvicorn...")
    try:
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception as e:
        print(f"Error initializing Uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
