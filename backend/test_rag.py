# backend/test_rag.py

from hybrid_rag import rag_answer

# Test 1 — Doctor asking clinical question
print("\n── Test 1: Doctor query ──")
result = rag_answer("What is the standard drug dosage protocol?", "doctor")
print("Answer:", result["answer"][:200])
print("Sources:", result["sources"])

# Test 2 — Nurse trying to access billing (RBAC test)
print("\n── Test 2: Nurse asking billing question ──")
result = rag_answer("What are the insurance billing codes?", "nurse")
print("Answer:", result["answer"][:200])
print("Sources:", result["sources"])

# Test 3 — Admin gets everything
print("\n── Test 3: Admin query ──")
result = rag_answer("What is the equipment maintenance schedule?", "admin")
print("Answer:", result["answer"][:200])
print("Sources:", result["sources"])