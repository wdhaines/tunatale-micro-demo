import json
from pathlib import Path
from typing import Dict, Any
from config import PROMPTS_DIR, CURRICULUM_PATH
from mock_llm import MockLLM

class CurriculumGenerator:
    def __init__(self):
        self.llm = MockLLM()
        self.curriculum_prompt = self._load_prompt('curriculum_prompt.txt')
    
    def _load_prompt(self, filename):
        prompt_path = PROMPTS_DIR / filename
        if not prompt_path.exists():
            # Create default prompt if it doesn't exist
            default_prompt = """Create a 5-day language learning curriculum for the following goal: {goal}
            
            For each day, include:
            1. Key phrases/concepts to learn
            2. Grammar points
            3. Vocabulary focus
            4. Suggested practice activities
            
            Make it progressive, starting simple and building complexity.
            Focus on practical, conversational language.
            """
            with open(prompt_path, 'w') as f:
                f.write(default_prompt)
            return default_prompt
        else:
            with open(prompt_path, 'r') as f:
                return f.read()
    
    def generate_curriculum(self, learning_goal: str) -> str:
        """Generate a 5-day curriculum based on the learning goal."""
        try:
            # Create the prompt
            prompt = self.curriculum_prompt.format(goal=learning_goal)
            
            # Get response from mock LLM
            response = self.llm.get_response(
                prompt=prompt,
                response_type="curriculum"
            )
            
            # Extract the content from the response
            curriculum = response['choices'][0]['message']['content']
            self._save_curriculum(curriculum, learning_goal)
            return curriculum
        except Exception as e:
            print(f"Error generating curriculum: {e}")
            return None
    
    def _save_curriculum(self, curriculum, learning_goal):
        """Save the generated curriculum to a file."""
        curriculum_data = {
            "learning_goal": learning_goal,
            "content": curriculum,
            "days": self._parse_curriculum_days(curriculum)
        }
        
        with open(CURRICULUM_PATH, 'w') as f:
            json.dump(curriculum_data, f, indent=2)
    
    def _parse_curriculum_days(self, curriculum_text):
        """Parse the curriculum text into structured day-by-day content."""
        # This is a simple parser - in a real implementation, you'd want to make this more robust
        days = {}
        current_day = None
        
        for line in curriculum_text.split('\n'):
            line = line.strip()
            if line.lower().startswith('day '):
                current_day = line.split(':')[0].strip()
                days[current_day] = []
            elif current_day and line:
                days[current_day].append(line)
        
        return days
