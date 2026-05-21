from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from orchestrator_api.modules.indexing.extract import extract_text_from_bytes
from orchestrator_api.modules.knowledge.normalize import normalize_to_markdown
from orchestrator_api.schemas.knowledge_documents import NormalizeRequest, NormalizeResponse

router = APIRouter()


@router.post("/normalize", response_model=NormalizeResponse)
async def normalize_content(payload: NormalizeRequest) -> NormalizeResponse:
    try:
        markdown, model = await normalize_to_markdown(raw_text=payload.content, title=payload.title)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return NormalizeResponse(markdown=markdown, model=model, char_count=len(markdown))


@router.post("/normalize-file", response_model=NormalizeResponse)
async def normalize_file(
    file: UploadFile = File(...),
    title: str | None = None,
) -> NormalizeResponse:
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file.")
    filename = file.filename or "document.txt"
    try:
        text, _suffix = extract_text_from_bytes(filename=filename, data=raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    doc_title = (title or "").strip() or filename
    try:
        markdown, model = await normalize_to_markdown(raw_text=text, title=doc_title)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return NormalizeResponse(markdown=markdown, model=model, char_count=len(markdown))
