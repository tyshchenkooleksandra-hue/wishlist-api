import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List

import redis
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import authenticate_user, create_access_token, get_current_user
from crud import (
    add_wish_item,
    create_user,
    create_wishlist,
    get_item_statuses,
    get_user_by_email,
    get_wish_items,
    get_wishlist_by_id,
    get_wishlists,
    mark_item_status,
)
from database import engine, get_db
from models import Base, User, WishItem, WishList
from schemas import (
    Token,
    UserCreate,
    UserResponse,
    WishItemCreate,
    WishItemResponse,
    WishItemStatusResponse,
    WishListCreate,
    WishListResponse,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Таблиці створюються під час запуску застосунку, а не під час імпорту модуля:
    # інакше будь-який імпорт main, навіть для тесту без бази, вимагав би живого Postgres.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Wish List API", version="1.0.0", lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


load_dotenv(override=False)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")

origins = [origin.strip() for origin in ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
# ssl_cert_reqs="none" - Disable SSL certificate verification for Upstash.
# Параметр існує лише для TLS-з'єднання (rediss://): зі звичайним redis:// він дає TypeError.
redis_options = {"ssl_cert_reqs": "none"} if REDIS_URL.startswith("rediss://") else {}
redis_client = redis.from_url(REDIS_URL, decode_responses=True, **redis_options)



# redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# docker run -d \
#   --name redis \
#   -p 6379:6379 \
#   redis:7-alpine

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    return create_user(db=db, user=user)


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/wishlists", response_model=WishListResponse)
async def create_new_wishlist(
        wishlist: WishListCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    new_wishlist = create_wishlist(db=db, wishlist=wishlist, user_id=current_user.id)

    redis_client.delete("all_wishlists")
    redis_client.delete(f"user_{current_user.id}_wishlists")

    return new_wishlist


@app.get("/wishlists", response_model=List[WishListResponse])
async def get_all_wishlists(db: Session = Depends(get_db)):
    cached_wishlists = redis_client.get("all_wishlists")
    if cached_wishlists:
        return json.loads(cached_wishlists)

    wishlists = get_wishlists(db)

    redis_client.setex("all_wishlists", 300, json.dumps(
        [wishlist.to_dict() for wishlist in wishlists]
    ))

    return wishlists


@app.get("/my-wishlists", response_model=List[WishListResponse])
async def get_my_wishlists(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    cached = redis_client.get(f"user_{current_user.id}_wishlists")
    if cached:
        return json.loads(cached)
    wishlists = db.query(WishList).filter(WishList.user_id == current_user.id).all()
    redis_client.setex(f"user_{current_user.id}_wishlists", 300,
                       json.dumps([wishlist.to_dict() for wishlist in wishlists]))

    return wishlists


@app.get("/wishlists/{wishlist_id}", response_model=WishListResponse)
async def get_wishlist(wishlist_id: int, db: Session = Depends(get_db)):
    wishlist = get_wishlist_by_id(db, wishlist_id)
    if wishlist is None:
        raise HTTPException(status_code=404, detail="Wishlist not found")
    return wishlist


@app.post("/wishlists/{wishlist_id}/items", response_model=WishItemResponse)
async def add_item_to_wishlist(
        wishlist_id: int,
        item: WishItemCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    wishlist = get_wishlist_by_id(db, wishlist_id)
    if wishlist is None:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    if wishlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    new_item = add_wish_item(db=db, item=item, wishlist_id=wishlist_id)

    redis_client.delete(f"wishlist_items_{wishlist_id}")
    redis_client.delete("all_wishlists")

    return new_item


@app.delete("/wishlists/{wishlist_id}/items/{item_id}", response_model=WishItemResponse)
async def delete_item_from_wishlist(
        wishlist_id: int,
        item_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    wishlist = db.query(WishList).filter(WishList.id == wishlist_id).first()
    if wishlist is None:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    if wishlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    item = db.query(WishItem).filter(
        WishItem.id == item_id,
        WishItem.wishlist_id == wishlist_id
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()

    redis_client.delete(f"wishlist_items_{wishlist_id}")
    redis_client.delete("all_wishlists")

    return item


@app.get("/wishlists/{wishlist_id}/items", response_model=List[WishItemResponse])
async def get_wishlist_items(wishlist_id: int, db: Session = Depends(get_db)):
    cached_items = redis_client.get(f"wishlist_items_{wishlist_id}")
    if cached_items:
        return json.loads(cached_items)

    items = get_wish_items(db, wishlist_id)

    redis_client.setex(f"wishlist_items_{wishlist_id}", 180, json.dumps(
        [item.to_dict() for item in items]
    ))

    return items


@app.post("/wishlists/{wishlist_id}/items/{item_id}/mark")
async def mark_item(
        wishlist_id: int,
        item_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    wishlist = get_wishlist_by_id(db, wishlist_id)
    if wishlist is None:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    items = get_wish_items(db, wishlist_id)
    item_exists = any(item.id == item_id for item in items)
    if not item_exists:
        raise HTTPException(status_code=404, detail="Item not found")

    status_record = mark_item_status(
        db=db,
        item_id=item_id,
        user_id=current_user.id
    )

    redis_client.delete(f"wishlist_items_{wishlist_id}")
    redis_client.delete(f"item_statuses_{item_id}")

    return {"message": "Item status updated", "marked": status_record.marked}


@app.get("/wishlists/{wishlist_id}/items/{item_id}/statuses", response_model=List[WishItemStatusResponse])
async def get_item_status_history(
        wishlist_id: int,
        item_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    wishlist = get_wishlist_by_id(db, wishlist_id)
    if wishlist is None:
        raise HTTPException(status_code=404, detail="Wishlist not found")

    if wishlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    cached_statuses = redis_client.get(f"item_statuses_{item_id}")
    if cached_statuses:
        return json.loads(cached_statuses)

    statuses = get_item_statuses(db, item_id)
    serialized_statuses = [status.to_dict() for status in statuses]

    redis_client.setex(f"item_statuses_{item_id}", 120, json.dumps(serialized_statuses))

    return serialized_statuses



@app.get("/health")
async def health_check():
    try:
        redis_client.ping()
        redis_status = "healthy"
    except redis.RedisError:
        redis_status = "unhealthy"

    return {
        "status": "healthy",
        "redis": redis_status,
        "timestamp": datetime.utcnow()
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
