from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Campaign, Contact
from ..schemas import ContactIn, ContactOut, ImportResult
from ..services.phone import to_e164


router = APIRouter(prefix="/campaigns/{campaign_id}/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def list_contacts(campaign_id: int, db: Session = Depends(get_db)):
    if not db.get(Campaign, campaign_id):
        raise HTTPException(404, "campaign not found")
    return db.query(Contact).filter(Contact.campaign_id == campaign_id).order_by(Contact.name).all()


@router.post("", response_model=ContactOut, status_code=201)
def create_contact(campaign_id: int, payload: ContactIn, db: Session = Depends(get_db)):
    if not db.get(Campaign, campaign_id):
        raise HTTPException(404, "campaign not found")
    e164 = to_e164(payload.phone)
    if not e164:
        raise HTTPException(400, "invalid phone")
    if db.query(Contact).filter_by(campaign_id=campaign_id, e164_phone=e164).first():
        raise HTTPException(409, "contact already exists in this campaign")
    c = Contact(campaign_id=campaign_id, e164_phone=e164, **payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{contact_id}", status_code=204)
def delete_contact(campaign_id: int, contact_id: int, db: Session = Depends(get_db)):
    c = db.get(Contact, contact_id)
    if not c or c.campaign_id != campaign_id:
        raise HTTPException(404)
    db.delete(c)
    db.commit()


@router.post("/import", response_model=ImportResult)
async def import_xlsx(
    campaign_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not db.get(Campaign, campaign_id):
        raise HTTPException(404, "campaign not found")

    content = await file.read()
    try:
        wb = load_workbook(BytesIO(content), data_only=True)
    except Exception as e:
        raise HTTPException(400, f"invalid xlsx: {e}")

    ws = wb.active
    imported = skipped = invalid = 0

    existing = set(
        r[0] for r in db.execute(
            Contact.__table__.select()
            .with_only_columns(Contact.e164_phone)
            .where(Contact.campaign_id == campaign_id)
        ).all()
    )

    for row in ws.iter_rows(min_row=2, values_only=True):
        name = row[0] if len(row) > 0 else None
        phone = row[1] if len(row) > 1 else None
        address = row[2] if len(row) > 2 else None
        rating = row[3] if len(row) > 3 else None
        website = row[4] if len(row) > 4 else None

        if not name or not phone or str(phone) == "N/A":
            invalid += 1
            continue
        e164 = to_e164(str(phone))
        if not e164:
            invalid += 1
            continue
        if e164 in existing:
            skipped += 1
            continue

        db.add(Contact(
            campaign_id=campaign_id,
            name=str(name),
            phone=str(phone),
            e164_phone=e164,
            address=str(address) if address else None,
            rating=str(rating) if rating else None,
            website=str(website) if website else None,
            source="xlsx",
        ))
        existing.add(e164)
        imported += 1

    db.commit()
    return ImportResult(imported=imported, skipped=skipped, invalid=invalid)
