from pydantic import BaseModel
from datetime import datetime
from typing import List

class TopicResponse(BaseModel):
    id: int
    file_id: int
    title: str | None
    summary: str
    questions: List[str]
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
    topics: List[TopicResponse] = []

class TagResponse(BaseModel):
    id: int
    name: str

class ReviewFeedback(BaseModel):
    topic_id: int
    quality: int
