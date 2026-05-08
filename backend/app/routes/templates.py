from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import RecipientType, Template
from ..schemas import TemplateIn, TemplateOut


router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
def list_templates(recipient_type_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Template)
    if recipient_type_id is not None:
        q = q.filter(Template.recipient_type_id == recipient_type_id)
    return q.order_by(Template.name).all()


@router.post("", response_model=TemplateOut, status_code=201)
def create_template(payload: TemplateIn, db: Session = Depends(get_db)):
    if not db.get(RecipientType, payload.recipient_type_id):
        raise HTTPException(400, "recipient_type_id not found")
    tpl = Template(**payload.model_dump())
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(template_id: int, payload: TemplateIn, db: Session = Depends(get_db)):
    tpl = db.get(Template, template_id)
    if not tpl:
        raise HTTPException(404)
    for k, v in payload.model_dump().items():
        setattr(tpl, k, v)
    db.commit()
    db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.get(Template, template_id)
    if not tpl:
        raise HTTPException(404)
    db.delete(tpl)
    db.commit()
