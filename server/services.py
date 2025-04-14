import logging

from models import User
from schemas import UserCreate, UserResponse
from sharding import get_shard_number
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)


class UserService:

    @staticmethod
    async def create_user(session: AsyncSession, user_data: UserCreate) -> UserResponse:

        # Determine shard
        shard = get_shard_number(user_data.username)
        shard_key = str(shard)

        logger.info(
            f"Creating user '{user_data.username}' with shard key {shard_key}",
            extra={"shard_info": str(shard_key)},
        )

        # Check if user already exists
        result = await session.execute(
            select(User).where(User.username == user_data.username)
        )
        existing = result.scalars().first()
        if existing:
            logger.warning(
                f"User '{user_data.username}' already exists on SHARD {existing.shard_key}"
            )
            raise ValueError(f"User with username {user_data.username} already exists")

        # Create new user
        user = User(
            username=user_data.username, email=user_data.email, shard_key=shard_key
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Return response model
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            shard=shard_key,
        )

    @staticmethod
    async def get_user(session: AsyncSession, username: str) -> UserResponse:

        # Calculate expected shard for informational purposes (though actual retrieval is done by querying)
        expected_shard = get_shard_number(username)
        logger.info(
            f"Attempting to retrieve user '{username}' (expected SHARD: {expected_shard})",
            extra={"shard_info": str(expected_shard)},
        )

        result = await session.execute(select(User).where(User.username == username))
        user = result.scalars().first()

        if not user:
            logger.warning(
                f"User '{username}' not found in database, expected SHARD {expected_shard}",
                extra={"shard_info": str(expected_shard)},
            )
            return None

        logger.info(
            f"Retrieved user '{username}' with ID {user.id} from SHARD {user.shard_key}",
            extra={"shard_info": user.shard_key},
        )

        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            shard=user.shard_key,
        )
