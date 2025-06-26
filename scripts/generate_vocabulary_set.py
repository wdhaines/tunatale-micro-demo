import json
from pathlib import Path

def generate_vocabulary_set():
    # Path to the input vocabulary file
    input_file = Path(__file__).parent.parent / 'vocabulary' / 'a2_background_vocabulary.json'
    
    # Path to the output file
    output_file = Path(__file__).parent.parent / 'vocabulary' / 'a2_vocabulary_set.json'
    
    # Read the input JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        vocabulary = json.load(f)
    
    # Flatten all words into a single list and convert to lowercase
    flattened_words = []
    for word_list in vocabulary.values():
        for word in word_list:
            # Handle multi-word phrases (like "as long as") by splitting them
            flattened_words.extend(w.lower() for w in word.split())
    
    # Remove duplicates while preserving order
    unique_words = []
    seen = set()
    for word in flattened_words:
        if word not in seen:
            seen.add(word)
            unique_words.append(word)
    
    # Sort the words alphabetically
    unique_words.sort()
    
    # Write the flattened vocabulary to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique_words, f, indent=2)
    
    print(f"Successfully created {output_file} with {len(unique_words)} unique words.")

if __name__ == "__main__":
    generate_vocabulary_set()
