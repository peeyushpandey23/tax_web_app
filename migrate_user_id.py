#!/usr/bin/env python3
"""
Manual migration script to add user_id column to UserFinancials table
Run this script to ensure the user_id column exists in your database
"""

import asyncio
import asyncpg
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """Run the user_id column migration"""
    try:
        # Build connection string
        connection_string = settings.CONNECTION_STRING
        
        if not connection_string:
            logger.error("CONNECTION_STRING not found in environment variables")
            return False
        
        logger.info("Connecting to database...")
        
        # Connect to database
        conn = await asyncpg.connect(connection_string)
        
        try:
            # Check if user_id column exists
            check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'UserFinancials' 
            AND column_name = 'user_id'
            """
            
            result = await conn.fetchrow(check_query)
            
            if result:
                logger.info("user_id column already exists")
                return True
            
            # Add user_id column
            logger.info("Adding user_id column...")
            alter_query = """
            ALTER TABLE "UserFinancials" ADD COLUMN user_id VARCHAR(36);
            """
            await conn.execute(alter_query)
            
            # Create index
            logger.info("Creating index on user_id...")
            index_query = """
            CREATE INDEX IF NOT EXISTS idx_userfinancials_user_id ON "UserFinancials"(user_id);
            """
            await conn.execute(index_query)
            
            logger.info("Migration completed successfully!")
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
