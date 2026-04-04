"""Tests for the transcription endpoint."""

from unittest.mock import patch, MagicMock
import io

import pytest


def test_transcribe_no_auth(client):
    resp = client.post("/api/transcribe")
    assert resp.status_code == 401


def test_transcribe_invalid_mime_type(client, auth_headers):
    files = {"file": ("test.txt", io.BytesIO(b"not audio"), "text/plain")}
    resp = client.post("/api/transcribe", files=files, headers=auth_headers)
    assert resp.status_code == 400
    assert "Unsupported audio format" in resp.json()["detail"]


def test_transcribe_file_too_large(client, auth_headers):
    # Create a file larger than 10MB
    large_data = b"x" * (10 * 1024 * 1024 + 1)
    files = {"file": ("recording.webm", io.BytesIO(large_data), "audio/webm")}
    resp = client.post("/api/transcribe", files=files, headers=auth_headers)
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"]


@patch("backend.api.transcribe.subprocess.run")
def test_transcribe_success(mock_run, client, auth_headers, tmp_path):
    # Mock ffmpeg success
    ffmpeg_result = MagicMock()
    ffmpeg_result.returncode = 0

    # Mock whisper success
    whisper_result = MagicMock()
    whisper_result.returncode = 0
    whisper_result.stdout = "Hello, this is a test transcription."

    mock_run.side_effect = [ffmpeg_result, whisper_result]

    audio_data = b"\x00" * 1024  # Minimal fake audio
    files = {"file": ("recording.webm", io.BytesIO(audio_data), "audio/webm")}

    with patch("backend.api.transcribe.os.path.exists", return_value=False):
        resp = client.post("/api/transcribe", files=files, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["text"] == "Hello, this is a test transcription."


@patch("backend.api.transcribe.subprocess.run")
def test_transcribe_ffmpeg_failure(mock_run, client, auth_headers):
    ffmpeg_result = MagicMock()
    ffmpeg_result.returncode = 1
    mock_run.return_value = ffmpeg_result

    audio_data = b"\x00" * 1024
    files = {"file": ("recording.webm", io.BytesIO(audio_data), "audio/webm")}
    resp = client.post("/api/transcribe", files=files, headers=auth_headers)

    assert resp.status_code == 500
    assert "conversion failed" in resp.json()["detail"]


@patch("backend.api.transcribe.subprocess.run")
def test_transcribe_whisper_failure(mock_run, client, auth_headers):
    ffmpeg_result = MagicMock()
    ffmpeg_result.returncode = 0

    whisper_result = MagicMock()
    whisper_result.returncode = 1

    mock_run.side_effect = [ffmpeg_result, whisper_result]

    audio_data = b"\x00" * 1024
    files = {"file": ("recording.webm", io.BytesIO(audio_data), "audio/webm")}
    resp = client.post("/api/transcribe", files=files, headers=auth_headers)

    assert resp.status_code == 500
    assert "Transcription failed" in resp.json()["detail"]
