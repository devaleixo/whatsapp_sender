from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import SendQueue
from ..schemas import QueueItemOut


router = APIRouter(prefix="/queue", tags=["queue"])


@router.get("", response_model=list[QueueItemOut])
def list_queue(limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(SendQueue)
        .order_by(SendQueue.priority.desc(), SendQueue.scheduled_for.asc())
        .limit(limit)
        .all()
    )


@router.delete("", status_code=204)
def clear_queue(db: Session = Depends(get_db)):
    db.query(SendQueue).delete()
    db.commit()


@router.delete("/{item_id}", status_code=204)
def remove_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(SendQueue, item_id)
    if item:
        db.delete(item)
        db.commit()
