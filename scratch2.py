import os

files = ['backend/tests/test_m82.py', 'backend/tests/test_m83.py', 'backend/tests/test_m86.py']

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace('headers=headers)', 'headers=headers, json={"checklist_confirmed": True})')
    content = content.replace('headers=_admin_headers(m83_db),', 'headers=_admin_headers(m83_db), json={"checklist_confirmed": True}')
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
