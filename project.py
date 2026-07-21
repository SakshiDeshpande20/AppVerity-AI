from __future__ import annotations

from datetime import datetime
from html import escape
from urllib.parse import parse_qs, urlparse

import streamlit as st

import fraud_detection


st.set_page_config(
    page_title="AppVerity AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at top right, #1e293b 0%, transparent 35%),
                linear-gradient(135deg, #080c16 0%, #111827 100%);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        .hero-card {
            padding: 2.2rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 24px;
            background: rgba(15, 23, 42, 0.82);
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.28);
            margin-bottom: 1.5rem;
        }

        .hero-title {
            margin: 0;
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            color: #f8fafc;
        }

        .hero-subtitle {
            margin-top: 0.75rem;
            max-width: 780px;
            color: #cbd5e1;
            font-size: 1.08rem;
            line-height: 1.65;
        }

        .badge {
            display: inline-block;
            margin-bottom: 1rem;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: rgba(99, 102, 241, 0.18);
            color: #c7d2fe;
            font-size: 0.85rem;
            font-weight: 700;
        }

        .result-card {
            padding: 1.5rem;
            border-radius: 20px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: rgba(15, 23, 42, 0.75);
            margin-top: 1rem;
            margin-bottom: 1rem;
        }

        .result-low {
            border-left: 6px solid #22c55e;
        }

        .result-medium {
            border-left: 6px solid #f59e0b;
        }

        .result-high {
            border-left: 6px solid #ef4444;
        }

        .small-muted {
            color: #94a3b8;
            font-size: 0.9rem;
        }

        div[data-testid="stForm"] {
            padding: 1.4rem;
            border-radius: 20px;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: rgba(15, 23, 42, 0.72);
        }

        div.stButton > button,
        div[data-testid="stFormSubmitButton"] button {
            border-radius: 12px;
            font-weight: 700;
            min-height: 46px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def extract_app_id(play_store_url: str) -> str | None:
    """Extract the Google Play package ID from a complete URL."""
    try:
        parsed = urlparse(play_store_url.strip())
        if parsed.netloc not in {"play.google.com", "www.play.google.com"}:
            return None
        if "/store/apps/details" not in parsed.path:
            return None

        app_id = parse_qs(parsed.query).get("id", [None])[0]
        if not app_id or "." not in app_id:
            return None
        return app_id
    except (TypeError, ValueError):
        return None


def risk_configuration(level: str) -> tuple[str, str, str]:
    normalized = level.lower()
    if normalized == "low":
        return "Lower risk signals detected", "result-low", "✅"
    if normalized == "medium":
        return "Moderate risk signals detected", "result-medium", "⚠️"
    return "High-risk signals detected", "result-high", "🚨"


def safety_recommendations(level: str) -> list[str]:
    common = [
        "Verify the developer's official website and support email.",
        "Read recent one-star and two-star reviews manually.",
        "Check whether requested permissions match the app's purpose.",
        "Never share OTPs, PINs, passwords or payment credentials.",
    ]

    if level == "High":
        return [
            "Avoid payments or sensitive data entry until the app and developer are verified.",
            "Consider using a trusted alternative application.",
            *common,
        ]
    if level == "Medium":
        return [
            "Use additional caution and verify repeated complaints before installation.",
            *common,
        ]
    return [
        "The sampled reviews show fewer warning signals, but continue normal safety checks.",
        *common,
    ]


def build_report(result: dict) -> str:
    reason_lines = "\n".join(
        f"- {reason}" for reason in result.get("risk_reasons", [])
    ) or "- No specific explanation was produced."

    keyword_lines = "\n".join(
        f"- {item['keyword']}: {item['mentions']} review mention(s)"
        for item in result.get("top_keywords", [])
    ) or "- No predefined warning phrases were detected."

    recommendations = "\n".join(
        f"- {item}" for item in safety_recommendations(result["risk_level"])
    )

    return f"""
APPVERITY AI — EXPLAINABLE APP RISK REPORT
==========================================

Generated: {datetime.now().strftime("%d %B %Y, %I:%M %p")}
Application: {result['app_name']}
Application ID: {result['app_id']}
Developer: {result.get('developer') or 'Not available'}
Google Play rating: {result.get('rating') if result.get('rating') is not None else 'Not available'}
Reviews analysed: {result['reviews_analyzed']}

RISK ASSESSMENT
---------------
Risk score: {result['risk_score']}/100
Risk level: {result['risk_level']}

SENTIMENT DISTRIBUTION
----------------------
Positive: {result['positive_percentage']:.1f}%
Neutral: {result['neutral_percentage']:.1f}%
Negative: {result['negative_percentage']:.1f}%
One-star reviews: {result['one_star_percentage']:.1f}%

RECENT TREND
------------
Recent negative reviews: {result['recent_negative_percentage']:.1f}%
Older negative reviews: {result['older_negative_percentage']:.1f}%
Difference: {result['trend_change']:+.1f} percentage points

WHY THIS SCORE WAS GIVEN
------------------------
{reason_lines}

TOP WARNING PHRASES
-------------------
{keyword_lines}

SUMMARY
-------
{result['summary']}

RECOMMENDED SAFETY CHECKS
-------------------------
{recommendations}

IMPORTANT
---------
This automated score is based on public review patterns and Google Play
metadata. It is a risk indication, not definitive proof that an application
is fraudulent.
""".strip()


if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []


st.markdown(
    """
    <section class="hero-card">
        <span class="badge">Explainable mobile application risk analysis</span>
        <h1 class="hero-title">AppVerity AI</h1>
        <p class="hero-subtitle">
            Analyse recent Google Play reviews, understand sentiment patterns,
            view a transparent risk score, and see the exact signals behind the
            assessment before installing an application.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)


analyze_tab, history_tab, about_tab = st.tabs(
    ["🔍 Analyse app", "🕘 Analysis history", "ℹ️ How it works"]
)


with analyze_tab:
    st.subheader("Check a Google Play application")
    st.caption(
        "Paste a complete Google Play Store link. AppVerity AI analyses recent "
        "English-language reviews from the Indian Google Play listing."
    )

    with st.form("analysis_form"):
        app_url = st.text_input(
            "Google Play Store URL",
            placeholder=(
                "https://play.google.com/store/apps/details"
                "?id=com.example.application"
            ),
        )

        review_count = st.select_slider(
            "Maximum reviews to analyse",
            options=[100, 250, 500, 1000, 2000],
            value=250,
            help="Start with 100 or 250 reviews for a faster test.",
        )

        submitted = st.form_submit_button(
            "Analyse application",
            use_container_width=True,
        )

    if submitted:
        app_id = extract_app_id(app_url)

        if not app_url.strip():
            st.warning("Enter a Google Play Store application link.")
        elif app_id is None:
            st.error("This is not a valid Google Play Store application URL.")
        else:
            try:
                with st.status(
                    "Analysing recent application reviews...",
                    expanded=True,
                ) as analysis_status:
                    st.write("✓ Validating the Google Play URL")
                    st.write("✓ Collecting recent reviews")
                    st.write("✓ Measuring positive, neutral and negative sentiment")
                    st.write("✓ Detecting predefined warning phrases")
                    st.write("✓ Calculating the explainable risk score")

                    result = fraud_detection.predict(app_id, review_count)

                    required_fields = {
                        "risk_score",
                        "risk_level",
                        "positive_percentage",
                        "neutral_percentage",
                        "negative_percentage",
                        "risk_reasons",
                        "summary",
                    }
                    missing_fields = required_fields.difference(result)
                    if missing_fields:
                        raise ValueError(
                            "The analysis engine did not return: "
                            + ", ".join(sorted(missing_fields))
                        )

                    analysis_status.update(
                        label="Analysis completed",
                        state="complete",
                        expanded=False,
                    )

                title, card_class, icon = risk_configuration(result["risk_level"])
                safe_app_name = escape(str(result["app_name"]))
                safe_app_id = escape(str(result["app_id"]))

                st.markdown(
                    f"""
                    <section class="result-card {card_class}">
                        <h2>{icon} {title}</h2>
                        <p><strong>{safe_app_name}</strong></p>
                        <p class="small-muted">Application ID: {safe_app_id}</p>
                    </section>
                    """,
                    unsafe_allow_html=True,
                )

                st.progress(
                    result["risk_score"] / 100,
                    text=f"Explainable risk score: {result['risk_score']}/100",
                )

                metric1, metric2, metric3, metric4 = st.columns(4)
                metric1.metric("Risk score", f"{result['risk_score']}/100")
                metric2.metric("Risk level", result["risk_level"])
                metric3.metric("Reviews analysed", f"{result['reviews_analyzed']:,}")
                metric4.metric(
                    "Google Play rating",
                    (
                        f"{result['rating']:.1f}/5"
                        if result.get("rating") is not None
                        else "Not available"
                    ),
                )

                st.subheader("Review sentiment")
                positive_col, neutral_col, negative_col = st.columns(3)
                positive_col.metric(
                    "Positive",
                    f"{result['positive_percentage']:.1f}%",
                )
                neutral_col.metric(
                    "Neutral",
                    f"{result['neutral_percentage']:.1f}%",
                )
                negative_col.metric(
                    "Negative",
                    f"{result['negative_percentage']:.1f}%",
                )

                chart_data = {
                    "Sentiment": ["Positive", "Neutral", "Negative"],
                    "Percentage": [
                        result["positive_percentage"],
                        result["neutral_percentage"],
                        result["negative_percentage"],
                    ],
                }
                st.bar_chart(chart_data, x="Sentiment", y="Percentage")

                st.subheader("Why did AppVerity give this score?")
                for reason in result["risk_reasons"]:
                    st.markdown(f"- {reason}")

                trend_col1, trend_col2, trend_col3 = st.columns(3)
                trend_col1.metric(
                    "Recent negative",
                    f"{result['recent_negative_percentage']:.1f}%",
                )
                trend_col2.metric(
                    "Older negative",
                    f"{result['older_negative_percentage']:.1f}%",
                )
                trend_col3.metric(
                    "Trend difference",
                    f"{result['trend_change']:+.1f} pp",
                    help="Positive means recent reviews were more negative.",
                )

                st.subheader("Top warning phrases")
                if result["top_keywords"]:
                    keyword_table = [
                        {
                            "Warning phrase": item["keyword"],
                            "Review mentions": item["mentions"],
                        }
                        for item in result["top_keywords"]
                    ]
                    st.dataframe(
                        keyword_table,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.success(
                        "No predefined warning phrases were found in the sampled reviews."
                    )

                with st.expander("Complaint categories"):
                    if result["complaint_categories"]:
                        for item in result["complaint_categories"]:
                            st.write(
                                f"**{item['category']}:** "
                                f"{item['mentions']} review mention(s)"
                            )
                    else:
                        st.write("No predefined complaint categories were detected.")

                st.subheader("Analysis summary")
                st.info(result["summary"])

                with st.expander("Recommended safety checks", expanded=True):
                    for recommendation in safety_recommendations(result["risk_level"]):
                        st.markdown(f"- {recommendation}")

                report = build_report(result)
                st.download_button(
                    "⬇️ Download explainable risk report",
                    data=report,
                    file_name=f"{result['app_id']}_appverity_report.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

                st.session_state.analysis_history.insert(
                    0,
                    {
                        "time": datetime.now().strftime("%d %b %Y, %I:%M %p"),
                        "app_id": result["app_id"],
                        "app_name": result["app_name"],
                        "risk_score": result["risk_score"],
                        "risk_level": result["risk_level"],
                        "reviews": result["reviews_analyzed"],
                        "summary": result["summary"],
                    },
                )

            except Exception as exc:
                st.error(
                    "The application could not be analysed. Confirm that the "
                    "listing exists, check your internet connection and try again."
                )
                with st.expander("Technical error"):
                    st.code(str(exc))


with history_tab:
    st.subheader("Current-session history")

    if not st.session_state.analysis_history:
        st.info("No applications have been analysed during this session yet.")
    else:
        if st.button("Clear session history"):
            st.session_state.analysis_history = []
            st.rerun()

        for number, item in enumerate(
            st.session_state.analysis_history,
            start=1,
        ):
            with st.expander(
                f"{number}. {item['app_name']} — "
                f"{item['risk_level']} ({item['risk_score']}/100)"
            ):
                st.write(f"**Application ID:** {item['app_id']}")
                st.write(f"**Analysed:** {item['time']}")
                st.write(f"**Reviews analysed:** {item['reviews']:,}")
                st.write(item["summary"])


with about_tab:
    st.subheader("How AppVerity AI works")

    step1, step2, step3, step4 = st.columns(4)

    with step1:
        st.markdown("### 1. Collect")
        st.write("Retrieves recent public reviews and app metadata from Google Play.")

    with step2:
        st.markdown("### 2. Analyse")
        st.write("Uses VADER NLP sentiment analysis for each review.")

    with step3:
        st.markdown("### 3. Score")
        st.write(
            "Combines negative sentiment, one-star reviews, warning phrases, "
            "rating and recent trend into a score from 0 to 100."
        )

    with step4:
        st.markdown("### 4. Explain")
        st.write("Shows the exact factors, warning phrases and trend behind the score.")

    st.markdown(
        """
        ### Risk levels

        - **Low (0–30):** fewer concerning signals were found in the sample.
        - **Medium (31–60):** some warning signals require manual verification.
        - **High (61–100):** stronger negative and complaint patterns were detected.
        """
    )

    st.warning(
        "AppVerity AI provides an automated risk indication. Reviews can be "
        "incomplete, manipulated, biased or unrelated to fraud. The result does "
        "not prove that an application is fraudulent or guarantee that it is safe."
    )
