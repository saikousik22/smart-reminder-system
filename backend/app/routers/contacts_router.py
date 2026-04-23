"""
Contacts CRUD router — saved phone book for quick reminder creation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Contact
from app.auth import get_current_user
from app.schemas import ContactCreate, ContactUpdate, ContactResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("", response_model=list[ContactResponse])
def list_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Contact).filter(Contact.user_id == current_user.id).order_by(Contact.name).all()


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    duplicate = (
        db.query(Contact)
        .filter(Contact.user_id == current_user.id, Contact.phone_number == payload.phone_number)
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A contact with phone number {payload.phone_number} already exists.",
        )
    contact = Contact(user_id=current_user.id, name=payload.name, phone_number=payload.phone_number)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    payload: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_id == current_user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    if payload.phone_number and payload.phone_number != contact.phone_number:
        duplicate = (
            db.query(Contact)
            .filter(
                Contact.user_id == current_user.id,
                Contact.phone_number == payload.phone_number,
                Contact.id != contact_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A contact with phone number {payload.phone_number} already exists.",
            )

    if payload.name is not None:
        contact.name = payload.name
    if payload.phone_number is not None:
        contact.phone_number = payload.phone_number

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", response_model=MessageResponse)
def delete_contact(
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_id == current_user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    name = contact.name
    db.delete(contact)
    db.commit()
    return {"message": f"Contact '{name}' deleted successfully"}
