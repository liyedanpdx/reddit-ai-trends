"""
Graph Service Module

This module provides services for working with graph databases
to analyze relationships between Reddit posts, users, and topics.
"""

from services.graphservice.reddit_graph import RedditGraphService
from database.graphdatabase import get_neo4j_client

__all__ = ['RedditGraphService', 'initialize_graph_database']

def initialize_graph_database():
    """
    Initialize the graph database connection and schema.
    This should be called during application startup.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        client = get_neo4j_client()
        service = RedditGraphService()
        service.create_schema()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to initialize graph database: {e}")
        return False 