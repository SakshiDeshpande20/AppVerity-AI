from __future__ import annotations

import csv
from datetime import datetime
from html import escape
from io import StringIO
from urllib.parse import parse_qs, urlparse

import streamlit as st

import apk_permission_analyzer
import fraud_detection
import history_db


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



def format_number(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "Not available"


def yes_no(value: object) -> str:
    return "Yes" if bool(value) else "No"


def render_developer_trust_panel(result: dict) -> None:
    st.subheader("Application and developer information")

    icon_col, identity_col = st.columns([1, 5])

    with icon_col:
        if result.get("icon"):
            st.image(result["icon"], width=112)
        else:
            st.info("No icon available")

    with identity_col:
        st.markdown(f"### {result['app_name']}")
        st.write(f"**Developer:** {result.get('developer') or 'Not available'}")
        st.caption(f"Package ID: {result['app_id']}")

    info1, info2, info3, info4 = st.columns(4)
    info1.metric(
        "Google Play rating",
        (
            f"{result['rating']:.1f}/5"
            if result.get("rating") is not None
            else "Not available"
        ),
    )
    info2.metric(
        "Installs",
        result.get("installs_label") or format_number(result.get("installs")),
    )
    info3.metric("Ratings", format_number(result.get("ratings_count")))
    info4.metric("Store reviews", format_number(result.get("total_review_count")))

    detail1, detail2, detail3, detail4 = st.columns(4)
    detail1.metric("Category", result.get("genre") or "Not available")
    detail2.metric(
        "Content rating",
        result.get("content_rating") or "Not available",
    )
    detail3.metric("Contains ads", yes_no(result.get("contains_ads")))
    detail4.metric("In-app purchases", yes_no(result.get("offers_iap")))

    date1, date2, date3 = st.columns(3)
    date1.metric("Released", result.get("released") or "Not available")
    date2.metric("Last updated", result.get("updated") or "Not available")
    date3.metric("Version", result.get("version") or "Not available")

    st.markdown("#### Developer transparency assessment")
    st.progress(
        result["transparency_score"] / 100,
        text=(
            f"{result['transparency_level']}: "
            f"{result['transparency_score']}/100"
        ),
    )
    st.caption(
        "This is a metadata-completeness and maturity indicator. "
        "It does not verify the developer's identity or prove that the app is safe."
    )

    positive_col, warning_col = st.columns(2)

    with positive_col:
        st.markdown("##### Positive transparency signals")
        if result.get("developer_positive_signals"):
            for signal in result["developer_positive_signals"]:
                st.markdown(f"- ✅ {signal}")
        else:
            st.write("No positive metadata signals were available.")

    with warning_col:
        st.markdown("##### Items requiring verification")
        if result.get("developer_warning_signals"):
            for signal in result["developer_warning_signals"]:
                st.markdown(f"- ⚠️ {signal}")
        else:
            st.write("No metadata warnings were generated.")

    with st.expander("Developer contact and policy links"):
        st.write(
            f"**Support email:** "
            f"{result.get('developer_email') or 'Not available'}"
        )
        st.write(
            f"**Developer address:** "
            f"{result.get('developer_address') or 'Not available'}"
        )

        link_col1, link_col2 = st.columns(2)
        if result.get("developer_website"):
            link_col1.link_button(
                "Open developer website",
                result["developer_website"],
                use_container_width=True,
            )
        else:
            link_col1.info("Developer website unavailable")

        if result.get("privacy_policy"):
            link_col2.link_button(
                "Open privacy policy",
                result["privacy_policy"],
                use_container_width=True,
            )
        else:
            link_col2.warning("Privacy policy unavailable")


def format_history_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
        return parsed.strftime("%d %b %Y, %I:%M %p")
    except (TypeError, ValueError):
        return value


def build_history_csv(records: list[dict]) -> str:
    output = StringIO(newline="")
    fieldnames = [
        "analyzed_at",
        "app_name",
        "app_id",
        "developer",
        "risk_score",
        "risk_level",
        "transparency_score",
        "positive_percentage",
        "neutral_percentage",
        "negative_percentage",
        "reviews_analyzed",
        "rating",
        "summary",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for record in records:
        writer.writerow(
            {field: record.get(field) for field in fieldnames}
        )

    return output.getvalue()


def apk_risk_configuration(level: str) -> tuple[str, str, str]:
    if level == "Low":
        return "Lower permission exposure", "result-low", "✅"
    if level == "Medium":
        return "Moderate permission exposure", "result-medium", "⚠️"
    return "High permission exposure", "result-high", "🚨"


def render_apk_permission_result(result: dict) -> None:
    title, card_class, icon = apk_risk_configuration(
        result["permission_risk_level"]
    )

    st.markdown(
        f"""
        <section class="result-card {card_class}">
            <h2>{icon} {title}</h2>
            <p><strong>{escape(str(result['app_name']))}</strong></p>
            <p class="small-muted">
                Package: {escape(str(result['package_name']))}
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.progress(
        result["permission_risk_score"] / 100,
        text=(
            f"Permission exposure score: "
            f"{result['permission_risk_score']}/100"
        ),
    )
    st.caption(
        "This score measures declared sensitive access, not whether the app is "
        "malicious. A declared permission may never be granted or used."
    )

    st.progress(
        result["purpose_mismatch_score"] / 100,
        text=(
            f"Purpose mismatch score: "
            f"{result['purpose_mismatch_score']}/100"
        ),
    )
    st.caption(
        f"Compared against the selected purpose: {result['app_purpose']}."
    )

    overview1, overview2, overview3, overview4 = st.columns(4)
    overview1.metric(
        "Exposure level",
        result["permission_risk_level"],
    )
    overview2.metric(
        "Requested permissions",
        result["total_permissions"],
    )
    overview3.metric(
        "Target SDK",
        result["target_sdk"],
    )
    overview4.metric(
        "APK size",
        f"{result['file_size_mb']:.2f} MB",
    )

    st.subheader("Quick sensitive-permission check")
    st.caption(
        "This directly answers whether the APK declares common sensitive permissions."
    )

    quick_rows = []
    permission_lookup = {
        item["short_name"]: item
        for item in result["permissions"]
    }
    for check in result["quick_permission_check"]:
        permission_item = permission_lookup.get(check["permission"])
        quick_rows.append(
            {
                "Capability": check["capability"],
                "Requested": check["requested"],
                "Necessity": (
                    permission_item.get("necessity")
                    if permission_item
                    else "Not requested"
                ),
                "Permission": check["permission"],
            }
        )

    st.dataframe(
        quick_rows,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Permission necessity summary")
    necessity_columns = st.columns(4)
    for column, label in zip(
        necessity_columns,
        [
            "Expected",
            "Possibly justified",
            "Unusual",
            "Critical mismatch",
        ],
    ):
        column.metric(
            label,
            result["necessity_counts"].get(label, 0),
        )

    if result["necessity_counts"].get("Critical mismatch", 0):
        st.error(
            "One or more powerful permissions do not normally match the selected app purpose."
        )
    elif result["necessity_counts"].get("Unusual", 0):
        st.warning(
            "Some sensitive permissions are unusual for the selected app purpose and need explanation."
        )
    else:
        st.success(
            "No critical permission-purpose mismatch was detected by the current rules."
        )

    st.subheader("APK identity")
    identity1, identity2, identity3, identity4 = st.columns(4)
    identity1.metric("Version name", result["version_name"])
    identity2.metric("Version code", result["version_code"])
    identity3.metric("Minimum SDK", result["min_sdk"])
    identity4.metric("Main activity", result["main_activity"])

    with st.expander("File fingerprint and component counts"):
        st.code(result["sha256"], language=None)
        st.caption("SHA-256 fingerprint of the exact uploaded APK file.")
        count1, count2, count3, count4 = st.columns(4)
        count1.metric("Activities", result["activity_count"])
        count2.metric("Services", result["service_count"])
        count3.metric("Receivers", result["receiver_count"])
        count4.metric("Providers", result["provider_count"])

    st.subheader("Permission summary")
    severity_columns = st.columns(5)
    for column, severity in zip(
        severity_columns,
        ["Critical", "High", "Medium", "Review", "Common"],
    ):
        column.metric(
            severity,
            result["severity_counts"].get(severity, 0),
        )

    if result["combination_warnings"]:
        st.markdown("#### Permission-combination warnings")
        for warning in result["combination_warnings"]:
            st.warning(warning)

    if result["component_special_accesses"]:
        st.markdown("#### Special component access")
        st.caption(
            "These capabilities can be declared on Android components rather "
            "than as ordinary uses-permission entries."
        )
        component_rows = [
            {
                "Severity": item["severity"],
                "Capability": item["title"],
                "Component type": item["component_type"],
                "Component": item["component_name"],
                "Manifest permission": item["permission"],
            }
            for item in result["component_special_accesses"]
        ]
        st.dataframe(
            component_rows,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Permissions this APK may request")
    severity_filter = st.multiselect(
        "Show severity",
        ["Critical", "High", "Medium", "Review", "Common"],
        default=["Critical", "High", "Medium", "Review", "Common"],
        key="apk_permission_severity_filter",
    )

    filtered_permissions = [
        item
        for item in result["permissions"]
        if item["severity"] in severity_filter
    ]

    if not filtered_permissions:
        st.info("No permissions match the selected severity filters.")
    else:
        table_rows = [
            {
                "Severity": item["severity"],
                "Permission": item["short_name"],
                "Meaning": item["title"],
                "Necessity": item.get("necessity", "Not assessed"),
                "Special access": "Yes" if item["special_access"] else "No",
                "Custom": "Yes" if item["custom_permission"] else "No",
            }
            for item in filtered_permissions
        ]
        st.dataframe(
            table_rows,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Plain-language explanations")
        for item in filtered_permissions:
            with st.expander(
                f"{item['severity']} — {item['short_name']}: {item['title']}"
            ):
                st.write(
                    f"**Necessity for {result['app_purpose']}:** "
                    f"{item.get('necessity', 'Not assessed')}"
                )
                st.write(
                    f"**Why:** {item.get('necessity_reason', 'Not available')}"
                )
                st.write(f"**What it allows:** {item['explanation']}")
                st.write(f"**Possible legitimate use:** {item['legitimate_use']}")
                st.write(f"**What to verify:** {item['verify']}")
                st.code(item["full_name"], language=None)

    st.download_button(
        "⬇️ Download APK permission report",
        data=result["report_text"],
        file_name=(
            f"{result['package_name'].replace('.', '_')}_"
            "permission_report.txt"
        ),
        mime="text/plain",
        use_container_width=True,
    )

    st.warning(
        "AppVerity performed static manifest analysis only. The APK was not "
        "installed or executed. Requested permissions are not the same as "
        "permissions the user has actually granted."
    )

def build_report(result: dict) -> str:
    reason_lines = "\n".join(
        f"- {reason}" for reason in result.get("risk_reasons", [])
    ) or "- No specific explanation was produced."

    keyword_lines = "\n".join(
        (
            f"- {item['keyword']} ({item.get('language', 'Unknown')}): "
            f"{item['mentions']} review mention(s)"
        )
        for item in result.get("top_keywords", [])
    ) or "- No predefined warning phrases were detected."

    recommendations = "\n".join(
        f"- {item}" for item in safety_recommendations(result["risk_level"])
    )

    language_lines = "\n".join(
        (
            f"- {item['language']}: {item['reviews']} reviews "
            f"({item['percentage']:.1f}%)"
        )
        for item in result.get("language_distribution", [])
    ) or "- Language information was unavailable."

    language_sentiment_lines = "\n".join(
        (
            f"- {item['language']}: "
            f"positive {item['positive_percentage']:.1f}%, "
            f"neutral {item['neutral_percentage']:.1f}%, "
            f"negative {item['negative_percentage']:.1f}%"
        )
        for item in result.get("sentiment_by_language", [])
    ) or "- Language-specific sentiment was unavailable."

    return f"""
APPVERITY AI — EXPLAINABLE APP RISK REPORT
==========================================

Generated: {datetime.now().strftime("%d %B %Y, %I:%M %p")}
Application: {result['app_name']}
Application ID: {result['app_id']}
Developer: {result.get('developer') or 'Not available'}
Developer email: {result.get('developer_email') or 'Not available'}
Developer website: {result.get('developer_website') or 'Not available'}
Privacy policy: {result.get('privacy_policy') or 'Not available'}
Google Play rating: {result.get('rating') if result.get('rating') is not None else 'Not available'}
Installs: {result.get('installs_label') or result.get('installs') or 'Not available'}
Ratings: {result.get('ratings_count') or 'Not available'}
Category: {result.get('genre') or 'Not available'}
Content rating: {result.get('content_rating') or 'Not available'}
Released: {result.get('released') or 'Not available'}
Last updated: {result.get('updated') or 'Not available'}
Contains ads: {yes_no(result.get('contains_ads'))}
Offers in-app purchases: {yes_no(result.get('offers_iap'))}
Reviews analysed: {result['reviews_analyzed']}

DEVELOPER TRANSPARENCY
----------------------
Transparency score: {result.get('transparency_score', 0)}/100
Transparency level: {result.get('transparency_level', 'Not available')}

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

LANGUAGE DISTRIBUTION
---------------------
{language_lines}

SENTIMENT BY LANGUAGE
---------------------
{language_sentiment_lines}

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


try:
    history_db.initialize_database()
except history_db.HistoryDatabaseError as exc:
    st.error("AppVerity could not initialise its local history database.")
    st.code(str(exc))
    st.stop()


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


analyze_tab, apk_tab, history_tab, about_tab = st.tabs(
    [
        "🔍 Analyse app",
        "📦 APK permissions",
        "🕘 Saved history",
        "ℹ️ How it works",
    ]
)


with analyze_tab:
    st.subheader("Check a Google Play application")
    st.caption(
        "Paste a complete Google Play Store link. AppVerity AI analyses recent "
        "English, Hindi and Hinglish reviews from the Indian Google Play listing."
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
                    st.write("✓ Detecting English, Hindi and Hinglish review patterns")
                    st.write("✓ Measuring multilingual sentiment")
                    st.write("✓ Detecting predefined warning phrases")
                    st.write("✓ Calculating the explainable risk score")

                    result = fraud_detection.predict(app_id, review_count)

                    required_fields = {
                        "risk_score",
                        "risk_level",
                        "positive_percentage",
                        "neutral_percentage",
                        "negative_percentage",
                        "language_distribution",
                        "sentiment_by_language",
                        "risk_reasons",
                        "summary",
                        "transparency_score",
                        "transparency_level",
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

                render_developer_trust_panel(result)

                st.divider()
                st.subheader("Review-based risk assessment")

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

                st.subheader("Language coverage")
                language_rows = result["language_distribution"]

                language_metric_columns = st.columns(
                    max(1, len(language_rows))
                )
                for column, item in zip(language_metric_columns, language_rows):
                    column.metric(
                        item["language"],
                        f"{item['reviews']} reviews",
                        f"{item['percentage']:.1f}%",
                    )

                st.bar_chart(
                    language_rows,
                    x="language",
                    y="reviews",
                )

                st.markdown("#### Sentiment by language")
                language_sentiment_table = [
                    {
                        "Language": item["language"],
                        "Reviews": item["reviews"],
                        "Positive": f"{item['positive_percentage']:.1f}%",
                        "Neutral": f"{item['neutral_percentage']:.1f}%",
                        "Negative": f"{item['negative_percentage']:.1f}%",
                    }
                    for item in result["sentiment_by_language"]
                ]
                st.dataframe(
                    language_sentiment_table,
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(
                    "Language detection is rule-based. Hindi uses Devanagari "
                    "script detection; Hinglish uses common transliterated Hindi "
                    "vocabulary and phrases."
                )

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
                            "Language": item.get("language", "Unknown"),
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

                try:
                    history_id = history_db.save_analysis(result, report)
                    st.success(
                        "Analysis saved permanently in local history "
                        f"(record #{history_id})."
                    )
                except history_db.HistoryDatabaseError as history_error:
                    st.warning(
                        "The analysis completed, but it could not be saved "
                        "to local history."
                    )
                    st.code(str(history_error))

            except Exception as exc:
                st.error(
                    "The application could not be analysed. Confirm that the "
                    "listing exists, check your internet connection and try again."
                )
                with st.expander("Technical error"):
                    st.code(str(exc))



with apk_tab:
    st.subheader("APK Permission Risk Analyzer")
    st.write(
        "Upload an Android APK to inspect the permissions and special access "
        "declared in its manifest. AppVerity does not install or execute the file."
    )

    uploaded_apk = st.file_uploader(
        "Upload Android APK",
        type=["apk"],
        accept_multiple_files=False,
        help="Maximum supported size: 200 MB.",
        key="apk_permission_upload",
    )

    if uploaded_apk is None:
        st.info(
            "Choose an APK file to view package information, permission "
            "explanations, sensitive-access warnings, and a downloadable report."
        )
    else:
        file_size_mb = uploaded_apk.size / (1024 * 1024)
        file1, file2 = st.columns(2)
        file1.metric("Selected file", uploaded_apk.name)
        file2.metric("File size", f"{file_size_mb:.2f} MB")

        selected_app_purpose = st.selectbox(
            "What type of application is this?",
            apk_permission_analyzer.APP_PURPOSES,
            index=0,
            help=(
                "AppVerity compares requested permissions with the expected "
                "needs of the selected app type."
            ),
            key="apk_app_purpose",
        )

        analyse_apk_clicked = st.button(
            "Analyse APK permissions",
            type="primary",
            use_container_width=True,
            key="analyse_apk_permissions_button",
        )

        if analyse_apk_clicked:
            try:
                with st.status(
                    "Reading the APK manifest...",
                    expanded=True,
                ) as apk_status:
                    st.write("✓ Validating APK archive structure")
                    st.write("✓ Calculating SHA-256 fingerprint")
                    st.write("✓ Extracting package and Android version details")
                    st.write("✓ Classifying requested permissions")
                    st.write("✓ Checking supported special component access")

                    apk_result = apk_permission_analyzer.analyze_apk(
                        uploaded_apk.getvalue(),
                        uploaded_apk.name,
                        selected_app_purpose,
                    )
                    st.session_state["apk_permission_result"] = apk_result

                    apk_status.update(
                        label="APK permission analysis completed",
                        state="complete",
                        expanded=False,
                    )
            except apk_permission_analyzer.APKAnalysisError as exc:
                st.session_state.pop("apk_permission_result", None)
                st.error(str(exc))
            except Exception as exc:
                st.session_state.pop("apk_permission_result", None)
                st.error("The APK could not be analysed.")
                with st.expander("Technical error"):
                    st.code(str(exc))

        apk_result = st.session_state.get("apk_permission_result")
        if (
            apk_result
            and apk_result.get("file_name") == uploaded_apk.name
            and apk_result.get("file_size_bytes") == uploaded_apk.size
            and apk_result.get("app_purpose") == selected_app_purpose
        ):
            render_apk_permission_result(apk_result)

with history_tab:
    st.subheader("Persistent analysis history")
    st.caption(
        "Analyses are saved locally in database/appverity_history.db and "
        "remain available after Streamlit is restarted."
    )

    try:
        stats = history_db.get_history_stats()
    except history_db.HistoryDatabaseError as exc:
        st.error("Saved history could not be loaded.")
        st.code(str(exc))
        stats = {
            "total": 0,
            "unique_apps": 0,
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
        }

    stat1, stat2, stat3, stat4 = st.columns(4)
    stat1.metric("Saved analyses", stats["total"])
    stat2.metric("Unique apps", stats["unique_apps"])
    stat3.metric("High-risk results", stats["high_risk"])
    stat4.metric("Medium-risk results", stats["medium_risk"])

    search_col, filter_col = st.columns([3, 1])
    with search_col:
        history_search = st.text_input(
            "Search saved analyses",
            placeholder="Search by app name, package ID or developer",
            key="history_search",
        )
    with filter_col:
        history_risk_filter = st.selectbox(
            "Risk level",
            ["All", "High", "Medium", "Low"],
            key="history_risk_filter",
        )

    try:
        history_records = history_db.list_analyses(
            search=history_search,
            risk_level=history_risk_filter,
        )
    except history_db.HistoryDatabaseError as exc:
        st.error("Saved analyses could not be loaded.")
        st.code(str(exc))
        history_records = []

    if history_records:
        st.download_button(
            "⬇️ Export filtered history as CSV",
            data=build_history_csv(history_records),
            file_name="appverity_analysis_history.csv",
            mime="text/csv",
            use_container_width=True,
        )

    tracked_apps = history_db.list_tracked_apps()
    if tracked_apps:
        st.markdown("### Risk changes over time")
        option_to_app_id = {
            (
                f"{item['app_name']} ({item['app_id']}) — "
                f"{item['analysis_count']} saved"
            ): item["app_id"]
            for item in tracked_apps
        }
        selected_label = st.selectbox(
            "Select an application",
            list(option_to_app_id),
            key="history_trend_app",
        )
        trend_rows = history_db.get_app_trend(
            option_to_app_id[selected_label]
        )

        if len(trend_rows) >= 2:
            chart_rows = [
                {
                    "Analysed": datetime.fromisoformat(item["analyzed_at"]),
                    "Risk score": item["risk_score"],
                    "Transparency score": item["transparency_score"],
                    "Negative reviews": item["negative_percentage"],
                }
                for item in trend_rows
            ]
            st.line_chart(
                chart_rows,
                x="Analysed",
                y=[
                    "Risk score",
                    "Transparency score",
                    "Negative reviews",
                ],
            )
        else:
            st.info(
                "Analyse this application again later to compare how its "
                "risk signals change over time."
            )

    st.markdown("### Saved records")

    if not history_records:
        st.info("No saved analyses match the current search and filter.")
    else:
        for number, item in enumerate(history_records, start=1):
            with st.expander(
                f"{number}. {item['app_name']} — "
                f"{item['risk_level']} ({item['risk_score']}/100)"
            ):
                detail1, detail2, detail3, detail4 = st.columns(4)
                detail1.metric("Risk score", f"{item['risk_score']}/100")
                detail2.metric("Risk level", item["risk_level"])
                detail3.metric(
                    "Transparency",
                    f"{item['transparency_score']}/100",
                )
                detail4.metric(
                    "Reviews analysed",
                    f"{item['reviews_analyzed']:,}",
                )

                st.write(f"**Application ID:** {item['app_id']}")
                st.write(
                    f"**Developer:** "
                    f"{item.get('developer') or 'Not available'}"
                )
                st.write(
                    f"**Analysed:** "
                    f"{format_history_time(item['analyzed_at'])}"
                )

                sentiment1, sentiment2, sentiment3 = st.columns(3)
                sentiment1.metric(
                    "Positive",
                    f"{item['positive_percentage']:.1f}%",
                )
                sentiment2.metric(
                    "Neutral",
                    f"{item['neutral_percentage']:.1f}%",
                )
                sentiment3.metric(
                    "Negative",
                    f"{item['negative_percentage']:.1f}%",
                )

                st.write(item["summary"])

                saved_analysis = history_db.get_analysis(item["id"])
                if saved_analysis:
                    saved_result = saved_analysis.get("result", {})
                    reasons = saved_result.get("risk_reasons", [])
                    if reasons:
                        st.markdown("#### Saved risk reasons")
                        for reason in reasons:
                            st.markdown(f"- {reason}")

                    st.download_button(
                        "Download saved report",
                        data=saved_analysis["report_text"],
                        file_name=(
                            f"{item['app_id']}_"
                            f"history_{item['id']}_report.txt"
                        ),
                        mime="text/plain",
                        key=f"history_report_{item['id']}",
                    )

                confirm_delete = st.checkbox(
                    "Confirm deletion of this saved record",
                    key=f"confirm_history_delete_{item['id']}",
                )
                if st.button(
                    "Delete this record",
                    key=f"delete_history_{item['id']}",
                    disabled=not confirm_delete,
                ):
                    history_db.delete_analysis(item["id"])
                    st.success("The saved record was deleted.")
                    st.rerun()

    with st.expander("History management"):
        st.warning(
            "Deleting history removes only your locally saved analysis "
            "records. It does not change the application or GitHub repository."
        )
        confirm_clear = st.checkbox(
            "I understand that all saved analyses will be permanently deleted.",
            key="confirm_clear_history",
        )
        if st.button(
            "Delete all saved analyses",
            disabled=not confirm_clear,
            key="clear_all_history",
        ):
            deleted_count = history_db.clear_history()
            st.success(f"Deleted {deleted_count} saved analysis record(s).")
            st.rerun()


with about_tab:
    st.subheader("How AppVerity AI works")

    step1, step2, step3, step4 = st.columns(4)

    with step1:
        st.markdown("### 1. Collect")
        st.write("Retrieves recent public reviews and app metadata from Google Play.")

    with step2:
        st.markdown("### 2. Analyse")
        st.write(
            "Uses VADER for English and transparent Hindi/Hinglish phrase, "
            "script, rating and translated-sentiment rules."
        )

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

    st.markdown(
        """
        ### Developer transparency panel

        AppVerity also shows public Google Play listing metadata such as the
        developer contact details, privacy-policy availability, release date,
        update recency, install count and rating volume. The transparency score
        measures metadata completeness and app maturity; it is not identity
        verification.
        """
    )

    st.markdown(
        """
        ### APK permission analysis

        The APK tab performs static manifest analysis. It extracts the package,
        version, Android SDK requirements, SHA-256 fingerprint, declared
        permissions, supported component-level special access, and permission
        combinations that deserve closer verification. The APK is never
        installed or executed.

        The permission score measures potential exposure, not maliciousness.
        The purpose mismatch checker compares declared permissions with a selected
        app category and labels them Expected, Possibly justified, Unusual, or
        Critical mismatch. These labels are heuristic and should be reviewed with
        the app's documented features.

        Actual access depends on Android version, runtime approval, special
        settings, the app's role, and device policy.
        """
    )

    st.markdown(
        """
        ### Multilingual and Hinglish analysis

        Reviews are classified as English, Hindi or Hinglish using transparent
        script and vocabulary rules. Common Hindi and transliterated Hinglish
        fraud, payment, refund, withdrawal, account and support phrases are
        included in sentiment and warning analysis. This is a heuristic system,
        not a general-purpose machine translation model.
        """
    )

    st.markdown(
        """
        ### Persistent local history

        Completed analyses are stored in a local SQLite database. The saved
        history supports search, risk-level filtering, CSV export, saved-report
        downloads, record deletion and trend comparison when the same app is
        analysed more than once.
        """
    )

    st.warning(
        "AppVerity AI provides an automated risk indication. Reviews can be "
        "incomplete, manipulated, biased or unrelated to fraud. The result does "
        "not prove that an application is fraudulent or guarantee that it is safe."
    )
