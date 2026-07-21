# Fraud Detection and Sentiment Analysis for Mobile Applications

Detect potentially fraudulent mobile apps on the Google Play Store by combining sentiment analysis of user reviews with machine learning–based fraud detection.

**Live Demo:** [project-mini.streamlit.app](https://project-mini.streamlit.app/)

## Overview

This project scrapes app data and user reviews from the Google Play Store, then applies Natural Language Processing (NLP) and machine learning to flag apps that show signs of fraudulent behavior. Reviews are analyzed for sentiment (positive, neutral, negative), summarized for quick insight, and combined with app metadata to help users make more informed decisions before installing an app.

## Features

- **Fraud Detection** — Uses machine learning models to identify fraud patterns based on app reviews and ratings.
- **Sentiment Analysis** — Applies NLP techniques to classify user feedback as positive, neutral, or negative.
- **Review Scraping** — Pulls app data and reviews directly from the Google Play Store using `google-play-scraper`.
- **Review Summarization** — Condenses large volumes of user reviews into concise summaries, including an AI-powered summary via Gemini.
- **Interactive Web App** — Built with Streamlit for an easy-to-use interface.

## Project Structure

```
fraud-app-detection/
├── database/            # Data storage
├── frontend/             # Frontend/UI assets
├── fraud_detection.py    # Machine learning model for fraud detection
├── summarizer.py         # NLP-based review summarization
├── ai_summary.py         # Review summarization using Gemini AI
├── project.py            # Main entry point, integrates all components
├── requirements.txt      # Project dependencies
└── LICENSE
```

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/bhargavsai-lingampalli/fraud-app-detection
   cd fraud-app-detection
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Requirements

- `emoji~=2.12.1`
- `google-play-scraper~=1.2.7`
- `nltk~=3.8.1`
- `numpy~=1.26.4`
- `sumy~=0.11.0`
- `textblob~=0.18.0.post0`
- `google-generativeai~=0.7.2`
- `streamlit~=1.39.0`

See [`requirements.txt`](./requirements.txt) for the full list.

## Usage

Run the main application (Streamlit UI):

```bash
streamlit run project.py
```

Run fraud detection directly:

```bash
python fraud_detection.py
```

Run review summarization:

```bash
python summarizer.py
```

## How It Works

1. **Data Collection** — App details and reviews are scraped from the Google Play Store.
2. **Sentiment Analysis** — Reviews are processed with NLP to determine overall sentiment.
3. **Summarization** — Long lists of reviews are distilled into short, readable summaries (extractive via `sumy`, and AI-generated via Gemini).
4. **Fraud Scoring** — Review sentiment, ratings, and other signals are fed into a fraud detection model to flag suspicious apps.
5. **Results** — Findings are presented through an interactive Streamlit interface.

## Future Enhancements

- Add more robust fraud detection algorithms.
- Improve the accuracy of sentiment analysis.
- Expand fraud signals beyond reviews (e.g., permissions, developer history).

## Contributing

Contributions are welcome. Feel free to open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](./LICENSE).
