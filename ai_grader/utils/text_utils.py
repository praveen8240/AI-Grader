"""Utility functions for text processing."""

import re

def normalize_text(text: str) -> str:
    """
    Converts text to lowercase, removes leading/trailing whitespace,
    and replaces multiple consecutive whitespace characters with a single space.
    """
    if text is None:
        return None
    text = text.lower()
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def count_words(text: str) -> int:
    """Splits the text by whitespace and returns the count of words."""
    if text is None:
        return 0
    return len(text.split())

import language_tool_python
from typing import List, Tuple

# Global variable to hold the language tool instance to avoid reinitialization
# This can cause issues if the user wants to switch languages dynamically,
# but for 'en-US' it's fine and more efficient.
_tool = None

def _get_language_tool():
    """Initializes and returns the language tool instance."""
    global _tool
    if _tool is None:
        try:
            # print("Initializing language_tool_python for en-US...") # For debugging
            _tool = language_tool_python.LanguageTool('en-US')
            # print("Initialization complete.") # For debugging
        except Exception as e:
            # print(f"Error initializing language_tool_python: {e}") # For debugging
            # This might happen if language model download fails or other setup issues.
            # Return a dummy tool or raise an exception depending on desired error handling.
            # For now, if it fails, subsequent calls will also fail.
            # Consider a more robust fallback or error reporting.
            raise e # Re-raise the exception to make the problem visible
    return _tool

def check_grammar_spelling(text: str) -> Tuple[List[str], int]:
    """
    Checks the text for grammar and spelling issues using language_tool_python.

    Returns:
        A tuple containing:
        - A list of strings, where each string is a description of an issue found.
        - An integer representing the total count of issues found.
    """
    if not text or text.isspace(): # Handle empty or whitespace-only text
        return [], 0

    issues_descriptions = []
    try:
        tool = _get_language_tool()
        matches = tool.check(text)
        for match in matches:
            # Construct a more informative message if possible
            message = f"Issue: '{match.message}'."
            if match.ruleId == 'MORFOLOGIK_RULE_EN_US' and match.replacements and match.message.startswith('Possible spelling mistake'):
                 message += f" Did you mean: {', '.join(match.replacements[:3])}?" # Suggest replacements
            elif match.context:
                context_start = max(0, match.offset - 20)
                context_end = min(len(text), match.offset + len(match.matchedText) + 20)
                highlighted_error = text[match.offset:match.offset+len(match.matchedText)]
                context_snippet = f"...{text[context_start:match.offset]}[{highlighted_error}]{text[match.offset+len(match.matchedText):context_end]}..."
                message += f" Context: {context_snippet}"
            issues_descriptions.append(message)
        return issues_descriptions, len(matches)
    except Exception as e:
        # print(f"Error during grammar/spelling check: {e}") # For debugging
        # If the tool failed to initialize, this will catch it.
        # Return empty list and 0 count, or a specific error message.
        error_message = f"LanguageTool Error: Could not perform grammar/spelling check due to: {str(e)}. Please ensure Java is installed and language model can be downloaded."
        return [error_message], 1 # Report as one major issue
