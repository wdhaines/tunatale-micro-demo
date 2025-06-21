def count_words(text: str) -> int:
    """
    Count the number of words in a string.
    
    Args:
        text: The text to count words in
        
    Returns:
        int: The number of words in the text
    """
    if not text or not text.strip():
        return 0
    # Split on whitespace and filter out empty strings
    return len([word for word in text.split() if word.strip()])
