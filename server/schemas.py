from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    shard_key: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    shard: str
