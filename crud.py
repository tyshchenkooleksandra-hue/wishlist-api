from typing import Optional, Type

from sqlalchemy.orm import Session, joinedload

from auth import get_password_hash
from models import User, WishItem, WishItemStatus, WishList
from schemas import UserCreate, WishItemCreate, WishListCreate


def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_wishlist(db: Session, wishlist: WishListCreate, user_id: int):
    db_wishlist = WishList(
        title=wishlist.title,
        description=wishlist.description,
        user_id=user_id
    )
    db.add(db_wishlist)
    db.commit()
    db.refresh(db_wishlist)
    return db_wishlist


def get_wishlists(db: Session, include_items: bool = False) -> list[Type[WishList]]:
    query = db.query(WishList).options(joinedload(WishList.owner))
    if include_items:
        query = query.options(joinedload(WishList.items))
    return query.all()


def get_wishlist_by_id(db: Session, wishlist_id: int, include_items: bool = True) -> Optional[WishList]:
    query = db.query(WishList).options(joinedload(WishList.owner))
    if include_items:
        query = query.options(joinedload(WishList.items))
    return query.filter(WishList.id == wishlist_id).first()


def add_wish_item(db: Session, item: WishItemCreate, wishlist_id: int):
    db_item = WishItem(
        title=item.title,
        description=item.description,
        priority=item.priority,
        wishlist_id=wishlist_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def get_wish_items(db: Session, wishlist_id: int):
    items = db.query(WishItem).filter(WishItem.wishlist_id == wishlist_id).all()

    for item in items:
        if item.statuses:
            latest_status = max(item.statuses, key=lambda s: s.created_at)
            item.is_marked = latest_status.marked
        else:
            item.is_marked = False

    return items


def mark_item_status(db: Session, item_id: int, user_id: int):
    last_status = db.query(WishItemStatus).filter(
        WishItemStatus.item_id == item_id,
        WishItemStatus.user_id == user_id
    ).order_by(WishItemStatus.created_at.desc()).first()

    new_marked_status = not (last_status.marked if last_status else False)

    db_status = WishItemStatus(
        item_id=item_id,
        user_id=user_id,
        marked=new_marked_status
    )
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status


def get_item_statuses(db: Session, item_id: int):
    return db.query(WishItemStatus).options(
        joinedload(WishItemStatus.user)).filter(
        WishItemStatus.item_id == item_id).order_by(
        WishItemStatus.created_at.desc()).all()
