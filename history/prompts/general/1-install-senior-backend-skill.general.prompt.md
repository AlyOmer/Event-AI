---
id: 1
title: Install senior-backend skill
stage: general
date: 2026-04-09
surface: agent
model: nvidia/nemotron-3-super-120b-a12b:free
feature: none
branch: 013-fastapi-jwt-auth
user: ali
command: npx claude-code-templates@latest --skill development/senior-backend
labels: [setup, skill-installation, claude-code]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .claude/skills/senior-backend/SKILL.md
  - .claude/skills/senior-backend/references/api_design_patterns.md
  - .claude/skills/senior-backend/references/backend_security_practices.md
  - .claude/skills/senior-backend/references/database_optimization_guide.md
  - .claude/skills/senior-backend/scripts/api_load_tester.py
  - .claude/skills/senior-backend/scripts/api_scaffolder.py
  - .claude/skills/senior-backend/scripts/database_migration_tool.py
tests:
  - None
## Prompt

install this globally in claude code npx claude-code-templates@latest --skill development/senior-backend

## Response snapshot

Successfully installed the senior-backend skill using npx claude-code-templates@latest. The skill was installed to .claude/ directory with all referenced files and scripts.

## Outcome

- ✅ Impact: Senior-backend skill installed successfully for backend development guidance
- 🧪 Tests: None
- 📁 Files: 7 files installed including skill documentation, references, and scripts
- 🔁 Next prompts: None
- 🧠 Reflection: Used npx approach after permission issues with global npm install

## Evaluation notes (flywheel)

- Failure modes observed: Permission denied when trying npm install -g due to lack of sudo privileges in non-interactive environment
- Graders run and results (PASS/FAIL): Skill installation verified by checking installed files
- Prompt variant (if applicable): None
- Next experiment (smallest change to try): None

---