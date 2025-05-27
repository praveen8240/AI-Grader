import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import numpy as np

# Assuming schemas and model are structured as previously discussed
from ai_grader.core.model import AIModel
from ai_grader.core.schemas import GradingInput, GradingOutput, CriterionScore, WordCountRange, EvaluationCriterion

# Mock SentenceTransformer before AIModel is imported for the first time by a test.
# This is to ensure that AIModel's __init__ which might call SentenceTransformer()
# uses the mock from the very beginning if 'autospec=True' or 'spec=True' is used broadly.
# However, for fine-grained control, we'll apply mocks directly to methods or within test methods.

class TestAIModel(unittest.TestCase):

    def setUp(self):
        """Setup common test data."""
        self.default_grading_input = GradingInput(
            question_text="Explain the theory of relativity.",
            student_answer="It's about E=mc^2.",
            reference_answer="The theory of relativity, developed by Albert Einstein, encompasses two interrelated theories: special relativity and general relativity. Special relativity applies to all physical phenomena in the absence of gravity. General relativity explains the law of gravitation and its relation to other forces of nature.",
            word_count_requirement=WordCountRange(min_words=50, max_words=150)
        )

    @patch('ai_grader.core.model.SentenceTransformer')
    def test_init_loads_model(self, MockSentenceTransformer):
        """Test that AIModel.__init__ attempts to load the SentenceTransformer."""
        mock_model_instance = MagicMock()
        MockSentenceTransformer.return_value = mock_model_instance
        model = AIModel()
        MockSentenceTransformer.assert_called_once_with('all-MiniLM-L6-v2')
        self.assertEqual(model.similarity_model, mock_model_instance)


    def test_preprocess_input(self):
        """Test the _preprocess_input method for text normalization."""
        # No mocking needed here as normalize_text is a direct import and tested separately
        # However, if AIModel.__init__ is problematic without mocks, this test might need adjustment.
        # For now, assuming we can instantiate AIModel or test _preprocess_input somewhat directly or with minimal init mocking.

        # To avoid issues with SentenceTransformer loading in __init__ for this specific test,
        # we can patch it just for the instantiation if needed, or rely on it being patchable for all tests.
        with patch('ai_grader.core.model.SentenceTransformer') as MockST:
            model = AIModel() # Instantiating AIModel

        input_data = GradingInput(
            question_text="  WHAT IS   Photosynthesis?  ",
            student_answer="  plants make food  ",
            reference_answer="  Sunlight energy conversion  "
        )
        processed = model._preprocess_input(input_data)
        self.assertEqual(processed.question_text, "what is photosynthesis?")
        self.assertEqual(processed.student_answer, "plants make food")
        self.assertEqual(processed.reference_answer, "sunlight energy conversion")

        input_data_no_ref = GradingInput(
            question_text="  Test  ",
            student_answer="  Ans  ",
        )
        processed_no_ref = model._preprocess_input(input_data_no_ref)
        self.assertEqual(processed_no_ref.reference_answer, None)


    @patch('ai_grader.core.model.SentenceTransformer')
    def test_calculate_relevance_score(self, MockSentenceTransformer):
        """Test _calculate_relevance_score with mocked sentence embeddings."""
        mock_similarity_model_instance = MagicMock()
        MockSentenceTransformer.return_value = mock_similarity_model_instance
        
        model = AIModel() # Model initializes with the mocked SentenceTransformer instance

        # Case 1: Valid student and reference answers, high similarity
        mock_similarity_model_instance.encode.side_effect = [np.array([1.0, 0.0]), np.array([1.0, 0.0])] # High similarity
        grading_input = self.default_grading_input
        # Ensure student_answer and reference_answer are pre-normalized for this test, or that _preprocess_input is called
        processed_input = model._preprocess_input(grading_input)

        score_obj = model._calculate_relevance_score(processed_input)
        self.assertIsInstance(score_obj, CriterionScore)
        self.assertEqual(score_obj.criterion_name, "Relevance")
        self.assertAlmostEqual(score_obj.score, 5.0) # Perfect similarity (1.0) * 5
        self.assertEqual(score_obj.max_score, 5.0)
        self.assertEqual(mock_similarity_model_instance.encode.call_count, 2)
        mock_similarity_model_instance.encode.reset_mock()

        # Case 2: Medium similarity
        mock_similarity_model_instance.encode.side_effect = [np.array([0.7, 0.3]), np.array([0.3, 0.7])] # Lower similarity
        score_obj = model._calculate_relevance_score(processed_input)
        self.assertTrue(0.0 <= score_obj.score <= 5.0) # Check if score is in range
        # The exact cosine similarity for these vectors would be (0.7*0.3 + 0.3*0.7) / (sqrt(0.7^2+0.3^2) * sqrt(0.3^2+0.7^2)) = (0.21+0.21)/(0.58) = 0.42/0.58 approx 0.72
        # Mapped score: 0.72 * 5 = 3.6 (approx)
        self.assertAlmostEqual(score_obj.score, 0.724 * 5, delta=0.1) # Allowing some delta
        mock_similarity_model_instance.encode.reset_mock()


        # Case 3: No reference answer
        input_no_ref = GradingInput(question_text="Q", student_answer="Ans", reference_answer=None)
        processed_no_ref = model._preprocess_input(input_no_ref)
        score_obj_no_ref = model._calculate_relevance_score(processed_no_ref)
        self.assertEqual(score_obj_no_ref.score, 0.0)
        self.assertIn("Reference answer not provided", score_obj_no_ref.feedback)
        mock_similarity_model_instance.encode.assert_not_called() # Should not attempt to encode
        mock_similarity_model_instance.encode.reset_mock()


        # Case 4: Empty student answer
        input_empty_student = GradingInput(question_text="Q", student_answer="", reference_answer="Ref")
        processed_empty_student = model._preprocess_input(input_empty_student)
        score_obj_empty_student = model._calculate_relevance_score(processed_empty_student)
        self.assertEqual(score_obj_empty_student.score, 0.0)
        self.assertIn("Student answer is empty", score_obj_empty_student.feedback)
        mock_similarity_model_instance.encode.assert_not_called() # Should not attempt to encode if student answer is empty
        mock_similarity_model_instance.encode.reset_mock()

        # Case 5: Embedding generation fails
        mock_similarity_model_instance.encode.side_effect = Exception("Embedding failed")
        score_obj_fail = model._calculate_relevance_score(processed_input) # uses valid processed_input from before
        self.assertEqual(score_obj_fail.score, 0.0)
        self.assertIn("Error calculating relevance: Embedding failed", score_obj_fail.feedback)
        mock_similarity_model_instance.encode.reset_mock()


    @patch('ai_grader.core.model.check_grammar_spelling') # Patch where it's used
    def test_calculate_grammar_spelling_score(self, mock_check_grammar):
        """Test _calculate_grammar_spelling_score with mocked grammar checks."""
        with patch('ai_grader.core.model.SentenceTransformer'): # Mock ST for AIModel instantiation
            model = AIModel()

        # Case 1: No errors
        mock_check_grammar.return_value = ([], 0)
        grading_input = self.default_grading_input
        processed_input = model._preprocess_input(grading_input)
        score_obj = model._calculate_grammar_spelling_score(processed_input)
        self.assertEqual(score_obj.criterion_name, "Grammar and Spelling")
        self.assertEqual(score_obj.score, 5.0)
        self.assertIn("No grammar or spelling issues found", score_obj.feedback)
        mock_check_grammar.assert_called_once_with(processed_input.student_answer)
        mock_check_grammar.reset_mock()

        # Case 2: Some errors (e.g., 3 errors)
        mock_check_grammar.return_value = (["Issue 1", "Issue 2", "Issue 3"], 3)
        score_obj = model._calculate_grammar_spelling_score(processed_input)
        self.assertEqual(score_obj.score, 3.0) # Based on current scoring logic (<=4 errors -> 3.0)
        self.assertIn("Found 3 grammar/spelling issue(s).", score_obj.feedback)
        self.assertIn("First few issues: Issue 1; Issue 2; Issue 3", score_obj.feedback)
        mock_check_grammar.reset_mock()
        
        # Case 3: Tool failure (e.g. Java missing)
        mock_check_grammar.return_value = (["LanguageTool Error: Java not found."], 1)
        score_obj = model._calculate_grammar_spelling_score(processed_input)
        self.assertEqual(score_obj.score, 0.0) # Critical tool error should result in 0
        self.assertIn("LanguageTool Error: Java not found.", score_obj.feedback)
        mock_check_grammar.reset_mock()

        # Case 4: Empty student answer
        empty_student_input = GradingInput(question_text="Q", student_answer="", reference_answer="Ref")
        processed_empty_input = model._preprocess_input(empty_student_input)
        score_obj = model._calculate_grammar_spelling_score(processed_empty_input)
        self.assertEqual(score_obj.score, 0.0)
        self.assertIn("Student answer is empty", score_obj.feedback)
        mock_check_grammar.assert_not_called() # Should not call if student answer is empty
        mock_check_grammar.reset_mock()

        # Case 5: check_grammar_spelling itself raises an exception (e.g. tool init failure propagated)
        mock_check_grammar.side_effect = Exception("Tool critical failure")
        score_obj = model._calculate_grammar_spelling_score(processed_input)
        self.assertEqual(score_obj.score, 0.0)
        self.assertIn("Could not perform grammar/spelling check: Tool critical failure", score_obj.feedback)
        mock_check_grammar.reset_mock()


    def test_check_word_count(self):
        """Test _check_word_count for various scenarios."""
        with patch('ai_grader.core.model.SentenceTransformer'): # Mock ST for AIModel instantiation
            model = AIModel()

        # Case 1: No word count requirement
        grading_input_no_wc = GradingInput("Q", "Ans", "Ref", word_count_requirement=None)
        processed_input_no_wc = model._preprocess_input(grading_input_no_wc)
        score_obj = model._check_word_count(processed_input_no_wc)
        self.assertIsNone(score_obj)

        # Case 2: Word count within range
        wc_req = WordCountRange(min_words=5, max_words=10)
        grading_input = GradingInput("Q", "This answer has seven words.", "Ref", word_count_requirement=wc_req)
        processed_input = model._preprocess_input(grading_input) # student_answer: "this answer has seven words." (5 words after normalize) -> actually "this answer has seven words." is 5 words.
                                                                # Let's use "one two three four five six seven" (7 words)
        grading_input.student_answer = "one two three four five six seven"
        processed_input = model._preprocess_input(grading_input)

        score_obj = model._check_word_count(processed_input)
        self.assertEqual(score_obj.criterion_name, "Word Count Adherence")
        self.assertEqual(score_obj.score, 5.0)
        self.assertIn(f"Word count (7) is within the required range ({wc_req.min_words}-{wc_req.max_words} words).", score_obj.feedback)

        # Case 3: Word count below minimum
        grading_input.student_answer = "Too short." # 2 words
        processed_input = model._preprocess_input(grading_input)
        score_obj = model._check_word_count(processed_input)
        self.assertEqual(score_obj.score, 2.5)
        self.assertIn(f"Word count (2) is below the minimum requirement of {wc_req.min_words} words.", score_obj.feedback)
        
        # Case 4: Word count above maximum
        grading_input.student_answer = "This answer is definitely way too long for the specified limits." # 11 words
        processed_input = model._preprocess_input(grading_input)
        score_obj = model._check_word_count(processed_input)
        self.assertEqual(score_obj.score, 2.5)
        self.assertIn(f"Word count (11) exceeds the maximum limit of {wc_req.max_words} words.", score_obj.feedback)

        # Case 5: Empty student answer, min_words > 0
        grading_input.student_answer = ""
        processed_input = model._preprocess_input(grading_input)
        score_obj = model._check_word_count(processed_input)
        self.assertEqual(score_obj.score, 2.5) # Penalized for being under
        self.assertIn(f"Word count (0) is below the minimum requirement of {wc_req.min_words} words.", score_obj.feedback)
        self.assertIn("The answer is empty.", score_obj.feedback)
        
        # Case 6: Invalid word count requirement (e.g. min_words > max_words)
        invalid_wc_req = WordCountRange(min_words=10, max_words=5)
        grading_input.word_count_requirement = invalid_wc_req
        grading_input.student_answer = "Some answer"
        processed_input = model._preprocess_input(grading_input)
        score_obj = model._check_word_count(processed_input)
        self.assertEqual(score_obj.score, 0.0)
        self.assertIn("Invalid word count requirement", score_obj.feedback)


    @patch('ai_grader.core.model.AIModel._check_word_count')
    @patch('ai_grader.core.model.AIModel._calculate_grammar_spelling_score')
    @patch('ai_grader.core.model.AIModel._calculate_relevance_score')
    @patch('ai_grader.core.model.SentenceTransformer') # For AIModel instantiation
    def test_evaluate_full_flow(self, MockST, mock_relevance, mock_grammar, mock_word_count):
        """Test the main evaluate method, mocking all sub-calculation methods."""
        model = AIModel()

        # Configure mocks to return predefined CriterionScore objects
        mock_relevance.return_value = CriterionScore("Relevance", 4.0, 5.0, "Good relevance.")
        mock_grammar.return_value = CriterionScore("Grammar and Spelling", 3.5, 5.0, "Few grammar issues.")
        mock_word_count.return_value = CriterionScore("Word Count Adherence", 5.0, 5.0, "Word count OK.")

        grading_input = self.default_grading_input # Uses default_grading_input which has a word count req
        
        output = model.evaluate(grading_input)

        self.assertIsInstance(output, GradingOutput)
        # Total score = 4.0 (relevance) + 3.5 (grammar) + 5.0 (word count) = 12.5
        self.assertAlmostEqual(output.total_score, 12.5)
        self.assertEqual(len(output.sub_scores), 3)
        self.assertIn("Relevance: Good relevance.", output.automated_feedback)
        self.assertIn("Grammar/Spelling: Few grammar issues.", output.automated_feedback)
        self.assertIn("Word Count: Word count OK.", output.automated_feedback)
        self.assertFalse(output.needs_teacher_review)
        self.assertIsNone(output.errors)

        mock_relevance.assert_called_once()
        mock_grammar.assert_called_once()
        mock_word_count.assert_called_once()
        
        # Test case: No word count requirement in input
        mock_relevance.reset_mock()
        mock_grammar.reset_mock()
        mock_word_count.reset_mock()
        mock_word_count.return_value = None # Simulate word count not being applicable

        grading_input_no_wc = GradingInput(
            question_text="Q", student_answer="A", reference_answer="R", word_count_requirement=None
        )
        output_no_wc = model.evaluate(grading_input_no_wc)
        # Total score = 4.0 (relevance) + 3.5 (grammar) = 7.5
        self.assertAlmostEqual(output_no_wc.total_score, 7.5)
        self.assertEqual(len(output_no_wc.sub_scores), 2) # Relevance and Grammar only
        self.assertNotIn("Word Count:", output_no_wc.automated_feedback)
        self.assertFalse(output_no_wc.needs_teacher_review)
        self.assertIsNone(output.errors)
        mock_word_count.assert_called_once() # _check_word_count is still called, but returns None


        # Test case: One component reports an error, needs_teacher_review = True
        mock_relevance.reset_mock()
        mock_grammar.reset_mock()
        mock_word_count.reset_mock()

        # Simulate relevance score indicating an error (e.g. reference answer missing)
        mock_relevance.return_value = CriterionScore("Relevance", 0.0, 5.0, "Reference answer not provided. Relevance could not be calculated.")
        mock_grammar.return_value = CriterionScore("Grammar and Spelling", 4.5, 5.0, "Good grammar.")
        mock_word_count.return_value = CriterionScore("Word Count Adherence", 5.0, 5.0, "Word count OK.")
        
        output_error = model.evaluate(grading_input)
        self.assertAlmostEqual(output_error.total_score, 9.5) # 0.0 + 4.5 + 5.0
        self.assertTrue(output_error.needs_teacher_review)
        self.assertIsNotNone(output_error.errors)
        self.assertEqual(len(output_error.errors), 1)
        self.assertIn("Reference answer not provided", output_error.errors[0])
        self.assertIn("Relevance: Reference answer not provided", output_error.automated_feedback)


if __name__ == '__main__':
    unittest.main()
