"""Transcription API using whisper CLI."""

from __future__ import annotations

import os
import subprocess
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from backend.core.deps import get_current_user
from backend.models.database import User

router = APIRouter(prefix="/api", tags=["transcribe"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav"}


class TranscribeResponse(BaseModel):
    text: str


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    # Validate mime type
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {file.content_type}")

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    tmp_audio = None
    tmp_wav = None
    try:
        # Write uploaded file to temp
        suffix = _get_suffix(file.content_type or "audio/webm")
        tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_audio.write(data)
        tmp_audio.close()

        # Convert to wav using ffmpeg
        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_wav.close()

        ffmpeg_result = subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_audio.name, "-ar", "16000", "-ac", "1", tmp_wav.name],
            capture_output=True,
            timeout=30,
        )
        if ffmpeg_result.returncode != 0:
            raise HTTPException(status_code=500, detail="Audio conversion failed")

        # Run whisper CLI
        whisper_result = subprocess.run(
            ["whisper", tmp_wav.name, "--model", "base", "--output_format", "txt", "--output_dir", tempfile.gettempdir()],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if whisper_result.returncode != 0:
            raise HTTPException(status_code=500, detail="Transcription failed")

        # Read transcription output
        txt_path = tmp_wav.name.replace(".wav", ".txt")
        if os.path.exists(txt_path):
            with open(txt_path) as f:
                text = f.read().strip()
            os.unlink(txt_path)
        else:
            # Fallback: parse stdout
            text = whisper_result.stdout.strip()

        return TranscribeResponse(text=text)

    finally:
        # Cleanup temp files
        if tmp_audio and os.path.exists(tmp_audio.name):
            os.unlink(tmp_audio.name)
        if tmp_wav and os.path.exists(tmp_wav.name):
            os.unlink(tmp_wav.name)


def _get_suffix(content_type: str) -> str:
    mapping = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".m4a",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
    }
    return mapping.get(content_type, ".webm")
