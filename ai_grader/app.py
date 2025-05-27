import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import BadRequest
from dataclasses import asdict

from ai_grader.core.model import AIModel
from ai_grader.core.schemas import GradingInput, WordCountRange

# 1. Flask App Initialization & Logging Configuration
app = Flask(__name__, template_folder='templates', static_folder='static')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 2. AIModel Initialization
ai_model: AIModel | None = None
try:
    ai_model = AIModel()
    logging.info("AIModel loaded successfully.")
except Exception as e:
    logging.critical(f"Failed to load AIModel: {e}", exc_info=True)
    ai_model = None # Ensure it's None if loading failed

# 3. Route for Index Page
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

# 4. Route for Evaluation
@app.route('/evaluate', methods=['POST'])
def evaluate_answer():
    """Handles the student answer evaluation requests."""
    if not ai_model:
        logging.error("Evaluation request received but AIModel is not loaded.")
        return jsonify({"error": "AI Model not loaded. Cannot process request."}), 500

    try:
        data = request.form
        logging.info(f"Received evaluation request with data: {data}")

        # Input Validation
        student_answer = data.get('student_answer')
        question_text = data.get('question_text')

        if not student_answer or not student_answer.strip():
            logging.warning("Validation error: Student answer is required.")
            return jsonify({"error": "Student answer is required."}), 400
        
        if not question_text or not question_text.strip():
            logging.warning("Validation error: Question text is required.")
            return jsonify({"error": "Question text is required."}), 400

        min_words_str = data.get('min_words', '0')
        max_words_str = data.get('max_words', '0')

        try:
            min_words = int(min_words_str) if min_words_str and min_words_str.strip() else 0
            max_words = int(max_words_str) if max_words_str and max_words_str.strip() else 0
        except ValueError:
            logging.warning("Validation error: Word counts must be valid integers.", exc_info=True)
            return jsonify({"error": "Word counts must be valid integers."}), 400

        if min_words < 0:
            logging.warning("Validation error: Minimum words cannot be negative.")
            return jsonify({"error": "Minimum words cannot be negative."}), 400
        if max_words < 0:
            logging.warning("Validation error: Maximum words cannot be negative.")
            return jsonify({"error": "Maximum words cannot be negative."}), 400
        
        # If max_words is specified (not 0), ensure max_words >= min_words
        if max_words != 0 and max_words < min_words:
            logging.warning(f"Validation error: Maximum words ({max_words}) must be greater than or equal to minimum words ({min_words}).")
            return jsonify({"error": f"Maximum words ({max_words}) must be greater than or equal to minimum words ({min_words})."}), 400

        # Construct WordCountRange
        word_count_requirement = None
        if min_words > 0 or max_words > 0:
            actual_max_words = float('inf') if max_words == 0 else max_words
            word_count_requirement = WordCountRange(min_words=min_words, max_words=actual_max_words)
            logging.info(f"Constructed WordCountRange: {word_count_requirement}")


        # Construct GradingInput
        reference_answer = data.get('reference_answer')
        if reference_answer and not reference_answer.strip():
            reference_answer = None # Treat empty string as None

        grading_input = GradingInput(
            question_text=question_text,
            student_answer=student_answer,
            reference_answer=reference_answer,
            word_count_requirement=word_count_requirement,
            evaluation_criteria=None, # V2: Not taking custom criteria from UI yet
            additional_metadata=None
        )
        logging.info(f"Constructed GradingInput: {grading_input.student_answer[:50]}...") # Log snippet

        # Call AI Model
        evaluation_result = ai_model.evaluate(grading_input)
        logging.info(f"Evaluation result: {evaluation_result.total_score}, Review needed: {evaluation_result.needs_teacher_review}")

        # Convert to dict and return JSON
        result_dict = asdict(evaluation_result)
        return jsonify(result_dict)

    except BadRequest as e: # Werkzeug's BadRequest for specific HTTP errors
        logging.warning(f"Bad request during evaluation: {e.description}", exc_info=True)
        return jsonify({"error": e.description}), e.code # e.code should be 400
    except Exception as e:
        logging.error(f"An unexpected error occurred during evaluation: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred on the server."}), 500

# 5. Main Block for Development Server
if __name__ == '__main__':
    # Note: Setting host='0.0.0.0' makes the server accessible externally.
    # For development, '127.0.0.1' (default) is often preferred for security.
    # Using 0.0.0.0 as requested.
    app.run(host='0.0.0.0', port=5000, debug=True)
