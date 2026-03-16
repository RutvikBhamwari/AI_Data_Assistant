# 🤖 AI Data Assistant

> Talk to your data in plain English. Powered by Claude AI.

A privacy-first AI tool that lets you query databases and analyse CSV files 
using natural language — no SQL knowledge required.

Built with Python, Streamlit, and the Anthropic Claude API.

---

## ✨ Features

**SQL Assistant**
- Upload any SQLite database
- Ask questions in plain English
- Get accurate SQL queries generated automatically
- See syntax-highlighted SQL with plain English explanations
- Results displayed as interactive, sortable tables

**Data Explainer**
- Upload any CSV file
- Get instant AI-powered business insights
- Automatic data quality checks
- Suggested follow-up questions
- Ask unlimited follow-up questions about your data

---

## 🔐 Privacy First

This tool is designed with data privacy at its core:

- **Schema only** — only your database structure is sent to the AI, never your actual data
- **Local execution** — all queries run on your machine, results never leave your computer
- **No data storage** — nothing is saved or logged between sessions

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- An Anthropic API key ([get one here](https://console.anthropic.com))

## 🎨 Design

Screens designed in Figma before building — following a design-first approach.

[View Figma Designs →](https://www.figma.com/design/cWQ6g5FToUlVigY3PVLcz0/M1-Data-Assitant?node-id=24-59&t=yrViGimidBFDcryJ-1)

**Screens designed:**
- Home Screen — mode selection
- SQL Assistant Screen — query interface
- CSV Explainer Screen — file upload and analysis

### Installation

1. Clone the repository:
```bash
git clone https://github.com/RutvikBhamwari/AI_Data_Assistant.git
cd AI_Data_Assistant
```

2. Install dependencies:
```bash
pip3 install anthropic streamlit pandas
```

3. Set your API key:
```bash
echo 'export ANTHROPIC_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

4. Run the app:
```bash
streamlit run app.py
```

5. Open your browser at `http://localhost:8501`

---

## 📁 Project Structure
```
AI_Data_Assistant/
├── app.py              # Terminal version (combined modes)
├── AI_Assistant.py     # Streamlit web interface
├── sql_assistant.py    # SQL Assistant (standalone)
├── data_explainer.py   # Data Explainer (standalone)
├── sales_data.csv      # Sample dataset for testing
└── .gitignore          # Keeps sensitive files out of GitHub
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Anthropic Claude API | AI query generation and analysis |
| Streamlit | Web interface |
| pandas | CSV processing and data summaries |
| sqlite3 | Database connectivity (built into Python) |

---

## 💡 How It Works

### SQL Assistant
1. User uploads a SQLite database
2. App extracts schema (table and column names only — no data)
3. Schema + question sent to Claude
4. Claude generates accurate SQL
5. SQL runs locally on your machine
6. Results displayed as interactive table

### Data Explainer
1. User uploads a CSV file
2. App generates a statistical summary (structure + stats, not raw rows)
3. Summary sent to Claude
4. Claude returns overview, insights, quality issues, and suggested questions
5. User can ask unlimited follow-up questions

---

## 📊 Sample Questions to Try

**SQL Assistant** (with Chinook database):
- "Who are the top 5 customers by total spending?"
- "Which genre has the most tracks?"
- "What are the top 3 best selling artists?"

**Data Explainer** (with sales_data.csv):
- "Which product is most profitable?"
- "Are there any regional performance patterns?"
- "What data quality issues should I be aware of?"

---

## 🗺️ Roadmap

- [ ] PostgreSQL and SQL Server support
- [ ] Export results to CSV
- [ ] Conversation history
- [ ] Multi-file CSV comparison
- [ ] Scheduled analysis reports

---

## 👤 Author

**Rutvik Bhamwari**  
[GitHub](https://github.com/RutvikBhamwari)

---
