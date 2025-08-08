"""
Dynamic Day Prompt Generator for TunaTale Content Generation

This module generates day-specific prompts that combine with the system prompt
to create vocabulary-informed, strategy-aware content generation.
"""

import logging
from typing import Dict, Optional, List
from pathlib import Path

from content_strategy import ContentStrategy, DifficultyLevel
from mock_srs import MockSRS, create_mock_srs


class DayPromptGenerator:
    """Generates dynamic day-specific prompts for content generation."""
    
    def __init__(self, mock_srs: Optional[MockSRS] = None):
        """Initialize with mock SRS for vocabulary constraints."""
        self.mock_srs = mock_srs or create_mock_srs()
        
        # El Nido scenario templates for each day
        self.scenario_templates = {
            1: {
                "title": "Welcome to El Nido!",
                "scenario": "arrival_and_first_impressions",
                "context": "Airport pickup, hotel check-in, first local interactions",
                "focus": "Basic greetings and courtesy"
            },
            2: {
                "title": "Getting Around Town",
                "scenario": "navigation_and_transportation", 
                "context": "Asking for directions, taking tricycle/jeepney, finding locations",
                "focus": "Location and movement vocabulary"
            },
            3: {
                "title": "Market and Shopping",
                "scenario": "local_market_shopping",
                "context": "Buying food, souvenirs, negotiating prices, local vendors",
                "focus": "Money, prices, and basic transactions"
            },
            4: {
                "title": "Food and Restaurants",
                "scenario": "dining_experiences",
                "context": "Ordering food, restaurant interactions, trying local cuisine",
                "focus": "Food vocabulary and dining etiquette"
            },
            5: {
                "title": "Accommodation Needs",
                "scenario": "hotel_and_lodging",
                "context": "Hotel services, room issues, asking for help with facilities",
                "focus": "Accommodation and comfort needs"
            },
            6: {
                "title": "Beach and Activities", 
                "scenario": "beach_and_recreation",
                "context": "Beach activities, weather, planning excursions, equipment rental",
                "focus": "Leisure activities and weather"
            },
            7: {
                "title": "Restaurant Confidence",
                "scenario": "advanced_dining",
                "context": "Complex restaurant interactions, special requests, social dining",
                "focus": "Sophisticated dining vocabulary"
            },
            8: {
                "title": "Departure Preparations",
                "scenario": "departure_and_farewell",
                "context": "Checking out, airport procedures, saying goodbye",
                "focus": "Travel logistics and farewells"
            }
        }
    
    def generate_day_prompt(
        self,
        day: int,
        strategy: ContentStrategy = ContentStrategy.BALANCED,
        source_day: Optional[int] = None,
        learning_objective: Optional[str] = None
    ) -> str:
        """Generate a complete day-specific prompt for content generation."""
        
        # Get SRS vocabulary data
        srs_data = self.mock_srs.get_srs_data_for_prompt(day, strategy)
        
        # Determine scenario and context
        scenario_info = self._get_scenario_info(day, source_day, strategy)
        
        # Generate strategy-specific guidance
        strategy_guidance = self._get_strategy_guidance(strategy, source_day)
        
        # Build the dynamic prompt
        day_prompt = f"""
**DYNAMIC DAY PROMPT - Day {day}**

**Learning Objective:** {learning_objective or scenario_info['title']}
**Scenario:** {scenario_info['scenario']}
**Context:** {scenario_info['context']}
**Focus:** {scenario_info['focus']}
**Strategy:** {strategy.value.upper()}

{srs_data['vocabulary_constraints']}

**SCENARIO REQUIREMENTS:**
{self._get_scenario_requirements(scenario_info, strategy)}

**STRATEGY-SPECIFIC GUIDANCE:**
{strategy_guidance}

**CONTENT GENERATION INSTRUCTIONS:**
Generate a complete structured lesson following the system prompt format with:

1. **Title**: [NARRATOR]: Day {day}: {scenario_info['title']}{' – Day ' + str(source_day) + ' Revisited' if source_day else ''}

2. **Key Phrases Section**: 
   - Focus on {srs_data['new_vocabulary_limit']} NEW practical phrases for this scenario
   - Must incorporate ALL review vocabulary: {', '.join(srs_data['review_vocabulary'])}
   - Use Pimsleur breakdown method for new Tagalog phrases only

3. **Natural Speed Section**:
   - 4-6 dialogue scenes based on: {scenario_info['context']}
   - 90%+ Filipino dialogue with strategic English only
   - Each scene 5-12 lines for substantial practice
   - Incorporate all learned vocabulary naturally: {', '.join(srs_data['learned_vocabulary'][-8:])}

4. **Slow Speed & Translated Sections**:
   - Mirror Natural Speed exactly with ellipses and translations
   - Provide cultural context for Filipino expressions when needed

**SUCCESS CRITERIA:**
- Vocabulary stays within constraints (max {srs_data['new_vocabulary_limit']} new words)
- All review vocabulary naturally incorporated
- Authentic Filipino conversation patterns
- Practical for El Nido travel scenario
- Appropriate for {srs_data['difficulty_level']} level

Generate the complete lesson now:
"""
        return day_prompt.strip()
    
    def _get_scenario_info(self, day: int, source_day: Optional[int], strategy: ContentStrategy) -> Dict[str, str]:
        """Get scenario information for the day."""
        
        if strategy == ContentStrategy.DEEPER and source_day:
            # For DEEPER strategy, enhance the source day scenario
            base_scenario = self.scenario_templates.get(source_day, self.scenario_templates[1])
            return {
                "title": f"{base_scenario['title']} Enhanced",
                "scenario": f"{base_scenario['scenario']}_enhanced", 
                "context": f"Advanced version: {base_scenario['context']}",
                "focus": f"Sophisticated {base_scenario['focus'].lower()}"
            }
        else:
            # Use day-specific scenario or default to departure if beyond map
            return self.scenario_templates.get(day, self.scenario_templates[8])
    
    def _get_strategy_guidance(self, strategy: ContentStrategy, source_day: Optional[int]) -> str:
        """Generate strategy-specific content guidance."""
        
        if strategy == ContentStrategy.DEEPER:
            return f"""
DEEPER STRATEGY - Enhanced Language Complexity:
- Build upon Day {source_day or 'previous'} content with sophisticated improvements
- Replace simple phrases with more natural Filipino expressions
- Use authentic Filipino conversation patterns vs. literal English translations
- Minimize English scaffolding while maintaining comprehension
- Include cultural nuances and indirect communication styles
- Example enhancement: "Magkano po?" → "Ano pong presyo nito?" (more formal register)
"""
        
        elif strategy == ContentStrategy.WIDER:
            return """
WIDER STRATEGY - Expanded Contexts:
- Introduce new scenarios while maintaining current language complexity
- Reuse established vocabulary in fresh situational contexts
- Generate variety in interactions while keeping difficulty consistent
- Focus on practical applications of known vocabulary
- Expand cultural contexts and social situations
"""
        
        else:
            return """
BALANCED STRATEGY - Steady Progression:
- Gradual introduction of new vocabulary and concepts
- Balanced mix of reinforcement and new learning
- Maintain steady complexity progression appropriate for day number
- Focus on practical, immediately useful language skills
"""
    
    def _get_scenario_requirements(self, scenario_info: Dict[str, str], strategy: ContentStrategy) -> str:
        """Generate specific requirements based on the scenario and strategy."""
        
        scenario_type = scenario_info['scenario']
        
        requirements = {
            "arrival_and_first_impressions": "Focus on polite greetings, basic courtesy, and establishing positive first contact with locals",
            "navigation_and_transportation": "Include asking for directions, understanding location responses, and transportation vocabulary",
            "local_market_shopping": "Emphasize price negotiation, product inquiries, and cultural shopping etiquette", 
            "dining_experiences": "Cover ordering food, expressing preferences, and restaurant social interactions",
            "hotel_and_lodging": "Include service requests, problem resolution, and accommodation-related needs",
            "beach_and_recreation": "Focus on activity planning, weather discussions, and leisure vocabulary",
            "advanced_dining": "Sophisticated restaurant interactions, complex orders, and social dining situations",
            "departure_and_farewell": "Cover logistics, expressing gratitude, and meaningful farewells"
        }
        
        base_requirement = requirements.get(scenario_type.split('_')[0], "Focus on practical communication for this scenario")
        
        if strategy == ContentStrategy.DEEPER:
            return f"{base_requirement}\nEMPHASIS: Use sophisticated Filipino expressions, minimize English, include cultural subtleties"
        elif strategy == ContentStrategy.WIDER:
            return f"{base_requirement}\nEMPHASIS: Expand contexts and situations while maintaining current language level"
        else:
            return base_requirement
    
    def load_system_prompt(self) -> str:
        """Load the persistent system prompt."""
        system_prompt_path = Path("prompts/system_prompt.txt")
        try:
            with open(system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logging.error(f"System prompt not found at {system_prompt_path}")
            return ""
    
    def combine_prompts(self, system_prompt: str, day_prompt: str) -> str:
        """Combine system prompt with day-specific prompt."""
        return f"{system_prompt}\n\n{'='*80}\n\n{day_prompt}"
    
    def generate_complete_prompt(
        self,
        day: int,
        strategy: ContentStrategy = ContentStrategy.BALANCED,
        source_day: Optional[int] = None,
        learning_objective: Optional[str] = None
    ) -> str:
        """Generate complete prompt combining system and day prompts."""
        
        system_prompt = self.load_system_prompt()
        day_prompt = self.generate_day_prompt(day, strategy, source_day, learning_objective)
        
        return self.combine_prompts(system_prompt, day_prompt)


def create_prompt_generator() -> DayPromptGenerator:
    """Factory function to create a prompt generator."""
    return DayPromptGenerator()