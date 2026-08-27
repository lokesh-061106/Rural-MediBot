import re, glob
for f in glob.glob('backend/tests/*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = re.sub(r'(client\.get\([^)]+),\s*json=\{"checklist_confirmed": True\}\)', r'\1)', content)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
