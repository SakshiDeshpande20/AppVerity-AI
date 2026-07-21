from __future__ import annotations

from datetime import datetime
from urllib.parse import parse_qs, urlparse

import streamlit as st

import fraud_detection


st.set_page_config(
    page_title="AppVerity AI",
    page_icon="ðŸ›¡ï¸",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# -------------------------------------------------------------------
# Styling
# -------------------------------------------------------------------

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
            max-width: 760px;
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
        }

        .result-safe {
            border-left: 6px solid #22c55e;
        }

        .result-risk {
            border-left: 6px solid #ef4444;
        }

        .result-unknown {
            border-left: 6px solid #f59e0b;
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


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def extract_app_id(play_store_url: str) -> str | None:
    """Extract the Google Play package ID from a Play Store URL."""
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


def canonical_play_store_url(app_id: str) -> str:
    return f"https://play.google.com/store/apps/details?id={app_id}"


def result_configuration(verdict: str) -> tuple[str, str, str]:
    normalized = verdict.lower()

    if "not fraudulent" in normalized:
        return "Lower risk detected", "result-safe", "âœ…"

    if "fraudulent" in normalized:
        return "High-risk signals detected", "result-risk", "âš ï¸"

    return "Insufficient review history", "result-unknown", "â„¹ï¸"


def build_report(
    app_id: str,
    verdict: str,
    summary: str,
    review_count: int,
) -> str:
    return f"""
APPVERITY AI â€” APPLICATION RISK REPORT
=====================================

Generated: {datetime.now().strftime("%d %B %Y, %I:%M %p")}
Application ID: {app_id}
Reviews requested: {review_count}
System result: {verdict}

ANALYSIS SUMMARY
----------------
{summary}

IMPORTANT
---------
This is an automated risk assessment based primarily on app metadata
and user-review sentiment. It is not definitive proof that an app is
fraudulent.

Recommended checks:
1. Verify the developer's official website and email.
2. Read recent one-star and two-star reviews.
3. Check requested permissions before installation.
4. Never share OTPs, passwords, PINs or banking information.
""".strip()


if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []


# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------

st.markdown(
    """
    <section class="hero-card">
        <span class="badge">AI-assisted mobile application analysis</span>
        <h1 class="hero-title">AppVerity AI</h1>
        <p class="hero-subtitle">
            Analyse Google Play Store reviews and app information to identify
            suspicious sentiment patterns and potential trust concerns before
            installing an application.
        </p>
    </section>
    """,
    unsafe_allow_html=True,
)


analyze_tab, history_tab, about_tab = st.tabs(
    ["ðŸ” Analyse app", "ðŸ•˜ Analysis history", "â„¹ï¸ How it works"]
)


# -------------------------------------------------------------------
# Analyse tab
# -------------------------------------------------------------------

with analyze_tab:
    st.subheader("Check a Google Play application")
    st.caption(
        "Paste the complete Google Play Store link. "
        "The application will collect reviews and perform sentiment-based analysis."
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
            "Number of reviews to analyse",
            options=[500, 1000, 2000, 3000, 5000],
            value=1000,
            help=(
                "A higher number may provide more evidence but will take "
                "longer to process."
            ),
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
            st.error(
                "This does not appear to be a valid Google Play Store "
                "application URL."
            )

        else:
            normalized_url = canonical_play_store_url(app_id)

            try:
                with st.status(
                    "Analysing application reviews...",
                    expanded=True,
                ) as analysis_status:
                    st.write("âœ“ Validating Google Play Store URL")
                    st.write("âœ“ Collecting app reviews")
                    st.write("âœ“ Running sentiment analysis")
                    st.write("âœ“ Preparing the risk summary")

                    result = fraud_detection.predict(
                        normalized_url,
                        review_count,
                    )

                    if not isinstance(result, (list, tuple)) or len(result) < 2:
                        raise ValueError(
                            "The analysis engine returned an invalid result."
                        )

                    verdict = str(result[0])
                    summary = str(result[1])

                    analysis_status.update(
                        label="Analysis completed",
                        state="complete",
                        expanded=False,
                    )

                display_title, card_class, icon = result_configuration(verdict)

                st.markdown(
                    f"""
                    <section class="result-card {card_class}">
                        <h2>{icon} {display_title}</h2>
                        <p class="small-muted">
                            Application ID: {app_id}
                        </p>
                    </section>
                    """,
                    unsafe_allow_html=True,
                )

                metric_col1, metric_col2, metric_col3 = st.columns(3)

                metric_col1.metric("System verdict", verdict)
                metric_col2.metric("Reviews requested", f"{review_count:,}")
                metric_col3.metric("Analysis source", "Google Play")

                st.subheader("Analysis summary")
                st.info(summary)

                with st.expander("Recommended safety checks", expanded=True):
                    st.markdown(
                        """
                        - Verify the developer's official website and email.
                        - Read recent one-star and two-star reviews manually.
                        - Check whether the requested permissions match the app's purpose.
                        - Avoid apps asking for unnecessary accessibility or SMS access.
                        - Never share OTPs, PINs, passwords or payment credentials.
                        """
                    )

                report = build_report(
                    app_id=app_id,
                    verdict=verdict,
                    summary=summary,
                    review_count=review_count,
                )

                st.download_button(
                    "â¬‡ï¸ Download analysis report",
                    data=report,
                    file_name=f"{app_id}_apptrust_report.txt",
                    mime="text/plain",
                    use_container_width=True,
                )

                st.session_state.analysis_history.insert(
                    0,
                    {
                        "time": datetime.now().strftime(
                            "%d %b %Y, %I:%M %p"
                        ),
                        "app_id": app_id,
                        "verdict": verdict,
                        "reviews": review_count,
                        "summary": summary,
                    },
                )

            except Exception as exc:
                st.error(
                    "The application could not be analysed. Confirm that the "
                    "link exists, check your internet connection and try again."
                )

                with st.expander("Technical error"):
                    st.code(str(exc))


# -------------------------------------------------------------------
# History tab
# -------------------------------------------------------------------

with history_tab:
    st.subheader("Current-session history")

    if not st.session_state.analysis_history:
        st.info(
            "No applications have been analysed during this session yet."
        )
    else:
        if st.button("Clear session history"):
            st.session_state.analysis_history = []
            st.rerun()

        for number, item in enumerate(
            st.session_state.analysis_history,
            start=1,
        ):
            with st.expander(
                f"{number}. {item['app_id']} â€” {item['verdict']}"
            ):
                st.write(f"**Analysed:** {item['time']}")
                st.write(f"**Reviews requested:** {item['reviews']:,}")
                st.write(item["summary"])


# -------------------------------------------------------------------
# About tab
# -------------------------------------------------------------------

with about_tab:
    st.subheader("How AppVerity AI works")

    step1, step2, step3 = st.columns(3)

    with step1:
        st.markdown("### 1. Collect")
        st.write(
            "Retrieves public app information and user reviews from "
            "Google Play."
        )

    with step2:
        st.markdown("### 2. Analyse")
        st.write(
            "Uses natural-language processing and sentiment signals to "
            "identify concerning patterns."
        )

    with step3:
        st.markdown("### 3. Explain")
        st.write(
            "Displays the result, review summary and recommended manual "
            "safety checks."
        )

    st.warning(
        "This tool provides an automated risk indication. Negative reviews "
        "do not automatically prove fraud, and positive reviews do not "
        "guarantee that an application is safe."
    )
