from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import RecipientType
from ..schemas import RecipientTypeIn, RecipientTypeOut


router = APIRouter(prefix="/recipient-types", tags=["recipient-types"])


@router.get("", response_model=list[RecipientTypeOut])
def list_types(db: Session = Depends(get_db)):
    return db.query(RecipientType).order_by(RecipientType.name).all()


@router.post("", response_model=RecipientTypeOut, status_code=201)
def create_type(payload: RecipientTypeIn, db: Session = Depends(get_db)):
    if db.query(RecipientType).filter_by(slug=payload.slug).first():
        raise HTTPException(400, "slug already exists")
    rt = RecipientType(**payload.model_dump())
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


@router.delete("/{type_id}", status_code=204)
def delete_type(type_id: int, db: Session = Depends(get_db)):
    rt = db.get(RecipientType, type_id)
    if not rt:
        raise HTTPException(404)
    db.delete(rt)
    db.commit()
