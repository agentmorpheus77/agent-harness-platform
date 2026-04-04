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
from backend.core.skills_manager import get_relevant_skills, load_skill_content
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
4. Present the draft and ask if it looks good. Do NOT tell the user to copy/paste — the UI will automatically show a submit button when the draft is ready, and the user can submit it directly to GitHub with one click.

When presenting the draft, always use this format:
# Draft GitHub Issue
**Title**: <issue title here>

<issue body in markdown>

If the feature involves UI changes, include "[UI]" at the start of your response when presenting the draft.

Keep responses concise and focused. Use English for the issue draft regardless of conversation language."""


class ChatStartRequest(BaseModel):
    repo_id: int


class ChatStartResponse(BaseModel):
    session_id: str
    message: str
    loaded_skills: list[str] = []


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

    # Load relevant skills for this repo
    relevant_skill_names = get_relevant_skills(None, repo.github_full_name)
    loaded_skills: list[str] = []
    skills_context = ""
    for skill_name in relevant_skill_names[:3]:  # Top 3 skills
        content = load_skill_content(skill_name)
        if content:
            loaded_skills.append(skill_name)
            skills_context += f"\n\n--- Skill: {skill_name} ---\n{content}"

    system_msg = SYSTEM_PROMPT_TEMPLATE.format(
        repo_name=repo.github_full_name,
        repo_context=repo_context,
    )
    if skills_context:
        system_msg += f"\n\nLoaded Skills:{skills_context}"

    opening = f"I looked at **{repo.github_full_name}**. What should I build or fix?"

    _chat_sessions[session_id] = {
        "repo_id": req.repo_id,
        "repo_name": repo.github_full_name,
        "user_id": user.id,
        "loaded_skills": loaded_skills,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "assistant", "content": opening},
        ],
    }

    return ChatStartResponse(session_id=session_id, message=opening, loaded_skills=loaded_skills)


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

    assistant_msg = choices[0].get("message", {}).get("content") or ""
    if not assistant_msg.strip():
        # Some free models return null/empty content — surface it clearly
        raise HTTPException(
            status_code=502,
            detail="LLM returned empty content. The model may be overloaded — try again.",
        )
    chat["messages"].append({"role": "assistant", "content": assistant_msg})

    # Detect if this is a draft (contains title-like pattern and body)
    is_draft = False
    draft_title = None
    draft_body = None
    is_ui_feature = False

    lines = assistant_msg.split("\n")
    draft_header_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect "# Draft GitHub Issue" header
        if stripped.lower().startswith("# draft github issue"):
            is_draft = True
            draft_header_idx = i
            continue
        # Detect title patterns: **Title:** / **Title**: / Title: / ## Title: / # Title:
        if stripped.startswith("**Title") and ":" in stripped:
            is_draft = True
            # Extract after the colon, strip markdown bold markers
            draft_title = stripped.split(":", 1)[-1].strip().strip("*").strip()
            break
        if stripped.startswith("## Title") or stripped.startswith("# Title"):
            is_draft = True
            if ":" in stripped:
                draft_title = stripped.split(":", 1)[-1].strip().strip("*").strip()
            break
        if stripped.startswith("Title:"):
            is_draft = True
            draft_title = stripped.split(":", 1)[-1].strip().strip("*").strip()
            break

    # If we found "# Draft GitHub Issue" but no title yet, look at following lines
    if is_draft and not draft_title and draft_header_idx is not None:
        for line in lines[draft_header_idx + 1 :]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("**Title") and ":" in stripped:
                draft_title = stripped.split(":", 1)[-1].strip().strip("*").strip()
                break
            # First non-empty line after header could be the title
            if stripped.startswith("#"):
                draft_title = stripped.lstrip("#").strip()
                break

    if is_draft:
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
