import streamlit as st
import anthropic
import sqlite3
import pandas as pd
import os

# ── Page configuration ───────────────────────────────────────────
# This must be the first Streamlit command in the file
# Sets the browser tab title, icon, and layout
st.set_page_config(
    page_title="AI Data Assistant",
    page_icon="🤖",
    layout="wide"  # Uses full browser width — better for data apps
)

# ── Custom CSS ───────────────────────────────────────────────────
# Streamlit has default styling but we can override it
# This matches the colour palette from our Figma design
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #F8F9FA;
    }
    /* Card style for panels */
    .css-1d391kg {
        background-color: white;
    }
    /* Primary button colour */
    .stButton > button {
        background-color: #2563EB;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton > button:hover {
        background-color: #1D4ED8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────
# st.markdown lets us write HTML/CSS for custom styling
st.markdown("""
<div style="background-color: #1E293B; padding: 1rem 2rem; margin: -1rem -1rem 2rem -1rem;">
    <h1 style="color: white; margin: 0; font-size: 1.5rem; font-weight: 600;">
        🤖 AI Data Assistant
    </h1>
</div>
""", unsafe_allow_html=True)

# ── Session state initialisation ─────────────────────────────────
# This runs every time the page loads
# but session_state values persist across reruns
# We only initialise if the key doesn't already exist

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "data_summary" not in st.session_state:
    st.session_state.data_summary = None

if "file_name" not in st.session_state:
    st.session_state.file_name = None

# ── Mode selection ───────────────────────────────────────────────
# st.radio creates a radio button selector
# This replaces our terminal menu
mode = st.selectbox(
    "Choose a mode:",
    ["SQL Assistant", "Data Explainer", "ETL Narrator"]
)

# ── Divider ──────────────────────────────────────────────────────
st.divider()

# ════════════════════════════════════════════════════════════════
#  MODE 1 — SQL ASSISTANT
# ════════════════════════════════════════════════════════════════

def get_schema(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    schema = ""
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        schema += f"Table: {table_name}\n"
        schema += f"Columns: {', '.join(col_names)}\n\n"
    return schema

def ask_claude_sql(question, schema):
    client = anthropic.Anthropic()
    system_prompt = f"""You are an expert SQL assistant.
You help users query a SQLite database by writing accurate SQL queries.

Here is the database schema:
{schema}

Format your response exactly like this:

SQL QUERY:
<the query here>

EXPLANATION:
<plain English explanation here>

Only use tables and columns that exist in the schema above.
"""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": question}]
    )
    return message.content[0].text

def extract_sql(response):
    try:
        sql_start = response.index("SQL QUERY:") + len("SQL QUERY:")
        sql_end = response.index("EXPLANATION:")
        sql = response[sql_start:sql_end].strip()
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[1]
        if sql.endswith("```"):
            sql = sql.rsplit("```", 1)[0]
        return sql.strip()
    except:
        return None

def extract_explanation(response):
    # Pull out just the explanation section from Claude's response
    try:
        exp_start = response.index("EXPLANATION:") + len("EXPLANATION:")
        return response[exp_start:].strip()
    except:
        return None

def run_query(cursor, sql):
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        col_names = [description[0] for description in cursor.description]
        return col_names, results
    except Exception as e:
        return None, str(e)

def sql_mode():
    # Two column layout matching our Figma design
    left_col, right_col = st.columns([4, 6])

    with left_col:
        st.subheader("Ask a Question")

        # File uploader for the database
        # Streamlit handles file uploads natively
        db_file = st.file_uploader(
            "Upload your SQLite database",
            type=["sqlite", "db"],
            help="Upload a .sqlite or .db file"
        )

        if db_file:
            # Save uploaded file temporarily so sqlite3 can read it
            # sqlite3 needs a file path, not a file object
            temp_path = f"/tmp/{db_file.name}"
            with open(temp_path, "wb") as f:
                f.write(db_file.getvalue())

            # Connect to database
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()

            # Show connected status
            st.success("✅ Database connected")

            # Get schema
            schema = get_schema(cursor)

            # Question input
            question = st.text_area(
                "Your question",
                placeholder="Ask a question about your data...",
                height=120
            )

            # Ask button
            if st.button("Ask Claude", type="primary"):
                if question:
                    with right_col:
                        st.subheader("Results")

                        # Show spinner while Claude is thinking
                        with st.spinner("Asking Claude..."):
                            response = ask_claude_sql(question, schema)

                        # Extract and display SQL
                        sql = extract_sql(response)
                        explanation = extract_explanation(response)

                        if sql:
                            st.markdown("**Generated SQL:**")
                            # st.code displays code with syntax highlighting
                            st.code(sql, language="sql")

                        if explanation:
                            st.markdown("**Explanation:**")
                            st.info(explanation)

                        if sql:
                            # Run the query
                            col_names, results = run_query(cursor, sql)
                            if col_names:
                                st.markdown("**Query Results:**")
                                # st.dataframe displays results as an interactive table
                                df_results = pd.DataFrame(results, columns=col_names)
                                st.dataframe(df_results, use_container_width=True)
                                st.caption(f"{len(results)} rows returned")
                            else:
                                st.error(f"Query error: {results}")
                else:
                    st.warning("Please enter a question first")
        else:
            # Empty state — shown before file is uploaded
            with right_col:
                st.subheader("Results")
                st.markdown("""
                <div style="text-align: center; color: #94A3B8; padding: 3rem;">
                    <p style="font-size: 2rem">🗄️</p>
                    <p>Upload a database and ask a question to see results here</p>
                </div>
                """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
#  MODE 2 — DATA EXPLAINER
# ════════════════════════════════════════════════════════════════

def summarise_csv(df):
    # Build a privacy-safe summary — stats and structure only
    # Never sends raw data rows to Claude
    summary = ""
    summary += f"Dataset: {df.shape[0]} rows x {df.shape[1]} columns\n\n"

    # Column names and data types
    summary += "Columns and data types:\n"
    for col in df.columns:
        summary += f"  - {col}: {df[col].dtype}\n"

    # 3 sample rows so Claude understands the data format
    summary += "\nSample rows (first 3):\n"
    summary += df.head(3).to_string(index=False)
    summary += "\n\n"

    # Statistical summary for numeric columns
    numeric_cols = df.select_dtypes(include='number').columns
    if len(numeric_cols) > 0:
        summary += "Statistical summary:\n"
        summary += df[numeric_cols].describe().to_string()
        summary += "\n\n"

    # ── NEW: Pre-calculated aggregations ────────────────────────
    # We calculate group totals using pandas before sending to Claude
    # This gives Claude precise numbers without sending raw data rows
    # Privacy preserved — only aggregated results, not individual records

    categorical_cols = df.select_dtypes(include='object').columns

    for cat_col in categorical_cols:
        # Only aggregate if column has a reasonable number of categories
        # Columns with too many unique values (like names) aren't useful to group by
        unique_values = df[cat_col].nunique()
        if unique_values <= 20:
            summary += f"Breakdown by {cat_col}:\n"
            for num_col in numeric_cols:
                group_totals = df.groupby(cat_col)[num_col].sum()
                group_means = df.groupby(cat_col)[num_col].mean().round(2)
                summary += f"  {num_col} totals: {group_totals.to_dict()}\n"
                summary += f"  {num_col} averages: {group_means.to_dict()}\n"
            summary += "\n"

    # Missing value check
    missing = df.isnull().sum()
    if missing.any():
        summary += "Missing values:\n"
        for col, count in missing.items():
            if count > 0:
                summary += f"  - {col}: {count} missing\n"
    else:
        summary += "Missing values: None found\n"

    return summary

def ask_claude_csv(summary, question, history=[]):
    client = anthropic.Anthropic()
    
    system_prompt = """You are an expert data analyst and business intelligence specialist.
You help non-technical people understand their data clearly and simply.
You remember the full conversation and can answer follow-up questions
that reference previous answers.

When given a data summary for the first time, format your response like this:

OVERVIEW:
<2-3 sentence plain English description>

KEY INSIGHTS:
1. <first insight>
2. <second insight>
3. <third insight>

DATA QUALITY:
<any issues noticed, or 'No issues found'>

SUGGESTED QUESTIONS:
1. <question this data could answer>
2. <question this data could answer>
3. <question this data could answer>

For follow-up questions, answer naturally and conversationally.
Reference previous answers where relevant.
"""

    # Build messages list with full conversation history
    # This is what gives Claude memory of previous exchanges
    messages = []
    
    # Add all previous exchanges first
    for exchange in history:
        messages.append({"role": "user", "content": exchange["question"]})
        messages.append({"role": "assistant", "content": exchange["answer"]})
    
    # Add the current question
    # Include the data summary only in the first message
    if not history:
        content = f"Here is the dataset summary:\n\n{summary}\n\nPlease analyse this data."
        if question:
            content = f"Here is the dataset summary:\n\n{summary}\n\nSpecific question: {question}"
    else:
        # Follow-up questions don't need the full summary again
        # Claude already has it from the first message
        content = question
    
    messages.append({"role": "user", "content": content})
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=messages
    )
    
    return message.content[0].text

def parse_analysis(response):
    # Parse Claude's structured response into sections
    # So we can display each section separately in the UI
    sections = {}
    current_section = None
    current_content = []

    for line in response.split('\n'):
        if line.startswith('OVERVIEW:'):
            current_section = 'overview'
        elif line.startswith('KEY INSIGHTS:'):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = 'insights'
            current_content = []
        elif line.startswith('DATA QUALITY:'):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = 'quality'
            current_content = []
        elif line.startswith('SUGGESTED QUESTIONS:'):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = 'questions'
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections

# ════════════════════════════════════════════════════════════════
#  MODE 4 — ETL NARRATOR
# ════════════════════════════════════════════════════════════════

def narrate_etl_log(log_text):
    client = anthropic.Anthropic()

    # System prompt built from your real ETL domain knowledge
    # This is better than what any developer without BI experience would write
    system_prompt = """You are an expert data engineering analyst who helps 
business stakeholders understand ETL pipeline logs clearly and quickly.

When given a pipeline log, produce a morning briefing with exactly this format:

PIPELINE SUMMARY:
<One sentence: X jobs ran, X succeeded, X failed>
<Time range the pipeline ran>

JOB RESULTS:
For each job provide:
[SUCCESS] or [FAILED] <job name> -- <status> -- <duration if available>
  Rows: <extracted> extracted, <loaded> loaded
  <Any warnings or errors on the next line, indented>

FAILURES - ACTION REQUIRED:
<Only if there are failures>
For each failed job:
[FAILED] <job name>
  Cause: <plain English explanation of why it failed>
  Action: <specific recommended action -- be precise>

WARNINGS - REVIEW RECOMMENDED:
<Only if there are warnings>
For each warning:
[WARNING] <job name>: <plain English explanation and potential impact>

DATA QUALITY FLAGS:
<Any patterns across jobs that indicate broader data quality issues>
<Or 'No data quality issues detected'>

Write in plain English for a business audience.
Be specific about numbers -- rows, durations, timestamps.
Always recommend a specific action for failures.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"Please narrate this ETL log:\n\n{log_text}"}
        ]
    )
    return message.content[0].text

def etl_mode():
    st.subheader("ETL Log Narrator")

    input_method = st.radio(
        "How would you like to provide the log?",
        ["Upload log file", "Paste log text"],
        horizontal=True
    )

    log_text = None

    if input_method == "Upload log file":
        log_file = st.file_uploader(
            "Upload your ETL log",
            type=["txt", "log"],
            help="Upload a .txt or .log file"
        )
        if log_file:
            log_text = log_file.read().decode("utf-8")
            st.success(f"File loaded: {log_file.name}")

    else:
        log_text = st.text_area(
            "Paste your ETL log here",
            placeholder="Paste your pipeline log output here...",
            height=300
        )

    if st.button("Narrate Log", type="primary"):
        if log_text and log_text.strip():
            st.subheader("Pipeline Briefing")
            with st.spinner("Analysing your pipeline log..."):
                narrative = narrate_etl_log(log_text)
            st.markdown(narrative)
        else:
            st.warning("Please upload or paste a log first")

def csv_mode():
    left_col, right_col = st.columns([4, 6])

    with left_col:
        st.subheader("Analyse Your Data")

        csv_file = st.file_uploader(
            "Upload your CSV file",
            type=["csv"],
            help="Upload a .csv file to analyse"
        )

        if csv_file:
            # Only re-process if a new file is uploaded
            if st.session_state.file_name != csv_file.name:
                df = pd.read_csv(csv_file)
                st.session_state.data_summary = summarise_csv(df)
                st.session_state.file_name = csv_file.name
                # Clear conversation when new file is loaded
                st.session_state.conversation_history = []

            st.success(f"✅ {csv_file.name} loaded")

            question = st.text_area(
                "Ask a question",
                placeholder="What would you like to know about this data?",
                height=80,
                key="csv_question"
            )

            if st.button("Ask Claude", type="primary", key="csv_ask"):
                if st.session_state.data_summary:
                    with st.spinner("Asking Claude..."):
                        response = ask_claude_csv(
                            st.session_state.data_summary,
                            question,
                            st.session_state.conversation_history
                        )

                    # Save this exchange to conversation history
                    st.session_state.conversation_history.append({
                        "question": question if question else "Please analyse this data.",
                        "answer": response
                    })

            # Clear conversation button
            if st.session_state.conversation_history:
                if st.button("🗑️ Clear conversation", key="csv_clear"):
                    st.session_state.conversation_history = []
                    st.rerun()

        else:
            # Reset state when file is removed
            st.session_state.data_summary = None
            st.session_state.file_name = None
            st.session_state.conversation_history = []

    with right_col:
        st.subheader("Analysis Results")

        if not st.session_state.conversation_history:
            # Empty state
            st.markdown("""
            <div style="text-align: center; color: #94A3B8; padding: 3rem;">
                <p style="font-size: 2rem">📊</p>
                <p>Upload a CSV file and ask a question to start the conversation</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Display full conversation history
            for i, exchange in enumerate(st.session_state.conversation_history):
                # User question bubble
                st.markdown(f"""
                <div style="background:#EFF6FF; border-left:3px solid #2563EB; 
                padding:0.75rem 1rem; border-radius:0 8px 8px 0; margin-bottom:0.5rem;">
                    <strong style="color:#2563EB;">You</strong><br>
                    {exchange['question']}
                </div>
                """, unsafe_allow_html=True)

                # Claude response
                st.markdown(f"""
                <div style="background:#F8F9FA; border-left:3px solid #64748B;
                padding:0.75rem 1rem; border-radius:0 8px 8px 0; margin-bottom:1rem;">
                    <strong style="color:#1E293B;">Claude</strong><br>
                    {exchange['answer']}
                </div>
                """, unsafe_allow_html=True)

# ── Route to correct mode ────────────────────────────────────────
# Based on user's radio button selection
if mode == "SQL Assistant":
    sql_mode()
elif mode == "Data Explainer":
    csv_mode()
elif mode == "ETL Narrator":
    etl_mode()