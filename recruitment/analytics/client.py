"""
DuckDB Analytics Warehouse Client

Provides a singleton connection to the DuckDB analytics database
with connection pooling, error handling, and query execution utilities.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb
import pandas as pd
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DuckDBClient:
    """
    Singleton client for DuckDB analytics warehouse.
    
    Features:
    - Connection pooling
    - Automatic schema initialization
    - Query execution with pandas integration
    - Parquet export/import
    - Error handling and logging
    """
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize DuckDB connection and create database file."""
        # Get database path from environment or use default
        db_path = os.getenv('DUCKDB_PATH', 'data/analytics.duckdb')
        
        # Create data directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to DuckDB
        self._connection = duckdb.connect(db_path)
        
        # Configure DuckDB for optimal performance
        self._connection.execute("SET memory_limit='2GB'")
        self._connection.execute("SET threads=4")
        
        logger.info(f"✅ DuckDB connection established: {db_path}")
    
    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Get the DuckDB connection."""
        if self._connection is None:
            self._initialize_connection()
        return self._connection
    
    @contextmanager
    def cursor(self):
        """Context manager for DuckDB cursor."""
        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute(self, query: str, parameters: Optional[List] = None) -> duckdb.DuckDBPyConnection:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            parameters: Optional query parameters
            
        Returns:
            DuckDB connection with query results
        """
        try:
            if parameters:
                result = self.connection.execute(query, parameters)
            else:
                result = self.connection.execute(query)
            
            logger.debug(f"Executed query: {query[:100]}...")
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            raise
    
    def query_df(self, query: str, parameters: Optional[List] = None) -> pd.DataFrame:
        """
        Execute a query and return results as a pandas DataFrame.
        
        Args:
            query: SQL query string
            parameters: Optional query parameters
            
        Returns:
            Pandas DataFrame with query results
        """
        try:
            result = self.execute(query, parameters)
            df = result.df()
            logger.debug(f"Query returned {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Query to DataFrame failed: {e}")
            raise
    
    def insert_df(self, table_name: str, df: pd.DataFrame, mode: str = 'append'):
        """
        Insert a pandas DataFrame into a DuckDB table.
        
        Args:
            table_name: Name of the target table
            df: Pandas DataFrame to insert
            mode: 'append' or 'replace'
        """
        try:
            if mode == 'replace':
                # Drop table if exists
                self.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Register DataFrame as a temporary view
            self.connection.register('temp_df', df)
            
            # Insert from temporary view
            if mode == 'append':
                self.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df")
            else:
                self.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            
            # Unregister temporary view
            self.connection.unregister('temp_df')
            
            logger.info(f"✅ Inserted {len(df)} rows into {table_name}")
            
        except Exception as e:
            logger.error(f"DataFrame insert failed: {e}")
            raise
    
    def export_to_parquet(self, table_name: str, output_path: str):
        """
        Export a DuckDB table to Parquet file.
        
        Args:
            table_name: Name of the table to export
            output_path: Path to output Parquet file
        """
        try:
            # Create output directory if needed
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Export to Parquet
            query = f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)"
            self.execute(query)
            
            logger.info(f"✅ Exported {table_name} to {output_path}")
            
        except Exception as e:
            logger.error(f"Parquet export failed: {e}")
            raise
    
    def import_from_parquet(self, table_name: str, parquet_path: str, mode: str = 'replace'):
        """
        Import a Parquet file into a DuckDB table.
        
        Args:
            table_name: Name of the target table
            parquet_path: Path to Parquet file
            mode: 'append' or 'replace'
        """
        try:
            if mode == 'replace':
                self.execute(f"DROP TABLE IF EXISTS {table_name}")
                query = f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{parquet_path}')"
            else:
                query = f"INSERT INTO {table_name} SELECT * FROM read_parquet('{parquet_path}')"
            
            self.execute(query)
            logger.info(f"✅ Imported {parquet_path} into {table_name}")
            
        except Exception as e:
            logger.error(f"Parquet import failed: {e}")
            raise
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            result = self.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [table_name]
            ).fetchone()
            return result[0] > 0
        except:
            return False
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table."""
        try:
            # Get row count
            row_count = self.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            # Get column info
            columns = self.query_df(f"DESCRIBE {table_name}")
            
            # Get table size (approximate)
            size_query = f"SELECT pg_size_pretty(pg_total_relation_size('{table_name}'))"
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'columns': columns.to_dict('records'),
                'exists': True
            }
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {'exists': False}
    
    def close(self):
        """Close the DuckDB connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("DuckDB connection closed")


# Singleton instance
_client = None

def get_client() -> DuckDBClient:
    """Get the singleton DuckDB client instance."""
    global _client
    if _client is None:
        _client = DuckDBClient()
    return _client
