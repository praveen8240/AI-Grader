import streamlit as st
from core.model import AIModel
from core.schemas import GradingInput, WordCountRange # EvaluationCriterion will be added later

# Load the model using st.cache_resource to avoid reloading on every interaction
@st.cache_resource
def load_model():
    """Loads and returns the AIModel instance."""
    # This is where you might load configurations or other resources for the model
    return AIModel()

model = load_model()

# --- Streamlit UI Setup ---
st.title("AI Student Response Grader 🤖📝")

st.markdown("""
Welcome to the AI Student Response Grader! 
Enter the question, the student's answer, and an optional reference answer. 
The AI will evaluate the response based on relevance, grammar, spelling, and word count.
""")

# Input Fields
with st.expander("Input Details", expanded=True):
    question_text = st.text_area("❓ Question Text", height=100, placeholder="e.g., What is the main theme of 'To Kill a Mockingbird'?")
    student_answer = st.text_area("✍️ Student's Answer", height=200, placeholder="e.g., The main theme is about justice and prejudice...")
    reference_answer = st.text_area("📚 Reference Answer (Optional)", height=100, placeholder="e.g., A comprehensive answer detailing themes like justice, prejudice, empathy, and loss of innocence...")

# Word Count Requirement
st.subheader("📊 Word Count Requirement (Optional)")
col1, col2 = st.columns(2)
with col1:
    min_words = st.number_input("Minimum Words", min_value=0, value=0, step=10, help="Set to 0 if no minimum.")
with col2:
    max_words = st.number_input("Maximum Words", min_value=0, value=0, step=10, help="Set to 0 if no maximum, or if only minimum is specified.")

# Submit Button and Processing Logic
if st.button("🚀 Evaluate Answer"):
    if not student_answer or student_answer.strip() == "":
        st.error("⚠️ Student Answer is required.")
    else:
        word_count_req = None
        if min_words > 0 or max_words > 0:
            # If max_words is 0, it means no upper limit (unless min_words is also 0)
            # If max_words > 0, it must be >= min_words
            if max_words > 0 and max_words < min_words:
                st.error("⚠️ Maximum words must be greater than or equal to minimum words if a maximum is set.")
                st.stop() # Halt execution for this callback
            
            actual_max_words = float('inf')
            if max_words > 0 : # User has specified a maximum
                actual_max_words = max_words
            elif min_words > 0 and max_words == 0: # User specified min, but not max, so max is infinite
                 actual_max_words = float('inf')
            elif min_words == 0 and max_words == 0: # No requirement
                word_count_req = None
            else: # Only max_words specified (min_words is 0)
                actual_max_words = max_words

            if min_words > 0 or max_words > 0: # Only create if there's some requirement
                word_count_req = WordCountRange(min_words=min_words, max_words=actual_max_words)


        grading_input = GradingInput(
            question_text=question_text,
            student_answer=student_answer,
            reference_answer=reference_answer if reference_answer.strip() else None,
            word_count_requirement=word_count_req,
            evaluation_criteria=None,  # V1: Not taking custom criteria from UI
            additional_metadata=None
        )

        try:
            with st.spinner("🧠 Evaluating your answer... Please wait."):
                result = model.evaluate(grading_input)

            st.subheader("🏆 Evaluation Results")

            # Display total score prominently
            # The definition of "total_score" from model.evaluate is the sum of achieved scores.
            # Max possible score is the sum of max_scores of active criteria.
            # For percentage, we'd need to know which criteria were active and their max_scores.
            # The result.sub_scores contains all active criteria.
            
            total_max_score_possible = sum(cs.max_score for cs in result.sub_scores)
            
            if total_max_score_possible > 0:
                percentage_score = (result.total_score / total_max_score_possible) * 100
                st.metric(
                    "Overall Grade", 
                    value=f"{percentage_score:.2f}%",
                    delta=f"{result.total_score:.2f} / {total_max_score_possible:.2f} points"
                )
            else: # Avoid division by zero if no criteria were scored or all max_scores are 0
                 st.metric("Overall Grade", value="N/A", delta=f"{result.total_score:.2f} points earned")


            if result.needs_teacher_review:
                st.warning("⚠️ This response may need teacher review.")
                if result.errors:
                    st.write("Reasons for review/errors:")
                    for err in result.errors:
                        st.error(f"👉 {err}")
            
            st.write("📝 **Overall Feedback:**")
            st.info(result.automated_feedback or "No specific feedback generated.")

            st.subheader("🧩 Detailed Sub-scores:")
            for criterion_score in result.sub_scores:
                # Use columns for better layout of score and progress bar
                col_score, col_progress = st.columns([0.7, 0.3])
                with col_score:
                    st.markdown(f"**{criterion_score.criterion_name}**: {criterion_score.score:.2f} / {criterion_score.max_score:.2f}")
                    if criterion_score.feedback:
                        st.caption(criterion_score.feedback)
                with col_progress:
                    if criterion_score.max_score > 0:
                        st.progress(criterion_score.score / criterion_score.max_score)
                    else: # Handle cases where max_score might be 0 to avoid division by zero
                        st.progress(0.0)
                st.divider()

        except Exception as e:
            st.error(f"🚨 An unexpected error occurred during evaluation: {str(e)}")
            st.exception(e) # Shows stack trace for debugging, can be removed for production

# To run the app: streamlit run ai_grader/app.py
if __name__ == '__main__':
    # The Streamlit script runs from top to bottom on every interaction.
    # The button click handles the logic within its 'if' block.
    pass
