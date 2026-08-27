import re
with open("backend/app/api/admin.py", "r", encoding="utf-8") as f:
    content = f.read()

replacement = """    medical_rag = "AUTHORITATIVE PRODUCTION DATASET: PENDING HUMAN ADMINISTRATIVE REVIEW"
    if k_authoritative > 0 and k_verified > 0 and k_active > 0:
        medical_rag = "CLINICALLY_DATA_READY"
    elif k_verified > 0 and k_active == 0:
        medical_rag = "AUTHORITATIVE PRODUCTION DATASET: VERIFIED BUT NOT ACTIVATED"
    elif k_pending > 0:
        medical_rag = "AUTHORITATIVE PRODUCTION DATASET: PENDING HUMAN ADMINISTRATIVE REVIEW"
        
    facility_network = "READY" if f_verified > 0 else "BLOCKED"
    
    overall_state = "CLINICALLY_DATA_READY" if (medical_rag == "CLINICALLY_DATA_READY" and facility_network == "READY") else medical_rag"""

content = re.sub(r'    medical_rag = "BLOCKED".*?else "BLOCKED"', replacement, content, flags=re.DOTALL)
with open("backend/app/api/admin.py", "w", encoding="utf-8") as f:
    f.write(content)
