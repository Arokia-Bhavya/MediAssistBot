# backend/sql_rag.py

import sqlite3
import re
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY)

DB_PATH = "data/db/mediassist.db"

# ── Schema shown to LLM for SQL generation ─────────────────────────────
DB_SCHEMA = """
Tables in mediassist.db:

1. claims
   - claim_id       TEXT     (primary key, e.g. CLM-2024-1000)
   - patient_id     TEXT
   - patient_name   TEXT
   - department     TEXT     (cardiology, neurology, nephrology, oncology, etc.)
   - claim_type     TEXT     (cashless, reimbursement)
   - diagnosis_code TEXT     (ICD-10 code)
   - insurer        TEXT     (Star Health, New India Assurance, Bajaj Allianz, etc.)
   - claimed_amount REAL     (original claimed amount in INR)
   - approved_amount REAL    (nullable — null if not yet approved)
   - status         TEXT     (pending, approved, rejected, escalated)
   - submitted_date TEXT     (YYYY-MM-DD)
   - resolved_date  TEXT     (YYYY-MM-DD, nullable)

2. maintenance_tickets
   - ticket_id      TEXT     (primary key, e.g. TKT-2024-2000)
   - equipment_name TEXT
   - equipment_id   TEXT
   - category       TEXT     (sterilisation, infusion, ventilator, monitor, etc.)
   - campus         TEXT     (MediAssist hospital campus name)
   - issue_type     TEXT     (preventive_maintenance, sensor_failure, battery_replacement, etc.)
   - fault_code     TEXT     (nullable)
   - raised_by      TEXT
   - raised_date    TEXT     (YYYY-MM-DD)
   - resolved_date  TEXT     (YYYY-MM-DD, nullable)
   - status         TEXT     (in_progress, resolved, open)
   - resolution_note TEXT    (nullable)
"""


def generate_sql(question: str) -> str:
    """Step 1: Translate natural language question to SQL using LLM."""
    prompt = f"""You are a SQL expert for a hospital database.
Given the schema below, write a single SQLite SQL query to answer the question.
Return ONLY the SQL query — no explanation, no markdown, no code fences.

Schema:
{DB_SCHEMA}

Question: {question}

SQL:"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,          # deterministic SQL generation
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def clean_sql(raw_sql: str) -> str:
    """
    Step 2: Extract pure SQL from LLM output.
    LLMs sometimes wrap SQL in markdown fences or add explanation text.
    """
    # Remove markdown code fences: ```sql ... ``` or ``` ... ```
    raw_sql = re.sub(r"```(?:sql)?", "", raw_sql, flags=re.IGNORECASE)
    raw_sql = raw_sql.replace("```", "")

    # Extract first SQL statement (starts with SELECT/WITH)
    match = re.search(
        r"(SELECT|WITH)\b.*",
        raw_sql,
        flags=re.IGNORECASE | re.DOTALL
    )
    if match:
        sql = match.group(0).strip()
    else:
        sql = raw_sql.strip()

    # Remove any trailing explanation text after semicolon
    if ";" in sql:
        sql = sql[:sql.index(";") + 1]

    return sql.strip()


def execute_sql(sql: str) -> tuple[list, list]:
    """Step 3a: Execute SQL and return (rows, column_names)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return [dict(row) for row in rows], columns


def generate_answer(question: str, sql: str, results: list) -> str:
    """Step 3b: Pass SQL results back to LLM for natural language answer."""
    if not results:
        results_text = "The query returned no results."
    else:
        # Format results as a readable table
        results_text = "\n".join(str(row) for row in results[:20])  # cap at 20 rows

    prompt = f"""You are MediBot, an assistant for MediAssist Health Network.
A database query was run to answer the user's question. 
Provide a clear, concise natural language answer based on the query results.

Question: {question}
SQL Query: {sql}
Results:
{results_text}

Answer:"""

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def sql_rag_chain(question: str) -> dict:
    """
    Full SQL RAG pipeline:
    1. NL → SQL (LLM)
    2. Clean SQL output
    3. Execute SQL
    4. SQL results → NL answer (LLM)
    """
    try:
        # Step 1 — Generate SQL
        raw_sql = generate_sql(question)

        # Step 2 — Clean SQL
        sql = clean_sql(raw_sql)
        print(f"  Generated SQL: {sql}")

        # Step 3 — Execute
        results, columns = execute_sql(sql)
        print(f"  Results: {len(results)} rows, columns: {columns}")

        # Step 4 — Natural language answer
        answer = generate_answer(question, sql, results)

        return {
            "answer": answer,
            "sql": sql,
            "row_count": len(results),
            "sources": [{"source_document": "mediassist.db", 
                        "section_title": "SQL Query", 
                        "collection": "database"}],
            "retrieval_type": "sql_rag",
        }

    except Exception as e:
        return {
            "answer": f"I encountered an error running the database query: {str(e)}",
            "sql": "",
            "row_count": 0,
            "sources": [],
            "retrieval_type": "sql_rag",
        }