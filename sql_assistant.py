import anthropic
import sqlite3
import os

# ── Connect to the database ──────────────────────────────────────
# sqlite3 is built into Python — no install needed
# It lets us connect to and query SQLite database files
db_path = "Chinook_Sqlite.sqlite"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ── Get the database schema ──────────────────────────────────────
# Schema = the structure of the database (table names + columns)
# We need to send this to Claude so it knows what tables exist
# Without this, Claude would be guessing blindly
def get_schema():
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    schema = ""
    for table in tables:
        table_name = table[0]
        # Get column info for each table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        # Build a readable description of each table
        col_names = [col[1] for col in columns]
        schema += f"Table: {table_name}\n"
        schema += f"Columns: {', '.join(col_names)}\n\n"
    
    return schema

# ── Ask Claude to write SQL ──────────────────────────────────────
def ask_claude(question, schema):
    # Create the Anthropic client
    # No API key here — it reads from your .zshrc automatically
    client = anthropic.Anthropic()
    
    # This is the system prompt — it tells Claude its role
    # Think of it as the instructions you give a new employee
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
    
    # Send the question to Claude
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,  # System prompt sets Claude's role
        messages=[
            {"role": "user", "content": question}
        ]
    )
    
    return message.content[0].text

# ── Run the query Claude wrote ───────────────────────────────────
def run_query(sql):
    try:
        # Execute the SQL query against the real database
        cursor.execute(sql)
        # Fetch all results
        results = cursor.fetchall()
        # Get column names for display
        col_names = [description[0] for description in cursor.description]
        return col_names, results
    except Exception as e:
        # If something goes wrong, tell us what — don't just crash
        return None, f"Query error: {str(e)}"

# ── Extract SQL from Claude's response ──────────────────────────
def extract_sql(response):
    # Claude wraps SQL in markdown code fences like ```sql ... ```
    # We need to strip those out before running the query
    try:
        sql_start = response.index("SQL QUERY:") + len("SQL QUERY:")
        sql_end = response.index("EXPLANATION:")
        sql = response[sql_start:sql_end].strip()
        
        # Remove markdown code fences if present
        # Claude sometimes wraps SQL in ```sql ... ``` blocks
        if sql.startswith("```"):
            # Remove the opening ```sql or ``` line
            sql = sql.split("\n", 1)[1]
        if sql.endswith("```"):
            # Remove the closing ``` line
            sql = sql.rsplit("```", 1)[0]
        
        return sql.strip()
    except:
        return None

# ── Main program ─────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  AI SQL Assistant — Powered by Claude")
    print("=" * 50)
    print("Type a question in plain English.")
    print("Type 'quit' to exit.\n")
    
    # Get the schema once at the start
    schema = get_schema()
    
    while True:
        # Ask the user for a question
        question = input("Your question: ").strip()
        
        # Exit if they type quit
        if question.lower() == "quit":
            print("Goodbye!")
            break
            
        # Skip empty input
        if not question:
            continue
        
        print("\n⏳ Asking Claude...\n")
        
        # Get Claude's response
        response = ask_claude(question, schema)
        
        # Show Claude's full explanation
        print("─" * 50)
        print(response)
        print("─" * 50)
        
        # Extract and run the SQL query
        sql = extract_sql(response)
        if sql:
            print("\n📊 Running query against database...\n")
            col_names, results = run_query(sql)
            
            if col_names:
                # Print column headers
                print(" | ".join(col_names))
                print("-" * 50)
                # Print each row of results
                for row in results[:10]:  # Show max 10 rows
                    print(" | ".join(str(val) for val in row))
                print(f"\n({len(results)} total rows)\n")
            else:
                print(results)  # Print error message
        else:
            print("⚠️ Could not extract SQL from response.\n")

# ── Run the program ──────────────────────────────────────────────
# This checks we're running this file directly
# not importing it from somewhere else
if __name__ == "__main__":
    main()