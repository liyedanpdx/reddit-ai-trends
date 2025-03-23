"""
Reddit Graph Service

This service provides functionality to analyze Reddit data using graph database.
It creates and queries relationships between posts, users, categories, and subreddits.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
# 添加项目根目录到Python路径
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from database.graphdatabase import get_neo4j_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditGraphService:
    """Service for analyzing Reddit data using graph database."""
    
    def __init__(self):
        """Initialize the Reddit graph service."""
        self.neo4j_client = get_neo4j_client()
        logger.info("Reddit Graph Service initialized")
    
    def create_schema(self):
        """Create the Reddit graph schema."""
        self.neo4j_client.create_reddit_graph_schema()
        logger.info("Reddit graph schema created")
    
    def import_posts(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Import Reddit posts into the graph database.
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            Import statistics
        """
        if not posts:
            return {"nodes_created": 0, "relationships_created": 0}
        
        nodes_created = 0
        relationships_created = 0
        
        try:
            for post in posts:
                # Process post data
                post_id = post.get('post_id') or post.get('id')
                if not post_id:
                    logger.warning(f"Skipping post without ID: {post.get('title', 'Unknown')}")
                    continue
                
                # Extract data
                author = post.get('author', 'anonymous')
                subreddit = post.get('subreddit', 'unknown')
                
                # Determine category based on available data
                category = None
                if 'category' in post:
                    category = post['category']
                elif 'link_flair_text' in post:
                    category = post['link_flair_text']
                
                # Create post properties
                post_props = {
                    'post_id': post_id,
                    'title': post.get('title', ''),
                    'created_utc': post.get('created_utc', ''),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0),
                    'upvote_ratio': post.get('upvote_ratio', 0.0),
                    'is_self': post.get('is_self', True),
                    'selftext': post.get('selftext', '')[:1000],  # Limit text length
                    'url': post.get('url', ''),
                    'permalink': post.get('permalink', '')
                }
                
                # Create post node
                self.neo4j_client.find_or_create_node("Post", post_props)
                nodes_created += 1
                
                # Create user node if author exists
                if author and author != 'anonymous' and author != '[deleted]':
                    user_props = {
                        'username': author,
                        'karma': post.get('author_karma', 0)
                    }
                    self.neo4j_client.find_or_create_node("User", user_props)
                    nodes_created += 1
                    
                    # Create POSTED relationship
                    self.neo4j_client.execute_query(
                        """
                        MATCH (p:Post {post_id: $post_id})
                        MATCH (u:User {username: $username})
                        MERGE (u)-[r:POSTED]->(p)
                        """,
                        {"post_id": post_id, "username": author}
                    )
                    relationships_created += 1
                
                # Create subreddit node
                if subreddit and subreddit != 'unknown':
                    subreddit_props = {
                        'name': subreddit
                    }
                    self.neo4j_client.find_or_create_node("Subreddit", subreddit_props)
                    nodes_created += 1
                    
                    # Create POSTED_IN relationship
                    self.neo4j_client.execute_query(
                        """
                        MATCH (p:Post {post_id: $post_id})
                        MATCH (s:Subreddit {name: $subreddit})
                        MERGE (p)-[r:POSTED_IN]->(s)
                        """,
                        {"post_id": post_id, "subreddit": subreddit}
                    )
                    relationships_created += 1
                
                # Create category node if available
                if category:
                    category_props = {
                        'name': category
                    }
                    self.neo4j_client.find_or_create_node("Category", category_props)
                    nodes_created += 1
                    
                    # Create BELONGS_TO relationship
                    self.neo4j_client.execute_query(
                        """
                        MATCH (p:Post {post_id: $post_id})
                        MATCH (c:Category {name: $category})
                        MERGE (p)-[r:BELONGS_TO]->(c)
                        """,
                        {"post_id": post_id, "category": category}
                    )
                    relationships_created += 1
            
            logger.info(f"Imported {len(posts)} posts into graph database")
            return {
                "nodes_created": nodes_created,
                "relationships_created": relationships_created
            }
        
        except Exception as e:
            logger.error(f"Error importing posts to graph database: {e}")
            raise
    
    def get_top_users_by_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top users by number of posts.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of users with post counts
        """
        query = """
        MATCH (u:User)-[:POSTED]->(p:Post)
        RETURN u.username as username, count(p) as post_count
        ORDER BY post_count DESC
        LIMIT $limit
        """
        return self.neo4j_client.execute_query(query, {"limit": limit})
    
    def get_top_categories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top categories by number of posts.
        
        Args:
            limit: Maximum number of categories to return
            
        Returns:
            List of categories with post counts
        """
        query = """
        MATCH (p:Post)-[:BELONGS_TO]->(c:Category)
        RETURN c.name as category, count(p) as post_count
        ORDER BY post_count DESC
        LIMIT $limit
        """
        return self.neo4j_client.execute_query(query, {"limit": limit})
    
    def get_user_interests(self, username: str) -> List[Dict[str, Any]]:
        """
        Get categories of interest for a specific user.
        
        Args:
            username: Username to analyze
            
        Returns:
            List of categories with post counts
        """
        query = """
        MATCH (u:User {username: $username})-[:POSTED]->(p:Post)-[:BELONGS_TO]->(c:Category)
        RETURN c.name as category, count(p) as post_count, 
               avg(p.score) as avg_score
        ORDER BY post_count DESC
        """
        return self.neo4j_client.execute_query(query, {"username": username})
    
    def get_related_categories(self, category: str) -> List[Dict[str, Any]]:
        """
        Get categories related to the specified category.
        
        Args:
            category: Category name
            
        Returns:
            List of related categories with relationship strength
        """
        query = """
        MATCH (c1:Category {name: $category})<-[:BELONGS_TO]-(p:Post)-[:BELONGS_TO]->(c2:Category)
        WHERE c1 <> c2
        RETURN c2.name as related_category, count(p) as common_posts
        ORDER BY common_posts DESC
        """
        return self.neo4j_client.execute_query(query, {"category": category})
    
    def get_category_sentiment(self, category: str) -> Dict[str, Any]:
        """
        Get sentiment analysis for a category, if posts have sentiment data.
        
        Args:
            category: Category name
            
        Returns:
            Sentiment statistics for the category
        """
        query = """
        MATCH (p:Post)-[:BELONGS_TO]->(c:Category {name: $category})
        WHERE p.sentiment_score IS NOT NULL
        RETURN avg(p.sentiment_score) as avg_sentiment,
               count(p) as post_count,
               sum(CASE WHEN p.sentiment_score > 0.05 THEN 1 ELSE 0 END) as positive_count,
               sum(CASE WHEN p.sentiment_score < -0.05 THEN 1 ELSE 0 END) as negative_count,
               sum(CASE WHEN p.sentiment_score >= -0.05 AND p.sentiment_score <= 0.05 THEN 1 ELSE 0 END) as neutral_count
        """
        results = self.neo4j_client.execute_query(query, {"category": category})
        if not results or results[0]["post_count"] == 0:
            return {
                "category": category,
                "has_sentiment_data": False,
                "message": "No sentiment data available for this category"
            }
        
        sentiment_data = results[0]
        return {
            "category": category,
            "has_sentiment_data": True,
            "avg_sentiment": sentiment_data["avg_sentiment"],
            "post_count": sentiment_data["post_count"],
            "positive_percent": (sentiment_data["positive_count"] / sentiment_data["post_count"]) * 100,
            "negative_percent": (sentiment_data["negative_count"] / sentiment_data["post_count"]) * 100,
            "neutral_percent": (sentiment_data["neutral_count"] / sentiment_data["post_count"]) * 100
        }
    
    def get_user_similarity(self, username1: str, username2: str) -> Dict[str, Any]:
        """
        Calculate similarity between two users based on posting patterns.
        
        Args:
            username1: First username
            username2: Second username
            
        Returns:
            Similarity metrics
        """
        query = """
        MATCH (u1:User {username: $username1})-[:POSTED]->(p1:Post)-[:BELONGS_TO]->(c:Category)
        WITH u1, c, count(p1) as u1_posts
        MATCH (u2:User {username: $username2})-[:POSTED]->(p2:Post)-[:BELONGS_TO]->(c)
        WITH u1, u2, c, u1_posts, count(p2) as u2_posts
        RETURN c.name as category, u1_posts, u2_posts
        ORDER BY u1_posts + u2_posts DESC
        """
        results = self.neo4j_client.execute_query(query, {
            "username1": username1,
            "username2": username2
        })
        
        if not results:
            return {
                "users": [username1, username2],
                "common_categories": 0,
                "similarity_score": 0,
                "common_interests": []
            }
        
        common_categories = len(results)
        common_interests = [{
            "category": r["category"],
            "user1_posts": r["u1_posts"],
            "user2_posts": r["u2_posts"]
        } for r in results]
        
        # Calculate simple similarity score
        total1 = sum(r["u1_posts"] for r in results)
        total2 = sum(r["u2_posts"] for r in results)
        overlap = sum(min(r["u1_posts"], r["u2_posts"]) for r in results)
        
        if total1 + total2 == 0:
            similarity_score = 0
        else:
            similarity_score = (2 * overlap) / (total1 + total2)
        
        return {
            "users": [username1, username2],
            "common_categories": common_categories,
            "similarity_score": similarity_score,
            "common_interests": common_interests
        }
    
    def find_community_structure(self) -> List[Dict[str, Any]]:
        """
        Find community structures in the Reddit graph using the Label Propagation algorithm.
        
        Returns:
            List of communities with their members
        """
        # This query implements a simple version of label propagation algorithm
        query = """
        CALL gds.graph.project('reddit',
          ['Post', 'User', 'Category', 'Subreddit'],
          ['POSTED', 'BELONGS_TO', 'POSTED_IN']
        )
        YIELD graphName, nodeCount, relationshipCount
        
        CALL gds.labelPropagation.stream('reddit')
        YIELD nodeId, communityId
        
        MATCH (n) WHERE id(n) = nodeId
        RETURN communityId, labels(n)[0] as type, 
               CASE 
                 WHEN labels(n)[0] = 'User' THEN n.username
                 WHEN labels(n)[0] = 'Category' THEN n.name
                 WHEN labels(n)[0] = 'Subreddit' THEN n.name
                 WHEN labels(n)[0] = 'Post' THEN n.title
               END as name,
               count(*) as count
        ORDER BY communityId, type, name
        """
        
        try:
            communities = self.neo4j_client.execute_query(query)
            # Process results to group by community
            community_map = {}
            for record in communities:
                community_id = record["communityId"]
                if community_id not in community_map:
                    community_map[community_id] = {
                        "community_id": community_id,
                        "users": [],
                        "categories": [],
                        "subreddits": [],
                        "posts": []
                    }
                
                if record["type"] == "User":
                    community_map[community_id]["users"].append(record["name"])
                elif record["type"] == "Category":
                    community_map[community_id]["categories"].append(record["name"])
                elif record["type"] == "Subreddit":
                    community_map[community_id]["subreddits"].append(record["name"])
                elif record["type"] == "Post":
                    if len(community_map[community_id]["posts"]) < 5:  # Limit posts to 5 per community
                        community_map[community_id]["posts"].append(record["name"])
            
            return list(community_map.values())
            
        except Exception as e:
            logger.error(f"Error finding community structure: {e}")
            return []
    
    def update_post_sentiment(self, post_id: str, sentiment_score: float) -> bool:
        """
        Update sentiment score for a post.
        
        Args:
            post_id: Post ID
            sentiment_score: Sentiment score from -1 (negative) to 1 (positive)
            
        Returns:
            True if updated successfully, False otherwise
        """
        query = """
        MATCH (p:Post {post_id: $post_id})
        SET p.sentiment_score = $sentiment_score
        RETURN p
        """
        try:
            result = self.neo4j_client.execute_query(query, {
                "post_id": post_id,
                "sentiment_score": sentiment_score
            })
            return bool(result)
        except Exception as e:
            logger.error(f"Error updating post sentiment: {e}")
            return False
    
    def clear_database(self) -> bool:
        """
        Clear all data from the database.
        
        Returns:
            True if successful, False otherwise
        """
        return self.neo4j_client.delete_all_nodes()


# Example usage
if __name__ == "__main__":
    # Initialize service
    service = RedditGraphService()
    
    # Create schema and clear database for testing
    service.clear_database()
    service.create_schema()
    
    # Create sample posts
    sample_posts = [
        {
            'post_id': 'post1',
            'title': 'Understanding GPT-4 Architecture',
            'selftext': 'A technical deep dive into the architecture of GPT-4...',
            'created_utc': datetime.now().isoformat(),
            'score': 150,
            'num_comments': 45,
            'upvote_ratio': 0.92,
            'author': 'ai_researcher',
            'subreddit': 'MachineLearning',
            'category': 'LLM',
            'url': 'https://reddit.com/r/MachineLearning/post1',
            'permalink': '/r/MachineLearning/comments/post1'
        },
        {
            'post_id': 'post2',
            'title': 'New Breakthrough in Computer Vision',
            'selftext': 'Researchers have achieved a new benchmark in object recognition...',
            'created_utc': datetime.now().isoformat(),
            'score': 120,
            'num_comments': 30,
            'upvote_ratio': 0.88,
            'author': 'vision_expert',
            'subreddit': 'ComputerVision',
            'category': 'Computer Vision',
            'url': 'https://reddit.com/r/ComputerVision/post2',
            'permalink': '/r/ComputerVision/comments/post2'
        },
        {
            'post_id': 'post3',
            'title': 'Ethics of AI in Healthcare',
            'selftext': 'Discussion on the ethical implications of AI in medical diagnostics...',
            'created_utc': datetime.now().isoformat(),
            'score': 95,
            'num_comments': 60,
            'upvote_ratio': 0.75,
            'author': 'ethics_advocate',
            'subreddit': 'AIEthics',
            'category': 'Ethics',
            'url': 'https://reddit.com/r/AIEthics/post3',
            'permalink': '/r/AIEthics/comments/post3'
        },
        {
            'post_id': 'post4',
            'title': 'GPT-4 vs Claude: A Comparison',
            'selftext': 'Detailed comparison of capabilities between GPT-4 and Claude...',
            'created_utc': datetime.now().isoformat(),
            'score': 200,
            'num_comments': 80,
            'upvote_ratio': 0.94,
            'author': 'ai_researcher',
            'subreddit': 'MachineLearning',
            'category': 'LLM',
            'url': 'https://reddit.com/r/MachineLearning/post4',
            'permalink': '/r/MachineLearning/comments/post4'
        },
        {
            'post_id': 'post5',
            'title': 'Reinforcement Learning for Robotics',
            'selftext': 'How RL is transforming robotic control systems...',
            'created_utc': datetime.now().isoformat(),
            'score': 110,
            'num_comments': 35,
            'upvote_ratio': 0.9,
            'author': 'robotics_phd',
            'subreddit': 'ReinforcementLearning',
            'category': 'Robotics',
            'url': 'https://reddit.com/r/ReinforcementLearning/post5',
            'permalink': '/r/ReinforcementLearning/comments/post5'
        },
        {
            'post_id': 'post6',
            'title': 'Computer Vision in Autonomous Vehicles',
            'selftext': 'The role of computer vision in self-driving cars...',
            'created_utc': datetime.now().isoformat(),
            'score': 130,
            'num_comments': 40,
            'upvote_ratio': 0.85,
            'author': 'vision_expert',
            'subreddit': 'ComputerVision',
            'category': 'Computer Vision',
            'url': 'https://reddit.com/r/ComputerVision/post6',
            'permalink': '/r/ComputerVision/comments/post6'
        },
        {
            'post_id': 'post7',
            'title': 'Future of AI Research',
            'selftext': 'Trends and predictions for AI research in the next decade...',
            'created_utc': datetime.now().isoformat(),
            'score': 180,
            'num_comments': 70,
            'upvote_ratio': 0.91,
            'author': 'ai_researcher',
            'subreddit': 'ArtificialIntelligence',
            'category': 'Research',
            'url': 'https://reddit.com/r/ArtificialIntelligence/post7',
            'permalink': '/r/ArtificialIntelligence/comments/post7'
        },
        {
            'post_id': 'post8',
            'title': 'Bias in AI Systems',
            'selftext': 'Identifying and mitigating bias in AI models...',
            'created_utc': datetime.now().isoformat(),
            'score': 140,
            'num_comments': 55,
            'upvote_ratio': 0.8,
            'author': 'ethics_advocate',
            'subreddit': 'AIEthics',
            'category': 'Ethics',
            'url': 'https://reddit.com/r/AIEthics/post8',
            'permalink': '/r/AIEthics/comments/post8'
        },
        {
            'post_id': 'post9',
            'title': 'GANs for Image Generation',
            'selftext': 'Recent advances in generative adversarial networks...',
            'created_utc': datetime.now().isoformat(),
            'score': 160,
            'num_comments': 50,
            'upvote_ratio': 0.89,
            'author': 'vision_expert',
            'subreddit': 'MachineLearning',
            'category': 'GANs',
            'url': 'https://reddit.com/r/MachineLearning/post9',
            'permalink': '/r/MachineLearning/comments/post9'
        },
        {
            'post_id': 'post10',
            'title': 'LLMs for Code Generation',
            'selftext': 'How large language models are revolutionizing programming...',
            'created_utc': datetime.now().isoformat(),
            'score': 220,
            'num_comments': 85,
            'upvote_ratio': 0.93,
            'author': 'ai_researcher',
            'subreddit': 'ArtificialIntelligence',
            'category': 'LLM',
            'url': 'https://reddit.com/r/ArtificialIntelligence/post10',
            'permalink': '/r/ArtificialIntelligence/comments/post10'
        }
    ]
    
    # Import sample posts
    import_stats = service.import_posts(sample_posts)
    print(f"Imported {len(sample_posts)} posts")
    print(f"Created {import_stats['nodes_created']} nodes")
    print(f"Created {import_stats['relationships_created']} relationships")
    
    # Add some sentiment scores for testing
    for i, post in enumerate(sample_posts, 1):
        # Generate some test sentiment scores
        sentiment = 0.5 - (i % 5) * 0.2  # Range from -0.3 to 0.5
        service.update_post_sentiment(post['post_id'], sentiment)
    
    # Run test queries
    print("\n--- Test Queries ---")
    
    # 1. Get top users by post count
    print("\nTop users by post count:")
    top_users = service.get_top_users_by_posts(limit=5)
    for user in top_users:
        print(f"- {user['username']}: {user['post_count']} posts")
    
    # 2. Get top categories
    print("\nTop categories:")
    top_categories = service.get_top_categories(limit=5)
    for category in top_categories:
        print(f"- {category['category']}: {category['post_count']} posts")
    
    # 3. Get user interests
    username = "ai_researcher"
    print(f"\nInterests for user '{username}':")
    interests = service.get_user_interests(username)
    for interest in interests:
        print(f"- {interest['category']}: {interest['post_count']} posts, Avg Score: {interest['avg_score']:.1f}")
    
    # 4. Get related categories
    category = "LLM"
    print(f"\nCategories related to '{category}':")
    related = service.get_related_categories(category)
    for rel in related:
        print(f"- {rel['related_category']}: {rel['common_posts']} common posts")
    
    # 5. Get category sentiment
    print(f"\nSentiment for '{category}' category:")
    sentiment = service.get_category_sentiment(category)
    if sentiment.get("has_sentiment_data", False):
        print(f"- Average sentiment: {sentiment['avg_sentiment']:.2f}")
        print(f"- Posts analyzed: {sentiment['post_count']}")
        print(f"- Positive: {sentiment['positive_percent']:.1f}%")
        print(f"- Negative: {sentiment['negative_percent']:.1f}%")
        print(f"- Neutral: {sentiment['neutral_percent']:.1f}%")
    else:
        print(f"- {sentiment.get('message', 'No data available')}")
    
    # 6. Get user similarity
    user1 = "ai_researcher"
    user2 = "vision_expert"
    print(f"\nSimilarity between '{user1}' and '{user2}':")
    similarity = service.get_user_similarity(user1, user2)
    print(f"- Similarity score: {similarity['similarity_score']:.2f}")
    print(f"- Common categories: {similarity['common_categories']}")
    for interest in similarity['common_interests']:
        print(f"- {interest['category']}: {user1}={interest['user1_posts']} posts, {user2}={interest['user2_posts']} posts")
    
    print("\nGraph database test completed successfully!") 