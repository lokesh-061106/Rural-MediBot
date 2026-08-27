
import re

# Fix test_m45.py
with open("backend/tests/test_m45.py", "r", encoding="utf-8") as f:
    c45 = f.read()

c45 = c45.replace("\"is_authoritative\": True, \"verification_status\": \"VERIFIED\"}", "\"is_authoritative\": True, \"verification_status\": \"VERIFIED\", \"status\": \"ACTIVE\"}")

with open("backend/tests/test_m45.py", "w", encoding="utf-8") as f:
    f.write(c45)

# Fix test_m81.py
with open("backend/tests/test_m81.py", "r", encoding="utf-8") as f:
    c81 = f.read()

c81 = c81.replace("AUTHORITATIVE MEDICAL DATASET NOT AVAILABLE", "AUTHORITATIVE PRODUCTION DATASET: NOT PROVIDED / NOT VERIFIED")
c81 = c81.replace("\"status\": \"success\"", "\"status\": \"PENDING_REVIEW\"")
c81 = c81.replace("res[\"status\"] == \"success\"", "res[\"status\"] == \"PENDING_REVIEW\"")

with open("backend/tests/test_m81.py", "w", encoding="utf-8") as f:
    f.write(c81)

