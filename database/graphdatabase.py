"""
Neo4j Graph Database Client Module

This module provides functionality to interact with Neo4j graph database for creating
network graphs of Reddit data, including relationships between posts, users, and categories.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable, ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Neo4jClient:
    """Client for interacting with Neo4j graph database."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern for database connection."""
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the Neo4j client using credentials from environment variables."""
        if self._initialized:
            return
            
        # Get credentials from environment variables
        self.uri = os.getenv('NEO4J_URI')
        self.username = os.getenv('NEO4J_USERNAME')
        self.password = os.getenv('NEO4J_PASSWORD')
        self.database = os.getenv('NEO4J_DATABASE')
        
        if not all([self.uri, self.username, self.password, self.database]):
            raise ValueError("Neo4j credentials not found in environment variables")
        
        # Create driver instance
        self.driver = GraphDatabase.driver(
            self.uri, 
            auth=(self.username, self.password)
        )
        
        # Ensure database exists
        self.ensure_database_exists()
        
        # Test connection
        self._test_connection()
        
        self._initialized = True
        logger.info(f"Connected to Neo4j database: {self.database}")
    
    def ensure_database_exists(self):
        """Ensure that the specified database exists, create it if it doesn't."""
        try:
            # Check if the database exists using system database
            with self.driver.session(database="system") as session:
                query = "SHOW DATABASES"
                result = session.run(query)
                databases = [record["name"] for record in result]
                
                if self.database not in databases:
                    logger.info(f"Database '{self.database}' not found, creating it now")
                    create_query = f"CREATE DATABASE {self.database}"
                    session.run(create_query)
                    
                    # Wait for database to be available
                    import time
                    for attempt in range(5):
                        try:
                            check_query = "SHOW DATABASES"
                            check_result = session.run(check_query)
                            check_databases = [record["name"] for record in check_result]
                            
                            if self.database in check_databases:
                                logger.info(f"Database '{self.database}' successfully created")
                                break
                        except Exception as e:
                            logger.warning(f"Waiting for database to be ready (attempt {attempt+1}): {e}")
                        
                        time.sleep(2)
                else:
                    logger.info(f"Database '{self.database}' already exists")
                    
        except Exception as e:
            logger.error(f"Error checking/creating database: {e}")
            # If we can't create the database, still try to proceed - it might exist but we lack permissions to see it
            logger.warning("Proceeding with connection attempt anyway")
    
    def _test_connection(self):
        """Test the connection to Neo4j."""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS test")
                record = result.single()
                if record and record["test"] == 1:
                    logger.info("Neo4j connection test successful")
                else:
                    raise ConnectionError("Neo4j connection test failed")
        except Neo4jError as e:
            if "Neo.ClientError.Database.DatabaseNotFound" in str(e):
                logger.error(f"Database '{self.database}' not found. Attempting to create it...")
                self.ensure_database_exists()
                # Try connection test again
                with self.driver.session(database=self.database) as session:
                    result = session.run("RETURN 1 AS test")
                    record = result.single()
                    if record and record["test"] == 1:
                        logger.info("Neo4j connection test successful after database creation")
                        # Initialize database
                        self.initialize_database()
                    else:
                        raise ConnectionError("Neo4j connection test failed after database creation")
            else:
                logger.error(f"Neo4j connection error: {e}")
                raise ConnectionError(f"Failed to connect to Neo4j: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {e}")
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    def initialize_database(self):
        """Initialize a new database with necessary settings and configurations."""
        try:
            # Set database configuration if needed
            logger.info(f"Initializing new database: {self.database}")
            
            # Create necessary constraints and indexes
            self.create_reddit_graph_schema()
            
            # Create initial nodes/relationships if needed
            self.create_initial_data()
            
            logger.info(f"Database '{self.database}' successfully initialized")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            logger.warning("Proceeding with connection anyway, but database may not be properly set up")
    
    def create_initial_data(self):
        """Create initial data for a new database."""
        try:
            with self.driver.session(database=self.database) as session:
                # Check if database is empty
                result = session.run("MATCH (n) RETURN count(n) as nodeCount")
                record = result.single()
                
                if record and record["nodeCount"] == 0:
                    logger.info("Creating initial data for empty database")
                    
                    # Create base category nodes
                    categories = [
                        "LLM", "Computer Vision", "AI Ethics", "Robotics",
                        "Machine Learning", "NLP", "Data Science", "Research",
                        "Neural Networks", "Reinforcement Learning"
                    ]
                    
                    for category in categories:
                        session.run(
                            "CREATE (c:Category {name: $name})",
                            {"name": category}
                        )
                    
                    # Create popular subreddit nodes
                    subreddits = [
                        "ArtificialIntelligence", "MachineLearning", "ComputerVision",
                        "AIEthics", "ReinforcementLearning", "OpenAI", "DataScience",
                        "learnmachinelearning", "LanguageTechnology", "deeplearning"
                    ]
                    
                    for subreddit in subreddits:
                        session.run(
                            "CREATE (s:Subreddit {name: $name})",
                            {"name": subreddit}
                        )
                    
                    logger.info(f"Created {len(categories)} categories and {len(subreddits)} subreddits")
                else:
                    logger.info("Database already contains data, skipping initial data creation")
                
        except Exception as e:
            logger.error(f"Error creating initial data: {e}")
            # Continue even if initial data creation fails
    
    def close(self):
        """Close the Neo4j driver connection."""
        if hasattr(self, 'driver'):
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return the results.
        
        Args:
            query: Cypher query string
            params: Query parameters
            
        Returns:
            List of result records as dictionaries
        """
        params = params or {}
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, params)
                return [dict(record) for record in result]
        except Neo4jError as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a node with the given label and properties.
        
        Args:
            label: Node label
            properties: Node properties
            
        Returns:
            Created node as a dictionary
        """
        query = f"""
        CREATE (n:{label} $props)
        RETURN n
        """
        result = self.execute_query(query, {"props": properties})
        return result[0]["n"] if result else None
    
    def create_relationship(self, 
                          from_node_label: str, 
                          from_node_props: Dict[str, Any],
                          to_node_label: str, 
                          to_node_props: Dict[str, Any],
                          rel_type: str,
                          rel_props: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a relationship between two nodes.
        
        Args:
            from_node_label: Label of the source node
            from_node_props: Properties to identify the source node
            to_node_label: Label of the target node
            to_node_props: Properties to identify the target node
            rel_type: Relationship type
            rel_props: Optional relationship properties
            
        Returns:
            Created relationship as a dictionary
        """
        rel_props = rel_props or {}
        
        query = f"""
        MATCH (from:{from_node_label}), (to:{to_node_label})
        WHERE from.{list(from_node_props.keys())[0]} = ${list(from_node_props.keys())[0]}
        AND to.{list(to_node_props.keys())[0]} = ${list(to_node_props.keys())[0]}
        CREATE (from)-[r:{rel_type} $rel_props]->(to)
        RETURN r
        """
        
        params = {
            list(from_node_props.keys())[0]: list(from_node_props.values())[0],
            list(to_node_props.keys())[0]: list(to_node_props.values())[0],
            "rel_props": rel_props
        }
        
        result = self.execute_query(query, params)
        return result[0]["r"] if result else None
        
    def find_or_create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        查找具有给定标签和属性的节点，如果不存在则创建它。
        
        参数:
            label: 节点标签
            properties: 节点属性
            
        返回:
            以字典形式返回找到或创建的节点
        """
        # 根据属性创建匹配条件
        match_props = {}
        for key, value in properties.items():
            if value is not None:
                match_props[key] = value
        
        if not match_props:
            raise ValueError("必须提供至少一个属性来查找或创建节点")
        
        # 为MERGE语句创建属性字符串
        props_string = ", ".join([f"{k}: ${k}" for k in match_props.keys()])
        
        query = f"""
        MERGE (n:{label} {{{props_string}}})
        ON CREATE SET n = $props
        RETURN n
        """
        
        params = dict(match_props)
        params["props"] = properties
        
        result = self.execute_query(query, params)
        return result[0]["n"] if result else None

    def find_node(self, label: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a node with the given label and properties.
        
        Args:
            label: Node label
            properties: Node properties to match
            
        Returns:
            Found node as a dictionary or None if not found
        """
        # Build match conditions for the query
        match_conditions = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
        
        query = f"""
        MATCH (n:{label})
        WHERE {match_conditions}
        RETURN n
        """
        
        result = self.execute_query(query, properties)
        return result[0]["n"] if result else None
    
    def get_node_relationships(self, 
                             label: str, 
                             properties: Dict[str, Any],
                             direction: str = "both") -> List[Dict[str, Any]]:
        """
        Get relationships for a node.
        
        Args:
            label: Node label
            properties: Node properties to match
            direction: Relationship direction ('both', 'outgoing', or 'incoming')
            
        Returns:
            List of relationships
        """
        # Build match conditions for the query
        match_conditions = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
        
        if direction == "outgoing":
            rel_pattern = "(n)-[r]->(m)"
        elif direction == "incoming":
            rel_pattern = "(n)<-[r]-(m)"
        else:  # both
            rel_pattern = "(n)-[r]-(m)"
        
        query = f"""
        MATCH (n:{label}), {rel_pattern}
        WHERE {match_conditions}
        RETURN r, m
        """
        
        return self.execute_query(query, properties)
    
    def delete_node(self, label: str, properties: Dict[str, Any]) -> bool:
        """
        Delete a node with the given label and properties.
        
        Args:
            label: Node label
            properties: Node properties to match
            
        Returns:
            True if successful, False otherwise
        """
        # Build match conditions for the query
        match_conditions = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
        
        query = f"""
        MATCH (n:{label})
        WHERE {match_conditions}
        DETACH DELETE n
        """
        
        try:
            self.execute_query(query, properties)
            return True
        except Neo4jError:
            return False
    
    def delete_all_nodes(self) -> bool:
        """
        Delete all nodes in the database.
        
        Returns:
            True if successful, False otherwise
        """
        query = """
        MATCH (n)
        DETACH DELETE n
        """
        
        try:
            self.execute_query(query)
            logger.info("All nodes deleted")
            return True
        except Neo4jError as e:
            logger.error(f"Error deleting all nodes: {e}")
            return False

    def create_reddit_graph_schema(self):
        """Create constraints and indexes for the Reddit graph schema."""
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Post) REQUIRE p.post_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.username IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Subreddit) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (p:Post) ON (p.created_utc)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Post) ON (p.score)",
        ]
        
        for query in queries:
            try:
                self.execute_query(query)
            except Neo4jError as e:
                logger.warning(f"Error creating schema element: {e}")
        
        logger.info("Reddit graph schema created")


# Singleton instance
neo4j_client = None

def get_neo4j_client() -> Neo4jClient:
    """Get the Neo4j client singleton instance."""
    global neo4j_client
    if neo4j_client is None:
        neo4j_client = Neo4jClient()
    return neo4j_client


# Example usage and test
if __name__ == "__main__":
    try:
        # Initialize client
        client = get_neo4j_client()
        print("Connected to Neo4j database")
        
        # Clear database for testing
        client.delete_all_nodes()
        
        # Create schema
        client.create_reddit_graph_schema()
        
        # Create sample data

        # 1. Create sample subreddits
        subreddits = ["ArtificialIntelligence", "MachineLearning", "OpenAI"]
        for subreddit in subreddits:
            client.find_or_create_node("Subreddit", {"name": subreddit})
            print(f"Created subreddit: {subreddit}")
        
        # 2. Create sample users
        users = ["ai_enthusiast", "ml_researcher", "tech_guru", "data_scientist"]
        for username in users:
            client.find_or_create_node("User", {
                "username": username,
                "karma": 1000 + hash(username) % 5000,
                "account_created": "2020-01-01"
            })
            print(f"Created user: {username}")
        
        # 3. Create sample categories
        categories = ["LLM", "Computer Vision", "AI Ethics", "Reinforcement Learning"]
        for category in categories:
            client.find_or_create_node("Category", {"name": category})
            print(f"Created category: {category}")
        
        # 4. Create sample posts
        sample_posts = [
            {
                "post_id": "post1",
                "title": "GPT-5 Performance Analysis",
                "created_utc": "2024-03-15T10:00:00",
                "score": 150,
                "num_comments": 45,
                "username": "ai_enthusiast",
                "subreddit": "ArtificialIntelligence",
                "category": "LLM"
            },
            {
                "post_id": "post2",
                "title": "Ethics of AI in Healthcare",
                "created_utc": "2024-03-14T15:30:00",
                "score": 120,
                "num_comments": 32,
                "username": "tech_guru",
                "subreddit": "ArtificialIntelligence",
                "category": "AI Ethics"
            },
            {
                "post_id": "post3",
                "title": "Latest Advancements in Computer Vision",
                "created_utc": "2024-03-13T09:15:00",
                "score": 200,
                "num_comments": 60,
                "username": "ml_researcher",
                "subreddit": "MachineLearning",
                "category": "Computer Vision"
            },
            {
                "post_id": "post4",
                "title": "Transformer Architecture Explained",
                "created_utc": "2024-03-12T14:45:00",
                "score": 180,
                "num_comments": 40,
                "username": "data_scientist",
                "subreddit": "MachineLearning",
                "category": "LLM"
            },
            {
                "post_id": "post5",
                "title": "OpenAI's New Research Paper",
                "created_utc": "2024-03-11T11:30:00",
                "score": 250,
                "num_comments": 75,
                "username": "ai_enthusiast",
                "subreddit": "OpenAI",
                "category": "LLM"
            },
            {
                "post_id": "post6",
                "title": "Reinforcement Learning in Robotics",
                "created_utc": "2024-03-10T16:00:00",
                "score": 140,
                "num_comments": 38,
                "username": "ml_researcher",
                "subreddit": "MachineLearning",
                "category": "Reinforcement Learning"
            },
            {
                "post_id": "post7",
                "title": "Bias in AI Models",
                "created_utc": "2024-03-09T13:20:00",
                "score": 160,
                "num_comments": 50,
                "username": "tech_guru",
                "subreddit": "ArtificialIntelligence",
                "category": "AI Ethics"
            },
            {
                "post_id": "post8",
                "title": "Computer Vision in Autonomous Vehicles",
                "created_utc": "2024-03-08T10:45:00",
                "score": 190,
                "num_comments": 55,
                "username": "data_scientist",
                "subreddit": "MachineLearning",
                "category": "Computer Vision"
            },
            {
                "post_id": "post9",
                "title": "Generative AI Breakthroughs",
                "created_utc": "2024-03-07T09:30:00",
                "score": 220,
                "num_comments": 65,
                "username": "ai_enthusiast",
                "subreddit": "OpenAI",
                "category": "LLM"
            },
            {
                "post_id": "post10",
                "title": "GPT Applications in Research",
                "created_utc": "2024-03-06T14:15:00",
                "score": 170,
                "num_comments": 48,
                "username": "ml_researcher",
                "subreddit": "ArtificialIntelligence",
                "category": "LLM"
            }
        ]
        
        # Create posts and relationships
        for post_data in sample_posts:
            # Extract data
            post_id = post_data["post_id"]
            username = post_data["username"]
            subreddit = post_data["subreddit"]
            category = post_data["category"]
            
            # Create post node
            post_props = {k: v for k, v in post_data.items() 
                         if k not in ["username", "subreddit", "category"]}
            post_node = client.find_or_create_node("Post", post_props)
            
            # Create relationships
            client.execute_query(
                """
                MATCH (p:Post {post_id: $post_id})
                MATCH (u:User {username: $username})
                MERGE (u)-[r:POSTED]->(p)
                """,
                {"post_id": post_id, "username": username}
            )
            
            client.execute_query(
                """
                MATCH (p:Post {post_id: $post_id})
                MATCH (s:Subreddit {name: $subreddit})
                MERGE (p)-[r:POSTED_IN]->(s)
                """,
                {"post_id": post_id, "subreddit": subreddit}
            )
            
            client.execute_query(
                """
                MATCH (p:Post {post_id: $post_id})
                MATCH (c:Category {name: $category})
                MERGE (p)-[r:BELONGS_TO]->(c)
                """,
                {"post_id": post_id, "category": category}
            )
            
            print(f"Created post: {post_data['title']}")
        
        # Run some test queries
        print("\n--- Test Queries ---")
        
        # 1. Find top posts by score
        print("\nTop 3 posts by score:")
        top_posts = client.execute_query("""
            MATCH (p:Post)
            RETURN p.title as title, p.score as score
            ORDER BY p.score DESC
            LIMIT 3
        """)
        for post in top_posts:
            print(f"- {post['title']} (Score: {post['score']})")
        
        # 2. Find all posts by a user
        user = "ai_enthusiast"
        print(f"\nPosts by {user}:")
        user_posts = client.execute_query("""
            MATCH (u:User {username: $username})-[:POSTED]->(p:Post)
            RETURN p.title as title, p.score as score
            ORDER BY p.score DESC
        """, {"username": user})
        for post in user_posts:
            print(f"- {post['title']} (Score: {post['score']})")
        
        # 3. Find posts by category
        category = "LLM"
        print(f"\nPosts in {category} category:")
        category_posts = client.execute_query("""
            MATCH (p:Post)-[:BELONGS_TO]->(c:Category {name: $category})
            RETURN p.title as title, p.score as score
            ORDER BY p.score DESC
        """, {"category": category})
        for post in category_posts:
            print(f"- {post['title']} (Score: {post['score']})")
        
        # 4. Find which users post in which subreddits
        print("\nUsers and their subreddits:")
        user_subreddits = client.execute_query("""
            MATCH (u:User)-[:POSTED]->(p:Post)-[:POSTED_IN]->(s:Subreddit)
            RETURN u.username as username, collect(distinct s.name) as subreddits
        """)
        for item in user_subreddits:
            print(f"- {item['username']}: {', '.join(item['subreddits'])}")
        
        # 5. Find most active categories
        print("\nMost active categories (by post count):")
        active_categories = client.execute_query("""
            MATCH (p:Post)-[:BELONGS_TO]->(c:Category)
            RETURN c.name as category, count(p) as post_count
            ORDER BY post_count DESC
        """)
        for category in active_categories:
            print(f"- {category['category']}: {category['post_count']} posts")
            
        print("\nTest completed successfully!")

        # # 6. Find relevant categories
        # print("\nMost relevant categories:")
        # category_name = "LLM"  # Replace with the category you want to find relations for
        # related_categories = client.execute_query("""
        #     MATCH path = (c1:Category {name: $category_name})-[*1..10]-(c2:Category)
        #     WHERE c1 <> c2
        #     RETURN c2.name as related_category, length(path) as distance, [node in nodes(path) | COALESCE(node.name, '')] as path_nodes
        #     ORDER BY distance, related_category
        # """, {"category_name": category_name})

        # for category in related_categories:
        #     print(f"- {category['related_category']} (Distance: {category['distance']})")
        #     print(f"  Path: {' -> '.join(filter(None, category['path_nodes']))}")
            
        # print("\nTest completed successfully!")
        
        
    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        # Close connection
        if 'client' in locals():
            client.close()
            print("\nDatabase connection closed") 