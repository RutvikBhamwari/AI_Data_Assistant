import anthropic
import sqlite3
import pandas as pd
import os

# ── Shared Claude client ─────────────────────────────────────────
# Created once and reused across both modes
# Reads API key from .zshrc automatically
client = anthropic.Anthropic()

# ════════════════════════════════════════════════════════════════
# MODE 1 — SQL ASSISTANT
# ════════════════════════════════════════════════════════════════

def get_schema(conn):
    # Extract table and column names only — no actual data
    cursor = conn.cursor()
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
    # System prompt defines Claude's role as SQL expert
    system_prompt = f"""You are an expert SQL assistant.
You help users query a SQLite database by writing accurate SQL queries.

Here is the database schema you are working with:
{schema}

When given a question:
1. Write a clean SQL query that answers it
2. Explain what the query does in plain English
3. Format your response exactly like this:

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
    # Pull out just the SQL from Claude's response
    # Strip markdown code fences if present
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

def run_query(conn, sql):
    # Execute SQL locally — results never leave your machine
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        col_names = [d[0] for d in cursor.description]
        return col_names, results
    except Exception as e:
        return None, f"Query error: {str(e)}"

def run_sql_mode():
    print("\n" + "=" * 50)
    print("  MODE 1 — SQL Assistant")
    print("=" * 50)

    # Ask for database path
    db_path = input("\nEnter path to your SQLite database file: ").strip()

    if not os.path.exists(db_path):
        print(f"❌ File not found: {db_path}")
        return

    # Connect to database
    conn = sqlite3.connect(db_path)
    print("✅ Connected to database")

    # Get schema once at the start
    schema = get_schema(conn)
    print(f"✅ Schema loaded\n")

    while True:
        question = input("Your question (or 'back' to return): ").strip()

        if question.lower() == "back":
            conn.close()
            break

        if not question:
            continue

        print("\n⏳ Asking Claude...\n")
        response = ask_claude_sql(question, schema)

        print("─" * 50)
        print(response)
        print("─" * 50)

        sql = extract_sql(response)
        if sql:
            print("\n📊 Running query...\n")
            col_names, results = run_query(conn, sql)

            if col_names:
                print(" | ".join(col_names))
                print("-" * 50)
                for row in results[:10]:
                    print(" | ".join(str(val) for val in row))
                print(f"\n({len(results)} total rows)\n")
            else:
                print(results)


# ════════════════════════════════════════════════════════════════
# MODE 2 — DATA EXPLAINER
# ════════════════════════════════════════════════════════════════

def summarise_csv(df):
    # Build privacy-safe summary — stats and structure only
    summary = ""
    summary += f"Dataset: {df.shape[0]} rows x {df.shape[1]} columns\n\n"

    summary += "Columns and data types:\n"
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
    else:
        summary += "\n\nMissing values: None found"

    return summary

def ask_claude_data(summary, question=None):
    # System prompt defines Claude as a BI analyst
    system_prompt = """You are an expert data analyst and BI specialist.
You help non-technical people understand their data clearly.

When given a data summary:
1. Write a plain English overview of what the dataset contains
2. Highlight the 3 most interesting insights
3. Flag any data quality issues
4. Suggest 3 questions this data could help answer

Format your response exactly like this:

OVERVIEW:
<2-3 sentence description>

KEY INSIGHTS:
1. <insight>
2. <insight>
3. <insight>

DATA QUALITY:
<issues found or 'No issues found'>

SUGGESTED QUESTIONS:
1. <question>
2. <question>
3. <question>
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

def run_data_mode():
    print("\n" + "=" * 50)
    print("  MODE 2 — Data Explainer")
    print("=" * 50)

    # Ask for CSV path
    file_path = input("\nEnter path to your CSV file: ").strip()

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    if not file_path.endswith('.csv'):
        print("❌ Please provide a CSV file")
        return

    print("\n⏳ Reading your data...")
    df = pd.read_csv(file_path)
    print(f"✅ Loaded {df.shape[0]} rows and {df.shape[1]} columns")

    # Build privacy-safe summary
    summary = summarise_csv(df)

    print("\n⏳ Asking Claude to analyse your data...\n")
    explanation = ask_claude_data(summary)

    print("=" * 50)
    print(explanation)
    print("=" * 50)

    # Follow-up question loop
    while True:
        print("\nAsk a follow-up question (or 'back' to return): ")
        follow_up = input("> ").strip()

        if follow_up.lower() == "back":
            break

        if not follow_up:
            continue

        print("\n⏳ Asking Claude...\n")
        response = ask_claude_data(summary, follow_up)
        print("=" * 50)
        print(response)
        print("=" * 50)


# ════════════════════════════════════════════════════════════════
# MAIN MENU
# ════════════════════════════════════════════════════════════════

def main():
    print("\n" + "=" * 50)
    print("  AI Data Assistant — Powered by Claude")
    print("  Your data stays on your machine.")
    print("=" * 50)

    while True:
        print("\nWhat would you like to do?")
        print("  1 — SQL Assistant (query a database)")
        print("  2 — Data Explainer (analyse a CSV)")
        print("  q — Quit")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "1":
            run_sql_mode()
        elif choice == "2":
            run_data_mode()
        elif choice == "q":
            print("\nGoodbye!")
            break
        else:
            print("Please enter 1, 2, or q")

# ── Run the program ──────────────────────────────────────────────
if __name__ == "__main__":
    main()