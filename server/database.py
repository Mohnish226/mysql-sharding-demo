import os

from sharding import get_shard_number
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Database:

    def __init__(self):
        self.shard_engines = {}
        self.shard_sessions = {}
        self.setup_shards()

    def setup_shards(self) -> None:
        """Setup the database shards.
        This method creates the database engines and sessionmakers for
        each shard based on the connection strings provided in the
        environment variables.
        """
        
        # Get connection strings from environment variables
        shard1_url = os.environ.get(
            "SHARD1_URL",
            "mysql+aiomysql://shard_user:shard_password@mysql-shard1:3306/shard_db",
        )
        shard2_url = os.environ.get(
            "SHARD2_URL",
            "mysql+aiomysql://shard_user:shard_password@mysql-shard2:3306/shard_db",
        )

        # Create engines
        self.shard_engines = {
            1: create_async_engine(shard1_url, echo=False),
            2: create_async_engine(shard2_url, echo=False),
        }

        # Create sessionmakers
        self.shard_sessions = {
            1: sessionmaker(
                self.shard_engines[1], expire_on_commit=False, class_=AsyncSession
            ),
            2: sessionmaker(
                self.shard_engines[2], expire_on_commit=False, class_=AsyncSession
            ),
        }

    async def create_tables(self) -> None:
        """Create tables in all shards.
        This method creates all tables defined in the Base metadata
        for all shard engines.
        """

        # Import here to avoid circular imports
        from models import Base

        for engine in self.shard_engines.values():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    async def get_shard(self, shard_key: str) -> AsyncSession:
        """Get the shard session based on the shard key.

        Args:
            shard_key (str): The shard key to determine which shard to use.

        Returns:
            AsyncSession: The session for the appropriate shard.
        """
        shard_id = get_shard_number(shard_key, len(self.shard_engines))
        return self.shard_sessions[shard_id]()


db = Database()
