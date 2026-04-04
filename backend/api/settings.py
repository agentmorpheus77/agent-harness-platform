from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from backend.core.deps import get_current_user, get_session
from backend.core.encryption import decrypt_value, encrypt_value
from backend.models.database import Setting, User

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingItem(BaseModel):
    key: str
    value: str


class SettingsResponse(BaseModel):
    settings: Dict[str, str]


@router.get("", response_model=SettingsResponse)
def get_settings(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items = session.exec(select(Setting).where(Setting.user_id == user.id)).all()
    result = {}
    for item in items:
        try:
            result[item.key] = decrypt_value(item.value_encrypted)
        except Exception:
            result[item.key] = "***decryption_error***"
    return SettingsResponse(settings=result)


@router.put("", response_model=SettingsResponse)
def update_settings(
    body: List[SettingItem],
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    for item in body:
        existing = session.exec(
            select(Setting).where(Setting.user_id == user.id, Setting.key == item.key)
        ).first()
        if existing:
            existing.value_encrypted = encrypt_value(item.value)
            session.add(existing)
        else:
            setting = Setting(
                user_id=user.id,
                key=item.key,
                value_encrypted=encrypt_value(item.value),
            )
            session.add(setting)
    session.commit()

    # Return all settings
    items = session.exec(select(Setting).where(Setting.user_id == user.id)).all()
    result = {item.key: decrypt_value(item.value_encrypted) for item in items}
    return SettingsResponse(settings=result)
