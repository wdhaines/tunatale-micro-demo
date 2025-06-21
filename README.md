# TunaTale Micro-Demo 1.0

A proof-of-concept for an AI-powered language learning app that generates personalized language learning content with a focus on natural language acquisition through contextual learning.

## Features

- **Curriculum Generation**: Create structured learning progressions based on learning goals
- **Collocation Extraction**: Automatically identify and rank 3-5 word phrases from generated content
- **Story Generation**: Create engaging stories that naturally incorporate target vocabulary
- **Interactive CLI**: User-friendly command-line interface for all operations
- **Mock LLM Support**: Built-in mock LLM for testing and development

## Prerequisites

- Python 3.9+
- pip (Python package manager)
- Git (for version control)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/wdhaines/tunatale-micro-demo.git
   cd tunatale-micro-demo
   ```

2. **Set up the environment**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Run the application**
   ```bash
   python main.py --help  # See available commands
   ```

## Usage

### Generate a Curriculum
Create a new learning curriculum:
```bash
python main.py generate "Your learning goal here"
```

### View Curriculum
View the generated curriculum:
```bash
python main.py view curriculum
```

### Extract Collocations
Extract key phrases from the curriculum:
```bash
python main.py extract
```

### Generate a Story
Generate a story for a specific day:
```bash
python main.py story 1  # For Day 1
```

## Development

### Project Structure
```
.
├── config.py               # Application configuration
├── curriculum_service.py   # Curriculum generation service
├── collocation_extractor.py # Collocation extraction logic
├── story_generator.py      # Story generation service
├── llm_mock.py            # Mock LLM implementation
├── main.py                 # Command-line interface
├── Makefile               # Common development tasks
├── pytest.ini             # Pytest configuration
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── tests/                  # Test suite
└── utils/                  # Utility functions
```

### Testing

Run the full test suite:
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest -v

# Run tests with coverage report
pytest --cov=.
```

### Code Quality

Format and check code quality:
```bash
# Format code with Black
black .


# Check for type errors
mypy .


# Run linter
flake8
```

## Mock Responses

The application includes a mock LLM implementation for testing and development. Mock responses are stored in the `data/mock_responses/` directory and are used when the application is run without an OpenAI API key.

To update mock responses:
1. Delete the contents of `data/mock_responses/`
2. Run the application - it will prompt for new mock responses

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
├── .env                  # Environment variables
├── data/
│   ├── curriculum.json    # Generated curriculum
│   ├── collocations.json  # Extracted collocations
│   └── generated_content/ # Generated stories
└── prompts/              # Prompt templates
    ├── curriculum_template.txt
    └── story_template.txt
```

## Customization

### Modifying Prompts
Edit the files in the `prompts/` directory to customize the behavior of the AI:
- `curriculum_template.txt`: Controls how the curriculum is generated
- `story_template.txt`: Controls how stories are generated

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
