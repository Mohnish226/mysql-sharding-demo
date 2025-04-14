from database import Base
from sqlalchemy import Column, Index, Integer, String


class User(Base):
    """User model for the application.
    This model represents a user in the application and includes
    attributes such as username, email, and shard key.
    The shard key is used for sharding the database.
    The model is mapped to the 'users' table in the database.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    shard_key = Column(String(50), nullable=False, index=True)

    __table_args__ = (Index("idx_user_shard_key", "shard_key"),)
