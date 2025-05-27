document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('grader-form');
    const resultsContainer = document.getElementById('results-container');
    const submitButton = form.querySelector('button[type="submit"]');
const originalButtonText = submitButton.textContent;
    // Result elements that need to be updated
    const totalScoreEl = document.getElementById('total-score');
    const teacherReviewFlagEl = document.getElementById('teacher-review-flag');
    const evaluationErrorsEl = document.getElementById('evaluation-errors');
    const overallFeedbackEl = document.getElementById('overall-feedback');
    const subScoresDetailsEl = document.getElementById('sub-scores-details');

    if (!form) {
        console.error("Grader form not found!");
        return;
    }
function setLoadingState(isLoading) {
    if (isLoading) {
        submitButton.disabled = true;
        submitButton.textContent = 'Evaluating...';
        submitButton.style.cursor = 'not-allowed';
        submitButton.style.opacity = '0.7';
    } else {
        submitButton.disabled = false;
        submitButton.textContent = originalButtonText;
        submitButton.style.cursor = 'pointer';
        submitButton.style.opacity = '1';
    }
}
    form.addEventListener('submit', function (event) {
        event.preventDefault(); // Prevent default form submission
        setLoadingState(true);

        // 1. Clear previous results and hide container / show loading state
        resultsContainer.style.display = 'none';
        totalScoreEl.textContent = 'N/A';
        teacherReviewFlagEl.textContent = ''; // Clear previous flag
        evaluationErrorsEl.innerHTML = '';    // Clear previous errors
        overallFeedbackEl.textContent = 'N/A';
        subScoresDetailsEl.innerHTML = '<p>Processing...</p>'; // Show loading for sub-scores

        // 2. Get form data
        const formData = new FormData(form);
        // Log form data for debugging (optional)
        // for (var pair of formData.entries()) {
        //     console.log(pair[0]+ ': ' + pair[1]); 
        // }

        // 3. Fetch API Call
        fetch('/evaluate', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            // Check if response is ok, if not, try to parse error from JSON body
            if (!response.ok) {
                return response.json().then(errData => {
                    // If server returns a JSON with an 'error' field, use that
                    throw new Error(errData.error || `Server error: ${response.status} ${response.statusText}`);
                }).catch(() => {
                    // If server error response is not JSON or no specific message from server JSON
                    throw new Error(`Server error: ${response.status} ${response.statusText}`);
                });
            }
            return response.json(); // Parse successful JSON response
        })
        .then(data => {
            // Handle cases where the server responds with 200 OK, but there's an application-level error
            // (e.g., validation handled by server returning a JSON with an error field, though typically these are 400s)
            if (data.error) {
                evaluationErrorsEl.innerHTML = `<p class="error-message">Application Error: ${data.error}</p>`;
                resultsContainer.style.display = 'block'; // Show container to display the error
                subScoresDetailsEl.innerHTML = ''; // Clear loading message
                return;
            }

            // 4. Update HTML with results
            // Overall Score: Calculate percentage if possible
            let totalMaxScorePossible = 0;
            if (data.sub_scores && data.sub_scores.length > 0) {
                data.sub_scores.forEach(sc => {
                    totalMaxScorePossible += parseFloat(sc.max_score);
                });
            }

            if (totalMaxScorePossible > 0) {
                const percentageScore = (parseFloat(data.total_score) / totalMaxScorePossible) * 100;
                totalScoreEl.textContent = `${percentageScore.toFixed(2)}% (${parseFloat(data.total_score).toFixed(2)} / ${totalMaxScorePossible.toFixed(2)} points)`;
            } else {
                totalScoreEl.textContent = `${parseFloat(data.total_score).toFixed(2)} points (Max score not determinable or 0)`;
            }
            
            // Teacher Review Flag and Errors
            if (data.needs_teacher_review) {
                teacherReviewFlagEl.textContent = "⚠️ This response may need teacher review.";
            } else {
                teacherReviewFlagEl.textContent = ""; // Clear if not needed
            }

            if (data.errors && data.errors.length > 0) {
                let errorMessages = data.errors.map(err => `<p class="error-detail">${err}</p>`).join('');
                evaluationErrorsEl.innerHTML = errorMessages;
            } else {
                evaluationErrorsEl.innerHTML = ""; // Clear if no errors
            }

            // Overall Feedback
            overallFeedbackEl.textContent = data.automated_feedback || "No specific feedback provided.";

            // Sub-scores Details
            if (data.sub_scores && data.sub_scores.length > 0) {
                let subScoresHtml = '<ul>';
                data.sub_scores.forEach(sc => {
                    const score = parseFloat(sc.score);
                    const maxScore = parseFloat(sc.max_score);
                    const progress = maxScore > 0 ? (score / maxScore) * 100 : 0;

                    subScoresHtml += `
                        <li>
                            <strong>${sc.criterion_name}:</strong> ${score.toFixed(2)} / ${maxScore.toFixed(2)}
                            <div class="progress-bar-container">
                                <div class="progress-bar" style="width: ${progress.toFixed(2)}%;"></div>
                            </div>
                            ${sc.feedback ? `<small class="feedback-text"><em>Feedback: ${sc.feedback}</em></small>` : ''}
                        </li>`;
                });
                subScoresHtml += '</ul>';
                subScoresDetailsEl.innerHTML = subScoresHtml;
            } else {
                subScoresDetailsEl.innerHTML = '<p>No sub-scores available.</p>';
            }
            
            resultsContainer.style.display = 'block'; // Make results visible
            setLoadingState(false);
        })
        .catch(error => {
            // 5. Error Display for fetch/network errors or errors thrown from response.ok check
            console.error('Evaluation Process Error:', error);
            // Ensure evaluationErrorsEl is the primary place for error messages
            evaluationErrorsEl.innerHTML = `<p class="error-message">Failed to evaluate. ${error.message}</p>`;
            // Clear other fields that might show partial/stale data
            totalScoreEl.textContent = 'Error';
            overallFeedbackEl.textContent = 'Error during processing.';
            subScoresDetailsEl.innerHTML = ''; // Clear loading/previous sub-scores
            teacherReviewFlagEl.textContent = '';


            resultsContainer.style.display = 'block'; // Show container to display the error
            setLoadingState(false);
        });
    });
});
