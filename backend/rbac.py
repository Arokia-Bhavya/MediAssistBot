# backend/rbac.py

ROLE_COLLECTIONS = {
    "doctor":            ["general", "clinical", "nursing"],
    "nurse":             ["general", "nursing"],
    "billing_executive": ["general", "billing"],
    "technician":        ["general", "equipment"],
    "admin":             ["general", "clinical", "nursing", "billing", "equipment"],
}

# Roles that can use SQL RAG
SQL_RAG_ROLES = {"billing_executive", "admin"}

def get_collections_for_role(role: str) -> list[str]:
    return ROLE_COLLECTIONS.get(role, [])

def can_use_sql_rag(role: str) -> bool:
    return role in SQL_RAG_ROLES