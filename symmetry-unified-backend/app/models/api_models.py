from pydantic import BaseModel
from typing import List

# "original_sentences": original_sentences,
# "translated_sentences": translated_sentences,
# "missing_info": missing_info,
# "extra_info": extra_info,
# "missing_info_indices": missing_info_indices,
# "extra_info_indices": extra_info_indices,
# "success": success

class ComparisonResponse(BaseModel):
    original_sentences: List[str]
    translated_sentences: List[str] 
    missing_info: List[str]
    extra_info: List[str]
    missing_info_indices: List[int]
    extra_info_indices: List[int]
    success: bool

class TranslationResponse(BaseModel):
    translated_text: str
    successful: bool

class ArticleResponse(BaseModel):
    source_article: str
    article_languages: List[str]

class ModelSelectionResponse(BaseModel):
    successful: str

class ListResponse(BaseModel):
    response: List[str]


