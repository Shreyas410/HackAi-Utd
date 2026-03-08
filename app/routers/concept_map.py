"""
Concept map endpoints.
Serves visual representations of skill topic relationships.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
import base64

from ..models.schemas import ConceptMapResponse
from ..services.concept_map import concept_map_service

router = APIRouter(prefix="/api/v1/concept-map", tags=["Concept Map"])


@router.get("/{skill}", response_model=ConceptMapResponse)
async def get_concept_map(
    skill: str,
    include_image: bool = True
):
    """
    Get concept map for a skill.
    
    The concept map visualizes relationships between sub-topics:
    - Nodes represent concepts/topics at different skill levels
    - Edges show relationships (builds_on, used_in, enables, etc.)
    - Colors indicate difficulty level (green=beginner, blue=intermediate, purple=advanced)
    
    Args:
        skill: The skill to get concept map for
        include_image: Whether to generate and include the image (default: True)
    
    Returns:
        ConceptMapResponse with nodes, edges, and optional base64 image
    
    Example:
        GET /api/v1/concept-map/Python%20programming
    """
    image_url, image_base64, nodes, edges = concept_map_service.get_concept_map(
        skill,
        generate_image=include_image
    )
    
    return ConceptMapResponse(
        skill=skill,
        image_url=image_url,
        image_base64=image_base64,
        nodes=nodes,
        edges=edges,
        format="png" if image_base64 else None
    )


@router.get("/{skill}/image")
async def get_concept_map_image(skill: str):
    """
    Get concept map as PNG image directly.
    
    This endpoint returns the raw PNG image for embedding.
    
    Args:
        skill: The skill to get concept map for
    
    Returns:
        PNG image response
    
    Example:
        <img src="/api/v1/concept-map/Python%20programming/image" />
    """
    _, image_base64, _, _ = concept_map_service.get_concept_map(
        skill,
        generate_image=True
    )
    
    if not image_base64:
        raise HTTPException(
            status_code=500,
            detail="Could not generate concept map image. Ensure networkx and matplotlib are installed."
        )
    
    image_bytes = base64.b64decode(image_base64)
    
    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{skill.replace(" ", "_")}_concept_map.png"',
            "Cache-Control": "max-age=3600"
        }
    )


@router.get("/{skill}/structure")
async def get_concept_map_structure(skill: str):
    """
    Get concept map structure only (no image).
    
    Returns just the nodes and edges for custom rendering.
    
    Args:
        skill: The skill to get concept map for
    
    Returns:
        JSON with nodes and edges arrays
    """
    _, _, nodes, edges = concept_map_service.get_concept_map(
        skill,
        generate_image=False
    )
    
    return {
        "skill": skill,
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
        "node_count": len(nodes),
        "edge_count": len(edges)
    }
