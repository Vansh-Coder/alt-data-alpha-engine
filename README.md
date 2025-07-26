<table width="100%">
  <tr>
    <td valign="middle" width="25%">
      <a href="https://rag-project-blond.vercel.app">
        <img
          src="frontend/assets/AppIcon.png"
          width="200"
          height="200"
          alt="Health Detect AI app icon"
        />
      </a>
    </td>
    <td valign="middle" width="75%">
      <h1 style="margin: 0;">
        <a href="https://rag-project-blond.vercel.app">Alt Data Alpha Engine</a>
      </h1>
      <p style="margin: 0; font-style: italic;">
        AI-driven Alpha Generation with Alternative Data and Sentiment Analysis
      </p>
      <p style="margin-top: 8px;">
        <img
          src="https://img.shields.io/github/license/Vansh-Coder/alt-data-alpha-engine?style=flat-square&logo=opensourceinitiative&logoColor=white&color=E92063"
          alt="License"
        />
        <img
          src="https://img.shields.io/github/languages/top/Vansh-Coder/alt-data-alpha-engine?style=flat-square&color=E92063"
          alt="Top Language"
        />
        <img
          src="https://img.shields.io/github/languages/count/Vansh-Coder/alt-data-alpha-engine?style=flat-square&color=E92063"
          alt="Language Count"
        />
      </p>
      <p style="margin-top: 16px; font-style: italic;">
        Built with the tools and technologies:
      </p>
      <p style="margin: 4px 0;">
        <img
          src="https://img.shields.io/badge/Python-3776AB.svg?style=flat-square&logo=python&logoColor=white"
          alt="Python"
        />
        <img
          src="https://img.shields.io/badge/pandas-150458.svg?style=flat-square&logo=pandas&logoColor=white"
          alt="pandas"
        />
        <img
          src="https://img.shields.io/badge/NumPy-013243.svg?style=flat-square&logo=numpy&logoColor=white"
          alt="NumPy"
        />
        <img
          src="https://img.shields.io/badge/yfinance-2D3E50.svg?style=flat-square&logo=yahoo&logoColor=white"
          alt="yfinance"
        />
        <img
          src="https://img.shields.io/badge/PRAW-FF4500.svg?style=flat-square&logo=reddit&logoColor=white"
          alt="PRAW"
        />
        <img
          src="https://img.shields.io/badge/SEC_Edgar-005288.svg?style=flat-square&logo=sec&logoColor=white"
          alt="SEC Edgar"
        />
        <img
          src="https://img.shields.io/badge/Transformers-FFDD00.svg?style=flat-square&logo=huggingface&logoColor=black"
          alt="Transformers"
        />
        <img
          src="https://img.shields.io/badge/Backtrader-FF5733.svg?style=flat-square"
          alt="Backtrader"
        />
      </p>
      <p style="margin: 4px 0;">
        <img
          src="https://img.shields.io/badge/Streamlit-FF4B4B.svg?style=flat-square&logo=streamlit&logoColor=white"
          alt="Streamlit"
        />
        <img
          src="https://img.shields.io/badge/Altair-FFBE33.svg?style=flat-square"
          alt="Altair"
        />
        <img
          src="https://img.shields.io/badge/Docker-2496ED.svg?style=flat-square&logo=docker&logoColor=white"
          alt="Docker"
        />
        <img
          src="https://img.shields.io/badge/GitHub_Actions-2088FF.svg?style=flat-square&logo=github-actions&logoColor=white"
          alt="GitHub Actions"
        />
        <img
          src="https://img.shields.io/badge/Git-F05032.svg?style=flat-square&logo=git&logoColor=white"
          alt="Git"
        />
        <img
          src="https://img.shields.io/badge/Visual_Studio_Code-007ACC.svg?style=flat-square&logo=visual-studio-code&logoColor=white"
          alt="VS Code"
        />
        <img
          src="https://img.shields.io/badge/macOS-000000.svg?style=flat-square&logo=apple&logoColor=white"
          alt="macOS"
        />
        <img
          src="https://img.shields.io/badge/Hetzner_Cloud-D50C2D.svg?style=flat-square"
          alt="Hetzner Cloud"
        />
      </p>
    </td>
  </tr>
</table>

# 📈 Alt Data Alpha Engine

**AI-driven Alpha Generation with Alternative Data and Sentiment Analysis**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://alt-data-alpha-engine.streamlit.app)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License](https://img.shields.io/github/license/Vansh-Coder/alt-data-alpha-engine)](LICENSE)

---

## 🚀 Overview

The **Alt Data Alpha Engine** utilizes **alternative data sources**—including financial news, Reddit discussions, and SEC filings—combined with advanced **sentiment analysis** and rigorous quantitative backtesting to identify profitable trading signals.

**Key components**:

- **Alternative Data Collection**: Real-time data retrieval from Yahoo Finance, Reddit, and SEC Edgar.
- **Sentiment Scoring**: NLP-driven sentiment quantification using transformer-based models.
- **Signal Generation**: Quantile-based long/short signals with conviction scoring.
- **Backtesting**: Robust trading strategy validation with Backtrader.
- **Interactive Dashboard**: Streamlit-powered dashboard for detailed insights.
- **Automated Pipeline**: Regular automated data refresh via GitHub Actions.

---

## 🎯 Features

- 🔍 **Real-time data pipeline** from Yahoo Finance, Reddit (`r/stocks`), and SEC Edgar (8-K filings).
- 📉 **Rolling sentiment analysis** across multiple horizons (1-day, 3-day, 5-day).
- 📊 **Conviction-based signal assignment** using adjustable quantile thresholds.
- ⚖️ **Comprehensive backtesting** evaluating Sharpe ratio, CAGR, maximum drawdown, and win rate.
- 📈 **Interactive visualization** with Streamlit dashboard and hourly sentiment aggregation.
- 🔄 **Fully automated weekly updates** using GitHub Actions.

---

## 📊 Live Dashboard

👉 [**Launch the Dashboard 🚀**](https://alt-data-alpha-engine.streamlit.app)

*Updated twice weekly: Every Tuesday and Thursday at 07:00 UTC.*

---

## 🛠️ Tech Stack

| Component                | Technologies Used                                           |
|--------------------------|-------------------------------------------------------------|
| **Data Collection**      | Yahoo Finance (`yfinance`), Reddit (`PRAW`), SEC Edgar API  |
| **Sentiment Analysis**   | Transformers, Python, Pandas, NumPy                         |
| **Signal Generation**    | Pandas, NumPy                                               |
| **Backtesting**          | Backtrader, Pandas, NumPy                                   |
| **Dashboard & Visualization** | Streamlit, Altair                                      |
| **Automation & CI/CD**   | GitHub Actions                                              |

---

## ⚡ Quickstart Guide

### 📌 Prerequisites

- Python 3.10 or newer
- Reddit API credentials ([Create here](https://www.reddit.com/prefs/apps))
- SEC Edgar API User Agent
- Streamlit account (optional for hosting)

### 💻 Installation

Clone this repository:

```bash
git clone https://github.com/Vansh-Coder/alt-data-alpha-engine.git
cd alt-data-alpha-engine
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 🔧 Configuration

Set up a `.env` file in the project root:

```env
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent
SEC_USER_AGENT=your_sec_user_agent
```

### 🚀 Running the Pipeline

Execute each script sequentially to build your dataset and signals:

```bash
python data_pipeline.py
python sentiment_analysis.py
python signals.py
python backtest.py
python grid_search.py
```

### 🖥️ Launch the Dashboard

Run Streamlit locally:

```bash
streamlit run dashboard.py
```

Then open: [`http://localhost:8501`](http://localhost:8501)

---

## 🔄 Automation with GitHub Actions

Automated data updates occur twice weekly (Tuesday & Thursday at 07:00 UTC).  
Configuration located in: `.github/workflows/data-refresh.yml`

---

## 📂 Project Structure

```
alt-data-alpha-engine
├── data_pipeline.py           # Fetch alternative data
├── sentiment_analysis.py      # NLP-based sentiment analysis
├── signals.py                 # Generate signals
├── backtest.py                # Backtesting strategy implementation
├── grid_search.py             # Hyperparameter tuning
├── dashboard.py               # Streamlit dashboard interface
├── data/                      # Data directory
├── .github/workflows/         # Automation workflows
├── .env                       # Credentials and API configs
└── requirements.txt           # Dependencies
```

---

## 📸 Dashboard Preview

![Dashboard Example](screenshots/dashboard_example.png)

---

## 🌟 About the Author

- **Vansh Gupta**  
  [![LinkedIn](https://img.shields.io/badge/LinkedIn-%230077B5.svg?&style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/vansh-gupta-22b226224/)
  [![GitHub](https://img.shields.io/badge/GitHub-%23181717.svg?&style=flat-square&logo=github&logoColor=white)](https://github.com/Vansh-Coder)

---

## 🤝 Contributing

Contributions, suggestions, and improvements are welcome! Feel free to open issues or submit pull requests.

---

## 📜 License

This project is licensed under the **[MIT License](LICENSE)**.

---
