"""
Translation preview endpoint.
Translates text from English into the selected language and returns the result
for user confirmation — translation is NEVER saved without explicit user action.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_user
from app.models import User
from app.schemas import TranslateRequest, TranslateResponse
from app.services.translate_service import translate_text, SUPPORTED_LANGUAGES

router = APIRouter(prefix="/translate", tags=["Translation"])


@router.get("/languages")
def list_languages(_: User = Depends(get_current_user)):
    """Return all supported target languages as {code: name} pairs."""
    return SUPPORTED_LANGUAGES


@router.post("", response_model=TranslateResponse)
def translate_preview(
    payload: TranslateRequest,
    _: User = Depends(get_current_user),
):
    """Translate *text* to *target_lang* and return the preview.

    The caller must explicitly save the result to the reminder — this endpoint
    only produces a translation for user review.
    """
    try:
        translated = translate_text(payload.text, payload.target_lang)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return TranslateResponse(
        original_text=payload.text,
        translated_text=translated,
        target_lang=payload.target_lang,
        language_name=SUPPORTED_LANGUAGES[payload.target_lang],
    )
