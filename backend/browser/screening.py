"""
Screening question handler for job applications.
Handles common screening questions using candidate profile and LLM.
"""
import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum

from utils.logger import get_logger
from llm.client import LLMClient
from llm.schemas import ProfileAnalysis

logger = get_logger(__name__)


class QuestionType(Enum):
    """Types of screening questions."""
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    YES_NO = "yes_no"
    NUMBER = "number"
    DATE = "date"
    FILE = "file"


@dataclass
class ScreeningQuestion:
    """A screening question from a job application."""
    question_text: str
    question_type: QuestionType
    options: List[str] = field(default_factory=list)
    required: bool = True
    field_name: Optional[str] = None
    field_id: Optional[str] = None


@dataclass
class ScreeningAnswer:
    """Answer to a screening question."""
    question: ScreeningQuestion
    answer: Any
    confidence: float = 1.0
    reasoning: str = ""
    needs_human: bool = False


class ScreeningHandler:
    """
    Handles screening questions in job applications.
    Uses profile data and LLM for intelligent answering.
    """

    def __init__(self, profile: Optional[Dict[str, Any]] = None, llm_client: Optional[LLMClient] = None):
        self.profile = profile or {}
        self.llm_client = llm_client or LLMClient()
        self._question_patterns = self._build_question_patterns()
        self._known_answers: Dict[str, ScreeningAnswer] = {}

    def _build_question_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build patterns for common screening questions."""
        return {
            # Work authorization
            r"(?:legally authorized|work authorization|eligible to work|work visa|sponsor|visa sponsorship)": {
                "field": "work_authorization",
                "type": QuestionType.YES_NO,
                "answer_map": {
                    True: "Yes",
                    False: "No",
                },
                "profile_key": "work_authorization",
            },

            # Years of experience
            r"(?:years? of experience|years? experience|experience.*years?)": {
                "field": "total_experience",
                "type": QuestionType.NUMBER,
                "profile_key": "total_years_experience",
            },

            # Notice period
            r"(?:notice period|notice.*weeks?|when can you start|available to start|start date)": {
                "field": "notice_period",
                "type": QuestionType.NUMBER,
                "profile_key": "notice_period_weeks",
            },

            # Salary expectations
            r"(?:salary expectation|expected salary|compensation expectation|desired salary|pay expectation)": {
                "field": "salary_expectation",
                "type": QuestionType.NUMBER,
                "profile_key": "salary_expectation_min",
            },

            # Education level
            r"(?:highest education|education level|degree|diploma)": {
                "field": "education_level",
                "type": QuestionType.SELECT,
                "profile_key": "highest_education",
            },

            # Willing to relocate
            r"(?:willing to relocate|relocate|relocation)": {
                "field": "willing_to_relocate",
                "type": QuestionType.YES_NO,
                "profile_key": "willing_to_relocate",
                "default": True,
            },

            # Remote work preference
            r"(?:remote work|work from home|remote.*work|hybrid)": {
                "field": "remote_preference",
                "type": QuestionType.SELECT,
                "profile_key": "remote_preferences",
            },

            # LinkedIn
            r"(?:linkedin|linked_in)": {
                "field": "linkedin_url",
                "type": QuestionType.TEXT,
                "profile_key": "linkedin_url",
            },

            # Portfolio/GitHub
            r"(?:portfolio|github|personal website)": {
                "field": "portfolio_url",
                "type": QuestionType.TEXT,
                "profile_key": "portfolio_url",
            },

            # How did you hear about us
            r"(?:how did you hear|where did you find|source|referral)": {
                "field": "source",
                "type": QuestionType.SELECT,
                "default": "Online Job Board",
            },

            # Diversity/EEO questions
            r"(?:gender|race|ethnicity|veteran|disability|lgbtq)": {
                "field": "eeo",
                "type": QuestionType.SELECT,
                "needs_human": True,
                "note": "EEO questions - prefer not to answer",
            },

            # Availability
            r"(?:availability|available to work|shift|schedule)": {
                "field": "availability",
                "type": QuestionType.SELECT,
                "default": "Full-time",
            },

            # Certification/license
            r"(?:certification|license|certified|licensed)": {
                "field": "certifications",
                "type": QuestionType.TEXTAREA,
                "profile_key": "certifications",
            },

            # Language proficiency
            r"(?:language|fluent|bilingual|english|french)": {
                "field": "languages",
                "type": QuestionType.TEXTAREA,
                "profile_key": "languages",
                "default": "English (Fluent)",
            },

            # Criminal background
            r"(?:criminal|background check|conviction|felony)": {
                "field": "background_check",
                "type": QuestionType.YES_NO,
                "needs_human": True,
                "default": False,
            },

            # Drug test
            r"(?:drug test|drug screening|substance)": {
                "field": "drug_test",
                "type": QuestionType.YES_NO,
                "needs_human": True,
                "default": True,
            },
        }

    def detect_questions(self, page_content: str) -> List[ScreeningQuestion]:
        """Detect screening questions from page content."""
        questions = []

        # Try to extract from HTML
        import re
        # Look for form fields with labels
        label_pattern = r'<label[^>]*>([^<]+)</label>'
        labels = re.findall(label_pattern, page_content, re.IGNORECASE)

        # Look for input fields near labels
        input_pattern = r'<input[^>]*(?:name|id)=["\']([^"\']+)["\'][^>]*>'
        inputs = re.findall(input_pattern, page_content, re.IGNORECASE)

        # Look for select fields
        select_pattern = r'<select[^>]*(?:name|id)=["\']([^"\']+)["\'][^>]*>(.*?)</select>'
        selects = re.findall(select_pattern, page_content, re.IGNORECASE | re.DOTALL)

        # Look for textarea
        textarea_pattern = r'<textarea[^>]*(?:name|id)=["\']([^"\']+)["\'][^>]*>'
        textareas = re.findall(textarea_pattern, page_content, re.IGNORECASE)

        # Combine all potential question texts
        all_text = " ".join(labels) + " " + page_content

        # Match against patterns
        for pattern, config in self._question_patterns.items():
            matches = re.finditer(pattern, all_text, re.IGNORECASE)
            for match in matches:
                question_text = match.group(0)
                # Get surrounding context
                start = max(0, match.start() - 100)
                end = min(len(all_text), match.end() + 100)
                context = all_text[start:end]

                q = ScreeningQuestion(
                    question_text=context.strip(),
                    question_type=config["type"],
                    required=config.get("required", True),
                    field_name=config["field"],
                )
                questions.append(q)

        return questions

    async def answer_questions(self, questions: List[ScreeningQuestion]) -> List[ScreeningAnswer]:
        """Answer a list of screening questions."""
        answers = []

        for question in questions:
            answer = await self._answer_single_question(question)
            answers.append(answer)

            # Cache for future use
            cache_key = self._get_cache_key(question)
            self._known_answers[cache_key] = answer

        return answers

    async def _answer_single_question(self, question: ScreeningQuestion) -> ScreeningAnswer:
        """Answer a single screening question."""
        # Check cache first
        cache_key = self._get_cache_key(question)
        if cache_key in self._known_answers:
            return self._known_answers[cache_key]

        # Try pattern matching
        for pattern, config in self._question_patterns.items():
            if re.search(pattern, question.question_text, re.IGNORECASE):
                return await self._answer_from_pattern(question, config)

        # If no pattern match, use LLM
        return await self._answer_with_llm(question)

    async def _answer_from_pattern(self, question: ScreeningQuestion, config: Dict) -> ScreeningAnswer:
        """Answer question using pattern configuration."""
        profile_key = config.get("profile_key")

        if profile_key and profile_key in self.profile:
            value = self.profile[profile_key]
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
        elif "default" in config:
            value = config["default"]
        else:
            value = ""

        # Transform based on question type
        if question.question_type == QuestionType.YES_NO:
            if isinstance(value, bool):
                answer_value = "Yes" if value else "No"
            elif isinstance(value, str):
                answer_value = "Yes" if value.lower() in ("yes", "true", "1", "y") else "No"
            else:
                answer_value = "Yes" if value else "No"
        elif question.question_type == QuestionType.SELECT:
            if question.options and value:
                # Find best matching option
                answer_value = self._find_best_option(value, question.options)
            else:
                answer_value = str(value) if value else (question.options[0] if question.options else "")
        else:
            answer_value = str(value) if value else ""

        needs_human = config.get("needs_human", False)

        return ScreeningAnswer(
            question=question,
            answer=answer_value,
            confidence=0.9 if not needs_human else 0.5,
            reasoning=f"Matched pattern: {config['field']}",
            needs_human=needs_human,
        )

    def _find_best_option(self, value: str, options: List[str]) -> str:
        """Find the best matching option."""
        value_lower = value.lower()
        for option in options:
            if value_lower in option.lower() or option.lower() in value_lower:
                return option
        return options[0] if options else value

    async def _answer_with_llm(self, question: ScreeningQuestion) -> ScreeningAnswer:
        """Use LLM to answer a question."""
        prompt = self._build_llm_prompt(question)

        try:
            response = await self.llm_client.generate_json(
                prompt=prompt,
                schema={
                    "type": "object",
                    "properties": {
                        "answer": {"type": ["string", "number", "boolean"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "reasoning": {"type": "string"},
                        "needs_human": {"type": "boolean"},
                    },
                    "required": ["answer", "confidence", "reasoning", "needs_human"],
                },
                temperature=0.1,
            )

            return ScreeningAnswer(
                question=question,
                answer=response.get("answer", ""),
                confidence=response.get("confidence", 0.5),
                reasoning=response.get("reasoning", "LLM generated"),
                needs_human=response.get("needs_human", False),
            )
        except Exception as e:
            logger.error(f"LLM answer failed: {e}")
            return ScreeningAnswer(
                question=question,
                answer="",
                confidence=0.0,
                reasoning=f"Failed to answer: {e}",
                needs_human=True,
            )

    def _build_llm_prompt(self, question: ScreeningQuestion) -> str:
        """Build prompt for LLM to answer question."""
        profile_summary = self._build_profile_summary()

        options_text = ""
        if question.options:
            options_text = f"\nOptions: {', '.join(question.options)}"

        return f"""You are helping a job applicant answer screening questions.
Answer based on the candidate profile below.

Candidate Profile:
{profile_summary}

Question: {question.question_text}
Question Type: {question.question_type.value}
Required: {question.required}{options_text}

Provide a JSON response with:
- answer: The answer to the question
- confidence: 0.0 to 1.0
- reasoning: Brief explanation
- needs_human: true if this requires human judgment (e.g., EEO, legal, personal preference)"""

    def _build_profile_summary(self) -> str:
        """Build a summary of the candidate profile for LLM."""
        if not self.profile:
            return "No profile data available."

        summary_parts = []

        if self.profile.get("name"):
            summary_parts.append(f"Name: {self.profile['name']}")

        if self.profile.get("total_years_experience"):
            summary_parts.append(f"Total Experience: {self.profile['total_years_experience']} years")

        if self.profile.get("work_authorization"):
            summary_parts.append(f"Work Authorization: {self.profile['work_authorization']}")

        if self.profile.get("notice_period_weeks"):
            summary_parts.append(f"Notice Period: {self.profile['notice_period_weeks']} weeks")

        if self.profile.get("salary_expectation_min"):
            summary_parts.append(f"Salary Expectation: ${self.profile['salary_expectation_min']:,}+")

        if self.profile.get("highest_education"):
            summary_parts.append(f"Highest Education: {self.profile['highest_education']}")

        if self.profile.get("certifications"):
            certs = self.profile["certifications"]
            if isinstance(certs, list):
                summary_parts.append(f"Certifications: {', '.join(certs)}")
            else:
                summary_parts.append(f"Certifications: {certs}")

        if self.profile.get("remote_preferences"):
            prefs = self.profile["remote_preferences"]
            if isinstance(prefs, list):
                summary_parts.append(f"Remote Preferences: {', '.join(prefs)}")
            else:
                summary_parts.append(f"Remote Preferences: {prefs}")

        if self.profile.get("willing_to_relocate") is not None:
            summary_parts.append(f"Willing to Relocate: {'Yes' if self.profile['willing_to_relocate'] else 'No'}")

        return "\n".join(summary_parts) if summary_parts else "No profile data available."

    def _get_cache_key(self, question: ScreeningQuestion) -> str:
        """Generate cache key for a question."""
        import hashlib
        key = f"{question.question_text}:{question.question_type.value}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    async def fill_answers(self, automation, answers: List[ScreeningAnswer]) -> Dict[str, bool]:
        """Fill answers into the form using browser automation."""
        results = {}

        for answer in answers:
            if answer.needs_human:
                results[answer.question.field_name or "unknown"] = False
                continue

            question = answer.question
            success = False

            # Try to find and fill the field
            selectors = []
            if question.field_id:
                selectors.append(f"#{question.field_id}")
            if question.field_name:
                selectors.append(f"[name='{question.field_name}']")

            # Add generic selectors based on question text
            keywords = self._extract_keywords(question.question_text)
            for kw in keywords:
                selectors.extend([
                    f"input[name*='{kw}']",
                    f"select[name*='{kw}']",
                    f"textarea[name*='{kw}']",
                    f"input[id*='{kw}']",
                ])

            for selector in selectors:
                try:
                    element = await automation.page.query_selector(selector)
                    if element and await element.is_visible():
                        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                        input_type = await element.get_attribute("type") or "text"

                        if tag_name == "select":
                            success = await automation.select_option(selector, str(answer.answer))
                        elif input_type in ("radio", "checkbox"):
                            if str(answer.answer).lower() in ("yes", "true", "1"):
                                success = await automation.click_element(selector)
                        elif tag_name == "textarea":
                            success = await automation.fill_field(selector, str(answer.answer))
                        else:
                            success = await automation.fill_field(selector, str(answer.answer))

                        if success:
                            await automation.wait_random(100, 300)
                            break
                except Exception as e:
                    logger.debug(f"Failed to fill {selector}: {e}")
                    continue

            results[question.field_name or "unknown"] = success

        return results

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from question text."""
        # Remove common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "what", "how", "when", "where", "why", "who", "which", "your", "you", "please", "enter", "select", "choose"}
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        return [w for w in words if w not in stop_words][:5]