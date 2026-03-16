import anthropic
import pandas as pd
import os

# ── Load and summarise the CSV ───────────────────────────────────
# We never send the full data to Claude — only a summary
# This protects privacy and keeps costs low
def load_csv(file_path):
    # pandas reads the CSV into a DataFrame
    # Think of a DataFrame as a spreadsheet in Python
    df = pd.read_csv(file_path)
    return df

def summarise_data(df):
    # Build a summary of the data without sending raw rows
    # This is our privacy-first approach — structure and stats only
    summary = ""
    
    # Basic info — how big is this dataset?
    summary += f"Dataset shape: {df.shape[0]} rows x {df.shape[1]} columns\n\n"
    
    # Column names and their data types
    summary += "Columns and types:\n"
    for col in df.columns:
        summary += f"  - {col}: {df[col].dtype}\n"
    summary += "\n"
    
    # Sample of just 3 rows so Claude understands the format
    # Not enough to leak sensitive data, enough to understand structure
    summary += "Sample rows (first 3):\n"
    summary += df.head(3).to_string(index=False)
    summary += "\n\n"
    
    # Basic statistics for number columns only
    # Mean, min, max, etc — no individual records exposed
    numeric_cols = df.select_dtypes(include='number').columns
    if len(numeric_cols) > 0:
        summary += "Statistical summary (numeric columns):\n"
        summary += df[numeric_cols].describe().to_string()
        summary += "\n\n"
    
    # Check for missing values — important data quality indicator
    missing = df.isnull().sum()
    if missing.any():
        summary += "Missing values per column:\n"
        for col, count in missing.items():
            if count > 0:
                summary += f"  - {col}: {count} missing\n"
    else:
        summary += "Missing values: None found\n"
    
    return summary

# ── Ask Claude to explain the data ──────────────────────────────
def explain_data(summary, user_question=None):
    # Create Claude client — reads API key from .zshrc automatically
    client = anthropic.Anthropic()
    
    # System prompt tells Claude its role and how to respond
    system_prompt = """You are an expert data analyst and business intelligence specialist.
You help non-technical people understand their data clearly and simply.

When given a data summary:
1. Write a plain English overview of what this dataset contains
2. Highlight the 3 most interesting or important insights
3. Flag any data quality issues you notice
4. Suggest 3 questions this data could help answer

Format your response exactly like this:

OVERVIEW:
<2-3 sentence plain English description of the dataset>

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

    # Build the message to send
    # If user asked a specific question, include it
    if user_question:
        content = f"Here is a summary of the dataset:\n\n{summary}\n\nSpecific question: {user_question}"
    else:
        content = f"Here is a summary of the dataset:\n\n{summary}\n\nPlease analyse this data."

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": content}
        ]
    )
    
    return message.content[0].text

# ── Main program ─────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  AI Data Explainer — Powered by Claude")
    print("=" * 50)
    
    # Ask for the file path
    file_path = input("\nEnter the path to your CSV file: ").strip()
    
    # Check the file actually exists before doing anything
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        print("Make sure the file path is correct and try again.")
        return
    
    # Check it's actually a CSV
    if not file_path.endswith('.csv'):
        print("❌ Please provide a CSV file (.csv)")
        return
    
    print("\n⏳ Reading your data...")
    
    # Load the CSV
    df = load_csv(file_path)
    print(f"✅ Loaded {df.shape[0]} rows and {df.shape[1]} columns")
    
    # Build the privacy-safe summary
    summary = summarise_data(df)
    
    # Ask if they have a specific question
    print("\nDo you have a specific question about this data?")
    user_question = input("(Press Enter to skip): ").strip()
    
    print("\n⏳ Asking Claude to analyse your data...\n")
    
    # Get Claude's explanation
    explanation = explain_data(summary, user_question if user_question else None)
    
    # Display the results
    print("=" * 50)
    print(explanation)
    print("=" * 50)
    
    # Ask if they want to ask another question about the same data
    while True:
        print("\nAsk another question about this data?")
        follow_up = input("(Press Enter to exit): ").strip()
        
        if not follow_up:
            print("\nGoodbye!")
            break
        
        print("\n⏳ Asking Claude...\n")
        response = explain_data(summary, follow_up)
        print("=" * 50)
        print(response)
        print("=" * 50)

# ── Run the program ──────────────────────────────────────────────
if __name__ == "__main__":
    main()