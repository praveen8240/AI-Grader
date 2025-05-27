"""Defines the data structures for input and output of the AI grading model."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class CriterionScore:
    """Represents the score for a single evaluation criterion."""
    criterion_name: str
    score: float
    max_score: float
    feedback: Optional[str] = None

@dataclass
class EvaluationCriterion:
    """Defines a criterion for evaluation."""
    name: str
    max_score: float
    weight: float = 1.0

@dataclass
class WordCountRange:
    """Specifies the acceptable word count range."""
    min_words: int
    max_words: int

@dataclass
class GradingInput:
    """Represents the input for the grading process."""
    question_text: str
    student_answer: str
    reference_answer: Optional[str] = None
    evaluation_criteria: Optional[List[EvaluationCriterion]] = None
    word_count_requirement: Optional[WordCountRange] = None
    additional_metadata: Optional[Dict] = None

@dataclass
class GradingOutput:
    """Represents the output of the grading process."""
    total_score: float
    sub_scores: List[CriterionScore]
    automated_feedback: str
    needs_teacher_review: bool
    errors: Optional[List[str]] = None
