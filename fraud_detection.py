from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import nltk
from google_play_scraper import Sort, app, reviews
from nltk.sentiment import SentimentIntensityAnalyzer


RISK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Fraud and deception": (
        "scam",
        "fraud",
        "fraudulent",
        "fake app",
        "cheating",
        "deceptive",
        "phishing",
    ),
    "Payment problems": (
        "money deducted",
        "payment failed",
        "money lost",
        "charged without",
        "unauthorized transaction",
        "unauthorised transaction",
        "upi fraud",
    ),
    "Withdrawal problems": (
        "withdrawal failed",
        "unable to withdraw",
        "cannot withdraw",
        "can't withdraw",
        "cash out failed",
        "payout not received",
    ),
    "Refund problems": (
        "refund not received",
        "no refund",
        "not refunded",
        "money back not received",
    ),
    "Account problems": (
        "account blocked",
        "account suspended",
        "account locked",
        "login blocked",
    ),
    "Privacy and malware": (
        "data theft",
        "stole my data",
        "privacy issue",
        "malware",
        "spyware",
        "steals data",
    ),
    "Customer support": (
        "customer support not responding",
        "customer care not responding",
        "no response from support",
        "support is useless",
    ),
}


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
) -> str:
    keyword_text = ""
    if top_keywords:
        phrases = ", ".join(item["keyword"] for item in top_keywords[:3])
        keyword_text = f" The most frequent warning phrases were: {phrases}."

    return (
        f"AppVerity AI analysed {total_reviews} recent English-language Google Play "
        f"reviews for {app_name}. The assessment produced a {risk_level.lower()} "
        f"risk score of {risk_score}/100, with {negative_percentage:.1f}% negative "
        f"reviews.{keyword_text} This score is a warning indicator based on public "
        "review patterns and app metadata; it is not proof of fraud."
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
        raise ValueError("No usable English-language reviews were returned for this app.")

    sia = SentimentIntensityAnalyzer()
    sentiment_labels: list[str] = []
    keyword_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    keyword_review_count = 0
    one_star_count = 0

    for row in usable_reviews:
        text = row["content"].strip()
        lower_text = text.lower()
        compound = sia.polarity_scores(text)["compound"]

        if compound >= 0.05:
            sentiment_labels.append("positive")
        elif compound <= -0.05:
            sentiment_labels.append("negative")
        else:
            sentiment_labels.append("neutral")

        if int(row.get("score") or 0) == 1:
            one_star_count += 1

        review_has_keyword = False
        for category, phrases in RISK_KEYWORDS.items():
            category_found = False
            for phrase in phrases:
                if phrase in lower_text:
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
        {"keyword": keyword, "mentions": mentions}
        for keyword, mentions in keyword_counts.most_common(8)
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

    app_name = str(app_details.get("title") or app_id)
    summary = _build_summary(
        app_name=app_name,
        total_reviews=total,
        risk_score=risk_score,
        risk_level=risk_level,
        negative_percentage=negative_percentage,
        top_keywords=top_keywords,
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
