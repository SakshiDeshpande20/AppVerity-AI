from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
            :root {
                --av-bg: #07111f;
                --av-surface: #0e1a2b;
                --av-card: #132238;
                --av-border: rgba(148, 163, 184, 0.18);
                --av-primary: #7c83ff;
                --av-secondary: #38bdf8;
                --av-success: #22c55e;
                --av-warning: #f59e0b;
                --av-danger: #ef4444;
                --av-text: #f8fafc;
                --av-muted: #94a3b8;
            }

            html { scroll-behavior: smooth; }

            .stApp {
                background:
                    radial-gradient(circle at 82% 0%, rgba(99,102,241,.15), transparent 32%),
                    radial-gradient(circle at 8% 18%, rgba(56,189,248,.08), transparent 27%),
                    linear-gradient(145deg, #07111f 0%, #091525 55%, #07111f 100%);
                color: var(--av-text);
            }

            [data-testid="stHeader"] { background: transparent; }

            .block-container {
                max-width: 1240px;
                padding-top: 2rem;
                padding-bottom: 4rem;
            }

            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0e1a2b 0%, #07111f 100%);
                border-right: 1px solid var(--av-border);
            }

            section[data-testid="stSidebar"] a { border-radius: 12px; }
            section[data-testid="stSidebar"] a:hover {
                background: rgba(124,131,255,.10);
            }

            .av-sidebar-brand { padding: .7rem .45rem 1rem; }
            .av-sidebar-row {
                display: flex;
                align-items: center;
                gap: .75rem;
            }
            .av-logo {
                display: grid;
                place-items: center;
                width: 42px;
                height: 42px;
                border-radius: 14px;
                background: linear-gradient(135deg, #7c83ff, #38bdf8);
                box-shadow: 0 12px 28px rgba(56,189,248,.18);
                font-size: 1.25rem;
            }
            .av-sidebar-title {
                color: var(--av-text);
                font-size: 1.02rem;
                font-weight: 800;
            }
            .av-sidebar-subtitle {
                color: var(--av-muted);
                font-size: .78rem;
                margin-top: .12rem;
            }

            .av-page-header { padding: .4rem 0 1.3rem; }
            .av-eyebrow {
                display: inline-block;
                margin-bottom: .7rem;
                color: #a5b4fc;
                font-size: .78rem;
                font-weight: 800;
                letter-spacing: .12em;
                text-transform: uppercase;
            }
            .av-page-title {
                margin: 0;
                color: var(--av-text);
                font-size: clamp(2rem, 5vw, 3.45rem);
                line-height: 1.05;
                letter-spacing: -.055em;
                font-weight: 850;
            }
            .av-page-subtitle {
                max-width: 850px;
                margin: .85rem 0 0;
                color: #b5c2d4;
                font-size: 1.03rem;
                line-height: 1.7;
            }

            .av-hero {
                position: relative;
                overflow: hidden;
                padding: clamp(1.6rem, 4vw, 3.2rem);
                border: 1px solid var(--av-border);
                border-radius: 28px;
                background: linear-gradient(140deg, rgba(19,34,56,.96), rgba(13,28,49,.92));
                box-shadow: 0 24px 70px rgba(0,0,0,.28);
                margin-bottom: 1.4rem;
            }
            .av-hero::after {
                content: "";
                position: absolute;
                width: 320px;
                height: 320px;
                border-radius: 999px;
                right: -110px;
                top: -130px;
                background: radial-gradient(circle, rgba(124,131,255,.24), transparent 66%);
                pointer-events: none;
            }
            .av-hero-title {
                position: relative;
                z-index: 1;
                max-width: 880px;
                margin: 0;
                color: var(--av-text);
                font-size: clamp(2.25rem, 6vw, 4.4rem);
                line-height: 1.02;
                letter-spacing: -.06em;
                font-weight: 880;
            }
            .av-gradient-text {
                background: linear-gradient(90deg, #a5b4fc, #67e8f9);
                -webkit-background-clip: text;
                background-clip: text;
                color: transparent;
            }
            .av-hero-copy {
                position: relative;
                z-index: 1;
                max-width: 790px;
                margin: 1.1rem 0 0;
                color: #c0ccda;
                font-size: 1.08rem;
                line-height: 1.72;
            }
            .av-chip-row {
                position: relative;
                z-index: 1;
                display: flex;
                flex-wrap: wrap;
                gap: .6rem;
                margin-top: 1.35rem;
            }
            .av-chip {
                padding: .45rem .72rem;
                border: 1px solid rgba(165,180,252,.20);
                border-radius: 999px;
                background: rgba(124,131,255,.08);
                color: #c7d2fe;
                font-size: .78rem;
                font-weight: 700;
            }

            .av-section { margin: 2rem 0 .9rem; }
            .av-section h2 {
                margin: 0;
                color: var(--av-text);
                font-size: 1.55rem;
                letter-spacing: -.035em;
            }
            .av-section p {
                margin: .42rem 0 0;
                color: var(--av-muted);
                line-height: 1.55;
            }

            .av-feature-card {
                min-height: 190px;
                height: 100%;
                padding: 1.25rem;
                border: 1px solid var(--av-border);
                border-radius: 20px;
                background: linear-gradient(145deg, rgba(19,34,56,.90), rgba(14,27,46,.90));
                box-shadow: 0 12px 34px rgba(0,0,0,.14);
                transition: transform 160ms ease, border-color 160ms ease;
            }
            .av-feature-card:hover {
                transform: translateY(-3px);
                border-color: rgba(124,131,255,.42);
            }
            .av-feature-icon {
                display: grid;
                place-items: center;
                width: 44px;
                height: 44px;
                margin-bottom: 1rem;
                border-radius: 14px;
                background: rgba(124,131,255,.15);
                color: #c7d2fe;
                font-size: 1.35rem;
            }
            .av-feature-card h3 {
                margin: 0;
                color: var(--av-text);
                font-size: 1.04rem;
            }
            .av-feature-card p {
                margin: .62rem 0 0;
                color: #9fb0c5;
                font-size: .9rem;
                line-height: 1.58;
            }

            .av-stat-card {
                min-height: 116px;
                padding: 1.05rem 1.1rem;
                border: 1px solid var(--av-border);
                border-radius: 18px;
                background: rgba(16,29,48,.82);
            }
            .av-stat-label {
                color: var(--av-muted);
                font-size: .78rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: .06em;
            }
            .av-stat-value {
                margin-top: .38rem;
                color: var(--av-text);
                font-size: 1.85rem;
                font-weight: 850;
            }
            .av-stat-note {
                margin-top: .24rem;
                color: #8293aa;
                font-size: .76rem;
            }

            .av-recent-card {
                padding: 1rem 1.1rem;
                border: 1px solid var(--av-border);
                border-radius: 17px;
                background: rgba(16,29,48,.72);
                margin-bottom: .65rem;
            }
            .av-recent-top {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
            }
            .av-recent-title {
                color: var(--av-text);
                font-weight: 760;
            }
            .av-recent-meta {
                margin-top: .28rem;
                color: var(--av-muted);
                font-size: .8rem;
            }
            .av-risk-pill {
                height: fit-content;
                padding: .28rem .58rem;
                border-radius: 999px;
                font-size: .72rem;
                font-weight: 800;
                text-transform: uppercase;
            }
            .av-risk-low { color: #86efac; background: rgba(34,197,94,.12); }
            .av-risk-medium { color: #fcd34d; background: rgba(245,158,11,.12); }
            .av-risk-high { color: #fca5a5; background: rgba(239,68,68,.12); }

            .av-step {
                min-height: 150px;
                padding: 1.1rem;
                border-left: 2px solid rgba(124,131,255,.55);
                background: rgba(16,29,48,.45);
                border-radius: 0 16px 16px 0;
            }
            .av-step-number {
                color: #a5b4fc;
                font-size: .75rem;
                font-weight: 850;
                text-transform: uppercase;
                letter-spacing: .08em;
            }
            .av-step h3 { margin: .55rem 0 0; color: var(--av-text); }
            .av-step p {
                margin: .5rem 0 0;
                color: var(--av-muted);
                font-size: .86rem;
                line-height: 1.55;
            }

            .hero-card {
                padding: 2rem;
                border: 1px solid var(--av-border);
                border-radius: 24px;
                background: rgba(15,29,49,.88);
                margin-bottom: 1.4rem;
            }
            .hero-title {
                margin: 0;
                font-size: 2.7rem;
                font-weight: 850;
                color: var(--av-text);
            }
            .hero-subtitle {
                color: #bdc9d8;
                line-height: 1.65;
            }
            .badge {
                display: inline-block;
                padding: .35rem .7rem;
                border-radius: 999px;
                background: rgba(124,131,255,.15);
                color: #c7d2fe;
                font-size: .78rem;
                font-weight: 800;
            }

            .result-card {
                padding: 1.35rem;
                border-radius: 20px;
                border: 1px solid var(--av-border);
                background: rgba(15,29,49,.82);
                margin: 1rem 0;
            }
            .result-low { border-left: 5px solid var(--av-success); }
            .result-medium { border-left: 5px solid var(--av-warning); }
            .result-high { border-left: 5px solid var(--av-danger); }
            .small-muted { color: var(--av-muted); font-size: .86rem; }

            div[data-testid="stForm"],
            [data-testid="stFileUploader"] {
                padding: 1.2rem;
                border: 1px solid var(--av-border);
                border-radius: 20px;
                background: rgba(15,29,49,.68);
            }
            div[data-testid="stMetric"] {
                padding: .95rem;
                border: 1px solid var(--av-border);
                border-radius: 16px;
                background: rgba(16,29,48,.70);
            }
            div.stButton > button,
            div[data-testid="stFormSubmitButton"] button,
            [data-testid="stPageLink"] a,
            [data-testid="stDownloadButton"] button {
                border-radius: 12px;
                min-height: 44px;
                font-weight: 760;
            }
            [data-testid="stDataFrame"] {
                border: 1px solid var(--av-border);
                border-radius: 16px;
                overflow: hidden;
            }
            [data-testid="stExpander"] {
                border: 1px solid var(--av-border);
                border-radius: 14px;
                background: rgba(16,29,48,.45);
            }

            @media (max-width: 760px) {
                .block-container {
                    padding-top: 1.1rem;
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
                .av-feature-card { min-height: auto; }
                .av-recent-top { flex-direction: column; }
            }

            @media (prefers-reduced-motion: reduce) {
                html { scroll-behavior: auto; }
                .av-feature-card { transition: none; }
            }
        
            .av-upload-intro {
                display: flex;
                align-items: center;
                gap: 1.2rem;
                padding: 1.35rem;
                margin-bottom: 1rem;
                border: 1px solid var(--av-border);
                border-radius: 22px;
                background: linear-gradient(
                    135deg,
                    rgba(19,34,56,.92),
                    rgba(12,27,46,.82)
                );
            }
            .av-upload-intro h2 {
                margin: 0;
                color: var(--av-text);
                font-size: 1.25rem;
            }
            .av-upload-intro p {
                margin: .4rem 0 0;
                color: var(--av-muted);
                line-height: 1.55;
            }
            .av-upload-icon {
                display: grid;
                place-items: center;
                width: 64px;
                height: 64px;
                flex: 0 0 64px;
                border-radius: 20px;
                background: linear-gradient(135deg, #7c83ff, #38bdf8);
                font-size: 1.8rem;
                box-shadow: 0 14px 32px rgba(56,189,248,.18);
            }
            .av-check-preview {
                min-height: 135px;
                padding: 1rem;
                margin-bottom: .75rem;
                border: 1px solid var(--av-border);
                border-radius: 18px;
                background: rgba(16,29,48,.68);
            }
            .av-check-preview span { font-size: 1.45rem; }
            .av-check-preview h3 {
                margin: .65rem 0 0;
                color: var(--av-text);
                font-size: .98rem;
            }
            .av-check-preview p {
                margin: .35rem 0 0;
                color: var(--av-muted);
                font-size: .82rem;
                line-height: 1.45;
            }
            .av-selected-file {
                display: flex;
                align-items: center;
                gap: .9rem;
                min-height: 92px;
                padding: 1rem;
                border: 1px solid var(--av-border);
                border-radius: 18px;
                background: rgba(16,29,48,.74);
            }
            .av-selected-file-icon {
                display: grid;
                place-items: center;
                width: 44px;
                height: 44px;
                border-radius: 13px;
                background: rgba(124,131,255,.14);
            }
            .av-selected-file strong {
                display: block;
                color: var(--av-text);
            }
            .av-selected-file small {
                display: block;
                margin-top: .22rem;
                color: var(--av-muted);
            }
            .av-apk-result-hero {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: 1.35rem;
                border: 1px solid var(--av-border);
                border-radius: 22px;
                background: linear-gradient(
                    135deg,
                    rgba(19,34,56,.95),
                    rgba(13,28,49,.88)
                );
            }
            .av-apk-result-hero h2 {
                margin: .1rem 0 0;
                color: var(--av-text);
                font-size: 1.5rem;
            }
            .av-apk-result-hero p {
                margin: .35rem 0 0;
                color: var(--av-muted);
            }
            .av-result-score-badge {
                min-width: 120px;
                padding: .9rem 1rem;
                border-radius: 18px;
                text-align: center;
                background: rgba(124,131,255,.12);
                border: 1px solid rgba(165,180,252,.18);
            }
            .av-result-score-badge span {
                display: block;
                color: var(--av-text);
                font-size: 2rem;
                font-weight: 850;
                line-height: 1;
            }
            .av-result-score-badge small {
                display: block;
                margin-top: .28rem;
                color: var(--av-muted);
                font-size: .72rem;
            }
            .av-permission-card {
                min-height: 150px;
                padding: 1rem;
                margin-bottom: .8rem;
                border-radius: 18px;
                border: 1px solid var(--av-border);
                background: rgba(16,29,48,.78);
            }
            .av-permission-card-top {
                display: flex;
                justify-content: space-between;
                gap: .6rem;
                align-items: center;
            }
            .av-permission-icon { font-size: 1.45rem; }
            .av-requested-pill {
                padding: .22rem .45rem;
                border-radius: 999px;
                font-size: .62rem;
                font-weight: 850;
                letter-spacing: .04em;
                background: rgba(148,163,184,.10);
                color: #cbd5e1;
            }
            .av-permission-card h3 {
                margin: .85rem 0 0;
                color: var(--av-text);
                font-size: 1rem;
            }
            .av-permission-card p {
                margin: .38rem 0 0;
                font-size: .82rem;
                font-weight: 760;
            }
            .av-permission-not-requested {
                border-color: rgba(148,163,184,.22);
            }
            .av-permission-not-requested p { color: #94a3b8; }
            .av-permission-expected {
                border-color: rgba(34,197,94,.34);
                background: rgba(34,197,94,.07);
            }
            .av-permission-expected p { color: #86efac; }
            .av-permission-possible {
                border-color: rgba(56,189,248,.30);
                background: rgba(56,189,248,.06);
            }
            .av-permission-possible p { color: #7dd3fc; }
            .av-permission-unusual {
                border-color: rgba(245,158,11,.36);
                background: rgba(245,158,11,.07);
            }
            .av-permission-unusual p { color: #fcd34d; }
            .av-permission-critical {
                border-color: rgba(239,68,68,.38);
                background: rgba(239,68,68,.08);
            }
            .av-permission-critical p { color: #fca5a5; }
            .av-score-heading span {
                display: block;
                color: var(--av-text);
                font-weight: 800;
            }
            .av-score-heading small {
                display: block;
                margin: .18rem 0 .55rem;
                color: var(--av-muted);
            }
            .av-mini-stat {
                min-height: 108px;
                padding: .85rem;
                border-radius: 16px;
                border: 1px solid var(--av-border);
                background: rgba(16,29,48,.72);
                text-align: center;
            }
            .av-mini-stat span {
                display: inline-grid;
                place-items: center;
                width: 28px;
                height: 28px;
                border-radius: 999px;
                font-weight: 850;
            }
            .av-mini-stat strong {
                display: block;
                margin-top: .45rem;
                color: var(--av-text);
                font-size: 1.35rem;
            }
            .av-mini-stat small {
                color: var(--av-muted);
                font-size: .74rem;
            }
            .av-mini-success span {
                color: #86efac;
                background: rgba(34,197,94,.12);
            }
            .av-mini-info span {
                color: #7dd3fc;
                background: rgba(56,189,248,.12);
            }
            .av-mini-warning span {
                color: #fcd34d;
                background: rgba(245,158,11,.12);
            }
            .av-mini-danger span {
                color: #fca5a5;
                background: rgba(239,68,68,.12);
            }
            @media (max-width: 760px) {
                .av-upload-intro,
                .av-apk-result-hero {
                    align-items: flex-start;
                    flex-direction: column;
                }
                .av-result-score-badge { width: 100%; }
            }

        
            .av-analysis-intro {
                display: flex;
                align-items: center;
                gap: 1.15rem;
                padding: 1.3rem;
                margin-bottom: 1rem;
                border: 1px solid var(--av-border);
                border-radius: 22px;
                background: linear-gradient(
                    135deg,
                    rgba(19,34,56,.92),
                    rgba(12,27,46,.82)
                );
            }

            .av-analysis-intro-icon {
                display: grid;
                place-items: center;
                width: 62px;
                height: 62px;
                flex: 0 0 62px;
                border-radius: 19px;
                background: linear-gradient(135deg, #7c83ff, #38bdf8);
                font-size: 1.65rem;
                box-shadow: 0 14px 32px rgba(56,189,248,.18);
            }

            .av-analysis-intro h2 {
                margin: 0;
                color: var(--av-text);
                font-size: 1.22rem;
            }

            .av-analysis-intro p {
                margin: .38rem 0 0;
                color: var(--av-muted);
                line-height: 1.55;
            }

            .av-review-result-hero {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                padding: 1.4rem;
                border: 1px solid var(--av-border);
                border-radius: 23px;
                background: linear-gradient(
                    135deg,
                    rgba(19,34,56,.96),
                    rgba(13,28,49,.90)
                );
                margin-top: 1rem;
            }

            .av-review-result-hero h2 {
                margin: .1rem 0 0;
                color: var(--av-text);
                font-size: 1.55rem;
            }

            .av-review-result-hero p {
                margin: .38rem 0 .72rem;
                color: var(--av-muted);
            }

            .av-risk-low-surface {
                border-left: 5px solid var(--av-success);
            }

            .av-risk-medium-surface {
                border-left: 5px solid var(--av-warning);
            }

            .av-risk-high-surface {
                border-left: 5px solid var(--av-danger);
            }

            .av-result-label {
                display: inline-block;
                padding: .3rem .62rem;
                border-radius: 999px;
                color: #dbeafe;
                background: rgba(124,131,255,.13);
                font-size: .74rem;
                font-weight: 780;
            }

            .av-review-score {
                min-width: 136px;
                padding: 1rem;
                border: 1px solid rgba(165,180,252,.18);
                border-radius: 18px;
                text-align: center;
                background: rgba(124,131,255,.10);
            }

            .av-review-score span {
                color: var(--av-text);
                font-size: 2.3rem;
                line-height: 1;
                font-weight: 880;
            }

            .av-review-score strong {
                color: #a5b4fc;
                font-size: .9rem;
            }

            .av-review-score small {
                display: block;
                margin-top: .3rem;
                color: var(--av-muted);
                font-size: .72rem;
            }

            .av-score-summary-card {
                min-height: 120px;
                padding: 1rem;
                margin: .85rem 0;
                border: 1px solid var(--av-border);
                border-radius: 17px;
                background: rgba(16,29,48,.72);
            }

            .av-score-summary-card small {
                display: block;
                color: var(--av-muted);
                font-size: .76rem;
                font-weight: 720;
                text-transform: uppercase;
                letter-spacing: .04em;
            }

            .av-score-summary-card strong {
                display: block;
                margin-top: .45rem;
                color: var(--av-text);
                font-size: 1.45rem;
                line-height: 1.1;
            }

            .av-score-summary-card p {
                margin: .38rem 0 0;
                color: #8496ad;
                font-size: .76rem;
                line-height: 1.4;
            }

            .av-reason-card {
                min-height: 132px;
                padding: 1rem;
                margin-bottom: .75rem;
                border: 1px solid var(--av-border);
                border-radius: 17px;
                background: rgba(16,29,48,.68);
            }

            .av-reason-number {
                display: grid;
                place-items: center;
                width: 29px;
                height: 29px;
                border-radius: 999px;
                color: #c7d2fe;
                background: rgba(124,131,255,.13);
                font-size: .76rem;
                font-weight: 850;
            }

            .av-reason-card p {
                margin: .75rem 0 0;
                color: #c0ccda;
                font-size: .88rem;
                line-height: 1.55;
            }

            .av-sentiment-card {
                min-height: 106px;
                padding: 1rem;
                border: 1px solid var(--av-border);
                border-radius: 17px;
                background: rgba(16,29,48,.68);
            }

            .av-sentiment-card small {
                display: block;
                color: var(--av-muted);
                font-size: .78rem;
            }

            .av-sentiment-card strong {
                display: block;
                margin-top: .4rem;
                color: var(--av-text);
                font-size: 1.65rem;
            }

            .av-sentiment-positive {
                border-bottom: 3px solid var(--av-success);
            }

            .av-sentiment-neutral {
                border-bottom: 3px solid var(--av-secondary);
            }

            .av-sentiment-negative {
                border-bottom: 3px solid var(--av-danger);
            }

            .av-app-icon-placeholder {
                display: grid;
                place-items: center;
                width: 96px;
                height: 96px;
                border: 1px solid var(--av-border);
                border-radius: 22px;
                background: rgba(124,131,255,.10);
                color: #c7d2fe;
                font-size: .86rem;
                font-weight: 850;
            }

            .av-app-identity h2 {
                margin: 0;
                color: var(--av-text);
                font-size: 1.5rem;
            }

            .av-app-identity p {
                margin: .35rem 0 0;
                color: var(--av-muted);
            }

            .av-transparency-score {
                min-height: 108px;
                padding: .9rem;
                border: 1px solid rgba(56,189,248,.20);
                border-radius: 18px;
                text-align: center;
                background: rgba(56,189,248,.07);
            }

            .av-transparency-score span {
                color: var(--av-text);
                font-size: 2rem;
                font-weight: 880;
                line-height: 1;
            }

            .av-transparency-score strong {
                color: #7dd3fc;
                font-size: .82rem;
            }

            .av-transparency-score small {
                display: block;
                margin-top: .35rem;
                color: var(--av-muted);
                font-size: .7rem;
            }

            @media (max-width: 760px) {
                .av-analysis-intro,
                .av-review-result-hero {
                    align-items: flex-start;
                    flex-direction: column;
                }

                .av-review-score {
                    width: 100%;
                }
            }

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="av-sidebar-brand">
                <div class="av-sidebar-row">
                    <div class="av-logo">🛡</div>
                    <div>
                        <div class="av-sidebar-title">AppVerity AI</div>
                        <div class="av-sidebar-subtitle">
                            Explainable Android app intelligence
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Risk indicators support human judgement; they do not prove fraud."
        )
        st.divider()


def render_page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <section class="av-page-header">
            <div class="av-eyebrow">{escape(eyebrow)}</div>
            <h1 class="av-page-title">{escape(title)}</h1>
            <p class="av-page-subtitle">{escape(subtitle)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_home_hero() -> None:
    st.markdown(
        """
        <section class="av-hero">
            <div class="av-eyebrow">Android application intelligence</div>
            <h1 class="av-hero-title">
                Know what an app may access
                <span class="av-gradient-text">before you trust it.</span>
            </h1>
            <p class="av-hero-copy">
                Analyse Google Play reviews, developer credibility, multilingual
                complaint patterns, and APK permissions through one explainable
                security workspace.
            </p>
            <div class="av-chip-row">
                <span class="av-chip">✓ Static APK analysis</span>
                <span class="av-chip">✓ English · Hindi · Hinglish</span>
                <span class="av-chip">✓ Explainable risk signals</span>
                <span class="av-chip">✓ Local saved history</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_heading(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <section class="av-section">
            <h2>{escape(title)}</h2>
            <p>{escape(subtitle)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_feature_card(icon: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <article class="av-feature-card">
            <div class="av-feature-icon">{escape(icon)}</div>
            <h3>{escape(title)}</h3>
            <p>{escape(description)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_stat_card(label: str, value: Any, note: str) -> None:
    st.markdown(
        f"""
        <article class="av-stat-card">
            <div class="av-stat-label">{escape(str(label))}</div>
            <div class="av-stat-value">{escape(str(value))}</div>
            <div class="av-stat-note">{escape(str(note))}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_recent_analysis(record: dict[str, Any]) -> None:
    risk_level = str(record.get("risk_level", "Unknown"))
    risk_class = {
        "Low": "av-risk-low",
        "Medium": "av-risk-medium",
        "High": "av-risk-high",
    }.get(risk_level, "av-risk-medium")

    st.markdown(
        f"""
        <article class="av-recent-card">
            <div class="av-recent-top">
                <div>
                    <div class="av-recent-title">
                        {escape(str(record.get("app_name", "Unknown app")))}
                    </div>
                    <div class="av-recent-meta">
                        {escape(str(record.get("app_id", "Unknown package")))}
                        · {escape(str(record.get("risk_score", 0)))}/100 risk
                    </div>
                </div>
                <span class="av-risk-pill {risk_class}">
                    {escape(risk_level)}
                </span>
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_step(number: int, title: str, description: str) -> None:
    st.markdown(
        f"""
        <article class="av-step">
            <div class="av-step-number">Step {number}</div>
            <h3>{escape(title)}</h3>
            <p>{escape(description)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )
