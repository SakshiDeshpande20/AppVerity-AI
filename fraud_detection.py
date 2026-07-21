from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import nltk
from google_play_scraper import Sort, app, reviews
from nltk.sentiment import SentimentIntensityAnalyzer


LANGUAGE_ORDER = ("English", "Hinglish", "Hindi")
DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")
LATIN_WORD_PATTERN = re.compile(r"[a-zA-Z']+")

HINGLISH_MARKERS = {
    "acha",
    "accha",
    "achha",
    "bahut",
    "bekar",
    "bekaar",
    "bakwas",
    "band",
    "chalu",
    "dhokha",
    "dhoka",
    "gaya",
    "gaye",
    "gayi",
    "hai",
    "hain",
    "ho",
    "kar",
    "karo",
    "kharab",
    "kat",
    "kate",
    "mila",
    "mile",
    "mili",
    "mera",
    "meri",
    "nakli",
    "nahi",
    "nhi",
    "paisa",
    "paise",
    "raha",
    "rahe",
    "rahi",
    "sahi",
    "wapas",
}

HINGLISH_STRONG_PHRASES = (
    "paise kat gaye",
    "paisa kat gaya",
    "paise deduct ho gaye",
    "refund nahi mila",
    "refund nhi mila",
    "paise wapas nahi mile",
    "withdrawal nahi ho raha",
    "withdrawal nhi ho raha",
    "paisa nikal nahi raha",
    "account block ho gaya",
    "customer care reply nahi",
    "reply nahi kar raha",
    "ye app fake hai",
    "app fake hai",
    "bahut acha",
    "bahut kharab",
)

POSITIVE_LANGUAGE_MARKERS = (
    "acha",
    "accha",
    "achha",
    "badhiya",
    "badiya",
    "bahut acha",
    "mast app",
    "sahi app",
    "useful hai",
    "helpful hai",
    "अच्छा",
    "अच्छी",
    "बढ़िया",
    "बहुत अच्छा",
    "सही",
    "उपयोगी",
    "सुरक्षित",
    "भरोसेमंद",
)

NEGATIVE_LANGUAGE_MARKERS = (
    "bakwas",
    "bekar",
    "bekaar",
    "kharab",
    "bahut kharab",
    "dhokha",
    "dhoka",
    "nakli",
    "fraud hai",
    "scam hai",
    "nahi mila",
    "nhi mila",
    "nahi ho raha",
    "nhi ho raha",
    "paise kat",
    "paisa kat",
    "paise wapas nahi",
    "account block",
    "reply nahi",
    "बेकार",
    "खराब",
    "घटिया",
    "धोखा",
    "फर्जी",
    "ठगी",
    "स्कैम",
    "नहीं मिला",
    "नहीं हो रहा",
    "पैसे कट",
    "पैसा कट",
    "पैसे वापस नहीं",
    "खाता ब्लॉक",
    "जवाब नहीं",
)

SENTIMENT_TRANSLATIONS = {
    "paise kat gaye": "money deducted bad",
    "paisa kat gaya": "money deducted bad",
    "paise deduct ho gaye": "money deducted bad",
    "refund nahi mila": "refund not received bad",
    "refund nhi mila": "refund not received bad",
    "paise wapas nahi mile": "money not returned bad",
    "withdrawal nahi ho raha": "withdrawal failed bad",
    "withdrawal nhi ho raha": "withdrawal failed bad",
    "paisa nikal nahi raha": "cannot withdraw money bad",
    "account block ho gaya": "account blocked bad",
    "customer care reply nahi": "customer support not responding bad",
    "reply nahi kar raha": "not responding bad",
    "ye app fake hai": "this app is fake scam",
    "app fake hai": "app is fake scam",
    "bahut acha": "very good",
    "bahut badhiya": "very good",
    "bahut kharab": "very bad",
    "bakwas": "terrible",
    "bekar": "bad",
    "bekaar": "bad",
    "dhokha": "fraud",
    "dhoka": "fraud",
    "nakli": "fake",
    "अच्छा": "good",
    "अच्छी": "good",
    "बढ़िया": "very good",
    "बहुत अच्छा": "very good",
    "सही": "good",
    "उपयोगी": "useful",
    "सुरक्षित": "safe",
    "भरोसेमंद": "trustworthy",
    "बेकार": "terrible",
    "खराब": "bad",
    "घटिया": "terrible",
    "धोखा": "fraud",
    "फर्जी": "fake",
    "ठगी": "fraud",
    "स्कैम": "scam",
    "रिफंड नहीं मिला": "refund not received bad",
    "पैसे वापस नहीं मिले": "money not returned bad",
    "निकासी नहीं हो रही": "withdrawal failed bad",
    "पैसे कट गए": "money deducted bad",
    "पैसा कट गया": "money deducted bad",
    "खाता ब्लॉक हो गया": "account blocked bad",
    "जवाब नहीं दे रहे": "not responding bad",
}

RISK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Fraud and deception": (
        "scam",
        "fraud",
        "fraudulent",
        "fake app",
        "cheating",
        "deceptive",
        "phishing",
        "ye app fake hai",
        "app fake hai",
        "fraud hai",
        "scam hai",
        "dhokha",
        "dhoka",
        "nakli app",
        "धोखा",
        "फर्जी",
        "फर्जी ऐप",
        "ठगी",
        "स्कैम",
    ),
    "Payment problems": (
        "money deducted",
        "payment failed",
        "money lost",
        "charged without",
        "unauthorized transaction",
        "unauthorised transaction",
        "upi fraud",
        "paise kat gaye",
        "paisa kat gaya",
        "paise deduct ho gaye",
        "पैसे कट गए",
        "पैसा कट गया",
        "भुगतान विफल",
        "पैसे चले गए",
    ),
    "Withdrawal problems": (
        "withdrawal failed",
        "unable to withdraw",
        "cannot withdraw",
        "can't withdraw",
        "cash out failed",
        "payout not received",
        "withdrawal nahi ho raha",
        "withdrawal nhi ho raha",
        "paisa nikal nahi raha",
        "paise nahi nikal rahe",
        "निकासी नहीं हो रही",
        "पैसे नहीं निकल रहे",
    ),
    "Refund problems": (
        "refund not received",
        "no refund",
        "not refunded",
        "money back not received",
        "refund nahi mila",
        "refund nhi mila",
        "paise wapas nahi mile",
        "रिफंड नहीं मिला",
        "पैसे वापस नहीं मिले",
    ),
    "Account problems": (
        "account blocked",
        "account suspended",
        "account locked",
        "login blocked",
        "account block ho gaya",
        "account lock ho gaya",
        "खाता ब्लॉक हो गया",
        "अकाउंट ब्लॉक",
    ),
    "Privacy and malware": (
        "data theft",
        "stole my data",
        "privacy issue",
        "malware",
        "spyware",
        "steals data",
        "data chori",
        "डेटा चोरी",
        "गोपनीयता समस्या",
    ),
    "Customer support": (
        "customer support not responding",
        "customer care not responding",
        "no response from support",
        "support is useless",
        "customer care reply nahi",
        "reply nahi kar raha",
        "koi response nahi",
        "कस्टमर केयर जवाब नहीं",
        "जवाब नहीं दे रहे",
    ),
}




def _normalise_text(text: str) -> str:
    return " ".join(text.lower().split())


def _detect_language(text: str) -> str:
    """Use transparent script and vocabulary rules for English/Hindi/Hinglish."""
    normalised = _normalise_text(text)

    if DEVANAGARI_PATTERN.search(normalised):
        return "Hindi"

    if any(phrase in normalised for phrase in HINGLISH_STRONG_PHRASES):
        return "Hinglish"

    tokens = set(LATIN_WORD_PATTERN.findall(normalised))
    marker_count = len(tokens.intersection(HINGLISH_MARKERS))

    if marker_count >= 2:
        return "Hinglish"

    if marker_count == 1 and any(
        marker in normalised
        for marker in (
            "bakwas",
            "bekar",
            "bekaar",
            "dhokha",
            "dhoka",
            "nakli",
            "nahi",
            "nhi",
            "paise",
            "paisa",
        )
    ):
        return "Hinglish"

    return "English"


def _phrase_language(phrase: str) -> str:
    return _detect_language(phrase)


def _prepare_multilingual_sentiment_text(text: str) -> str:
    prepared = _normalise_text(text)
    for phrase, replacement in sorted(
        SENTIMENT_TRANSLATIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        prepared = prepared.replace(phrase, replacement)
    return prepared


def _classify_multilingual_sentiment(
    text: str,
    star_score: int,
    analyser: SentimentIntensityAnalyzer,
) -> str:
    normalised = _normalise_text(text)
    prepared = _prepare_multilingual_sentiment_text(text)
    vader_score = analyser.polarity_scores(prepared)["compound"]

    positive_hits = sum(
        1 for marker in POSITIVE_LANGUAGE_MARKERS if marker in normalised
    )
    negative_hits = sum(
        1 for marker in NEGATIVE_LANGUAGE_MARKERS if marker in normalised
    )

    manual_score = min(0.9, positive_hits * 0.35) - min(
        1.0,
        negative_hits * 0.45,
    )

    if star_score <= 2:
        rating_score = -0.55
    elif star_score >= 4:
        rating_score = 0.40
    else:
        rating_score = 0.0

    combined_score = (
        vader_score * 0.60
        + manual_score * 0.30
        + rating_score * 0.10
    )

    if negative_hits and combined_score > -0.05:
        combined_score = -0.20
    elif positive_hits and not negative_hits and combined_score < 0.05:
        combined_score = 0.18

    if combined_score >= 0.05:
        return "positive"
    if combined_score <= -0.05:
        return "negative"
    return "neutral"


def _language_distribution(
    language_counts: Counter[str],
    total: int,
) -> list[dict[str, Any]]:
    return [
        {
            "language": language,
            "reviews": int(language_counts.get(language, 0)),
            "percentage": _percentage(
                int(language_counts.get(language, 0)),
                total,
            ),
        }
        for language in LANGUAGE_ORDER
        if language_counts.get(language, 0)
    ]


def _sentiment_distribution_by_language(
    sentiment_counts: dict[str, Counter[str]],
    language_counts: Counter[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for language in LANGUAGE_ORDER:
        total = int(language_counts.get(language, 0))
        if not total:
            continue

        counts = sentiment_counts.get(language, Counter())
        rows.append(
            {
                "language": language,
                "reviews": total,
                "positive_percentage": _percentage(
                    int(counts.get("positive", 0)),
                    total,
                ),
                "neutral_percentage": _percentage(
                    int(counts.get("neutral", 0)),
                    total,
                ),
                "negative_percentage": _percentage(
                    int(counts.get("negative", 0)),
                    total,
                ),
            }
        )

    return rows

def _extract_app_id(app_reference: str) -> str:
    """Accept either a package ID or a complete Google Play URL."""
    value = app_reference.strip()
    if not value:
        raise ValueError("Application link or package ID is empty.")

    if "play.google.com" not in value:
        if "." not in value or " " in value:
            raise ValueError("Invalid Google Play package ID.")
        return value

    parsed = urlparse(value)
    app_id = parse_qs(parsed.query).get("id", [None])[0]
    if not app_id:
        raise ValueError("The Google Play URL does not contain an application ID.")
    return app_id


def _ensure_nltk_data() -> None:
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)


def _percentage(part: int, total: int) -> float:
    return round((part / total) * 100, 1) if total else 0.0


def _negative_percentage(labels: list[str]) -> float:
    return _percentage(labels.count("negative"), len(labels))


def _risk_level(score: int) -> str:
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    return "High"


def _build_reasons(
    negative_percentage: float,
    keyword_review_percentage: float,
    one_star_percentage: float,
    trend_change: float,
    app_rating: float | None,
    category_counts: Counter[str],
) -> list[str]:
    reasons: list[str] = []

    if negative_percentage >= 60:
        reasons.append(
            f"{negative_percentage:.1f}% of analysed reviews were negative."
        )
    elif negative_percentage >= 35:
        reasons.append(
            f"A notable {negative_percentage:.1f}% of analysed reviews were negative."
        )
    else:
        reasons.append(
            f"Only {negative_percentage:.1f}% of analysed reviews were negative."
        )

    if keyword_review_percentage >= 15:
        reasons.append(
            f"{keyword_review_percentage:.1f}% of reviews contained predefined risk phrases."
        )

    if one_star_percentage >= 35:
        reasons.append(
            f"{one_star_percentage:.1f}% of analysed reviews gave the app one star."
        )

    if trend_change >= 10:
        reasons.append(
            f"Recent negative sentiment was {trend_change:.1f} percentage points "
            "higher than older reviews in the sample."
        )
    elif trend_change <= -10:
        reasons.append(
            f"Recent negative sentiment improved by {abs(trend_change):.1f} "
            "percentage points compared with older reviews in the sample."
        )

    if app_rating is not None and app_rating < 3.5:
        reasons.append(
            f"The current Google Play rating is relatively low ({app_rating:.1f}/5)."
        )

    for category, count in category_counts.most_common(2):
        if count:
            reasons.append(f"{category} appeared in {count} analysed reviews.")

    return reasons[:6]


def _build_summary(
    app_name: str,
    total_reviews: int,
    risk_score: int,
    risk_level: str,
    negative_percentage: float,
    top_keywords: list[dict[str, Any]],
    language_distribution: list[dict[str, Any]],
) -> str:
    keyword_text = ""
    if top_keywords:
        phrases = ", ".join(item["keyword"] for item in top_keywords[:3])
        keyword_text = f" The most frequent warning phrases were: {phrases}."

    language_text = ", ".join(
        f"{item['language']} {item['reviews']}"
        for item in language_distribution
    )

    return (
        f"AppVerity AI analysed {total_reviews} recent Google Play reviews for "
        f"{app_name}. Detected language coverage: {language_text}. The assessment "
        f"produced a {risk_level.lower()} risk score of {risk_score}/100, with "
        f"{negative_percentage:.1f}% negative reviews.{keyword_text} English "
        "sentiment uses VADER, while Hindi and Hinglish use transparent phrase, "
        "script, rating and translated-sentiment rules. The result is a warning "
        "indicator, not proof of fraud."
    )



def _format_updated_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    try:
        timestamp = float(value)
        # Defensive support in case a source returns milliseconds.
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%d %b %Y")
    except (TypeError, ValueError, OSError, OverflowError):
        return str(value)


def _parse_release_date(value: Any) -> datetime | None:
    if not value:
        return None

    text = str(value).strip()
    for date_format in ("%b %d, %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _developer_transparency_assessment(
    app_details: dict[str, Any],
    app_rating: float | None,
) -> dict[str, Any]:
    """Build a metadata-completeness and maturity assessment.

    This is not identity verification and must not be presented as proof that
    the developer is trustworthy.
    """
    score = 100
    positive_signals: list[str] = []
    warning_signals: list[str] = []

    developer_email = app_details.get("developerEmail")
    developer_website = app_details.get("developerWebsite")
    privacy_policy = app_details.get("privacyPolicy")
    real_installs = int(app_details.get("realInstalls") or 0)
    ratings_count = int(app_details.get("ratings") or 0)

    if privacy_policy:
        positive_signals.append("A privacy-policy link is available.")
    else:
        score -= 25
        warning_signals.append("No privacy-policy link was found on the listing.")

    if developer_website:
        positive_signals.append("A developer website is listed.")
    else:
        score -= 15
        warning_signals.append("No developer website was found.")

    if developer_email:
        positive_signals.append("A developer support email is listed.")
    else:
        score -= 15
        warning_signals.append("No developer support email was found.")

    if real_installs >= 1_000_000:
        positive_signals.append("The app has at least one million recorded installs.")
    elif real_installs >= 10_000:
        positive_signals.append("The app has at least ten thousand recorded installs.")
    elif real_installs > 0:
        score -= 8
        warning_signals.append(
            "The app has a relatively small recorded install base."
        )
    else:
        score -= 12
        warning_signals.append("Install information was unavailable.")

    if ratings_count >= 10_000:
        positive_signals.append("The listing has a substantial number of ratings.")
    elif ratings_count >= 1_000:
        positive_signals.append("The listing has more than one thousand ratings.")
    elif ratings_count > 0:
        score -= 6
        warning_signals.append(
            "The listing has relatively few ratings, so reputation evidence is limited."
        )
    else:
        score -= 10
        warning_signals.append("Rating-count information was unavailable.")

    release_date = _parse_release_date(app_details.get("released"))
    now = datetime.now(timezone.utc)

    if release_date:
        age_days = max(0, (now - release_date).days)
        if age_days >= 730:
            positive_signals.append("The app has been listed for at least two years.")
        elif age_days < 30:
            score -= 12
            warning_signals.append(
                "The app appears to have been released less than 30 days ago."
            )
        elif age_days < 180:
            score -= 6
            warning_signals.append(
                "The app appears to have been released less than six months ago."
            )
    else:
        age_days = None
        warning_signals.append("The original release date was unavailable.")

    raw_updated = app_details.get("updated")
    updated_date: datetime | None = None
    try:
        if raw_updated is not None:
            timestamp = float(raw_updated)
            if timestamp > 10_000_000_000:
                timestamp /= 1000
            updated_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        updated_date = None

    if updated_date:
        days_since_update = max(0, (now - updated_date).days)
        if days_since_update <= 180:
            positive_signals.append("The app was updated within the last six months.")
        elif days_since_update > 730:
            score -= 10
            warning_signals.append(
                "The app has not been updated for more than two years."
            )
        elif days_since_update > 365:
            score -= 5
            warning_signals.append(
                "The app has not been updated for more than one year."
            )
    else:
        days_since_update = None
        warning_signals.append("The last-updated date was unavailable.")

    if app_rating is not None:
        if app_rating >= 4.0:
            positive_signals.append(
                f"The current Google Play rating is {app_rating:.1f}/5."
            )
        elif app_rating < 3.0:
            score -= 10
            warning_signals.append(
                f"The current Google Play rating is low ({app_rating:.1f}/5)."
            )
        elif app_rating < 3.5:
            score -= 5
            warning_signals.append(
                f"The current Google Play rating is below 3.5 ({app_rating:.1f}/5)."
            )

    score = max(0, min(100, score))
    if score >= 75:
        label = "Strong transparency"
    elif score >= 50:
        label = "Moderate transparency"
    else:
        label = "Limited transparency"

    return {
        "transparency_score": score,
        "transparency_level": label,
        "positive_signals": positive_signals,
        "warning_signals": warning_signals,
        "app_age_days": age_days,
        "days_since_update": days_since_update,
    }

def predict(app_reference: str, n: int = 500) -> dict[str, Any]:
    """Analyse recent Google Play reviews and return an explainable risk result."""
    if n < 1:
        raise ValueError("The review count must be greater than zero.")

    app_id = _extract_app_id(app_reference)
    _ensure_nltk_data()

    app_details = app(app_id, lang="en", country="in")
    review_rows, _ = reviews(
        app_id,
        lang="en",
        country="in",
        sort=Sort.NEWEST,
        count=n,
    )

    usable_reviews = [
        row
        for row in review_rows
        if isinstance(row.get("content"), str) and row["content"].strip()
    ]
    if not usable_reviews:
        raise ValueError("No usable reviews were returned for this app.")

    sia = SentimentIntensityAnalyzer()
    sia.lexicon.update(
        {
            "bakwas": -3.4,
            "bekar": -2.8,
            "bekaar": -2.8,
            "kharab": -2.6,
            "dhokha": -3.5,
            "dhoka": -3.5,
            "nakli": -2.8,
            "badhiya": 2.8,
            "badiya": 2.8,
            "acha": 2.2,
            "accha": 2.2,
            "achha": 2.2,
        }
    )

    sentiment_labels: list[str] = []
    keyword_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    sentiment_counts_by_language: dict[str, Counter[str]] = {
        language: Counter() for language in LANGUAGE_ORDER
    }
    keyword_review_count = 0
    one_star_count = 0

    for row in usable_reviews:
        text = row["content"].strip()
        lower_text = _normalise_text(text)
        star_score = int(row.get("score") or 0)
        language = _detect_language(text)
        sentiment_label = _classify_multilingual_sentiment(
            text,
            star_score,
            sia,
        )

        language_counts[language] += 1
        sentiment_counts_by_language[language][sentiment_label] += 1
        sentiment_labels.append(sentiment_label)

        if star_score == 1:
            one_star_count += 1

        review_has_keyword = False
        for category, phrases in RISK_KEYWORDS.items():
            category_found = False
            for phrase in phrases:
                if _normalise_text(phrase) in lower_text:
                    keyword_counts[phrase] += 1
                    category_found = True
                    review_has_keyword = True
            if category_found:
                category_counts[category] += 1

        if review_has_keyword:
            keyword_review_count += 1

    total = len(usable_reviews)
    positive_count = sentiment_labels.count("positive")
    neutral_count = sentiment_labels.count("neutral")
    negative_count = sentiment_labels.count("negative")

    positive_percentage = _percentage(positive_count, total)
    neutral_percentage = _percentage(neutral_count, total)
    negative_percentage = _percentage(negative_count, total)
    keyword_review_percentage = _percentage(keyword_review_count, total)
    one_star_percentage = _percentage(one_star_count, total)
    language_distribution = _language_distribution(language_counts, total)
    sentiment_by_language = _sentiment_distribution_by_language(
        sentiment_counts_by_language,
        language_counts,
    )
    multilingual_review_count = int(
        language_counts.get("Hindi", 0)
        + language_counts.get("Hinglish", 0)
    )

    segment_size = max(1, total // 3)
    recent_labels = sentiment_labels[:segment_size]
    older_labels = sentiment_labels[-segment_size:]
    recent_negative_percentage = _negative_percentage(recent_labels)
    older_negative_percentage = _negative_percentage(older_labels)
    trend_change = round(
        recent_negative_percentage - older_negative_percentage,
        1,
    )

    raw_rating = app_details.get("score")
    app_rating = round(float(raw_rating), 1) if raw_rating is not None else None
    transparency = _developer_transparency_assessment(app_details, app_rating)

    sentiment_component = negative_percentage * 0.50
    keyword_component = keyword_review_percentage * 0.25
    one_star_component = one_star_percentage * 0.10
    rating_component = (
        max(0.0, min(10.0, (4.2 - app_rating) * 5.0))
        if app_rating is not None
        else 0.0
    )
    trend_component = min(5.0, max(0.0, trend_change) * 0.25)

    risk_score = int(
        round(
            min(
                100.0,
                sentiment_component
                + keyword_component
                + one_star_component
                + rating_component
                + trend_component,
            )
        )
    )
    risk_level = _risk_level(risk_score)

    top_keywords = [
        {
            "keyword": keyword,
            "mentions": mentions,
            "language": _phrase_language(keyword),
        }
        for keyword, mentions in keyword_counts.most_common(10)
    ]
    complaint_categories = [
        {"category": category, "mentions": mentions}
        for category, mentions in category_counts.most_common()
    ]

    risk_reasons = _build_reasons(
        negative_percentage=negative_percentage,
        keyword_review_percentage=keyword_review_percentage,
        one_star_percentage=one_star_percentage,
        trend_change=trend_change,
        app_rating=app_rating,
        category_counts=category_counts,
    )

    multilingual_warning_mentions = sum(
        mentions
        for phrase, mentions in keyword_counts.items()
        if _phrase_language(phrase) in {"Hindi", "Hinglish"}
    )
    if multilingual_warning_mentions:
        risk_reasons.append(
            f"Detected {multilingual_warning_mentions} Hindi/Hinglish "
            "warning-phrase mention(s)."
        )
    elif multilingual_review_count:
        risk_reasons.append(
            f"Analysed {multilingual_review_count} Hindi/Hinglish review(s) "
            "using multilingual rules."
        )
    risk_reasons = risk_reasons[:7]

    app_name = str(app_details.get("title") or app_id)
    summary = _build_summary(
        app_name=app_name,
        total_reviews=total,
        risk_score=risk_score,
        risk_level=risk_level,
        negative_percentage=negative_percentage,
        top_keywords=top_keywords,
        language_distribution=language_distribution,
    )

    return {
        "app_id": app_id,
        "app_name": app_name,
        "developer": app_details.get("developer"),
        "developer_email": app_details.get("developerEmail"),
        "developer_website": app_details.get("developerWebsite"),
        "developer_address": app_details.get("developerAddress"),
        "privacy_policy": app_details.get("privacyPolicy"),
        "icon": app_details.get("icon"),
        "rating": app_rating,
        "ratings_count": app_details.get("ratings"),
        "total_review_count": app_details.get("reviews"),
        "installs": app_details.get("realInstalls"),
        "installs_label": app_details.get("installs"),
        "genre": app_details.get("genre"),
        "content_rating": app_details.get("contentRating"),
        "contains_ads": bool(app_details.get("containsAds")),
        "offers_iap": bool(app_details.get("offersIAP")),
        "in_app_product_price": app_details.get("inAppProductPrice"),
        "released": app_details.get("released"),
        "updated": _format_updated_timestamp(app_details.get("updated")),
        "version": app_details.get("version"),
        "free": app_details.get("free"),
        "transparency_score": transparency["transparency_score"],
        "transparency_level": transparency["transparency_level"],
        "developer_positive_signals": transparency["positive_signals"],
        "developer_warning_signals": transparency["warning_signals"],
        "app_age_days": transparency["app_age_days"],
        "days_since_update": transparency["days_since_update"],
        "reviews_requested": n,
        "reviews_analyzed": total,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "positive_percentage": positive_percentage,
        "neutral_percentage": neutral_percentage,
        "negative_percentage": negative_percentage,
        "language_distribution": language_distribution,
        "sentiment_by_language": sentiment_by_language,
        "multilingual_review_count": multilingual_review_count,
        "one_star_percentage": one_star_percentage,
        "keyword_review_percentage": keyword_review_percentage,
        "recent_negative_percentage": recent_negative_percentage,
        "older_negative_percentage": older_negative_percentage,
        "trend_change": trend_change,
        "risk_reasons": risk_reasons,
        "top_keywords": top_keywords,
        "complaint_categories": complaint_categories,
        "summary": summary,
    }


if __name__ == "__main__":
    reference = input("Enter a Google Play URL or package ID: ")
    result = predict(reference, 250)
    print(result)
