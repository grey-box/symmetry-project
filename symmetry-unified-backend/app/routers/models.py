import logging
from fastapi import APIRouter, Query

from app.models import (
    ModelSelectionResponse,
    ListResponse,
)
from app.models.server_model import ServerModel

router = APIRouter(prefix="/models", tags=["models"])

server = ServerModel()


@router.get(
    "/translation/select",
    response_model=ModelSelectionResponse,
    summary="Select Translation Model",
    description="Sets the active translation model from available models.",
)
def select_translation_model(
    modelname: str = Query(..., description="Name of the translation model to select"),
):
    return {"successful": str(server.select_translation_model(modelname))}


@router.get(
    "/translation/delete",
    response_model=ModelSelectionResponse,
    summary="Delete Translation Model",
    description="Removes a translation model from the available models.",
)
def delete_translation_model(
    modelname: str = Query(..., description="Name of the translation model to delete"),
):
    return {"successful": str(server.delete_translation_model(modelname))}


@router.get(
    "/translation/import",
    response_model=ModelSelectionResponse,
    summary="Import Translation Model",
    description="Imports a new translation model from HuggingFace or local storage.",
)
def import_translation_model(
    model: str = Query(
        ..., description="Name or path of the translation model to import"
    ),
    from_huggingface: bool = Query(
        False,
        description="Whether to import from HuggingFace (true) or local storage (false)",
    ),
):
    return {
        "successful": str(server.import_new_translation_model(model, from_huggingface))
    }


@router.get(
    "/comparison/select",
    response_model=ModelSelectionResponse,
    summary="Select Comparison Model",
    description="Sets the active comparison model from available models.",
)
def select_comparison_model(
    modelname: str = Query(..., description="Name of the comparison model to select"),
):
    return {"successful": str(server.select_comparison_model(modelname))}


@router.get(
    "/comparison/delete",
    response_model=ModelSelectionResponse,
    summary="Delete Comparison Model",
    description="Removes a comparison model from the available models.",
)
def delete_comparison_model(
    modelname: str = Query(..., description="Name of the comparison model to delete"),
):
    return {"successful": str(server.delete_comparison_model(modelname))}


@router.get(
    "/comparison/import",
    response_model=ModelSelectionResponse,
    summary="Import Comparison Model",
    description="Imports a new comparison model from HuggingFace or local storage.",
)
def import_comparison_model(
    model: str = Query(
        ..., description="Name or path of the comparison model to import"
    ),
    from_huggingface: bool = Query(
        False,
        description="Whether to import from HuggingFace (true) or local storage (false)",
    ),
):
    return {
        "successful": str(server.import_new_comparison_model(model, from_huggingface))
    }


@router.get(
    "/translation",
    response_model=ListResponse,
    summary="List Translation Models",
    description="Returns a list of all available translation models.",
)
def list_translation_models():
    return {"response": server.available_translation_models_list()}


@router.get(
    "/comparison",
    response_model=ListResponse,
    summary="List Comparison Models",
    description="Returns a list of all available comparison models.",
)
def list_comparison_models():
    return {"response": server.available_comparison_models_list()}


@router.get(
    "/comparison/selected",
    response_model=ListResponse,
    summary="Get Selected Comparison Model",
    description="Returns the currently selected comparison model.",
)
def get_selected_comparison_model():
    return {"response": [server.selected_comparison_model]}


@router.get(
    "/translation/selected",
    response_model=ListResponse,
    summary="Get Selected Translation Model",
    description="Returns the currently selected translation model.",
)
def get_selected_translation_model():
    return {"response": [server.selected_translation_model]}
