import asyncio
import asyncpg
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseAdapter:
    """Adapter interface to maintain compatibility with REST-style calls"""
    def __init__(self, db_manager):
        self._db_manager = db_manager
    
    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert record using REST-style interface"""
        result = await self._db_manager.insert_record(table, data)
        return result or {}
    
    async def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Update record using REST-style interface"""
        result = await self._db_manager.update_record(table, data, filters)
        return result or {}
    
    async def fetch_all(self, table: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Fetch all records using REST-style interface"""
        return await self._db_manager.find_by_filters(table, filters)
    
    async def fetch_one(self, table: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch one record using REST-style interface"""
        return await self._db_manager.find_one_by_filters(table, filters)
    
    async def delete(self, table: str, filters: Dict[str, Any]) -> None:
        """Delete records using REST-style interface"""
        await self._db_manager.delete_record(table, filters)

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._connection_string = self._build_connection_string()
        # Create adapter for backward compatibility
        self.adapter = DatabaseAdapter(self)
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string from Supabase credentials"""
        # Use CONNECTION_STRING if available, otherwise build from components
        if settings.CONNECTION_STRING:
            logger.info("Using CONNECTION_STRING from environment")
            # Use the connection string exactly as provided
            conn_str = settings.CONNECTION_STRING
            logger.info("Using connection string as-is from environment")
            
            # Fix common Supabase hostname issues
            if "db.wmycabivhsbbnkowyuex.supabase.co" in conn_str:
                logger.warning("Detected potentially incorrect Supabase hostname, trying alternatives...")
                # Try different hostname patterns that Supabase actually uses
                alternatives = [
                    # Try with pooler endpoints first (more reliable for external connections)
                    conn_str.replace("db.wmycabivhsbbnkowyuex.supabase.co:5432", "wmycabivhsbbnkowyuex.pooler.supabase.com:6543"),
                    # Try different pooler regions
                    conn_str.replace("db.wmycabivhsbbnkowyuex.supabase.co:5432", "aws-0-us-east-1.pooler.supabase.com:6543"),
                    conn_str.replace("db.wmycabivhsbbnkowyuex.supabase.co:5432", "aws-0-us-west-1.pooler.supabase.com:6543"),
                    conn_str.replace("db.wmycabivhsbbnkowyuex.supabase.co:5432", "aws-0-eu-west-1.pooler.supabase.com:6543"),
                    # Try without the 'db.' prefix on port 5432
                    conn_str.replace("db.wmycabivhsbbnkowyuex.supabase.co", "wmycabivhsbbnkowyuex.supabase.co"),
                    # Try direct connection with project ID on port 6543
                    conn_str.replace("db.wmycabivhsbbnkowyuex.supabase.co:5432", "wmycabivhsbbnkowyuex.supabase.co:6543"),
                ]
                
                # Test each alternative with actual connection test
                import socket
                import re
                for alt_conn_str in alternatives:
                    try:
                        # Extract hostname and port to test
                        hostname_match = re.search(r'@([^:]+):(\d+)', alt_conn_str)
                        if hostname_match:
                            hostname = hostname_match.group(1)
                            port = int(hostname_match.group(2))
                            
                            # Test DNS resolution first
                            socket.gethostbyname(hostname)
                            
                            # Test port connectivity
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(5)
                            result = sock.connect_ex((hostname, port))
                            sock.close()
                            
                            if result == 0:
                                logger.info(f"Found working connection: {hostname}:{port}")
                                return alt_conn_str
                            else:
                                logger.debug(f"Port {port} not accessible on {hostname}")
                    except (socket.gaierror, socket.timeout, OSError) as e:
                        logger.debug(f"Connection test failed for {hostname_match.group(1) if hostname_match else 'unknown'}: {e}")
                        continue
                
                logger.warning("No working hostname found, using original connection string")
            
            return conn_str
        
        # Fallback: Build from individual components
        if not settings.DATABASE_URL or not settings.DATABASE_PASSWORD:
            raise ValueError("DATABASE_URL and DATABASE_PASSWORD are required if CONNECTION_STRING is not provided")
        
        # Extract host from DATABASE_URL (handle both web URLs and direct hostnames)
        db_url = settings.DATABASE_URL
        if db_url.startswith("https://") or db_url.startswith("http://"):
            host = db_url.replace("https://", "").replace("http://", "")
        else:
            host = db_url
        
        # Build connection string
        connection_string = (
            f"postgresql://postgres:{settings.DATABASE_PASSWORD}"
            f"@{host}:5432/postgres"
        )
        
        logger.info(f"Database connection string built for host: {host}")
        return connection_string
    
    async def create_pool(self) -> None:
        """Create database connection pool"""
        try:
            logger.info("Creating database connection pool...")
            logger.info(f"Connection string: {self._connection_string[:50]}...")
            
            self.pool = await asyncpg.create_pool(
                self._connection_string,
                min_size=1,
                max_size=10,
                command_timeout=30,
                statement_cache_size=0,  # Disable prepared statements for pgbouncer compatibility
                server_settings={
                    'application_name': 'tax_advisor_app'
                }
            )
            logger.info("Database connection pool created successfully")
        except asyncpg.InvalidAuthorizationSpecificationError as e:
            logger.error(f"Database authentication failed - check credentials: {e}")
            raise
        except asyncpg.CannotConnectNowError as e:
            logger.error(f"Database server not accepting connections: {e}")
            raise
        except asyncpg.ConnectionDoesNotExistError as e:
            logger.error(f"Database connection does not exist - check hostname: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create database pool: {type(e).__name__}: {e}")
            logger.error(f"Connection string used: {self._connection_string[:50]}...")
            raise
    
    async def close_pool(self) -> None:
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.pool:
            await self.create_pool()
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            logger.info("Testing database connection...")
            async with self.get_connection() as conn:
                result = await conn.fetchval("SELECT 1")
                logger.info(f"Database connection test successful - result: {result}")
                return True
        except asyncpg.InvalidAuthorizationSpecificationError as e:
            logger.error(f"Database connection test failed - authentication error: {e}")
            return False
        except asyncpg.CannotConnectNowError as e:
            logger.error(f"Database connection test failed - server not accepting connections: {e}")
            return False
        except asyncpg.ConnectionDoesNotExistError as e:
            logger.error(f"Database connection test failed - connection does not exist: {e}")
            return False
        except Exception as e:
            logger.error(f"Database connection test failed: {type(e).__name__}: {e}")
            return False
    
    async def execute_query(self, query: str, *args) -> Any:
        """Execute a database query"""
        try:
            if not self.pool:
                await self.create_pool()
            
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *args)
                return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch one row from database"""
        try:
            if not self.pool:
                await self.create_pool()
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Fetch one failed: {e}")
            raise
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows from database"""
        try:
            if not self.pool:
                await self.create_pool()
            
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Fetch all failed: {e}")
            raise
    
    async def create_tables(self) -> None:
        """Create all required database tables"""
        try:
            # Create UserFinancials table
            user_financials_table = """
            CREATE TABLE IF NOT EXISTS "UserFinancials" (
                session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id VARCHAR(36),
                gross_salary NUMERIC(15, 2) NOT NULL,
                basic_salary NUMERIC(15, 2) NOT NULL,
                hra_received NUMERIC(15, 2) DEFAULT 0,
                rent_paid NUMERIC(15, 2) DEFAULT 0,
                deduction_80c NUMERIC(15, 2) DEFAULT 0,
                deduction_80d NUMERIC(15, 2) DEFAULT 0,
                standard_deduction NUMERIC(15, 2) DEFAULT 50000,
                professional_tax NUMERIC(15, 2) DEFAULT 0,
                tds NUMERIC(15, 2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'completed',
                draft_expires_at TIMESTAMPTZ,
                is_draft BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
            
            # Create TaxComparison table
            tax_comparison_table = """
            CREATE TABLE IF NOT EXISTS "TaxComparison" (
                session_id UUID PRIMARY KEY REFERENCES "UserFinancials"(session_id) ON DELETE CASCADE,
                tax_old_regime NUMERIC(15, 2) NOT NULL,
                tax_new_regime NUMERIC(15, 2) NOT NULL,
                best_regime VARCHAR(10) NOT NULL CHECK (best_regime IN ('old', 'new')),
                selected_regime VARCHAR(10) CHECK (selected_regime IN ('old', 'new')),
                calculation_details JSONB,
                recommendations JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
            
            # Create indexes
            indexes = """
            CREATE INDEX IF NOT EXISTS idx_userfinancials_created_at ON "UserFinancials"(created_at);
            CREATE INDEX IF NOT EXISTS idx_userfinancials_status ON "UserFinancials"(status);
            CREATE INDEX IF NOT EXISTS idx_userfinancials_draft_expires ON "UserFinancials"(draft_expires_at);
            CREATE INDEX IF NOT EXISTS idx_taxcomparison_session ON "TaxComparison"(session_id);
            CREATE INDEX IF NOT EXISTS idx_taxcomparison_best_regime ON "TaxComparison"(best_regime);
            CREATE INDEX IF NOT EXISTS idx_taxcomparison_created_at ON "TaxComparison"(created_at);
            """
            
            # Create constraint (using DO block to handle IF NOT EXISTS)
            constraint = """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'chk_status' 
                    AND conrelid = '"UserFinancials"'::regclass
                ) THEN
                    ALTER TABLE "UserFinancials" ADD CONSTRAINT chk_status 
                    CHECK (status IN ('draft', 'completed'));
                END IF;
            END $$;
            """
            
            async with self.get_connection() as conn:
                await conn.execute(user_financials_table)
                await conn.execute(tax_comparison_table)
                await conn.execute(indexes)
                await conn.execute(constraint)
            
            # Add user_id column if it doesn't exist (for existing databases)
            await self._migrate_add_user_id_column()
            
            logger.info("UserFinancials and TaxComparison tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    async def _migrate_add_user_id_column(self) -> None:
        """Add user_id column to existing UserFinancials table if it doesn't exist"""
        try:
            migration_query = """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'UserFinancials' 
                    AND column_name = 'user_id'
                ) THEN
                    ALTER TABLE "UserFinancials" ADD COLUMN user_id VARCHAR(36);
                    CREATE INDEX IF NOT EXISTS idx_userfinancials_user_id ON "UserFinancials"(user_id);
                END IF;
            END $$;
            """
            
            async with self.get_connection() as conn:
                await conn.execute(migration_query)
                logger.info("Migration completed: user_id column added if needed")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # Don't raise exception as this is not critical for app startup
    
    # CRUD Methods for REST-style operations
    async def insert_record(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert a record into a table and return the inserted record"""
        try:
            # Build INSERT query dynamically
            columns = list(data.keys())
            placeholders = [f"${i+1}" for i in range(len(columns))]
            values = list(data.values())
            
            query = f"""
                INSERT INTO "{table}" ({', '.join(f'"{col}"' for col in columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """
            
            async with self.get_connection() as conn:
                row = await conn.fetchrow(query, *values)
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Insert record failed for table {table}: {e}")
            raise
    
    async def update_record(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update records in a table based on filters and return updated record"""
        try:
            # Build UPDATE query dynamically
            set_clauses = [f'"{col}" = ${i+1}' for i, col in enumerate(data.keys())]
            set_values = list(data.values())
            
            # Build WHERE clause
            where_clauses = []
            where_values = []
            param_index = len(set_values) + 1
            
            for col, val in filters.items():
                where_clauses.append(f'"{col}" = ${param_index}')
                where_values.append(val)
                param_index += 1
            
            query = f"""
                UPDATE "{table}" 
                SET {', '.join(set_clauses)}
                WHERE {' AND '.join(where_clauses)}
                RETURNING *
            """
            
            all_values = set_values + where_values
            
            async with self.get_connection() as conn:
                row = await conn.fetchrow(query, *all_values)
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Update record failed for table {table}: {e}")
            raise
    
    async def find_by_filters(self, table: str, filters: Dict[str, Any] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Find records in a table based on filters"""
        try:
            query_parts = [f'SELECT * FROM "{table}"']
            values = []
            
            if filters:
                where_clauses = []
                for i, (col, val) in enumerate(filters.items(), 1):
                    where_clauses.append(f'"{col}" = ${i}')
                    values.append(val)
                query_parts.append(f"WHERE {' AND '.join(where_clauses)}")
            
            if limit:
                query_parts.append(f"LIMIT {limit}")
            
            query = ' '.join(query_parts)
            
            async with self.get_connection() as conn:
                rows = await conn.fetch(query, *values)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Find by filters failed for table {table}: {e}")
            raise
    
    async def find_one_by_filters(self, table: str, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find one record in a table based on filters"""
        try:
            results = await self.find_by_filters(table, filters, limit=1)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Find one by filters failed for table {table}: {e}")
            raise
    
    async def delete_record(self, table: str, filters: Dict[str, Any]) -> int:
        """Delete records from a table based on filters and return count of deleted records"""
        try:
            where_clauses = []
            values = []
            
            for i, (col, val) in enumerate(filters.items(), 1):
                where_clauses.append(f'"{col}" = ${i}')
                values.append(val)
            
            query = f'DELETE FROM "{table}" WHERE {" AND ".join(where_clauses)}'
            
            async with self.get_connection() as conn:
                result = await conn.execute(query, *values)
                # Extract number from result like "DELETE 3"
                return int(result.split()[-1]) if result.split()[-1].isdigit() else 0
                
        except Exception as e:
            logger.error(f"Delete record failed for table {table}: {e}")
            raise

# Create global database manager instance
db_manager = DatabaseManager()
