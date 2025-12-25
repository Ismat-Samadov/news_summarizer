"""
News summarization using Google Gemini API
"""

import sys
import os
import time
from typing import Dict, List, Optional
from datetime import datetime

# Fix encoding for Azerbaijani characters on Windows
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import io
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class GeminiSummarizer:
    """
    Summarize news articles using Google Gemini API

    Free tier limits (Gemini 2.0 Flash):
    - 15 requests per minute
    - 1 million tokens per minute
    - 1500 requests per day
    """

    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.enabled = bool(self.api_key)
        self.client = None
        self.model_name = 'gemini-2.0-flash'  # Current stable flash model

        # Rate limiting
        self.requests_per_minute = 15
        self.request_times = []

        if not self.enabled:
            print("[INFO] Summarization disabled (missing GEMINI_API_KEY)")
        else:
            self._initialize_client()

    def _initialize_client(self):
        """Initialize Gemini client with new SDK"""
        try:
            from google import genai

            # Create client (automatically reads GEMINI_API_KEY or GOOGLE_API_KEY)
            self.client = genai.Client(api_key=self.api_key)

            print(f"[SUCCESS] Gemini API initialized ({self.model_name})")

        except ImportError:
            print("[ERROR] google-genai package not installed")
            print("[INFO] Run: pip install google-genai")
            self.enabled = False

        except Exception as e:
            print(f"[ERROR] Failed to initialize Gemini: {e}")
            self.enabled = False

    def _wait_for_rate_limit(self):
        """
        Ensure we don't exceed rate limits (15 requests per minute)
        """
        current_time = time.time()

        # Remove requests older than 60 seconds
        self.request_times = [
            t for t in self.request_times
            if current_time - t < 60
        ]

        # If we've made 15 requests in the last minute, wait
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60 - (current_time - self.request_times[0])
            if wait_time > 0:
                print(f"[INFO] Rate limit: waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                # Clear old requests after waiting
                self.request_times = []

        # Record this request
        self.request_times.append(time.time())

    def filter_relevant_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Filter articles to keep only those relevant to banking/finance sector

        Args:
            articles: List of all articles

        Returns:
            List of relevant articles only
        """
        if not self.enabled or not articles:
            return articles

        try:
            print(f"\n[INFO] Filtering {len(articles)} articles for banking/finance relevance...")
            self._wait_for_rate_limit()

            # Prepare articles for filtering
            articles_list = []
            for i, article in enumerate(articles, 1):
                content_snippet = article.get('content', '')[:200]
                articles_list.append(
                    f"{i}. {article['title']}\n{content_snippet}..."
                )

            articles_text = "\n\n".join(articles_list)

            # Filtering prompt
            filter_prompt = f"""Sən bank sektorunda Business Analyst üçün asistansan. Aşağıdakı xəbərləri analiz et və YALNIZ bank sektoruna aid olanları seç.

RELEVANT (UYĞUN) XƏBƏRLƏR:
- Bank və maliyyə sektoru xəbərləri
- Makroiqtisadi göstəricilər (inflyasiya, iqtisadi artım, və s.)
- Tənzimləmə və qanunvericilik dəyişiklikləri
- Kredit, ipoteka, depozit bazarları
- Bank kapitalı və maliyyə nəticələri
- Fintex və rəqəmsal bank xidmətləri
- Valyuta məzənnəsi və pul siyasəti
- Beynəlxalq maliyyə təşkilatları (IMF, World Bank, və s.)
- Biznes mühiti və investisiya iqlimi

IRRELEVANT (UYĞUN OLMAYAN) XƏBƏRLƏR:
- Beynəlxalq siyasət və münaqişələr (bank sektoruna təsiri yoxdursa)
- İdman xəbərləri
- Mədəniyyət və əyləncə
- Texnologiya (fintex deyilsə)
- Ümumi infrastruktur layihələri (maliyyələşmə aspekti yoxdursa)

XƏBƏRLƏR:
{articles_text}

TAPŞıRıQ: Yuxarıdakı xəbərlərdən YALNIZ bank sektoru üçün relevant olanların nömrələrini ver.
Cavabı bu formatda ver: 1,3,5,7 (vergüllə ayrılmış nömrələr, heç bir izahat yox)

RELEVANT XƏBƏRLƏR:"""

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=filter_prompt
            )
            relevant_indices_str = response.text.strip()

            # Parse indices
            try:
                relevant_indices = [int(x.strip()) - 1 for x in relevant_indices_str.split(',') if x.strip().isdigit()]
                relevant_articles = [articles[i] for i in relevant_indices if 0 <= i < len(articles)]

                print(f"[SUCCESS] Filtered: {len(relevant_articles)}/{len(articles)} articles are banking-relevant")
                return relevant_articles

            except Exception as parse_error:
                print(f"[WARNING] Could not parse filter results: {parse_error}")
                print(f"[INFO] Using all articles as fallback")
                return articles

        except Exception as e:
            print(f"[ERROR] Filtering failed: {e}")
            print(f"[INFO] Using all articles as fallback")
            return articles

    def create_session_summary(self, articles: List[Dict], sources_stats: List[Dict]) -> Optional[str]:
        """
        Create banking intelligence summary with actionable insights

        Args:
            articles: List of ALL articles (new ones) from this session
            sources_stats: List of stats per source

        Returns:
            Banking intelligence report in Azerbaijani with strategic insights
        """
        if not self.enabled or not articles:
            return None

        try:
            # STEP 1: Filter for relevant articles
            relevant_articles = self.filter_relevant_articles(articles)

            if not relevant_articles:
                return "Bu sessiyada bank sektoruna aid heç bir xəbər tapılmadı."

            # STEP 2: Create banking intelligence report
            self._wait_for_rate_limit()

            # Prepare article summaries WITHOUT source names (for public channel)
            article_summaries = []
            for i, article in enumerate(relevant_articles, 1):
                content_snippet = article.get('content', '')[:400]
                # Don't mention source name - looks more professional
                article_summaries.append(
                    f"{i}. {article['title']}\n"
                    f"   {content_snippet}..."
                )

            articles_text = "\n\n".join(article_summaries[:40])

            # Banking intelligence prompt - SHORT and CLEAN format for PUBLIC CHANNEL
            prompt = f"""Sən Azərbaycan bank sektoru üzrə peşəkar analitik mərkəzsən.
Aşağıdakı xəbərlərdən QISA və PROFESSIONAL banking intelligence report hazırla.

BANK SEKTORU XƏBƏRLƏRI (SON 24 SAAT):
{articles_text}

REPORT FORMATI (QISA VƏ SADƏ):

🔥 ƏSAS TRENDLƏR
(1-2 cümlə, ən vacib nə baş verir)

💰 MALİYYƏ VƏ MAKRO
• İnflyasiya/faiz dərəcələri: [faktlar]
• Bank nəticələri: [rəqəmlər]
• Kredit/depozit bazarı: [dəyişikliklər]

📋 TƏNZİMLƏMƏ VƏ QANUN
• Mərkəzi Bank qərarları: [nə dəyişdi]
• Yeni tələblər: [nə etmək lazımdır]

🚀 İMKANLAR
• [İmkan 1 - konkret addım]
• [İmkan 2 - konkret addım]

⚠️ RİSKLƏR
• [Risk 1 - nə təhlükə yaradır]
• [Risk 2 - nə təhlükə yaradır]

✅ NƏ ETMƏK LAZIM
Bu həftə:
1. [Konkret addım]
2. [Konkret addım]

Bu ay:
1. [Strateji təklif]
2. [Strateji təklif]

👀 İZLƏ
• [Trend 1]
• [Trend 2]

VACIB QAYDALAR:
- Çox qısa və konkret yaz (maksimum 15-20 sətir)
- Hər bölmədə maksimum 2-3 punkt
- Emojilər sadə saxla (💰📋🚀⚠️✅👀)
- Heç bir markdown simvol işlətmə (###, **, və s.)
- Rəqəmlər və faktlar ver, söz-söhbət yox
- Azərbaycan dilində sadə professional dil
- MƏNBƏ QEYD ETMƏ (Banker.az, Marja.az və s. adlarını çəkmə)
- Professional analitik kimi yaz, xəbər toplayıcı kimi yox
- "Xəbərlərə görə", "Bildirilir ki" kimi ifadələr işlət

PROFESSIONAL BANKING INTELLIGENCE REPORT:"""

            # Generate banking intelligence
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            summary = response.text.strip()

            print(f"[SUCCESS] Created banking intelligence report from {len(relevant_articles)} relevant articles")
            print(f"[INFO] Filtered out {len(articles) - len(relevant_articles)} non-banking articles")

            return summary

        except Exception as e:
            try:
                print(f"[ERROR] Failed to create banking intelligence: {e}")
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(f"[ERROR] Failed to create banking intelligence (encoding error)")
            return None

    def get_usage_stats(self) -> Dict:
        """
        Get current usage statistics

        Returns:
            Dictionary with usage stats
        """
        current_time = time.time()

        # Count requests in last minute
        recent_requests = [
            t for t in self.request_times
            if current_time - t < 60
        ]

        return {
            'requests_last_minute': len(recent_requests),
            'requests_limit': self.requests_per_minute,
            'requests_available': max(0, self.requests_per_minute - len(recent_requests)),
            'enabled': self.enabled
        }
