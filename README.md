# TunaTale Micro-Demo 0.1

A proof-of-concept for an AI-powered language learning app that generates personalized audio curricula with dynamic corpus evolution.

## Features

- **Curriculum Generation**: Create 5-day learning progressions based on learning goals using mock responses
- **Collocation Extraction**: Automatically identify and rank 3-5 word phrases from curriculum
- **Story Generation**: Create engaging stories that naturally incorporate target collocations using mock responses
- **Progressive Learning**: Each day's content builds on previous learning

## How It Works

1. **Curriculum Generation**: The app generates a 5-day language learning curriculum based on your learning goal using mock responses.
2. **Collocation Extraction**: It then extracts 3-5 word phrases (collocations) from the curriculum using spaCy.
3. **Story Generation**: Finally, it generates engaging stories that naturally incorporate the target collocations using mock responses.

### Mock Responses

When you run the app for the first time, it will prompt you to provide mock responses for:
- Curriculum generation
- Story generation

These responses will be saved in the `data/mock_responses/` directory and reused in subsequent runs. This allows you to:
1. Provide consistent responses during development
2. Test the app without needing API keys
3. Easily modify or update responses as needed

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tunatale-micro-demo
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

### 1. Generate a Curriculum
```bash
python main.py generate "Learning goal here"
Example: python main.py generate "Ordering food in a restaurant"
```

### 2. View the Generated Curriculum
```bash
python main.py view curriculum
```

### 3. Extract Collocations
```bash
python main.py extract
```

### 4. View Extracted Collocations
```bash
python main.py view collocations
```

### 5. Generate a Story for a Specific Day
```bash
python main.py story 1  # For Day 1
python main.py story 2  # For Day 2, etc.
```

### 6. View Generated Stories
```bash
python main.py view story --day 1
```

## File Structure

```
tunatale_micro_demo/
├── config.py              # Configuration and paths
├── curriculum_generator.py # Curriculum generation logic
├── collocation_extractor.py # Collocation extraction logic
├── content_generator.py   # Story generation logic
├── main.py                # Command-line interface
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables
├── data/
│   ├── curriculum.json    # Generated curriculum
│   ├── collocations.json  # Extracted collocations
│   └── generated_content/ # Generated stories
└── prompts/              # Prompt templates
    ├── curriculum_prompt.txt
    └── story_generation_prompt.txt
```

## Customization

### Modifying Prompts
Edit the files in the `prompts/` directory to customize the behavior of the AI:
- `curriculum_prompt.txt`: Controls how the curriculum is generated
- `story_generation_prompt.txt`: Controls how stories are generated

### Adjusting Collocation Extraction
Edit the `extract_collocations` method in `collocation_extractor.py` to modify how collocations are identified and filtered.

## Next Steps

1. **Add audio generation** using a TTS service
2. **Implement SRS (Spaced Repetition System)**
3. **Add user feedback** to improve content generation
4. **Create a web interface**
5. **Add more language support**

## License

MIT License
