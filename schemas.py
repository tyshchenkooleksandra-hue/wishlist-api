from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class WishListBase(BaseModel):
    title: str
    description: Optional[str] = None

class WishListCreate(WishListBase):
    pass

class WishListResponse(WishListBase):
    id: int
    user_id: int
    created_at: datetime
    owner_name: Optional[str] = None
    items_count: int = 0

    class Config:
        from_attributes = True

class WishItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 1

class WishItemCreate(WishItemBase):
    pass

class WishItemResponse(WishItemBase):
    id: int
    wishlist_id: int
    created_at: datetime
    is_marked: bool = False
    marked_by: Optional[str] = None
    marked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WishItemStatusResponse(BaseModel):
    id: int
    item_id: int
    user_id: int
    marked: bool
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True
