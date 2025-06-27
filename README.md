# TunaTale Micro-Demo 1.0

A proof-of-concept for an AI-powered language learning app that generates personalized language learning content with a focus on natural language acquisition through contextual learning.

## Current Status: Tested & Verified ✅

- **Story Generation**: Successfully tested for days 1-5 with proper vocabulary integration
- **Vocabulary**: A2-level vocabulary integration verified
- **Collocation Recycling**: Confirmed working with 5 collocations recycled per day after day 1
- **Test Coverage**: 86% overall test coverage
- **Python Version**: 3.13.5 (Homebrew)
- **OpenSSL Version**: 3.5.0

## Recent Updates
- **2025-06-26**: Updated to Python 3.13.5 with OpenSSL 3.5.0 support
- **2025-06-26**: Fixed all deprecation warnings in the codebase
- **2025-06-26**: Added comprehensive test suite with 94 passing tests
- **2025-06-25**: Completed end-to-end testing of story generation for days 1-5
- **2025-06-25**: Fixed vocabulary integration and prompt template issues

## Features

- **Curriculum Generation**: Create structured learning progressions based on learning goals
- **Collocation Extraction**: Automatically identify and rank 3-5 word phrases from generated content
- **Story Generation**: Create engaging stories that naturally incorporate target vocabulary
- **Interactive CLI**: User-friendly command-line interface for all operations
- **Mock LLM Support**: Built-in mock LLM for testing and development

## Prerequisites

- **Python 3.13.5** (Recommended: Install via Homebrew for OpenSSL 3.5.0 support)
- **pip** (Python package manager)
- **Git** (for version control)
- **Homebrew** (macOS package manager, recommended for Python/OpenSSL setup)

### Python and OpenSSL Setup (macOS)

For optimal performance and security, we recommend using Python 3.13.5 with OpenSSL 3.5.0:

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.13.5 with Homebrew (includes OpenSSL 3.5.0)
brew install python@3.13

# Verify Python and OpenSSL versions
python3 --version  # Should show Python 3.13.5
python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"  # Should show OpenSSL 3.5.0
```

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/wdhaines/tunatale-micro-demo.git
   cd tunatale-micro-demo
   ```

2. **Set up the Python environment**
   ```bash
   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Upgrade pip and setuptools
   pip install --upgrade pip setuptools

   # Install project dependencies
   pip install -r requirements.txt

   # Install spaCy language model
   python -m spacy download en_core_web_sm
   ```

3. **Verify the installation**
   ```bash
   # Run tests to verify everything is working
   pytest
   ```

## Development Setup

For development, install additional development dependencies:

```bash
# Install development tools
pip install -r requirements-dev.txt  # Includes testing and linting tools

# Run the full test suite
pytest

# Run tests with coverage report
pytest --cov=.


# Run type checking
mypy .

# Run code formatter
black .
# Run linter
flake8
```

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# API Keys (if using external services)
# OPENAI_API_KEY=your_api_key_here

# Application Settings
LOG_LEVEL=INFO
```

3. **Run the application**
   ```bash
   python main.py --help  # See available commands
   ```

## Testing

### Automated Tests
Run the full test suite:
```bash
pytest tests/
```

### Manual Testing
To manually test story generation for a specific day:
```bash
# Generate story for day N (1-5)
python main.py generate-day N

# Force regenerate if needed
python main.py generate-day N --force
```

### Test Coverage
- Story generation and saving
- Vocabulary integration
- Collocation recycling
- Error handling
- File naming and organization

## CLI Commands

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
# Basic extraction
python main.py extract

# Extract with verbose output
python main.py extract --verbose
```

### Analyze Content
Analyze vocabulary and collocations in text:
```bash
# Analyze a specific file
python main.py analyze --file data/generated_content/story_day1_example.txt

# Analyze direct text input
python main.py analyze --text "The quick brown fox jumps over the lazy dog."

# Analyze by curriculum day number
python main.py analyze --day 1

# Get detailed analysis with more results
python main.py analyze --day 1 --verbose --top-words 20 --top-collocations 15
```

### Generate Content

#### Generate a Single Story
Generate a story with specific parameters:
```bash
python main.py story --learning-objective "Learn about space exploration" --cefr-level A2 --length 200
```

#### Generate a Story for a Specific Day
Generate a story based on the curriculum for a specific day:
```bash
# Generate story for day 1
python main.py generate-day 1

# Force regenerate even if story exists
python main.py generate-day 1 --force
```

### View Help
Get help for any command:
```bash
python main.py --help
python main.py extract --help
python main.py analyze --help
python main.py generate-day --help
```

## File Naming Convention

Generated story files follow this pattern:
- `story_day{number}_{topic}.txt` (e.g., `story_day1_space_exploration.txt`)
- Files are saved in the `data/generated_content/` directory
- Old files with the previous naming convention (`story_phaseN_*`) are automatically moved to `data/generated_content/archive/`

## Development

### Example Output

### Sample Story Generation
```
**Emma's Amazing Discovery**

Emma loved visiting the botanical garden with her grandfather every Saturday...

**VOCABULARY NOTES**
- **botanical**: related to plants
- **discovery**: finding something new

**REUSED COLLOCATIONS**
- very strange plants
- catch small bugs
- look at this
- plants that eat
- want to tell
```

## Vocabulary Files

The project uses two main vocabulary files for language learning content generation:

1. **`a2_categorized_vocabulary.json`** 
   - **Location**: `vocabulary/a2_categorized_vocabulary.json`
   - **Purpose**: This is the manually maintained source file containing A2-level vocabulary words organized by categories (nouns, verbs, adjectives, etc.).
   - **Usage**: Used as input to generate the flat vocabulary list.
   - **Format**: JSON object with category keys and arrays of words as values.

2. **`a2_flat_vocabulary.json`**
   - **Location**: `data/a2_flat_vocabulary.json`
   - **Purpose**: A flat, deduplicated, and alphabetically sorted list of all vocabulary words.
   - **Generation**: Automatically generated from the categorized vocabulary using `scripts/generate_vocabulary_set.py`.
   - **Usage**: Used by the application at runtime for vocabulary-related features.

### Updating Vocabulary

To update the vocabulary:

1. Edit the categorized vocabulary file:
   ```bash
   # To view the categorized vocabulary:
   code vocabulary/a2_categorized_vocabulary.json
   ```

2. Regenerate the flat vocabulary list:
   ```bash
   # Run the generation script
   python scripts/generate_vocabulary_set.py
   ```

3. Verify the changes:
   ```bash
   # Check the number of unique words
   python -c "import json; print(len(json.load(open('data/a2_flat_vocabulary.json'))))"
   ```

## Project Structure
```
.
├── data/                           # Contains all data files (generated and source)
│   ├── a2_flat_vocabulary.json        # Generated flat vocabulary list (A2 level)
│   ├── collocations.json             # Extracted collocations
│   ├── curriculum_processed.json      # Finalized, processed curriculum (used at runtime)
│   ├── curriculum_raw.json           # Raw curriculum data (intermediate format)
│   ├── mock_responses/               # Cached LLM responses for development
│   └── generated_content/            # Generated story files
│
├── prompts/                      # Template and prompt files
│   ├── curriculum_template.txt       # Simple curriculum template
│   └── heuristic_curriculum_template.example.txt  # Advanced curriculum template
│
├── scripts/                      # Utility scripts
│   ├── convert_curriculum.py        # Converts curriculum data to JSON
│   ├── extract_curriculum.py        # Extracts curriculum from text
│   └── generate_vocabulary_set.py   # Generates vocabulary set
│
├── tests/                        # Test files
└── ...
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
│   ├── curriculum_processed.json  # Processed curriculum (validated and structured)
│   ├── curriculum_raw.json       # Raw curriculum (generated by LLM)
│   ├── collocations.json        # Extracted collocations
│   └── generated_content/       # Generated stories
└── prompts/              # Prompt templates
    └── curriculum_template.txt
```

## Customization

### Modifying Prompts
Edit the files in the `prompts/` directory to customize the behavior of the AI:
- `curriculum_template.txt`: Controls how the curriculum is generated
- `story_prompt.txt`: Controls how stories are generated, including vocabulary and formatting

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
