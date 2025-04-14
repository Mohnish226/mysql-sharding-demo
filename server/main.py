import logging
from contextlib import asynccontextmanager

import uvicorn
from database import db
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from schemas import UserCreate, UserResponse
from services import UserService
from sharding import get_shard_number
from sqlalchemy.ext.asyncio import AsyncSession


# Define a log filter to add shard_info
class ShardInfoFilter(logging.Filter):
    def filter(self, record):
        # Ensure shard_info exists for ALL log records
        if not hasattr(record, "shard_info"):
            record.shard_info = "SYSTEM"
        return True


# Make sure to configure logging before importing any other modules
# that might create their own loggers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(shard_info)s] - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Add the filter to the root logger
root_logger = logging.getLogger()
root_logger.addFilter(ShardInfoFilter())

# Set SQLAlchemy loggers to WARNING level to reduce verbosity
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


# Define lifespan context manager to replace on_event
@asynccontextmanager
async def lifespan(app: FastAPI):

    # Startup logic
    await db.create_tables()
    logging.info("Database tables initialized")

    yield  # Yield control to the application

    # Shutdown logic
    logging.info("Shutting down application")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Sharded User Service",
    description="Automatically sharded user database service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
# This is a placeholder for CORS settings. Adjust as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db_session(
    request: Request = None, username_path: str = None
) -> AsyncSession:
    """Dependency that automatically determines the correct shard"""

    # First try to get username from path parameter
    if username_path:
        shard_key = username_path
    else:
        # For POST requests, extract username from JSON body
        try:
            body = await request.json()
            shard_key = body.get("username")
        except:
            shard_key = None

    if not shard_key:
        raise HTTPException(status_code=400, detail="Username is required for sharding")

    return await db.get_shard(shard_key)


@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user: UserCreate, request: Request, session: AsyncSession = Depends(get_db_session)
):
    """Create a new user with automatic sharding."""

    try:
        result = await UserService.create_user(session, user)
        # Use extra parameter to include shard_key in log record
        logging.info(
            f"Created user {user.username} on shard {result.shard}",
            extra={"shard_info": result.shard},
        )
        await session.commit()  # Explicitly commit the transaction
        return result
    except Exception as e:
        await session.rollback()  # Rollback on error
        logging.error(
            f"Error creating user {user.username}: {str(e)}",
            extra={"shard_info": "ERROR"},
        )
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await session.close()  # Ensure session is closed


@app.get("/users/{username_path}", response_model=UserResponse)
async def get_user(username_path: str, session: AsyncSession = Depends(get_db_session)):
    """Get user details by username with automatic shard routing."""

    try:
        user = await UserService.get_user(session, username_path)
        if not user:
            # Calculate expected shard for logging purposes
            expected_shard = get_shard_number(username_path)
            logging.warning(
                f"User not found: {username_path} (expected shard: {expected_shard})",
                extra={"shard_info": str(expected_shard)},
            )
            raise HTTPException(status_code=404, detail="User not found")
        logging.info(
            f"Retrieved user {username_path} from shard {user.shard}",
            extra={"shard_info": user.shard},
        )
        return user
    finally:
        await session.close()  # Ensure session is closed


@app.get("/health")
async def health_check():
    """Service health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
