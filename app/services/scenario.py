"""
Scenario-based practice service.
Implements branching scenarios with decision points, consequences, and feedback.
"""

import json
import os
import uuid
from typing import Dict, Any, List, Optional, Tuple
from ..models.schemas import (
    SkillLevel, ScenarioNode, ScenarioAction, ScenarioFeedback
)
from ..config import SKILLS_CONFIG_DIR


class ScenarioService:
    """
    Service for managing scenario-based practice.
    
    Scenarios follow branching logic:
    - Each scenario has multiple nodes (decision points)
    - Each node presents a situation and possible actions
    - Actions lead to consequences and feedback
    - Difficulty adjusts based on learner performance
    """
    
    def __init__(self):
        self._skill_configs: Dict[str, Any] = {}
        self._active_scenarios: Dict[str, Dict[str, Any]] = {}  # session_id -> scenario state
    
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
    
    def get_available_scenarios(
        self,
        skill: str,
        level: Optional[SkillLevel] = None
    ) -> List[Dict[str, Any]]:
        """Get list of available scenarios for a skill."""
        config = self._load_skill_config(skill)
        if not config or "scenarios" not in config:
            return []
        
        scenarios = config["scenarios"]
        
        if level:
            scenarios = [
                s for s in scenarios
                if s.get("difficulty", "intermediate") == level.value
            ]
        
        return [
            {
                "scenario_id": s["scenario_id"],
                "title": s["title"],
                "difficulty": s.get("difficulty", "intermediate"),
                "learning_outcomes": s.get("learning_outcomes", [])
            }
            for s in scenarios
        ]
    
    def start_scenario(
        self,
        session_id: str,
        skill: str,
        level: SkillLevel,
        scenario_id: Optional[str] = None
    ) -> Tuple[str, str, str, List[str], ScenarioNode]:
        """
        Start a new scenario practice session.
        
        Args:
            session_id: The learning session ID
            skill: The skill being practiced
            level: Target difficulty level
            scenario_id: Specific scenario ID (optional)
        
        Returns:
            Tuple of (scenario_id, title, skill, learning_outcomes, first_node)
        """
        config = self._load_skill_config(skill)
        
        if config and "scenarios" in config:
            scenarios = config["scenarios"]
            
            # Filter by level
            level_scenarios = [
                s for s in scenarios
                if s.get("difficulty", "intermediate") == level.value
            ]
            
            if scenario_id:
                scenario = next(
                    (s for s in scenarios if s["scenario_id"] == scenario_id),
                    None
                )
            elif level_scenarios:
                scenario = level_scenarios[0]
            elif scenarios:
                scenario = scenarios[0]
            else:
                scenario = None
        else:
            scenario = None
        
        if not scenario:
            # Generate a generic scenario
            scenario = self._generate_generic_scenario(skill, level)
        
        # Initialize scenario state
        scenario_instance_id = f"{scenario['scenario_id']}_{uuid.uuid4().hex[:8]}"
        
        self._active_scenarios[session_id] = {
            "scenario_id": scenario_instance_id,
            "original_id": scenario["scenario_id"],
            "scenario_data": scenario,
            "current_node_id": "start",
            "actions_taken": [],
            "score": 0
        }
        
        # Get first node
        first_node = self._get_node(scenario, "start")
        
        return (
            scenario_instance_id,
            scenario["title"],
            skill,
            scenario.get("learning_outcomes", []),
            first_node
        )
    
    def _get_node(self, scenario: Dict[str, Any], node_id: str) -> ScenarioNode:
        """Get a scenario node by ID."""
        nodes = scenario.get("nodes", {})
        node_data = nodes.get(node_id, {})
        
        actions = [
            ScenarioAction(
                action_id=a["action_id"],
                description=a["description"],
                is_optimal=a.get("is_optimal")
            )
            for a in node_data.get("actions", [])
        ]
        
        return ScenarioNode(
            node_id=node_data.get("node_id", node_id),
            narrative=node_data.get("narrative", "Continue with the scenario."),
            actions=actions,
            is_terminal=node_data.get("is_terminal", False)
        )
    
    def take_action(
        self,
        session_id: str,
        scenario_id: str,
        node_id: str,
        action_id: str
    ) -> ScenarioFeedback:
        """
        Process an action taken in a scenario.
        
        Args:
            session_id: The learning session ID
            scenario_id: The scenario instance ID
            node_id: Current node ID
            action_id: Chosen action ID
        
        Returns:
            ScenarioFeedback with consequences and next node
        """
        state = self._active_scenarios.get(session_id)
        
        if not state or state["scenario_id"] != scenario_id:
            return ScenarioFeedback(
                action_taken=action_id,
                consequence="Scenario not found or expired.",
                feedback="Please start a new scenario.",
                score_delta=0,
                scenario_complete=True,
                final_score=0
            )
        
        scenario = state["scenario_data"]
        
        # Validate current node
        if state["current_node_id"] != node_id:
            return ScenarioFeedback(
                action_taken=action_id,
                consequence="Node mismatch - you may have navigated incorrectly.",
                feedback="Please refresh and try again.",
                score_delta=0
            )
        
        # Get the current node and action
        current_node_data = scenario["nodes"].get(node_id, {})
        actions = current_node_data.get("actions", [])
        action = next((a for a in actions if a["action_id"] == action_id), None)
        
        if not action:
            return ScenarioFeedback(
                action_taken=action_id,
                consequence="Invalid action selected.",
                feedback="Please choose from the available actions.",
                score_delta=0
            )
        
        # Calculate score delta
        is_optimal = action.get("is_optimal", False)
        score_delta = 10 if is_optimal else -5 if is_optimal is False else 0
        state["score"] += score_delta
        
        # Record action
        state["actions_taken"].append({
            "node_id": node_id,
            "action_id": action_id,
            "is_optimal": is_optimal
        })
        
        # Get feedback
        feedback_key = f"{action_id}_{node_id}"
        feedback_text = scenario.get("feedback", {}).get(
            feedback_key,
            "Good choice!" if is_optimal else "Consider alternative approaches."
        )
        
        # Get next node
        transitions = scenario.get("transitions", {})
        node_transitions = transitions.get(node_id, {})
        next_node_id = node_transitions.get(action_id)
        
        # Determine consequence
        if is_optimal:
            consequence = "Your decision led to a positive outcome."
        elif is_optimal is False:
            consequence = "This approach has some drawbacks you should consider."
        else:
            consequence = "The outcome depends on additional factors."
        
        # Get next node or end scenario
        if next_node_id and next_node_id in scenario["nodes"]:
            state["current_node_id"] = next_node_id
            next_node = self._get_node(scenario, next_node_id)
            
            return ScenarioFeedback(
                action_taken=action["description"],
                consequence=consequence,
                feedback=feedback_text,
                score_delta=score_delta,
                next_node=next_node if not next_node.is_terminal else None,
                scenario_complete=next_node.is_terminal,
                final_score=state["score"] if next_node.is_terminal else None
            )
        else:
            # Scenario complete
            return ScenarioFeedback(
                action_taken=action["description"],
                consequence=consequence,
                feedback=feedback_text + " Scenario complete!",
                score_delta=score_delta,
                scenario_complete=True,
                final_score=state["score"]
            )
    
    def get_scenario_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of an active scenario."""
        state = self._active_scenarios.get(session_id)
        if not state:
            return None
        
        scenario = state["scenario_data"]
        current_node = self._get_node(scenario, state["current_node_id"])
        
        return {
            "scenario_id": state["scenario_id"],
            "title": scenario["title"],
            "current_node": current_node,
            "score": state["score"],
            "actions_taken": len(state["actions_taken"])
        }
    
    def _generate_generic_scenario(
        self,
        skill: str,
        level: SkillLevel
    ) -> Dict[str, Any]:
        """Generate a generic scenario when no config exists."""
        scenario_id = f"generic_{skill.replace(' ', '_').lower()}_{level.value}"
        
        return {
            "scenario_id": scenario_id,
            "title": f"Practical {skill} Challenge",
            "difficulty": level.value,
            "learning_outcomes": [
                f"Apply {skill} concepts in a realistic situation",
                "Make decisions under constraints",
                "Learn from feedback"
            ],
            "nodes": {
                "start": {
                    "node_id": "start",
                    "narrative": f"You're working on a project that requires {skill}. A colleague asks for your help with a problem they're stuck on. How do you approach this?",
                    "actions": [
                        {
                            "action_id": "a1",
                            "description": "Immediately provide a solution based on your experience",
                            "is_optimal": False
                        },
                        {
                            "action_id": "a2",
                            "description": "Ask clarifying questions to understand the problem better",
                            "is_optimal": True
                        },
                        {
                            "action_id": "a3",
                            "description": "Suggest they search online for solutions",
                            "is_optimal": False
                        }
                    ],
                    "is_terminal": False
                },
                "node_2": {
                    "node_id": "node_2",
                    "narrative": "After understanding the problem, you identify the core issue. What's your next step?",
                    "actions": [
                        {
                            "action_id": "a1",
                            "description": "Write the solution yourself to save time",
                            "is_optimal": False
                        },
                        {
                            "action_id": "a2",
                            "description": "Guide your colleague through solving it step by step",
                            "is_optimal": True
                        }
                    ],
                    "is_terminal": False
                },
                "end": {
                    "node_id": "end",
                    "narrative": "Great work! You've successfully helped your colleague while also reinforcing your own understanding.",
                    "actions": [],
                    "is_terminal": True
                }
            },
            "transitions": {
                "start": {"a1": "node_2", "a2": "node_2", "a3": "node_2"},
                "node_2": {"a1": "end", "a2": "end"}
            },
            "feedback": {
                "a2_start": "Excellent! Understanding the problem fully before proposing solutions is key.",
                "a1_start": "Quick solutions may miss important context. Consider asking questions first.",
                "a2_node_2": "Teaching others is one of the best ways to solidify your own knowledge."
            }
        }


scenario_service = ScenarioService()
