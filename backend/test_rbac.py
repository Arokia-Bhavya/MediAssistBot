from rbac import get_collections_for_role

print("Nurse allowed:", get_collections_for_role("nurse"))
print("Doctor allowed:", get_collections_for_role("doctor"))
print("Admin allowed:", get_collections_for_role("admin"))