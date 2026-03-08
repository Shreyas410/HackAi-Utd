"""
Concept map generation service.
Creates visual representations of skill topic relationships.
"""

import json
import os
import base64
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple
from ..models.schemas import SkillLevel, ConceptMapNode, ConceptMapEdge
from ..config import SKILLS_CONFIG_DIR, CONCEPT_MAPS_DIR

try:
    import networkx as nx
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


class ConceptMapService:
    """
    Service for generating and serving concept maps.
    
    Concept maps visualize relationships between sub-topics:
    - Nodes represent concepts/topics
    - Edges show relationships (builds_on, used_in, enables, etc.)
    - Colors indicate difficulty level
    """
    
    def __init__(self):
        self._skill_configs: Dict[str, Any] = {}
        self._cached_images: Dict[str, str] = {}  # skill -> base64 image
        
        # Ensure concept maps directory exists
        os.makedirs(CONCEPT_MAPS_DIR, exist_ok=True)
    
    def _normalize_skill_name(self, skill: str) -> str:
        """Convert skill name to config file name."""
        return skill.lower().replace(" ", "_").replace("-", "_")
    
    def _load_skill_config(self, skill: str) -> Optional[Dict[str, Any]]:
        """Load skill configuration from JSON file."""
        normalized = self._normalize_skill_name(skill)
        
        if normalized in self._skill_configs:
            return self._skill_configs[normalized]
        
        config_path = os.path.join(SKILLS_CONFIG_DIR, f"{normalized}.json")
        
        if not os.path.exists(config_path):
            if os.path.exists(SKILLS_CONFIG_DIR):
                for filename in os.listdir(SKILLS_CONFIG_DIR):
                    if normalized in filename or filename.replace(".json", "") in normalized:
                        config_path = os.path.join(SKILLS_CONFIG_DIR, filename)
                        break
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self._skill_configs[normalized] = config
                return config
        
        return None
    
    def get_concept_map(
        self,
        skill: str,
        generate_image: bool = True
    ) -> Tuple[Optional[str], Optional[str], List[ConceptMapNode], List[ConceptMapEdge]]:
        """
        Get concept map for a skill.
        
        Args:
            skill: The skill to get concept map for
            generate_image: Whether to generate/return image
        
        Returns:
            Tuple of (image_url, image_base64, nodes, edges)
        """
        config = self._load_skill_config(skill)
        
        if config and "concept_map" in config:
            concept_map = config["concept_map"]
            nodes = [
                ConceptMapNode(
                    id=n["id"],
                    label=n["label"],
                    level=SkillLevel(n["level"]) if n.get("level") else None
                )
                for n in concept_map.get("nodes", [])
            ]
            edges = [
                ConceptMapEdge(
                    source=e["source"],
                    target=e["target"],
                    relationship=e.get("relationship", "relates_to")
                )
                for e in concept_map.get("edges", [])
            ]
        else:
            # Generate generic concept map
            nodes, edges = self._generate_generic_concept_map(skill)
        
        # Check for pre-generated image
        normalized = self._normalize_skill_name(skill)
        image_path = os.path.join(CONCEPT_MAPS_DIR, f"{normalized}.png")
        
        if os.path.exists(image_path):
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")
            return None, image_base64, nodes, edges
        
        # Generate image if requested and networkx available
        if generate_image and NETWORKX_AVAILABLE:
            image_base64 = self._generate_image(nodes, edges, skill)
            return None, image_base64, nodes, edges
        
        return None, None, nodes, edges
    
    def _generate_generic_concept_map(
        self,
        skill: str
    ) -> Tuple[List[ConceptMapNode], List[ConceptMapEdge]]:
        """Generate a generic concept map structure."""
        nodes = [
            ConceptMapNode(id="root", label=skill, level=None),
            ConceptMapNode(id="fundamentals", label="Fundamentals", level=SkillLevel.BEGINNER),
            ConceptMapNode(id="core_concepts", label="Core Concepts", level=SkillLevel.BEGINNER),
            ConceptMapNode(id="practical_skills", label="Practical Skills", level=SkillLevel.INTERMEDIATE),
            ConceptMapNode(id="best_practices", label="Best Practices", level=SkillLevel.INTERMEDIATE),
            ConceptMapNode(id="advanced_topics", label="Advanced Topics", level=SkillLevel.ADVANCED),
            ConceptMapNode(id="specializations", label="Specializations", level=SkillLevel.ADVANCED),
        ]
        
        edges = [
            ConceptMapEdge(source="root", target="fundamentals", relationship="starts_with"),
            ConceptMapEdge(source="fundamentals", target="core_concepts", relationship="builds_on"),
            ConceptMapEdge(source="core_concepts", target="practical_skills", relationship="applied_in"),
            ConceptMapEdge(source="practical_skills", target="best_practices", relationship="guided_by"),
            ConceptMapEdge(source="best_practices", target="advanced_topics", relationship="enables"),
            ConceptMapEdge(source="advanced_topics", target="specializations", relationship="leads_to"),
        ]
        
        return nodes, edges
    
    def _generate_image(
        self,
        nodes: List[ConceptMapNode],
        edges: List[ConceptMapEdge],
        skill: str
    ) -> str:
        """Generate concept map image using networkx and matplotlib."""
        if not NETWORKX_AVAILABLE:
            return ""
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add nodes with attributes
        level_colors = {
            None: "#808080",  # Gray for root/unspecified
            SkillLevel.BEGINNER: "#4CAF50",  # Green
            SkillLevel.INTERMEDIATE: "#2196F3",  # Blue
            SkillLevel.ADVANCED: "#9C27B0"  # Purple
        }
        
        node_colors = []
        for node in nodes:
            G.add_node(node.id, label=node.label)
            node_colors.append(level_colors.get(node.level, "#808080"))
        
        # Add edges
        for edge in edges:
            G.add_edge(edge.source, edge.target, relationship=edge.relationship)
        
        # Create layout
        try:
            pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        except:
            pos = nx.circular_layout(G)
        
        # Create figure
        plt.figure(figsize=(12, 8))
        plt.title(f"Concept Map: {skill}", fontsize=16, fontweight='bold')
        
        # Draw nodes
        nx.draw_networkx_nodes(
            G, pos,
            node_color=node_colors,
            node_size=2000,
            alpha=0.9
        )
        
        # Draw labels
        labels = {n.id: n.label for n in nodes}
        nx.draw_networkx_labels(
            G, pos,
            labels=labels,
            font_size=9,
            font_weight='bold'
        )
        
        # Draw edges
        nx.draw_networkx_edges(
            G, pos,
            edge_color='#666666',
            arrows=True,
            arrowsize=20,
            connectionstyle="arc3,rad=0.1"
        )
        
        # Draw edge labels
        edge_labels = {(e.source, e.target): e.relationship.replace("_", " ") for e in edges}
        nx.draw_networkx_edge_labels(
            G, pos,
            edge_labels=edge_labels,
            font_size=7,
            font_color='#444444'
        )
        
        # Add legend
        legend_elements = [
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#808080',
                      markersize=10, label='Root/General'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#4CAF50',
                      markersize=10, label='Beginner'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#2196F3',
                      markersize=10, label='Intermediate'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='#9C27B0',
                      markersize=10, label='Advanced'),
        ]
        plt.legend(handles=legend_elements, loc='upper left', fontsize=8)
        
        plt.axis('off')
        plt.tight_layout()
        
        # Convert to base64
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
        
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        # Cache the image
        normalized = self._normalize_skill_name(skill)
        self._cached_images[normalized] = image_base64
        
        return image_base64
    
    def save_concept_map_image(self, skill: str) -> str:
        """Generate and save concept map image to file."""
        _, image_base64, nodes, edges = self.get_concept_map(skill, generate_image=True)
        
        if image_base64:
            normalized = self._normalize_skill_name(skill)
            image_path = os.path.join(CONCEPT_MAPS_DIR, f"{normalized}.png")
            
            with open(image_path, "wb") as f:
                f.write(base64.b64decode(image_base64))
            
            return image_path
        
        return ""


concept_map_service = ConceptMapService()
