from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings as env_settings
from ..deps import get_db
from ..models import AppSettings
from ..schemas import AppSettingsIn, AppSettingsOut


router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create(db: Session) -> AppSettings:
    row = db.query(AppSettings).first()
    if not row:
        row = AppSettings(
            send_window_start=env_settings.bot_window_start,
            send_window_end=env_settings.bot_window_end,
            worker_tick_seconds=env_settings.worker_tick_seconds,
            typing_delay_seconds=3,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=AppSettingsOut)
def get_settings(db: Session = Depends(get_db)):
    return _get_or_create(db)


@router.put("", response_model=AppSettingsOut)
def update_settings(payload: AppSettingsIn, db: Session = Depends(get_db)):
    if payload.send_window_end <= payload.send_window_start:
        raise HTTPException(400, "send_window_end deve ser maior que send_window_start")
    days = sorted({d for d in payload.send_days.split(",") if d.strip().isdigit()})
    if not days:
        raise HTTPException(400, "selecione pelo menos um dia da semana")
    row = _get_or_create(db)
    row.send_window_start = payload.send_window_start
    row.send_window_end = payload.send_window_end
    row.worker_tick_seconds = payload.worker_tick_seconds
    row.typing_delay_seconds = payload.typing_delay_seconds
    row.send_days = ",".join(days)
    db.commit()
    db.refresh(row)
    return row
