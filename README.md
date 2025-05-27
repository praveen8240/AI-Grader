# AI Student Response Grader

The AI Student Response Grader is a Python application designed to automatically evaluate student-written responses. It leverages Natural Language Processing (NLP) techniques to assess answers based on relevance to a reference answer, grammar and spelling accuracy, and adherence to word count requirements, providing both a quantitative score and qualitative feedback.

## Overview

This project provides an automated system for grading student answers. Key functionalities include:

- **Relevance Scoring**: Comparing the student's answer semantically against a provided reference answer.
- **Grammar and Spelling Checks**: Identifying and suggesting corrections for grammatical errors and misspellings.
- **Word Count Adherence**: Validating if the student's answer meets specified word count limits.
- **Automated Feedback**: Generating feedback based on the evaluation criteria.

The system utilizes pre-trained NLP models for sentence similarity and a dedicated tool for grammar/spelling analysis.

## Features

- **Semantic Relevance Scoring**: Utilizes sentence embeddings to compare the student's answer with a teacher-provided reference answer.
- **Grammar and Spelling Correction**: Integrates `language-tool-python` to detect errors and provide suggestions.
- **Word Count Validation**: Checks if the answer length is within the specified minimum and maximum word counts.
- **Aggregated Scoring**: Provides a total score based on achieved points across criteria.
- **Detailed Sub-scores**: Offers scores for each evaluation criterion (relevance, grammar, word count).
- **Automated Feedback Generation**: Consolidates feedback from all evaluation modules.
- **Flag for Teacher Review**: Marks responses that encountered issues during automated grading (e.g., missing reference answer, tool errors) for manual review.
- **Simple Web Interface**: A Flask-based UI for easy interaction, input, and visualization of results.

## Project Structure

Assuming the repository is cloned into a directory (e.g., `ai_grader_project_root`), the structure is:

- `ai_grader_project_root/`
  - `ai_grader/`: Main Python package.
    - `core/`: Contains the core AI model logic (`model.py`) and data structures/schemas (`schemas.py`).
    - `utils/`: Includes utility functions for text processing (`text_utils.py`).
    - `tests/`: Contains unit tests for the application modules.
    - `app.py`: The main Flask web application.
    - `templates/`: HTML templates for the Flask web interface.
    - `static/`: Static files (CSS, JavaScript) for the Flask web interface.
    - `streamlit_app_backup.py`: Backup of the previous Streamlit application (can be removed if not needed).
    - `__init__.py` (and in subdirectories like `core`, `utils`, `tests`)
  - `requirements.txt`: Lists all Python dependencies for the project. (Located in the repository root)
  - `README.md`: This file. (Located in the repository root)

## Setup Instructions

### Prerequisites

- **Python**: Version 3.9 or higher is recommended.
  - Download from [python.org](https://www.python.org/downloads/)
- **Java Development Kit (JDK)**: Version 8 or higher. This is required by `language-tool-python`.
  - To check if Java is installed, open a terminal or command prompt and type: `java -version`
  - If not installed, you can download it from [Adoptium (OpenJDK)](https://adoptium.net/) or [Oracle JDK](https://www.oracle.com/java/technologies/downloads/).

### Installation Steps

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/praveen8240/AI-Grader.git ai_grader_project_root
    ```

2.  **Navigate to the project's root directory**:

    ```bash
    cd ai_grader_project_root
    # This is the directory containing this README.md, requirements.txt, and the inner 'ai_grader' package.
    ```

3.  **Create a Python virtual environment**:

    ```bash
    python -m venv venv
    # Or for Python 3 explicitly: python3 -m venv venv
    ```

4.  **Activate the virtual environment**:

    - On Windows:
      ```bash
      venv\Scripts\activate
      ```
    - On macOS and Linux:
      ```bash
      source venv/bin/activate
      ```

5.  **Install dependencies**:
    (Ensure you are in the repository root directory where `requirements.txt` is located)

    ```bash
    pip install -r requirements.txt
    ```

    This will install all necessary libraries. `language-tool-python` may download language model files on its first run, which requires an internet connection.

    **Note on TensorFlow/Keras Compatibility:** This project uses `sentence-transformers`, which relies on the `transformers` library. Some versions of `transformers` require a Keras 2.x interface when used with TensorFlow. The `requirements.txt` file includes `tf-keras` to ensure this compatibility and help avoid issues with Keras 3. If you have Keras 3 installed globally, the local project environment created with `requirements.txt` should manage this.

## Running the Application

Ensure your virtual environment is activated and you are in the **repository root directory** (e.g., `ai_grader_project_root/`) before running the commands.

### Unit Tests

To run the suite of unit tests:

```bash
python -m unittest discover ai_grader/tests
```

### Web Interface

To run the Flask web interface:

**Option 1: Using the `flask` command (recommended for development)**

1. Set the Flask application environment variables (do this once per terminal session, or set permanently):
   - On macOS/Linux:
     ```bash
     export FLASK_APP=ai_grader/app.py
     export FLASK_ENV=development
     ```
   - On Windows (Command Prompt):
     ```cmd
     set FLASK_APP=ai_grader/app.py
     set FLASK_ENV=development
     ```
   - On Windows (PowerShell):
     ```powershell
     $env:FLASK_APP = "ai_grader/app.py"
     $env:FLASK_ENV = "development"
     ```
2. Run the Flask development server:
   ```bash
   flask run
   ```
   This will typically start the server on `http://127.0.0.1:5000/`.

**Option 2: Running the Python script directly**
You can also run the application by executing the `app.py` script directly (as it includes `app.run()` configured to run on `0.0.0.0:5000`):

```bash
python ai_grader/app.py
```

This will start the server, and the output will indicate the address (e.g., `Running on http://0.0.0.0:5000/`). You can access it via `http://127.0.0.1:5000/` in your browser.

## Using the Web Interface

The web interface provides the following fields for input:

- **❓ Question Text**: The original question posed to the student.
- **✍️ Student's Answer**: The answer submitted by the student. (This field is required for evaluation).
- **📚 Reference Answer (Optional)**: An ideal or model answer for comparison. If not provided, the relevance score will be 0 or not calculated.
- **Minimum Words**: The minimum number of words required for the student's answer. Set to 0 if there is no minimum.
- **Maximum Words**: The maximum number of words allowed for the student's answer. Set to 0 if there is no maximum, or if only a minimum is specified (implying no upper limit).

After submitting the input by clicking "🚀 Evaluate Answer", the results will be displayed:

- **Overall Grade**: A percentage score representing the overall performance, along with the total points achieved versus the maximum possible points from the scored criteria.
- **Teacher Review Flag**: A warning (⚠️) may appear if the system encountered issues during evaluation (e.g., missing reference answer, critical tool errors). Specific errors or reasons for review will be listed.
- **Overall Feedback**: A compiled text summary of feedback from all evaluation modules.
- **Detailed Sub-scores**:
  - Each criterion (e.g., Relevance, Grammar and Spelling, Word Count Adherence) will have its own section.
  - Displays the **score achieved / maximum possible score** for that criterion.
  - Includes specific **feedback text** related to that criterion's evaluation.
  - A **progress bar** visually represents the score relative to the maximum for that criterion.

## Dependencies

The project relies on several key Python libraries:

- **Flask**: For creating the web application framework and interface.
- **sentence-transformers**: For generating sentence embeddings used in semantic similarity calculations.
- **scikit-learn**: For utility functions like cosine similarity.
- **numpy**: For numerical operations, especially with embeddings.
- **language-tool-python**: For checking grammar and spelling.
- **tf-keras**: Provides Keras 2.x API compatibility for TensorFlow, used by some versions of the `transformers` library.

Refer to `requirements.txt` for a complete list of dependencies and their specific versions.
