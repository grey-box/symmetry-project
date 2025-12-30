import logging
from fastapi import APIRouter, Query

from app.models import (
    ModelSelectionResponse,
    ListResponse,
)
from app.models.server_model import ServerModel

router = APIRouter(prefix="/models", tags=["models"])

server = ServerModel()


@router.get("/translation/select", response_model=ModelSelectionResponse)
def select_translation_model(modelname: str):
    return {"successful": str(server.select_translation_model(modelname))}


@router.get("/translation/delete", response_model=ModelSelectionResponse)
def delete_translation_model(modelname: str):
    return {"successful": str(server.delete_translation_model(modelname))}


@router.get("/translation/import", response_model=ModelSelectionResponse)
def import_translation_model(model: str, from_huggingface: bool):
    return {
        "successful": str(server.import_new_translation_model(model, from_huggingface))
    }


@router.get("/comparison/select", response_model=ModelSelectionResponse)
def select_comparison_model(modelname: str):
    return {"successful": str(server.select_comparison_model(modelname))}


@router.get("/comparison/delete", response_model=ModelSelectionResponse)
def delete_comparison_model(modelname: str):
    return {"successful": str(server.delete_comparison_model(modelname))}


@router.get("/comparison/import", response_model=ModelSelectionResponse)
def import_comparison_model(model: str, from_huggingface: bool):
    return {
        "successful": str(server.import_new_comparison_model(model, from_huggingface))
    }


@router.get("/translation", response_model=ListResponse)
def list_translation_models():
    return {"response": server.available_translation_models_list()}


@router.get("/comparison", response_model=ListResponse)
def list_comparison_models():
    return {"response": server.available_comparison_models_list()}


@router.get("/comparison/selected", response_model=ListResponse)
def get_selected_comparison_model():
    return {"response": [server.selected_comparison_model]}


@router.get("/translation/selected", response_model=ListResponse)
def get_selected_translation_model():
    return {"response": [server.selected_translation_model]}
