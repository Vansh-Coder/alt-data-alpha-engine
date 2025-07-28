<table width="100%">
  <tr>
    <td valign="middle" width="30%">
      <a href="https://alt-data-alpha-engine.xyz">
        <img
          src="assets/Logo.png"
          width="225"
          height="225"
          alt="Alt Data Alpha Engine Logo"
        />
      </a>
    </td>
    <td valign="middle" width="70%">
      <h1 style="margin: 0;">
        <a href="https://alt-data-alpha-engine.xyz">Alt Data Alpha Engine</a>
      </h1>
      <p style="margin: 0; font-style: italic;">
        <strong>AI-driven Alpha Generation with Alternative Data and Sentiment Analysis</strong>
      </p>
      <p style="margin-top: 8px;">
        <img
          src="https://img.shields.io/github/actions/workflow/status/Vansh-Coder/alt-data-alpha-engine/update_pipeline.yml?label=GitHub%20Actions&color=E92063"
          alt="GitHub Actions"
        />
        <img
          src="https://img.shields.io/badge/python-3.10+-E92063.svg"
          alt="Python 3.10+"
        />
        <a href="LICENSE"><img src="https://img.shields.io/github/license/Vansh-Coder/alt-data-alpha-engine?style=logo=opensourceinitiative&logoColor=white&color=E92063" alt="License"/></a>
        <img
          src="https://img.shields.io/github/last-commit/Vansh-Coder/alt-data-alpha-engine?color=E92063"
          alt="Last Commit"
        />
      </p>
      <p style="margin-top: 16px; font-style: italic;">
        <strong>Built with the tools and technologies:</strong>
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
          src="https://img.shields.io/badge/GitHub_Actions-2088FF.svg?style=flat-square&logo=github-actions&logoColor=white"
          alt="GitHub Actions"
        />
        <img
          src="https://img.shields.io/badge/Git-F05032.svg?style=flat-square&logo=git&logoColor=white"
          alt="Git"
        />
        <img
          src="https://img.shields.io/badge/OpenAI-412991.svg?style=flat-square&logo=OpenAI&logoColor=white"
          alt="OpenAI"
        />
        <img
          src="https://img.shields.io/badge/Hetzner_Cloud-009EE3.svg?style=flat-square"
          alt="Hetzner Cloud"
        />
        <img
          src="https://img.shields.io/badge/Nginx-009639.svg?style=flat-square&logo=nginx&logoColor=white"
          alt="Nginx"
        />
        <img
          src="https://img.shields.io/badge/Let's_Encrypt-000000.svg?style=flat-square&logo=letsencrypt&logoColor=white"
          alt="Let's Encrypt"
        />
      </p>
    </td>
  </tr>
</table>

## 📈 Live Dashboard

👉 [**Launch the Dashboard ↗**](https://alt-data-alpha-engine.xyz)

*Updated twice weekly: Every Tuesday and Thursday at 07:00 UTC.*

---

## 🚀 Overview

The **Alt Data Alpha Engine** utilizes **alternative data sources** - including financial news, Reddit discussions, and SEC filings-combined with advanced **sentiment analysis** and rigorous quantitative backtesting to identify profitable trading signals.

**Key components**:

- **Alternative Data Collection**: Real-time data retrieval from Yahoo Finance, Reddit, and SEC Edgar.
- **Sentiment Scoring**: NLP-driven sentiment quantification using OpenAI models.
- **Signal Generation**: Quantile-based long/short signals with conviction scoring.
- **Backtesting**: Robust trading strategy validation with Backtrader.
- **Interactive Dashboard**: Streamlit-powered dashboard for detailed insights.
- **Automated Pipeline**: Regular automated data refresh and deployment to Hetzner VPS via GitHub Actions.

---

## 🎯 Features

- 🔍 **Real-time data pipeline** from Yahoo Finance, Reddit (`r/stocks`), and SEC Edgar (8-K filings).
- 📉 **Rolling sentiment analysis** across multiple horizons (1-day, 3-day, 5-day).
- 📊 **Conviction-based signal assignment** using adjustable quantile thresholds.
- ⚖️ **Comprehensive backtesting** evaluating Sharpe ratio, CAGR, maximum drawdown, and win rate.
- 📈 **Interactive visualization** with Streamlit dashboard and hourly sentiment aggregation.
- 🔄 **Fully automated weekly updates** using GitHub Actions.

---

## 🛠️ Tech Stack

| Component                | Technologies Used                                           |
|--------------------------|-------------------------------------------------------------|
| **Data Collection**      | Yahoo Finance (`yfinance`), Reddit (`PRAW`), SEC Edgar API  |
| **Sentiment Analysis**   | OpenAI, Python, Pandas, NumPy                               |
| **Signal Generation**    | Pandas, NumPy                                               |
| **Backtesting**          | Backtrader, Pandas, NumPy                                   |
| **Dashboard & Visualization** | Streamlit, Altair                                      |
| **Hosting & Infrastructure** | Hetzner Cloud VPS, Nginx, Systemd, Certbot (HTTPS)      |
| **Automation & CI/CD**   | GitHub Actions                                              |

---

## ⚡ Quickstart Guide

### 📌 Prerequisites

- Python 3.10 or newer
- Reddit API credentials ([Create here](https://www.reddit.com/prefs/apps))
- SEC Edgar API User Agent
- OpenAI API key
- NASDAQ API User Agent
- Hetzner Cloud VPS (optional for hosting)

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
OPENAI_API_KEY=your_openai_api_key
NASDAQ_USER_AGENT=your_nasdaq_user_agent
```

### 🚀 Running the Pipeline

Execute each script sequentially to build your dataset and signals:

```bash
python data_pipeline.py
python sentiment_analysis.py
python signals.py
```

For local backtesting (optional):

```bash
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
Configuration located in: `.github/workflows/update_pipeline.yml`

---

## 📂 Project Structure

```
alt-data-alpha-engine
├── data_pipeline.py           # Fetch latest alternative data
├── sentiment_analysis.py      # NLP-based sentiment analysis
├── signals.py                 # Generate signals
├── backtest.py                # Backtesting strategy implementation
├── grid_search.py             # Hyperparameter tuning
├── dashboard.py               # Streamlit dashboard interface
├── data/                      # Data directory
├── assets/                    # Assets directory
├── .github/workflows/         # Automation workflows
├── .env                       # Credentials and API configs
└── requirements.txt           # Dependencies
```

---

## 📸 Dashboard Preview

![Dashboard Preview](assets/Dashboard_Preview.png)

---

## 🌟 About the Author

- **Vansh Gupta** - Full-stack AI/ML engineer & software developer.  
  GitHub: [@Vansh-Coder](https://github.com/Vansh-Coder)  
  Email: vgupta95@asu.edu

---

## 🤝 Contributing

Contributions, suggestions, and improvements are welcome! Feel free to open issues or submit pull requests.

---

## 📜 License

This project is licensed under the **[MIT License](LICENSE)**.

---
