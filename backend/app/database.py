"""
Database Connection Module
===========================
Handles MongoDB connection using Motor (async MongoDB driver).

Why Motor?
- Fully async/await compatible with FastAPI
- Non-blocking I/O for better performance
- Built on top of pymongo

Connection Pattern:
- Singleton pattern: One connection for the entire app
- Lazy connection: Connect when first accessed
- Graceful shutdown: Close connection on app shutdown
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """
    MongoDB Database Manager
    
    Singleton pattern ensures only one database connection exists.
    Usage:
        from app.database import database
        db = await database.get_database()
    """
    
    def __init__(self):
        """Initialize database manager (doesn't connect yet)"""
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> bool:
        """
        Connect to MongoDB Atlas
        
        This method is called once during app startup.
        Creates indexes for optimal query performance.
        """
        url = (settings.MONGODB_URL or "").strip()
        if not url or url.lower() in {"disabled", "skip", "none"}:
            logger.info("MongoDB not configured; continuing without a database")
            return False
        try:
            logger.info(f"Connecting to MongoDB at {url[:20]}...")
            
            # Create async MongoDB client
            client = AsyncIOMotorClient(
                url,
                serverSelectionTimeoutMS=5000  # 5 second timeout
            )
            
            # Test connection before publishing the client. A failed ping must
            # leave health as disconnected instead of a half-open client.
            await client.admin.command('ping')
            self.client = client
            self.database = client[settings.DATABASE_NAME]
            logger.info(f"✓ Connected to MongoDB database: {settings.DATABASE_NAME}")
            
            # Create indexes for better performance
            await self._create_indexes()
            return True
            
        except Exception as e:
            self.client = None
            self.database = None
            logger.error(f"✗ Failed to connect to MongoDB: {e}")
            raise
    
    async def _create_indexes(self):
        """
        Create database indexes for optimal query performance
        
        Indexes speed up queries on frequently-searched fields.
        """
        try:
            # Swimmers collection indexes
            await self.database.swimmers.create_index(
                [("camera_id", 1), ("track_id", 1)],
                unique=True  # One swimmer per track_id per camera
            )
            await self.database.swimmers.create_index("status")
            await self.database.swimmers.create_index("last_seen")
            
            # Heatmaps collection indexes
            await self.database.heatmaps.create_index(
                [("camera_id", 1), ("timestamp", -1)]
            )
            # TTL index: Auto-delete old heatmaps after 24 hours
            await self.database.heatmaps.create_index(
                "created_at",
                expireAfterSeconds=settings.HEATMAP_RETENTION_HOURS * 3600
            )
            
            # Alerts collection indexes
            await self.database.alerts.create_index("camera_id")
            await self.database.alerts.create_index("status")
            await self.database.alerts.create_index("severity")
            await self.database.alerts.create_index("timestamp")
            
            # Cameras collection indexes
            await self.database.cameras.create_index("camera_id", unique=True)
            await self.database.cameras.create_index("status")
            
            logger.info("✓ Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    async def disconnect(self):
        """
        Disconnect from MongoDB
        
        This method is called during app shutdown.
        Ensures clean connection closure.
        """
        if self.client:
            logger.info("Disconnecting from MongoDB...")
            self.client.close()
            logger.info("✓ Disconnected from MongoDB")
    
    def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get database instance
        
        Returns the active database connection.
        Raises exception if not connected.
        """
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.database


# Global database instance
# Import this in other modules: from app.database import database
database = Database()


