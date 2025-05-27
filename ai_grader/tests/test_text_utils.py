import unittest
from unittest.mock import patch, MagicMock
from ai_grader.utils.text_utils import normalize_text, count_words, check_grammar_spelling

class TestTextUtils(unittest.TestCase):

    def test_normalize_text(self):
        self.assertEqual(normalize_text("  Hello   World  "), "hello world")
        self.assertEqual(normalize_text("MixedCase Test"), "mixedcase test")
        self.assertEqual(normalize_text("Already Normal"), "already normal")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text("   "), "")
        self.assertEqual(normalize_text(None), None)

    def test_count_words(self):
        self.assertEqual(count_words("Hello world"), 2)
        self.assertEqual(count_words("One"), 1)
        self.assertEqual(count_words("  Leading and   trailing spaces  "), 4)
        self.assertEqual(count_words(""), 0)
        self.assertEqual(count_words("   "), 0) # Should be 0 as split() on "   " yields empty list for some logic, or 1 if it yields ['']
        self.assertEqual(count_words(None), 0)


    @patch('ai_grader.utils.text_utils.language_tool_python.LanguageTool')
    def test_check_grammar_spelling(self, MockLanguageTool):
        # Configure the mock LanguageTool instance and its check method
        mock_tool_instance = MagicMock()
        MockLanguageTool.return_value = mock_tool_instance

        # Test case 1: No errors
        mock_tool_instance.check.return_value = []
        issues, count = check_grammar_spelling("This is a perfect sentence.")
        self.assertEqual(count, 0)
        self.assertEqual(issues, [])
        mock_tool_instance.check.assert_called_once_with("This is a perfect sentence.")
        mock_tool_instance.reset_mock() # Reset for the next test case

        # Test case 2: Some errors
        mock_match1 = MagicMock()
        mock_match1.message = "Spelling mistake"
        mock_match1.ruleId = "MORFOLOGIK_RULE_EN_US"
        mock_match1.replacements = ["correction1"]
        mock_match1.context = "This is a sentance with a misteke."
        mock_match1.offset = 10
        mock_match1.matchedText = "sentance"


        mock_match2 = MagicMock()
        mock_match2.message = "Grammar error"
        mock_match2.ruleId = "SOME_GRAMMAR_RULE"
        mock_match2.replacements = []
        mock_match2.context = "It have a grammar error."
        mock_match2.offset = 3
        mock_match2.matchedText = "have"

        mock_tool_instance.check.return_value = [mock_match1, mock_match2]
        text_with_errors = "This is a sentance with a misteke. It have a grammar error."
        issues, count = check_grammar_spelling(text_with_errors)
        self.assertEqual(count, 2)
        self.assertIn("Issue: 'Spelling mistake'. Did you mean: correction1? Context: ...This is a [sentance] with a misteke....", issues[0])
        self.assertIn("Issue: 'Grammar error'. Context: ...It [have] a grammar error....", issues[1])
        mock_tool_instance.check.assert_called_once_with(text_with_errors)
        mock_tool_instance.reset_mock()

        # Test case 3: Empty string input
        issues, count = check_grammar_spelling("")
        self.assertEqual(count, 0)
        self.assertEqual(issues, [])
        # Ensure check is not called for empty string if handled early
        # Depending on implementation, it might be called or not.
        # If it's designed to not call `check` for empty strings:
        mock_tool_instance.check.assert_not_called()
        mock_tool_instance.reset_mock()

        # Test case 4: Whitespace-only string input
        issues, count = check_grammar_spelling("   \t\n  ")
        self.assertEqual(count, 0)
        self.assertEqual(issues, [])
        mock_tool_instance.check.assert_not_called() # Assuming similar handling to empty string
        mock_tool_instance.reset_mock()

        # Test case 5: LanguageTool initialization fails (mock _get_language_tool to raise error)
        with patch('ai_grader.utils.text_utils._get_language_tool', side_effect=Exception("Tool init failed")):
            issues, count = check_grammar_spelling("Some text.")
            self.assertEqual(count, 1)
            self.assertIn("LanguageTool Error: Could not perform grammar/spelling check due to: Tool init failed.", issues[0])
        # Ensure the original mock is restored if necessary or re-patch for subsequent tests if _get_language_tool is module-level

    # Test to ensure the global _tool is initialized only once
    @patch('ai_grader.utils.text_utils.language_tool_python.LanguageTool')
    def test_check_grammar_spelling_tool_initialization_once(self, MockLanguageToolGlobal):
        # This test relies on the global _tool object behavior.
        # We need to reset the global _tool for this test to be meaningful in isolation.
        # This is a bit tricky as it involves manipulating module's global state.
        # One way is to add a reset function in text_utils or manually reset here.
        
        # For simplicity, we'll assume text_utils._tool can be set to None for testing.
        # This is an intrusive way to test, ideally the module manages this itself.
        import ai_grader.utils.text_utils
        ai_grader.utils.text_utils._tool = None # Reset global tool

        mock_tool_instance = MagicMock()
        MockLanguageToolGlobal.return_value = mock_tool_instance
        mock_tool_instance.check.return_value = []

        check_grammar_spelling("First call.")
        check_grammar_spelling("Second call.")
        
        MockLanguageToolGlobal.assert_called_once() # Tool should be initialized only on the first call
        self.assertEqual(mock_tool_instance.check.call_count, 2)

        # Clean up by resetting the tool again for other tests.
        ai_grader.utils.text_utils._tool = None


if __name__ == '__main__':
    unittest.main()
