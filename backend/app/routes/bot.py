from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import BotConfig, RecipientType
from ..schemas import BotConfigIn, BotConfigOut


router = APIRouter(prefix="/bot-configs", tags=["bot"])


@router.get("", response_model=list[BotConfigOut])
def list_configs(db: Session = Depends(get_db)):
    return db.query(BotConfig).all()


@router.get("/by-type/{recipient_type_id}", response_model=BotConfigOut)
def get_by_type(recipient_type_id: int, db: Session = Depends(get_db)):
    cfg = db.query(BotConfig).filter_by(recipient_type_id=recipient_type_id).first()
    if not cfg:
        raise HTTPException(404)
    return cfg


@router.put("/by-type/{recipient_type_id}", response_model=BotConfigOut)
def upsert_by_type(recipient_type_id: int, payload: BotConfigIn, db: Session = Depends(get_db)):
    if payload.recipient_type_id != recipient_type_id:
        raise HTTPException(400, "recipient_type_id mismatch")
    if not db.get(RecipientType, recipient_type_id):
        raise HTTPException(404, "recipient type not found")
    cfg = db.query(BotConfig).filter_by(recipient_type_id=recipient_type_id).first()
    if cfg:
        for k, v in payload.model_dump(exclude={"recipient_type_id"}).items():
            setattr(cfg, k, v)
    else:
        cfg = BotConfig(**payload.model_dump())
        db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg
