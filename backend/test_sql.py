# backend/test_sql.py

from sql_rag import sql_rag_chain

questions = [
    "How many billing claims were escalated last month?",
    "What is the total claim amount by department?",
    "How many maintenance tickets are currently open?",
    "Which insurer has the most rejected claims?",
]

for q in questions:
    print("\n" + "─" * 50)
    print(f"Q: {q}")
    result = sql_rag_chain(q)
    print(f"SQL: {result['sql']}")
    print(f"Answer: {result['answer']}")