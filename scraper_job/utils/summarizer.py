"""
AI Summarization Module using Google Gemini API
Generates summaries, extracts entities, and performs sentiment analysis
"""

import json
import re
from typing import Dict, List, Optional
from loguru import logger
import google.generativeai as genai

from scraper_job.config import GEMINI_API_KEY


class NewsSummarizer:
    """
    AI-powered news summarizer using Google Gemini

    Uses Gemini 2.5 Flash-Lite for fast, efficient summarization
    Free tier: 1,000 requests/day
    """

    def __init__(self, api_key: str = GEMINI_API_KEY):
        """
        Initialize the summarizer with Gemini API

        Args:
            api_key: Google Gemini API key
        """
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Configure Gemini
        genai.configure(api_key=api_key)

        # Use Gemini 2.5 Flash-Lite (free tier, 1000 requests/day)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Configure generation settings
        self.generation_config = {
            'temperature': 0.3,  # Lower temperature for more focused summaries
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 2048,
        }

        logger.info("Initialized Gemini summarizer with model: gemini-2.0-flash-exp")

    def create_summary_prompt(self, article: Dict) -> str:
        """
        Create a structured prompt for the AI model

        Args:
            article: Article dictionary with title and content

        Returns:
            Formatted prompt string
        """
        title = article.get('title', 'No title')
        content = article.get('content', '')
        source = article.get('source_name', 'Unknown source')

        # Limit content length to avoid token limits
        max_content_length = 8000  # characters
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        prompt = f"""You are a professional news summarizer for Azerbaijani news articles.
Analyze the following article and provide a comprehensive summary in JSON format.

Article Source: {source}
Article Title: {title}

Article Content:
{content}

Provide your analysis in the following JSON format:
{{
    "summary_short": "1-2 sentence summary in Azerbaijani",
    "summary_medium": "1 paragraph (3-5 sentences) summary in Azerbaijani",
    "summary_long": "Detailed multi-paragraph summary in Azerbaijani",
    "key_points": ["key point 1 in Azerbaijani", "key point 2", "key point 3"],
    "entities": {{
        "people": ["person names mentioned"],
        "organizations": ["organizations mentioned"],
        "locations": ["places mentioned"]
    }},
    "topics": ["main topic 1", "main topic 2", "main topic 3"],
    "sentiment": "positive OR negative OR neutral",
    "language": "az"
}}

Important:
- Write ALL summaries and key points in Azerbaijani language
- Keep the short summary under 50 words
- Keep the medium summary under 150 words
- Make the long summary comprehensive but under 500 words
- Extract 3-5 key points
- Identify all named entities (people, organizations, locations)
- Classify sentiment as positive, negative, or neutral
- Ensure valid JSON format
"""
        return prompt

    def parse_gemini_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse Gemini's JSON response

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            # Try to extract JSON from response
            # Sometimes Gemini wraps JSON in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.error("No JSON found in response")
                    return None

            # Parse JSON
            result = json.loads(json_str)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return None

    def summarize_article(self, article: Dict) -> Optional[Dict]:
        """
        Generate AI summary for a single article

        Args:
            article: Article dictionary with content

        Returns:
            Summary dictionary or None if failed
        """
        try:
            # Create prompt
            prompt = self.create_summary_prompt(article)

            # Generate summary
            logger.debug(f"Generating summary for article: {article.get('title', 'Unknown')[:50]}...")

            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )

            # Parse response
            if not response.text:
                logger.error("Empty response from Gemini")
                return None

            result = self.parse_gemini_response(response.text)

            if not result:
                logger.error("Failed to parse Gemini response")
                return None

            # Add metadata
            result['model_used'] = 'gemini-2.0-flash-exp'
            result['model_version'] = '2.0-flash-exp'

            # Calculate confidence score (based on response quality)
            confidence = self.calculate_confidence(result)
            result['confidence_score'] = confidence

            logger.success(f"Successfully generated summary with confidence {confidence:.2f}")

            return result

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None

    def calculate_confidence(self, summary: Dict) -> float:
        """
        Calculate confidence score for the summary

        Args:
            summary: Generated summary dictionary

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0

        # Check if all required fields are present
        required_fields = ['summary_short', 'summary_medium', 'summary_long', 'key_points', 'sentiment']
        for field in required_fields:
            if field in summary and summary[field]:
                score += 0.15

        # Check if entities are extracted
        if 'entities' in summary and summary['entities']:
            score += 0.1

        # Check if topics are identified
        if 'topics' in summary and len(summary.get('topics', [])) >= 2:
            score += 0.1

        # Check summary quality (length checks)
        if len(summary.get('summary_short', '')) > 20:
            score += 0.05
        if len(summary.get('summary_medium', '')) > 50:
            score += 0.05
        if len(summary.get('summary_long', '')) > 100:
            score += 0.05

        # Check key points count
        if len(summary.get('key_points', [])) >= 3:
            score += 0.05

        return min(score, 1.0)

    def batch_summarize(
        self,
        articles: List[Dict],
        max_articles: Optional[int] = None
    ) -> List[Dict]:
        """
        Summarize multiple articles in batch

        Args:
            articles: List of article dictionaries
            max_articles: Maximum number of articles to process

        Returns:
            List of summary results
        """
        if max_articles:
            articles = articles[:max_articles]

        results = []
        success_count = 0
        failed_count = 0

        logger.info(f"Starting batch summarization of {len(articles)} articles")

        for idx, article in enumerate(articles, 1):
            logger.info(f"Processing article {idx}/{len(articles)}: {article.get('title', 'Unknown')[:50]}...")

            try:
                summary = self.summarize_article(article)

                if summary:
                    results.append({
                        'article_id': article.get('id'),
                        'summary': summary,
                        'success': True
                    })
                    success_count += 1
                else:
                    results.append({
                        'article_id': article.get('id'),
                        'summary': None,
                        'success': False,
                        'error': 'Failed to generate summary'
                    })
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error processing article {article.get('id')}: {e}")
                results.append({
                    'article_id': article.get('id'),
                    'summary': None,
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1

        logger.info(f"Batch summarization completed: {success_count} successful, {failed_count} failed")

        return results

    def test_connection(self) -> bool:
        """
        Test Gemini API connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_prompt = "Say 'Hello' in JSON format: {\"message\": \"Hello\"}"
            response = self.model.generate_content(test_prompt)

            if response.text:
                logger.success("Gemini API connection test successful")
                return True
            else:
                logger.error("Gemini API connection test failed: Empty response")
                return False

        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
