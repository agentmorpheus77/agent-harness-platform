"""Chat API for issue creation conversations."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.core.encryption import decrypt_value
from backend.core.llm_client import chat_completion, get_default_model
from backend.models.database import Repo, Setting, User, Workspace

router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory chat sessions (MVP; upgrade to Redis later)
_chat_sessions: dict[str, dict] = {}

SYSTEM_PROMPT_TEMPLATE = """You are an AI assistant helping create a GitHub issue for the repository "{repo_name}".

Repository context:
{repo_context}

Your job:
1. Ask the user what they want to build or fix (if they haven't said yet).
2. Ask up to 3 follow-up questions to clarify requirements (type, scope, acceptance criteria).
3. Once you have enough info, generate a well-structured issue draft with:
   - A clear, concise title (in English)
   - A detailed body in markdown (in English) with sections: Description, Acceptance Criteria, Technical Notes
4. Present the draft and ask if it looks good.

If the feature involves UI changes, include "[UI]" at the start of your response when presenting the draft.

Keep responses concise and focused. Use English for the issue draft regardless of conversation language."""


class ChatStartRequest(BaseModel):
    repo_id: int


class ChatStartResponse(BaseModel):
    session_id: str
    message: str


class ChatMessageRequest(BaseModel):
    message: str
    is_transcription: bool = False


class ChatMessageResponse(BaseModel):
    message: str
    is_draft: bool = False
    draft_title: Optional[str] = None
    draft_body: Optional[str] = None
    is_ui_feature: bool = False


@router.post("/start", response_model=ChatStartResponse)
def start_chat(
    req: ChatStartRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Verify repo belongs to user
    workspaces = session.exec(select(Workspace).where(Workspace.owner_id == user.id)).all()
    workspace_ids = [w.id for w in workspaces]
    repo = session.exec(
        select(Repo).where(Repo.id == req.repo_id, Repo.workspace_id.in_(workspace_ids))
    ).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Build repo context
    repo_context = f"Repository: {repo.github_full_name}\nDeploy provider: {repo.deploy_provider}"

    session_id = str(uuid.uuid4())
    system_msg = SYSTEM_PROMPT_TEMPLATE.format(
        repo_name=repo.github_full_name,
        repo_context=repo_context,
    )

    opening = f"I looked at **{repo.github_full_name}**. What should I build or fix?"

    _chat_sessions[session_id] = {
        "repo_id": req.repo_id,
        "repo_name": repo.github_full_name,
        "user_id": user.id,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "assistant", "content": opening},
        ],
    }

    return ChatStartResponse(session_id=session_id, message=opening)


@router.post("/{session_id}/message", response_model=ChatMessageResponse)
async def send_message(
    session_id: str,
    req: ChatMessageRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    chat = _chat_sessions.get(session_id)
    if not chat or chat["user_id"] != user.id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Get OpenRouter API key
    setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "openrouter_api_key")
    ).first()
    if not setting:
        raise HTTPException(status_code=400, detail="OpenRouter API key not configured")

    api_key = decrypt_value(setting.value_encrypted)

    # Add user message
    chat["messages"].append({"role": "user", "content": req.message})

    # Call LLM
    model = get_default_model("free")
    result = await chat_completion(api_key, model, chat["messages"])

    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    choices = result.get("choices", [])
    if not choices:
        raise HTTPException(status_code=502, detail="No response from LLM")

    assistant_msg = choices[0].get("message", {}).get("content", "")
    chat["messages"].append({"role": "assistant", "content": assistant_msg})

    # Detect if this is a draft (contains title-like pattern and body)
    is_draft = False
    draft_title = None
    draft_body = None
    is_ui_feature = False

    if "**Title:" in assistant_msg or "## Title" in assistant_msg or "# Title" in assistant_msg:
        is_draft = True
        # Try to extract title
        for line in assistant_msg.split("\n"):
            stripped = line.strip()
            if stripped.startswith("**Title:") or stripped.startswith("## Title") or stripped.startswith("# Title"):
                draft_title = stripped.split(":", 1)[-1].strip().strip("*").strip()
                break
            if stripped.startswith("Title:"):
                draft_title = stripped.split(":", 1)[-1].strip().strip("*").strip()
                break
        # Body is the full message as markdown
        draft_body = assistant_msg

    if assistant_msg.startswith("[UI]"):
        is_ui_feature = True
        assistant_msg = assistant_msg[4:].strip()

    return ChatMessageResponse(
        message=assistant_msg,
        is_draft=is_draft,
        draft_title=draft_title,
        draft_body=draft_body,
        is_ui_feature=is_ui_feature,
    )
