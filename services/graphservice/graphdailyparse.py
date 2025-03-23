"""
Graph Daily Parse Module

This module generates a JSON file from Neo4j database for 3D graph visualization.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from database.graphdatabase import get_neo4j_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GraphDataGenerator:
    """Generate graph data from Neo4j database for visualization."""
    
    def __init__(self):
        """Initialize the graph data generator."""
        self.neo4j_client = get_neo4j_client()
        logger.info("Graph data generator initialized")
    
    def generate_graph_data(self) -> Dict[str, Any]:
        """
        Generate graph data from Neo4j database.
        
        Returns:
            Dictionary containing nodes and links
        """
        logger.info("Generating graph data from Neo4j database")
        
        # Get all nodes
        nodes_result = self.neo4j_client.execute_query("""
            MATCH (n)
            RETURN n, labels(n) as labels
        """)
        
        # Get all relationships
        links_result = self.neo4j_client.execute_query("""
            MATCH (n)-[r]->(m)
            RETURN id(n) as source_id, id(m) as target_id, 
                   n.name as source_name, m.name as target_name,
                   n.post_id as source_post_id, m.post_id as target_post_id,
                   n.username as source_username, m.username as target_username,
                   type(r) as relationship_type, 
                   labels(n) as source_labels, labels(m) as target_labels
        """)
        
        # Transform nodes
        nodes = []
        node_id_map = {}  # Map Neo4j internal IDs to our consecutive IDs
        
        for i, record in enumerate(nodes_result):
            node = record["n"]
            labels = record["labels"]
            
            # Determine node type (group)
            node_type = labels[0] if labels else "Unknown"
            
            # Determine node name based on type
            if "Post" in labels:
                name = node.get("title", f"Post {node.get('post_id', i)}")
                val = node.get("score", 1) / 100 + 1  # Scale the node size
            elif "User" in labels:
                name = node.get("username", f"User {i}")
                val = 1
            elif "Subreddit" in labels:
                name = node.get("name", f"Subreddit {i}")
                val = 2
            elif "Category" in labels:
                name = node.get("name", f"Category {i}")
                val = 1.2
            else:
                name = node.get("name", f"Node {i}")
                val = 1
            
            # Create node object
            node_data = {
                "id": str(i),  # Use consecutive IDs for the visualization
                "name": name,
                "group": node_type,
                "val": val
            }
            
            # Store mapping from Neo4j ID to our consecutive ID
            node_id_map[node.id] = str(i)
            
            nodes.append(node_data)
        
        # Transform links
        links = []
        
        for record in links_result:
            source_id = record["source_id"]
            target_id = record["target_id"]
            
            # Skip if we don't have the node in our map (shouldn't happen)
            if source_id not in node_id_map or target_id not in node_id_map:
                continue
            
            # Create link object
            link_data = {
                "source": node_id_map[source_id],
                "target": node_id_map[target_id],
                "type": record["relationship_type"]
            }
            
            links.append(link_data)
        
        # Combine data
        graph_data = {
            "nodes": nodes,
            "links": links,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated graph data with {len(nodes)} nodes and {len(links)} links")
        return graph_data
    
    def save_graph_data(self, output_path: str = "visualization/3D-graph/graph_data.json") -> str:
        """
        Generate graph data and save to JSON file.
        
        Args:
            output_path: Path to save the JSON file
            
        Returns:
            Path to the saved JSON file
        """
        # Generate graph data
        graph_data = self.generate_graph_data()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved graph data to {output_path}")
        return output_path

def generate_daily_graph_data():
    """Generate graph data for today and save to JSON file."""
    generator = GraphDataGenerator()
    
    # Generate filename with date
    today = datetime.now().strftime("%Y%m%d")
    filename = f"graph_data_{today}.json"
    output_path = os.path.join("visualization", "3D-graph", filename)
    
    # Save current data
    generator.save_graph_data(output_path)
    
    # Also save as latest for direct HTML access
    latest_path = os.path.join("visualization", "3D-graph", "graph_data.json")
    generator.save_graph_data(latest_path)
    
    logger.info(f"Generated daily graph data for {today}")
    return output_path

if __name__ == "__main__":
    try:
        output_file = generate_daily_graph_data()
        print(f"Successfully generated graph data: {output_file}")
    except Exception as e:
        logger.error(f"Error generating graph data: {e}", exc_info=True)
        print(f"Error: {e}")
