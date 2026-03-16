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

# ── Mode selection ───────────────────────────────────────────────
# st.radio creates a radio button selector
# This replaces our terminal menu
mode = st.radio(
    "Choose a mode:",
    ["🗄️ SQL Assistant", "📊 Data Explainer"],
    horizontal=True  # Display options side by side
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
    summary = f"Dataset: {df.shape[0]} rows x {df.shape[1]} columns\n\n"
    summary += "Columns and types:\n"
    for col in df.columns:
        summary += f"  - {col}: {df[col].dtype}\n"
    summary += "\nSample rows (first 3):\n"
    summary += df.head(3).to_string(index=False)
    numeric_cols = df.select_dtypes(include='number').columns
    if len(numeric_cols) > 0:
        summary += "\n\nStatistical summary:\n"
        summary += df[numeric_cols].describe().to_string()
    missing = df.isnull().sum()
    if missing.any():
        summary += "\n\nMissing values:\n"
        for col, count in missing.items():
            if count > 0:
                summary += f"  - {col}: {count} missing\n"
    return summary

def ask_claude_csv(summary, question=None):
    client = anthropic.Anthropic()
    system_prompt = """You are an expert data analyst and business intelligence specialist.
You help non-technical people understand their data clearly and simply.

Format your response exactly like this:

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
"""
    content = f"Dataset summary:\n\n{summary}"
    if question:
        content += f"\n\nSpecific question: {question}"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": content}]
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

def csv_mode():
    left_col, right_col = st.columns([4, 6])

    with left_col:
        st.subheader("Analyse Your Data")

        # CSV file uploader
        csv_file = st.file_uploader(
            "Upload your CSV file",
            type=["csv"],
            help="Upload a .csv file to analyse"
        )

        if csv_file:
            # Read CSV directly from the uploaded file object
            # pandas can read file objects directly — no temp file needed
            df = pd.read_csv(csv_file)
            st.success(f"✅ {csv_file.name} — {df.shape[0]} rows, {df.shape[1]} columns")

            # Build summary once
            summary = summarise_csv(df)

            # Optional specific question
            question = st.text_area(
                "Ask a specific question (optional)",
                placeholder="What would you like to know about this data?",
                height=80
            )

            if st.button("Analyse with Claude", type="primary"):
                with right_col:
                    st.subheader("Analysis Results")

                    with st.spinner("Analysing your data..."):
                        response = ask_claude_csv(summary, question if question else None)
                        sections = parse_analysis(response)

                    # Display each section separately with styling
                    if 'overview' in sections:
                        st.markdown("**OVERVIEW**")
                        st.write(sections['overview'])
                        st.divider()

                    if 'insights' in sections:
                        st.markdown("**KEY INSIGHTS**")
                        st.info(sections['insights'])
                        st.divider()

                    if 'quality' in sections:
                        st.markdown("**DATA QUALITY**")
                        st.write(sections['quality'])
                        st.divider()

                    if 'questions' in sections:
                        st.markdown("**SUGGESTED QUESTIONS**")
                        st.write(sections['questions'])

                    # Follow-up question
                    st.divider()
                    follow_up = st.text_input(
                        "Ask a follow-up question",
                        placeholder="Ask anything about this data..."
                    )
                    if st.button("Ask Follow-up"):
                        if follow_up:
                            with st.spinner("Asking Claude..."):
                                follow_response = ask_claude_csv(summary, follow_up)
                            st.write(follow_response)
        else:
            with right_col:
                st.subheader("Analysis Results")
                st.markdown("""
                <div style="text-align: center; color: #94A3B8; padding: 3rem;">
                    <p style="font-size: 2rem">📊</p>
                    <p>Upload a CSV file to see your analysis here</p>
                </div>
                """, unsafe_allow_html=True)

# ── Route to correct mode ────────────────────────────────────────
# Based on user's radio button selection
if mode == "🗄️ SQL Assistant":
    sql_mode()
elif mode == "📊 Data Explainer":
    csv_mode()