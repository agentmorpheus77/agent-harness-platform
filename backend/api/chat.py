"""Chat API for issue creation conversations with phase-aware flow."""

from __future__ import annotations

import uuid
from typing import Optional

import httpx
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

{file_tree_context}

Your job is to have a focused conversation to create a well-structured GitHub issue. Follow these phases:

## Phase 1: Greeting
- Briefly mention what you noticed about the repo (tech stack, structure).
- Ask what the user wants to build or fix.

## Phase 2: Clarification (max 3 follow-up questions)
- Ask about: type (feature/bug/refactor), affected areas, acceptance criteria.
- Be concise — one question at a time is fine.
- If the user gives enough detail, skip to Phase 3.

## Phase 3: Draft
- Present a structured issue draft using this EXACT format:

# Draft GitHub Issue
**Title**: <concise title in English>

## Description
<what and why>

## Acceptance Criteria
- [ ] <criterion 1>
- [ ] <criterion 2>

## Technical Notes
<implementation hints, affected files, etc.>

- Ask if the draft looks good or needs changes.

## Phase 4: Confirm
- When the user says "OK", "looks good", "passt", "submit", etc. → respond with:
  "Great, submitting now!" (the UI handles the actual submission)

## Rules:
- Always use English for the issue draft regardless of conversation language.
- If the feature involves UI changes, include "[UI]" at the start of your response when presenting the draft.
- Keep responses concise and focused.
- Do NOT tell the user to copy/paste — the UI automatically shows a submit button when the draft is ready."""


async def _fetch_repo_context(github_full_name: str, github_token: str) -> str:
    """Fetch repo file tree and README via GitHub API for context."""
    context_parts = []

    try:
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Fetch top-level file tree
            tree_resp = await client.get(
                f"https://api.github.com/repos/{github_full_name}/contents/",
                headers=headers,
            )
            if tree_resp.status_code == 200:
                entries = tree_resp.json()
                file_list = [
                    f"{'d' if e['type'] == 'dir' else 'f'} {e['name']}"
                    for e in entries[:50]
                ]
                context_parts.append("File tree (top-level):\n" + "\n".join(file_list))

            # Fetch README
            readme_resp = await client.get(
                f"https://api.github.com/repos/{github_full_name}/readme",
                headers=headers,
            )
            if readme_resp.status_code == 200:
                import base64
                readme_data = readme_resp.json()
                content = base64.b64decode(readme_data.get("content", "")).decode("utf-8", errors="replace")
                # Truncate to first 1500 chars
                if len(content) > 1500:
                    content = content[:1500] + "\n... (truncated)"
                context_parts.append(f"README.md:\n{content}")

    except Exception:
        pass

    return "\n\n".join(context_parts) if context_parts else "No additional repo context available."


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
    phase: str = "chat"  # greeting | clarification | draft | confirm
    is_draft: bool = False
    draft_title: Optional[str] = None
    draft_body: Optional[str] = None
    is_ui_feature: bool = False


@router.post("/start", response_model=ChatStartResponse)
async def start_chat(
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

    # Get GitHub token for repo context
    gh_setting = session.exec(
        select(Setting).where(Setting.user_id == user.id, Setting.key == "github_token")
    ).first()
    github_token = decrypt_value(gh_setting.value_encrypted) if gh_setting else ""

    # Fetch repo context (file tree + README) from GitHub API
    file_tree_context = ""
    if github_token:
        file_tree_context = await _fetch_repo_context(repo.github_full_name, github_token)

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
        file_tree_context=file_tree_context,
    )
    if skills_context:
        system_msg += f"\n\nLoaded Skills:{skills_context}"

    opening = f"I looked at **{repo.github_full_name}**. What should I build or fix?"

    _chat_sessions[session_id] = {
        "repo_id": req.repo_id,
        "repo_name": repo.github_full_name,
        "user_id": user.id,
        "loaded_skills": loaded_skills,
        "phase": "greeting",
        "question_count": 0,
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
        raise HTTPException(
            status_code=502,
            detail="LLM returned empty content. The model may be overloaded — try again.",
        )
    chat["messages"].append({"role": "assistant", "content": assistant_msg})

    # Detect phase and draft
    is_draft = False
    draft_title = None
    draft_body = None
    is_ui_feature = False
    phase = chat.get("phase", "chat")

    lines = assistant_msg.split("\n")
    draft_header_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.lower().startswith("# draft github issue"):
            is_draft = True
            draft_header_idx = i
            continue
        if stripped.startswith("**Title") and ":" in stripped:
            is_draft = True
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

    if is_draft and not draft_title and draft_header_idx is not None:
        for line in lines[draft_header_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("**Title") and ":" in stripped:
                draft_title = stripped.split(":", 1)[-1].strip().strip("*").strip()
                break
            if stripped.startswith("#"):
                draft_title = stripped.lstrip("#").strip()
                break

    if is_draft:
        draft_body = assistant_msg
        phase = "draft"
        chat["phase"] = "draft"
    elif chat["phase"] == "draft":
        # User confirmed or is in confirm phase
        confirm_words = {"ok", "looks good", "passt", "submit", "ja", "yes", "gut", "perfect", "ship it", "go", "lgtm"}
        if any(w in req.message.lower() for w in confirm_words):
            phase = "confirm"
            chat["phase"] = "confirm"
    elif chat["phase"] == "greeting":
        chat["phase"] = "clarification"
        chat["question_count"] = 1
        phase = "clarification"
    elif chat["phase"] == "clarification":
        chat["question_count"] = chat.get("question_count", 0) + 1
        phase = "clarification"

    if assistant_msg.startswith("[UI]"):
        is_ui_feature = True
        assistant_msg = assistant_msg[4:].strip()

    return ChatMessageResponse(
        message=assistant_msg,
        phase=phase,
        is_draft=is_draft,
        draft_title=draft_title,
        draft_body=draft_body,
        is_ui_feature=is_ui_feature,
    )
