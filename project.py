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
import ui_theme


st.set_page_config(
    page_title="AppVerity AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


ui_theme.apply_theme()

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
    st.markdown("### Developer and listing profile")

    identity_left, identity_main, identity_score = st.columns([1, 4.2, 1.35])

    with identity_left:
        if result.get("icon"):
            st.image(result["icon"], width=104)
        else:
            st.markdown(
                """
                <div class="av-app-icon-placeholder">APP</div>
                """,
                unsafe_allow_html=True,
            )

    with identity_main:
        st.markdown(
            f"""
            <div class="av-app-identity">
                <h2>{escape(str(result['app_name']))}</h2>
                <p>{escape(str(result.get('developer') or 'Developer unavailable'))}</p>
                <div class="av-chip-row">
                    <span class="av-chip">
                        {escape(str(result.get('genre') or 'Category unavailable'))}
                    </span>
                    <span class="av-chip">
                        {escape(str(result.get('content_rating') or 'Content rating unavailable'))}
                    </span>
                    <span class="av-chip">
                        {escape(str(result['app_id']))}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with identity_score:
        st.markdown(
            f"""
            <article class="av-transparency-score">
                <span>{result['transparency_score']}</span>
                <strong>/100</strong>
                <small>{escape(str(result['transparency_level']))}</small>
            </article>
            """,
            unsafe_allow_html=True,
        )

    listing_metrics = st.columns(4)
    listing_values = [
        (
            "Google Play rating",
            (
                f"{result['rating']:.1f}/5"
                if result.get("rating") is not None
                else "Not available"
            ),
        ),
        (
            "Installs",
            result.get("installs_label")
            or format_number(result.get("installs")),
        ),
        ("Ratings", format_number(result.get("ratings_count"))),
        ("Last updated", result.get("updated") or "Not available"),
    ]
    for column, (label, value) in zip(
        listing_metrics,
        listing_values,
    ):
        column.metric(label, value)

    transparency_tab, listing_tab, contact_tab = st.tabs(
        [
            "Transparency signals",
            "Listing details",
            "Contact and policy",
        ]
    )

    with transparency_tab:
        st.progress(
            result["transparency_score"] / 100,
            text=(
                f"{result['transparency_level']} · "
                f"{result['transparency_score']}/100"
            ),
        )
        st.caption(
            "This measures listing completeness and maturity. It does not verify the developer's identity."
        )

        positive_col, warning_col = st.columns(2)

        with positive_col:
            st.markdown("#### Positive signals")
            if result.get("developer_positive_signals"):
                for signal in result["developer_positive_signals"]:
                    st.success(signal)
            else:
                st.info("No positive metadata signals were available.")

        with warning_col:
            st.markdown("#### Items to verify")
            if result.get("developer_warning_signals"):
                for signal in result["developer_warning_signals"]:
                    st.warning(signal)
            else:
                st.success("No metadata warnings were generated.")

    with listing_tab:
        detail_columns = st.columns(3)
        detail_values = [
            ("Released", result.get("released") or "Not available"),
            ("Version", result.get("version") or "Not available"),
            (
                "Store reviews",
                format_number(result.get("total_review_count")),
            ),
            ("Contains ads", yes_no(result.get("contains_ads"))),
            (
                "In-app purchases",
                yes_no(result.get("offers_iap")),
            ),
            (
                "Purchase range",
                result.get("in_app_product_price") or "Not available",
            ),
        ]
        for index, (label, value) in enumerate(detail_values):
            detail_columns[index % 3].metric(label, value)

    with contact_tab:
        contact_left, contact_right = st.columns(2)

        with contact_left:
            st.markdown("#### Developer contact")
            st.write(
                f"**Support email:** "
                f"{result.get('developer_email') or 'Not available'}"
            )
            st.write(
                f"**Address:** "
                f"{result.get('developer_address') or 'Not available'}"
            )

        with contact_right:
            st.markdown("#### Public links")
            if result.get("developer_website"):
                st.link_button(
                    "Open developer website",
                    result["developer_website"],
                    use_container_width=True,
                )
            else:
                st.info("Developer website unavailable")

            if result.get("privacy_policy"):
                st.link_button(
                    "Open privacy policy",
                    result["privacy_policy"],
                    use_container_width=True,
                )
            else:
                st.warning("Privacy policy unavailable")

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
        <section class="av-apk-result-hero {card_class}">
            <div>
                <div class="av-eyebrow">APK permission assessment</div>
                <h2>{icon} {escape(str(result['app_name']))}</h2>
                <p>{escape(str(result['package_name']))}</p>
            </div>
            <div class="av-result-score-badge">
                <span>{result['permission_risk_score']}</span>
                <small>/100 exposure</small>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Static manifest analysis only. The APK was not installed or executed."
    )

    permission_lookup = {
        item["short_name"]: item
        for item in result["permissions"]
    }

    quick_icon_map = {
        "Microphone": "🎤",
        "Camera": "📷",
        "Read SMS": "💬",
        "Contacts": "👥",
        "Background location": "📍",
        "Accessibility service": "♿",
        "Receive SMS": "📨",
        "Send SMS": "✉️",
        "Precise location": "🧭",
        "Display over other apps": "◫",
        "Install unknown apps": "⬇️",
        "Manage all files": "🗂️",
    }

    primary_capabilities = [
        "Microphone",
        "Camera",
        "Read SMS",
        "Contacts",
        "Background location",
        "Accessibility service",
    ]

    quick_items = {
        item["capability"]: item
        for item in result["quick_permission_check"]
    }

    st.markdown("### Sensitive permissions at a glance")
    st.caption(
        "The first row directly answers the most important permission questions."
    )

    quick_columns = st.columns(3)
    for index, capability in enumerate(primary_capabilities):
        check = quick_items.get(
            capability,
            {
                "capability": capability,
                "permission": "",
                "requested": "No",
            },
        )
        permission_item = permission_lookup.get(check["permission"])
        requested = check["requested"] == "Yes"

        if not requested:
            necessity = "Not requested"
            state_class = "av-permission-not-requested"
        else:
            necessity = permission_item.get(
                "necessity",
                "Needs review",
            )
            state_class = {
                "Expected": "av-permission-expected",
                "Possibly justified": "av-permission-possible",
                "Unusual": "av-permission-unusual",
                "Critical mismatch": "av-permission-critical",
            }.get(necessity, "av-permission-possible")

        icon_text = quick_icon_map.get(capability, "•")

        with quick_columns[index % 3]:
            st.markdown(
                f"""
                <article class="av-permission-card {state_class}">
                    <div class="av-permission-card-top">
                        <span class="av-permission-icon">{icon_text}</span>
                        <span class="av-requested-pill">
                            {"REQUESTED" if requested else "NOT REQUESTED"}
                        </span>
                    </div>
                    <h3>{escape(capability)}</h3>
                    <p>{escape(necessity)}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("View all sensitive permission checks"):
        additional_rows = []
        for check in result["quick_permission_check"]:
            if check["capability"] in primary_capabilities:
                continue

            permission_item = permission_lookup.get(check["permission"])
            additional_rows.append(
                {
                    "Capability": check["capability"],
                    "Requested": check["requested"],
                    "Assessment": (
                        permission_item.get("necessity")
                        if permission_item
                        else "Not requested"
                    ),
                    "Permission": check["permission"],
                }
            )

        if additional_rows:
            st.dataframe(
                additional_rows,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No additional sensitive permission checks are available.")

    st.markdown("### Risk and necessity summary")
    score_left, score_right = st.columns(2)

    with score_left:
        st.markdown(
            """
            <div class="av-score-heading">
                <span>Permission exposure</span>
                <small>Sensitive access declared by the APK</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(
            result["permission_risk_score"] / 100,
            text=(
                f"{result['permission_risk_score']}/100 · "
                f"{result['permission_risk_level']}"
            ),
        )

    with score_right:
        st.markdown(
            """
            <div class="av-score-heading">
                <span>Purpose mismatch</span>
                <small>How well permissions fit the selected app type</small>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(
            result["purpose_mismatch_score"] / 100,
            text=f"{result['purpose_mismatch_score']}/100",
        )

    st.caption(
        f"Compared against the selected purpose: **{result['app_purpose']}**."
    )

    necessity_columns = st.columns(4)
    necessity_items = [
        ("Expected", "✓", "av-mini-success"),
        ("Possibly justified", "?", "av-mini-info"),
        ("Unusual", "!", "av-mini-warning"),
        ("Critical mismatch", "×", "av-mini-danger"),
    ]
    for column, (label, symbol, style_class) in zip(
        necessity_columns,
        necessity_items,
    ):
        with column:
            st.markdown(
                f"""
                <article class="av-mini-stat {style_class}">
                    <span>{symbol}</span>
                    <strong>{result['necessity_counts'].get(label, 0)}</strong>
                    <small>{escape(label)}</small>
                </article>
                """,
                unsafe_allow_html=True,
            )

    if result["necessity_counts"].get("Critical mismatch", 0):
        st.error(
            "Powerful permissions were found that do not normally match the selected app purpose."
        )
    elif result["necessity_counts"].get("Unusual", 0):
        st.warning(
            "Some sensitive permissions are unusual for the selected app purpose and need explanation."
        )
    else:
        st.success(
            "No critical permission-purpose mismatch was detected by the current rules."
        )

    st.markdown("### APK identity and technical overview")
    identity_columns = st.columns(4)
    identity_values = [
        ("Version", result["version_name"]),
        ("Target SDK", result["target_sdk"]),
        ("Minimum SDK", result["min_sdk"]),
        ("APK size", f"{result['file_size_mb']:.2f} MB"),
    ]
    for column, (label, value) in zip(identity_columns, identity_values):
        column.metric(label, value)

    with st.expander("File fingerprint and Android component counts"):
        st.code(result["sha256"], language=None)
        st.caption("SHA-256 fingerprint of the exact uploaded APK.")
        count1, count2, count3, count4 = st.columns(4)
        count1.metric("Activities", result["activity_count"])
        count2.metric("Services", result["service_count"])
        count3.metric("Receivers", result["receiver_count"])
        count4.metric("Providers", result["provider_count"])
        st.write(f"**Main activity:** {result['main_activity']}")
        st.write(f"**Version code:** {result['version_code']}")

    st.markdown("### Permission severity")
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
        st.markdown("### Permission-combination warnings")
        for warning in result["combination_warnings"]:
            st.warning(warning)

    if result["component_special_accesses"]:
        st.markdown("### Special component access")
        st.caption(
            "These capabilities can be declared on Android components rather than as ordinary permissions."
        )
        component_rows = [
            {
                "Severity": item["severity"],
                "Capability": item["title"],
                "Component type": item["component_type"],
                "Component": item["component_name"],
            }
            for item in result["component_special_accesses"]
        ]
        st.dataframe(
            component_rows,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Detailed permissions")
    necessity_filter = st.radio(
        "Filter by necessity",
        [
            "All",
            "Critical mismatch",
            "Unusual",
            "Possibly justified",
            "Expected",
        ],
        horizontal=True,
        key="apk_necessity_filter",
    )

    severity_filter = st.multiselect(
        "Filter by access severity",
        ["Critical", "High", "Medium", "Review", "Common"],
        default=["Critical", "High", "Medium", "Review", "Common"],
        key="apk_permission_severity_filter",
    )

    filtered_permissions = [
        item
        for item in result["permissions"]
        if item["severity"] in severity_filter
        and (
            necessity_filter == "All"
            or item.get("necessity") == necessity_filter
        )
    ]

    if not filtered_permissions:
        st.info("No permissions match the selected filters.")
    else:
        table_rows = [
            {
                "Permission": item["short_name"],
                "Necessity": item.get("necessity", "Not assessed"),
                "Access severity": item["severity"],
                "Meaning": item["title"],
                "Special access": "Yes" if item["special_access"] else "No",
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
                f"{item.get('necessity', 'Review')} · "
                f"{item['short_name']} — {item['title']}"
            ):
                st.write(
                    f"**Fit for {result['app_purpose']}:** "
                    f"{item.get('necessity', 'Not assessed')}"
                )
                st.write(
                    f"**Why:** "
                    f"{item.get('necessity_reason', 'Not available')}"
                )
                st.write(f"**What it allows:** {item['explanation']}")
                st.write(
                    f"**Possible legitimate use:** "
                    f"{item['legitimate_use']}"
                )
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
        "Requested permissions are not the same as permissions already granted by a user."
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

def render_home_page() -> None:
    ui_theme.render_home_hero()

    action_left, action_right = st.columns(2)
    with action_left:
        st.page_link(
            PLAY_STORE_PAGE,
            label="🔍  Analyse a Play Store application",
            help="Review risk, developer transparency, language and complaint analysis.",
            use_container_width=True,
        )
    with action_right:
        st.page_link(
            APK_PAGE,
            label="📦  Inspect an Android APK",
            help="Check camera, microphone, SMS, contacts, location and other permissions.",
            use_container_width=True,
        )

    ui_theme.render_section_heading(
        "One workspace, four layers of evidence",
        "AppVerity separates evidence into clear modules instead of forcing a single unexplained verdict.",
    )

    feature_columns = st.columns(4)
    features = [
        (
            "◉",
            "Review intelligence",
            "Measure sentiment, complaints, warning phrases, recent trends and evidence coverage.",
        ),
        (
            "⌁",
            "APK permission scanner",
            "Inspect declared permissions without installing or executing the uploaded APK.",
        ),
        (
            "अ",
            "Multilingual analysis",
            "Understand English, Hindi and Hinglish complaint and payment-risk patterns.",
        ),
        (
            "◇",
            "Explainable assessment",
            "See why a score was produced and which factors require manual verification.",
        ),
    ]
    for column, feature in zip(feature_columns, features):
        with column:
            ui_theme.render_feature_card(*feature)

    try:
        stats = history_db.get_history_stats()
        recent_records = history_db.list_analyses(limit=3)
    except history_db.HistoryDatabaseError:
        stats = {
            "total": 0,
            "unique_apps": 0,
            "high_risk": 0,
        }
        recent_records = []

    ui_theme.render_section_heading(
        "Your local investigation dashboard",
        "Saved Play Store analyses remain on this device in the local SQLite history.",
    )

    stat_columns = st.columns(4)
    stat_values = [
        ("Saved analyses", stats.get("total", 0), "Persistent local records"),
        ("Unique apps", stats.get("unique_apps", 0), "Distinct package IDs checked"),
        ("High-risk results", stats.get("high_risk", 0), "Strong review-risk signals"),
        ("APK scanner", "Ready", "Static permission analysis"),
    ]
    for column, stat in zip(stat_columns, stat_values):
        with column:
            ui_theme.render_stat_card(*stat)

    recent_left, safety_right = st.columns([1.45, 1])
    with recent_left:
        ui_theme.render_section_heading(
            "Recent analyses",
            "Your latest saved Play Store assessments.",
        )
        if recent_records:
            for record in recent_records:
                ui_theme.render_recent_analysis(record)
            st.page_link(
                HISTORY_PAGE,
                label="Open all saved reports",
                icon="🕘",
                use_container_width=True,
            )
        else:
            st.info(
                "No saved analyses yet. Analyse a Play Store application to build your dashboard."
            )

    with safety_right:
        ui_theme.render_section_heading(
            "Safety by design",
            "What AppVerity does—and what it deliberately avoids.",
        )
        st.success(
            "APK uploads are read statically. They are not installed or executed."
        )
        st.info(
            "Results are risk indicators, not definitive accusations of fraud."
        )
        st.warning(
            "A declared permission does not mean the user granted or used it."
        )

    ui_theme.render_section_heading(
        "How an AppVerity assessment works",
        "A simple evidence-first workflow designed for non-technical users.",
    )

    step_columns = st.columns(3)
    steps = [
        (
            1,
            "Provide an app or APK",
            "Paste a Play Store link or upload an Android APK from a source you trust.",
        ),
        (
            2,
            "Inspect multiple signals",
            "AppVerity examines reviews, languages, metadata, permissions and purpose mismatches.",
        ),
        (
            3,
            "Review the evidence",
            "Use explanations, reports and warning signals to make a safer decision.",
        ),
    ]
    for column, step in zip(step_columns, steps):
        with column:
            ui_theme.render_step(*step)



def render_play_store_page() -> None:
    ui_theme.render_page_header(
        "Play Store intelligence",
        "Analyse a Google Play application",
        "Review sentiment, multilingual complaints, developer transparency and explainable risk signals.",
    )

    st.markdown(
        """
        <section class="av-analysis-intro">
            <div class="av-analysis-intro-icon">🔍</div>
            <div>
                <h2>Start with a Google Play link</h2>
                <p>
                    AppVerity analyses recent English, Hindi and Hinglish reviews,
                    public listing metadata and developer transparency signals.
                </p>
                <div class="av-chip-row">
                    <span class="av-chip">Review intelligence</span>
                    <span class="av-chip">Multilingual NLP</span>
                    <span class="av-chip">Explainable scoring</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    with st.form("analysis_form"):
        app_url = st.text_input(
            "Google Play Store URL",
            placeholder=(
                "https://play.google.com/store/apps/details"
                "?id=com.example.application"
            ),
        )

        review_count = st.radio(
            "Reviews to analyse",
            options=[100, 250, 500, 1000, 2000],
            index=1,
            horizontal=True,
            help="Use 100 or 250 reviews for a faster first test.",
        )

        submitted = st.form_submit_button(
            "Analyse application",
            type="primary",
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
                    "Building the AppVerity assessment...",
                    expanded=True,
                ) as analysis_status:
                    st.write("✓ Validating the Google Play listing")
                    st.write("✓ Collecting recent reviews")
                    st.write("✓ Detecting English, Hindi and Hinglish")
                    st.write("✓ Measuring multilingual sentiment")
                    st.write("✓ Finding complaint and warning patterns")
                    st.write("✓ Evaluating developer transparency")
                    st.write("✓ Preparing the explainable result")

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

                    report = build_report(result)

                    history_id = None
                    history_error_message = None
                    try:
                        history_id = history_db.save_analysis(
                            result,
                            report,
                        )
                    except history_db.HistoryDatabaseError as history_error:
                        history_error_message = str(history_error)

                    st.session_state["play_store_result"] = result
                    st.session_state["play_store_report"] = report
                    st.session_state["play_store_history_id"] = history_id
                    st.session_state[
                        "play_store_history_error"
                    ] = history_error_message

                    analysis_status.update(
                        label="AppVerity assessment completed",
                        state="complete",
                        expanded=False,
                    )

            except Exception as exc:
                st.error(
                    "The application could not be analysed. Confirm that the "
                    "listing exists, check your internet connection and try again."
                )
                with st.expander("Technical error"):
                    st.code(str(exc))

    result = st.session_state.get("play_store_result")
    if not result:
        st.markdown("### What the assessment includes")
        preview_columns = st.columns(3)
        previews = [
            (
                "◉",
                "Review risk",
                "Sentiment, complaint phrases and recent negative-review trends.",
            ),
            (
                "अ",
                "Language intelligence",
                "English, Hindi and Hinglish review coverage and sentiment.",
            ),
            (
                "◇",
                "Developer transparency",
                "Listing maturity, contact details, policy links and update recency.",
            ),
        ]
        for column, preview in zip(preview_columns, previews):
            with column:
                ui_theme.render_feature_card(*preview)
        return

    report = st.session_state.get(
        "play_store_report",
        build_report(result),
    )

    action_left, action_right = st.columns([5, 1])
    with action_right:
        if st.button(
            "Clear result",
            use_container_width=True,
            key="clear_play_store_result",
        ):
            for key in (
                "play_store_result",
                "play_store_report",
                "play_store_history_id",
                "play_store_history_error",
            ):
                st.session_state.pop(key, None)
            st.rerun()

    risk_title, risk_class, risk_icon = risk_configuration(
        result["risk_level"]
    )
    risk_style = {
        "Low": "av-risk-low-surface",
        "Medium": "av-risk-medium-surface",
        "High": "av-risk-high-surface",
    }.get(result["risk_level"], "av-risk-medium-surface")

    evidence_label = (
        "Strong"
        if result["reviews_analyzed"] >= 500
        else "Moderate"
        if result["reviews_analyzed"] >= 250
        else "Limited"
    )

    st.markdown(
        f"""
        <section class="av-review-result-hero {risk_style}">
            <div class="av-review-result-identity">
                <div class="av-eyebrow">Explainable review assessment</div>
                <h2>{risk_icon} {escape(str(result['app_name']))}</h2>
                <p>
                    {escape(str(result.get('developer') or 'Developer unavailable'))}
                    · {escape(str(result['app_id']))}
                </p>
                <span class="av-result-label">
                    {escape(risk_title)}
                </span>
            </div>
            <div class="av-review-score">
                <span>{result['risk_score']}</span>
                <strong>/100</strong>
                <small>{escape(str(result['risk_level']))} review risk</small>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    score_columns = st.columns(4)
    score_values = [
        (
            "Review risk",
            f"{result['risk_score']}/100",
            result["risk_level"],
        ),
        (
            "Developer transparency",
            f"{result['transparency_score']}/100",
            result["transparency_level"],
        ),
        (
            "Evidence coverage",
            evidence_label,
            f"{result['reviews_analyzed']:,} reviews analysed",
        ),
        (
            "Google Play rating",
            (
                f"{result['rating']:.1f}/5"
                if result.get("rating") is not None
                else "Not available"
            ),
            result.get("installs_label") or "Install count unavailable",
        ),
    ]
    for column, (label, value, note) in zip(
        score_columns,
        score_values,
    ):
        with column:
            st.markdown(
                f"""
                <article class="av-score-summary-card">
                    <small>{escape(str(label))}</small>
                    <strong>{escape(str(value))}</strong>
                    <p>{escape(str(note))}</p>
                </article>
                """,
                unsafe_allow_html=True,
            )

    history_id = st.session_state.get("play_store_history_id")
    history_error_message = st.session_state.get(
        "play_store_history_error"
    )
    if history_id:
        st.success(
            f"Saved to local history as record #{history_id}."
        )
    elif history_error_message:
        st.warning(
            "The analysis completed, but it could not be saved to history."
        )

    overview_tab, intelligence_tab, developer_tab, report_tab = st.tabs(
        [
            "Overview",
            "Review intelligence",
            "Developer profile",
            "Report and safety",
        ]
    )

    with overview_tab:
        st.markdown("### Why AppVerity gave this score")
        reasons = result.get("risk_reasons", [])

        for row_start in range(0, len(reasons), 3):
            reason_columns = st.columns(3)
            for offset, reason in enumerate(
                reasons[row_start : row_start + 3]
            ):
                with reason_columns[offset]:
                    st.markdown(
                        f"""
                        <article class="av-reason-card">
                            <div class="av-reason-number">
                                {row_start + offset + 1}
                            </div>
                            <p>{escape(str(reason))}</p>
                        </article>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("### Sentiment overview")
        sentiment_columns = st.columns(3)
        sentiment_values = [
            (
                "Positive",
                result["positive_percentage"],
                "av-sentiment-positive",
            ),
            (
                "Neutral",
                result["neutral_percentage"],
                "av-sentiment-neutral",
            ),
            (
                "Negative",
                result["negative_percentage"],
                "av-sentiment-negative",
            ),
        ]
        for column, (label, value, css_class) in zip(
            sentiment_columns,
            sentiment_values,
        ):
            with column:
                st.markdown(
                    f"""
                    <article class="av-sentiment-card {css_class}">
                        <small>{label}</small>
                        <strong>{value:.1f}%</strong>
                    </article>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("### Recent complaint trend")
        trend_columns = st.columns(3)
        trend_columns[0].metric(
            "Recent negative",
            f"{result['recent_negative_percentage']:.1f}%",
        )
        trend_columns[1].metric(
            "Older negative",
            f"{result['older_negative_percentage']:.1f}%",
        )
        trend_columns[2].metric(
            "Difference",
            f"{result['trend_change']:+.1f} pp",
            help="Positive means recent reviews were more negative.",
        )

        st.info(result["summary"])

    with intelligence_tab:
        sentiment_left, language_right = st.columns(2)

        with sentiment_left:
            st.markdown("### Sentiment distribution")
            sentiment_chart = {
                "Sentiment": [
                    "Positive",
                    "Neutral",
                    "Negative",
                ],
                "Percentage": [
                    result["positive_percentage"],
                    result["neutral_percentage"],
                    result["negative_percentage"],
                ],
            }
            st.bar_chart(
                sentiment_chart,
                x="Sentiment",
                y="Percentage",
            )

        with language_right:
            st.markdown("### Language coverage")
            st.bar_chart(
                result["language_distribution"],
                x="language",
                y="reviews",
            )

        st.markdown("### Sentiment by language")
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
            "Hindi uses Devanagari detection; Hinglish uses common transliterated Hindi vocabulary and phrases."
        )

        st.markdown("### Top warning phrases")
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
                category_columns = st.columns(2)
                for index, item in enumerate(
                    result["complaint_categories"]
                ):
                    category_columns[index % 2].metric(
                        item["category"],
                        item["mentions"],
                        "review mentions",
                    )
            else:
                st.write(
                    "No predefined complaint categories were detected."
                )

    with developer_tab:
        render_developer_trust_panel(result)

    with report_tab:
        st.markdown("### Analysis summary")
        st.info(result["summary"])

        st.markdown("### Recommended safety checks")
        for recommendation in safety_recommendations(
            result["risk_level"]
        ):
            st.markdown(f"- {recommendation}")

        st.warning(
            "AppVerity provides an automated risk indication based on public evidence. It does not prove that an application is fraudulent or guarantee that it is safe."
        )

        st.download_button(
            "⬇️ Download explainable risk report",
            data=report,
            file_name=f"{result['app_id']}_appverity_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

def render_apk_page() -> None:
    ui_theme.render_page_header(
        "Static Android analysis",
        "Inspect APK permissions",
        "Check camera, microphone, SMS, contacts, location, special access and purpose mismatches without executing the APK.",
    )

    st.markdown(
        """
        <section class="av-upload-intro">
            <div class="av-upload-icon">📦</div>
            <div>
                <h2>Upload an Android APK</h2>
                <p>
                    AppVerity reads the APK manifest and package metadata only.
                    The file is never installed or executed.
                </p>
                <div class="av-chip-row">
                    <span class="av-chip">Static analysis</span>
                    <span class="av-chip">Maximum 200 MB</span>
                    <span class="av-chip">APK files only</span>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    uploaded_apk = st.file_uploader(
        "Choose Android APK",
        type=["apk"],
        accept_multiple_files=False,
        help="Upload an APK you built yourself or obtained from a trusted source.",
        key="apk_permission_upload",
    )

    if uploaded_apk is None:
        st.info(
            "Upload an APK to check camera, microphone, SMS, contacts, location, accessibility and other declared permissions."
        )
        st.markdown("### What AppVerity checks")
        checks = [
            ("🎤", "Microphone", "Whether audio recording is declared"),
            ("📷", "Camera", "Whether image or video capture is declared"),
            ("💬", "SMS", "Read, receive and send SMS access"),
            ("👥", "Contacts", "Address-book access"),
            ("📍", "Location", "Precise and background location"),
            ("♿", "Special access", "Accessibility, overlays and installations"),
        ]
        for row_start in range(0, len(checks), 3):
            row_columns = st.columns(3)
            for column, (icon_text, title, copy) in zip(
                row_columns,
                checks[row_start : row_start + 3],
            ):
                with column:
                    st.markdown(
                        f"""
                        <article class="av-check-preview">
                            <span>{icon_text}</span>
                            <h3>{title}</h3>
                            <p>{copy}</p>
                        </article>
                        """,
                        unsafe_allow_html=True,
                    )
        return

    file_size_mb = uploaded_apk.size / (1024 * 1024)

    selected_left, selected_right = st.columns([1.35, 1])
    with selected_left:
        st.markdown(
            f"""
            <article class="av-selected-file">
                <div class="av-selected-file-icon">📄</div>
                <div>
                    <strong>{escape(uploaded_apk.name)}</strong>
                    <small>{file_size_mb:.2f} MB selected</small>
                </div>
            </article>
            """,
            unsafe_allow_html=True,
        )

    with selected_right:
        selected_app_purpose = st.selectbox(
            "Application purpose",
            apk_permission_analyzer.APP_PURPOSES,
            index=0,
            help=(
                "AppVerity compares requested permissions with the expected needs of the selected app type."
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
                "Analysing the APK...",
                expanded=True,
            ) as apk_status:
                st.write("✓ Validating APK archive structure")
                st.write("✓ Calculating SHA-256 fingerprint")
                st.write("✓ Extracting Android package details")
                st.write("✓ Detecting sensitive permissions")
                st.write("✓ Comparing permissions with app purpose")
                st.write("✓ Preparing the explainable report")

                apk_result = apk_permission_analyzer.analyze_apk(
                    uploaded_apk.getvalue(),
                    uploaded_apk.name,
                    selected_app_purpose,
                )
                st.session_state["apk_permission_result"] = apk_result

                apk_status.update(
                    label="APK analysis completed",
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
        st.divider()
        render_apk_permission_result(apk_result)

def render_history_page() -> None:
    ui_theme.render_page_header(
        "Local evidence library",
        "Saved reports and trends",
        "Search previous analyses, reopen reports, compare repeated scans and export local history.",
    )
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


def render_about_page() -> None:
    ui_theme.render_page_header(
        "Transparent methodology",
        "How AppVerity AI works",
        "Understand the scoring logic, supported evidence, privacy model and important limitations.",
    )

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


HOME_PAGE = st.Page(
    render_home_page,
    title="Home",
    icon="🏠",
    default=True,
)
PLAY_STORE_PAGE = st.Page(
    render_play_store_page,
    title="Play Store Analysis",
    icon="🔍",
    url_path="play-store-analysis",
)
APK_PAGE = st.Page(
    render_apk_page,
    title="APK Permissions",
    icon="📦",
    url_path="apk-permissions",
)
HISTORY_PAGE = st.Page(
    render_history_page,
    title="Saved Reports",
    icon="🕘",
    url_path="saved-reports",
)
ABOUT_PAGE = st.Page(
    render_about_page,
    title="About & Methodology",
    icon="ℹ️",
    url_path="about",
)

ui_theme.render_sidebar_brand()

current_page = st.navigation(
    [
        HOME_PAGE,
        PLAY_STORE_PAGE,
        APK_PAGE,
        HISTORY_PAGE,
        ABOUT_PAGE,
    ],
    position="sidebar",
)
current_page.run()
