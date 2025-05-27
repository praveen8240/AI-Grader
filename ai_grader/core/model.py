"""Core AI Model for student response evaluation."""

from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ai_grader.core.schemas import GradingInput, GradingOutput, CriterionScore
from ai_grader.utils.text_utils import normalize_text, check_grammar_spelling, count_words

class AIModel:
    """Handles the AI-powered grading of student responses."""

    def __init__(self):
        """Initializes the AIModel."""
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')

    def _preprocess_input(self, grading_input: GradingInput) -> GradingInput:
        """Normalizes the text fields in the GradingInput object."""
        processed_input = GradingInput(
            question_text=normalize_text(grading_input.question_text),
            student_answer=normalize_text(grading_input.student_answer),
            reference_answer=normalize_text(grading_input.reference_answer) if grading_input.reference_answer else None,
            evaluation_criteria=grading_input.evaluation_criteria,
            word_count_requirement=grading_input.word_count_requirement,
            additional_metadata=grading_input.additional_metadata
        )
        return processed_input

    def _calculate_relevance_score(self, processed_input: GradingInput) -> CriterionScore | None:
        """Calculates the relevance score based on semantic similarity."""
        if not processed_input.reference_answer:
            return CriterionScore(
                criterion_name="Relevance",
                score=0.0,
                max_score=5.0,
                feedback="Reference answer not provided. Relevance could not be calculated."
            )

        if not processed_input.student_answer:
            return CriterionScore(
                criterion_name="Relevance",
                score=0.0,
                max_score=5.0,
                feedback="Student answer is empty. Relevance could not be calculated."
            )

        try:
            student_embedding = self.similarity_model.encode(processed_input.student_answer, convert_to_tensor=False)
            reference_embedding = self.similarity_model.encode(processed_input.reference_answer, convert_to_tensor=False)

            # Ensure embeddings are 2D arrays for cosine_similarity
            student_embedding = np.asarray(student_embedding).reshape(1, -1)
            reference_embedding = np.asarray(reference_embedding).reshape(1, -1)

            similarity = cosine_similarity(student_embedding, reference_embedding)[0][0]

            # Map similarity (0 to 1) to a 0-5 scale
            mapped_score = round(similarity * 5, 2)

            return CriterionScore(
                criterion_name="Relevance",
                score=mapped_score,
                max_score=5.0,
                feedback="Relevance score based on semantic similarity."
            )
        except Exception as e:
            # Handle cases where embedding generation might fail unexpectedly
            return CriterionScore(
                criterion_name="Relevance",
                score=0.0,
                max_score=5.0,
                feedback=f"Error calculating relevance: {str(e)}"
            )

    def _calculate_grammar_spelling_score(self, processed_input: GradingInput) -> CriterionScore:
        """Calculates the grammar and spelling score."""
        if not processed_input.student_answer or processed_input.student_answer.isspace():
            return CriterionScore(
                criterion_name="Grammar and Spelling",
                score=0.0,
                max_score=5.0,
                feedback="Student answer is empty. Grammar and spelling could not be assessed."
            )

        try:
            issues, issue_count = check_grammar_spelling(processed_input.student_answer)
        except Exception as e: # Catch potential errors from language_tool initialization
             return CriterionScore(
                criterion_name="Grammar and Spelling",
                score=0.0,
                max_score=5.0,
                feedback=f"Could not perform grammar/spelling check: {str(e)}"
            )


        score = 0.0
        if issue_count == 0:
            score = 5.0
            feedback = "No grammar or spelling issues found."
        elif issue_count <= 2:
            score = 4.0
        elif issue_count <= 4:
            score = 3.0
        elif issue_count <= 6:
            score = 2.0
        elif issue_count <= 8:
            score = 1.0
        else: # issue_count > 8
            score = 0.0

        if issue_count > 0:
            feedback = f"Found {issue_count} grammar/spelling issue(s)."
            if issues: # issues might contain a general error message from the tool itself
                # Check if the first issue is the specific LanguageTool Error
                if issues[0].startswith("LanguageTool Error:"):
                    feedback = issues[0] # Use the specific error from the tool
                    score = 0.0 # Override score if tool failed critically
                else:
                    feedback += f" First few issues: {'; '.join(issues[:3])}"


        return CriterionScore(
            criterion_name="Grammar and Spelling",
            score=score,
            max_score=5.0,
            feedback=feedback
        )

    def evaluate(self, grading_input: GradingInput) -> GradingOutput:
        """
        Evaluates the student's answer based on various criteria.
        """
        processed_input = self._preprocess_input(grading_input)

        sub_scores_list: List[CriterionScore] = []
        feedback_list: List[str] = []
        total_score_achieved: float = 0.0
        total_max_score: float = 0.0 # This will be the sum of max_scores of active criteria
        errors_list: List[str] = []


        # Call Relevance Scoring
        try:
            relevance_score_obj = self._calculate_relevance_score(processed_input)
            if relevance_score_obj: # Should always return an object or None
                sub_scores_list.append(relevance_score_obj)
                total_score_achieved += relevance_score_obj.score
                total_max_score += relevance_score_obj.max_score
                if relevance_score_obj.feedback:
                    feedback_list.append(f"Relevance: {relevance_score_obj.feedback}")
                if "Error calculating relevance" in relevance_score_obj.feedback or \
                   "Reference answer not provided" in relevance_score_obj.feedback:
                    errors_list.append(relevance_score_obj.feedback)
        except Exception as e:
            error_msg = f"Critical error in relevance scoring: {str(e)}"
            errors_list.append(error_msg)
            feedback_list.append(error_msg)
            # Optionally add a placeholder CriterionScore to sub_scores_list
            sub_scores_list.append(CriterionScore("Relevance", 0, 5.0, error_msg))
            total_max_score += 5.0 # Assuming 5.0 is the standard max for relevance

        # Call Grammar/Spelling Scoring
        try:
            grammar_score_obj = self._calculate_grammar_spelling_score(processed_input)
            # This method is designed to always return a CriterionScore object
            sub_scores_list.append(grammar_score_obj)
            total_score_achieved += grammar_score_obj.score
            total_max_score += grammar_score_obj.max_score
            if grammar_score_obj.feedback:
                feedback_list.append(f"Grammar/Spelling: {grammar_score_obj.feedback}")
            if "LanguageTool Error" in grammar_score_obj.feedback or \
               "Could not perform grammar/spelling check" in grammar_score_obj.feedback :
                errors_list.append(grammar_score_obj.feedback)
        except Exception as e:
            error_msg = f"Critical error in grammar/spelling scoring: {str(e)}"
            errors_list.append(error_msg)
            feedback_list.append(error_msg)
            sub_scores_list.append(CriterionScore("Grammar and Spelling", 0, 5.0, error_msg))
            total_max_score += 5.0 # Assuming 5.0 is the standard max

        # Call Word Count Check
        try:
            word_count_obj = self._check_word_count(processed_input)
            if word_count_obj: # Returns None if not applicable
                sub_scores_list.append(word_count_obj)
                total_score_achieved += word_count_obj.score
                total_max_score += word_count_obj.max_score
                if word_count_obj.feedback:
                    feedback_list.append(f"Word Count: {word_count_obj.feedback}")
                if "Invalid word count requirement" in word_count_obj.feedback:
                     errors_list.append(word_count_obj.feedback)
        except Exception as e:
            error_msg = f"Critical error in word count checking: {str(e)}"
            errors_list.append(error_msg)
            feedback_list.append(error_msg)
            # If word count was expected, add a placeholder
            if grading_input.word_count_requirement:
                sub_scores_list.append(CriterionScore("Word Count Adherence", 0, 5.0, error_msg))
                total_max_score += 5.0


        # Compile Automated Feedback
        compiled_feedback_string = "\n".join(feedback_list)
        if not feedback_list:
            compiled_feedback_string = "Evaluation complete. No specific feedback items generated."

        # Set needs_teacher_review (currently False)
        needs_teacher_review = False
        if errors_list: # If any module reported an error, flag for review.
            needs_teacher_review = True


        # For GradingOutput, total_score is the sum of achieved scores from active criteria
        # The percentage can be calculated by the frontend/reporting layer if needed,
        # using total_score_achieved and total_max_score.

        return GradingOutput(
            total_score=total_score_achieved,
            sub_scores=sub_scores_list,
            automated_feedback=compiled_feedback_string,
            needs_teacher_review=needs_teacher_review,
            errors=errors_list if errors_list else None
        )

    def _check_word_count(self, processed_input: GradingInput) -> CriterionScore | None:
        """Checks if the student's answer adheres to the word count requirements."""
        if not processed_input.word_count_requirement:
            return None # Not applicable if no requirement is set

        min_words = processed_input.word_count_requirement.min_words
        max_words = processed_input.word_count_requirement.max_words

        # Handle cases where min_words or max_words might not be properly set or are invalid
        if min_words is None or max_words is None or min_words < 0 or max_words < 0 or min_words > max_words:
            # Or, could raise a ValueError if the requirement itself is invalid
            return CriterionScore(
                criterion_name="Word Count Adherence",
                score=0.0,
                max_score=5.0,
                feedback="Invalid word count requirement provided (e.g., min/max not set, negative, or min > max)."
            )

        student_answer_text = processed_input.student_answer if processed_input.student_answer else ""
        word_count = count_words(student_answer_text)

        score = 0.0
        feedback = ""

        if min_words <= word_count <= max_words:
            score = 5.0
            feedback = f"Word count ({word_count}) is within the required range ({min_words}-{max_words} words)."
        elif word_count < min_words:
            score = 2.5 # Penalty for being under
            feedback = f"Word count ({word_count}) is below the minimum requirement of {min_words} words."
        else: # word_count > max_words
            score = 2.5 # Penalty for being over
            feedback = f"Word count ({word_count}) exceeds the maximum limit of {max_words} words."
        
        # Consider if student answer is empty and it's below min_words (unless min_words is 0)
        if not student_answer_text and min_words > 0:
             feedback += " The answer is empty."


        return CriterionScore(
            criterion_name="Word Count Adherence",
            score=score,
            max_score=5.0,
            feedback=feedback
        )
