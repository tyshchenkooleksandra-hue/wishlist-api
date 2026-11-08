from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    wishlists = relationship("WishList", back_populates="owner")
    item_statuses = relationship("WishItemStatus", back_populates="user")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class WishList(Base):
    __tablename__ = "wishlists"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="wishlists")
    items = relationship("WishItem", back_populates="wishlist", cascade="all, delete-orphan")

    @property
    def owner_name(self):
        return self.owner.full_name if self.owner else None

    @property
    def items_count(self):
        return len(self.items) if self.items else 0

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "owner_name": self.owner.full_name if self.owner else None,
            "items_count": len(self.items) if self.items else 0
        }


class WishItem(Base):
    __tablename__ = "wish_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    priority = Column(Integer, default=1)
    wishlist_id = Column(Integer, ForeignKey("wishlists.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    wishlist = relationship("WishList", back_populates="items")
    statuses = relationship("WishItemStatus", back_populates="item", cascade="all, delete-orphan")

    def to_dict(self):
        is_marked = False
        marked_by = None
        marked_at = None

        if self.statuses:
            latest_status = max(self.statuses, key=lambda x: x.created_at)
            is_marked = latest_status.marked
            if is_marked:
                marked_by = latest_status.user.full_name if latest_status.user else None
                marked_at = latest_status.created_at.isoformat() if latest_status.created_at else None

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "wishlist_id": self.wishlist_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_marked": is_marked,
            "marked_by": marked_by,
            "marked_at": marked_at
        }


class WishItemStatus(Base):
    __tablename__ = "wish_item_statuses"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("wish_items.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    marked = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    item = relationship("WishItem", back_populates="statuses")
    user = relationship("User", back_populates="item_statuses")

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "user_id": self.user_id,
            "marked": self.marked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_name": self.user.full_name if self.user else None
        }
