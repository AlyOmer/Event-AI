# 🚀 Quick Start Guide

Get up and running with Event-AI subagents in 5 minutes.

## Prerequisites

You're already in the Event-AI project directory with Claude Code installed.

##Verify Installation

```bash
cd /home/ali/Desktop/Event-AI-Latest
bash skills/validate-skills.sh
```

Expected: `✅ All skills are properly structured!`

---

## Your First Skill Invocation

Try the **API Designer** to create a new endpoint:

```bash
/api-designer \
  --endpoint_name="health_check" \
  --method="GET" \
  --purpose="Simple health check endpoint for backend liveness probe" \
  --package="backend"
```

**Expected output**:
- TypeScript route code
- Zod validation schema (minimal for health check)
- Response format
- Rate limiting notes

---

## Common Workflows

### 1. Add a New Table (e.g., Category)

**Step 1**: Design the database entity

```bash
/db-architect \
  --entity_name="Category" \
  --purpose="Vendor categories for filtering (photographer, caterer, venue, etc.)" \
  --fields='[
    {"name":"name", "type":"String", "required":true, "unique":true, "indexed":true, "description":"Category name"},
    {"name":"description", "type":"String", "required":false, "indexed":false, "description":"Optional description"}
  ]' \
  --relations='[
    {"type":"many-to-many", "target":"Vendor", "field":"vendors", "inverseField":"categories"}
  ]'
```

**Step 2**: Add API endpoints

```bash
/api-designer \
  --endpoint_name="list_categories" \
  --method="GET" \
  --purpose="List all vendor categories" \
  --package="backend"
```

---

### 2. Build an AI Agent Tool

**Step 1**: Design the tool

```bash
/agent-architect \
  --agent_name="VendorDiscoveryAgent" \
  --responsibility="Find vendors matching event requirements" \
  --handoffs=["BookingAgent"] \
  --tools='[
    {"name":"search_vendors", "purpose":"Search by filters", "parameters":["category:str","city:str","budget:int"]},
    {"name":"get_vendor_reviews", "purpose":"Fetch reviews for vendor", "parameters":["vendor_id:str","limit:int=10"]}
  ]' \
  --package="ai"
```

**Step 2**: Write tests for the tool

```bash
/test-gen \
  --test_type="unit" \
  --target="search_vendors_tool" \
  --framework="pytest" \
  --package="ai" \
  --mock_dependencies=["LLM", "Neon DB"]
```

**Output**: Test file ready to run (update implementation to pass).

---

### 3. Code Review Before Commit

```bash
/review \
  --file_path="packages/backend/src/routes/bookings.routes.ts" \
  --change_type="new_feature" \
  --package="backend"
```

**Output**:
- Constitution compliance matrix
- Issue list with fixes
- Approval or request changes

---

### 4. Full Feature Workflow

Use **orchestrator** to automate the complete TDD cycle:

```bash
/orchestrate \
  --feature="vendor-reviews" \
  --workflow=["plan","tasks","db_design","api_design","tests","code","review"] \
  --dry_run=false
```

This will:
1. Check `specs/vendor-reviews/` exists
2. Generate plan and tasks
3. Design database schema
4. Design API endpoints
5. Generate test suite
6. Wait for you to implement code
7. Run code review

**Dry-run first** to see the plan:

```bash
/orchestrate --feature="vendor-reviews" --workflow=["plan","tasks","code"] --dry_run=true
```

---

## Pro Tips

### 1. Copy-Paste Commands

All examples are ready-to-run. Replace placeholder values:
- `"endpoint_name"` → your endpoint in snake_case
- `"agent_name"` → PascalCase agent name
- `package` → one of: `backend`, `ai`, `user`, `admin`, `vendor`

### 2. Use Tab Completion

Claude Code can help autocomplete `/skill-name` commands. Just start typing `/` and see available skills.

### 3. Chain Commands

```bash
# Design DB → Design API → Generate tests
/db-architect ... && /api-designer ... && /test-gen ...
```

### 4. Learn from Examples

See `skills/EXAMPLES.md` for comprehensive patterns.

---

## What Skills Do What?

| Action | Skill | Packages |
|--------|-------|----------|
| Design database | `/db-architect` | backend, ai |
| Design API endpoint | `/api-designer` | backend |
| Design AI agent | `/agent-architect` | ai |
| Design domain event | `/event-model` | backend |
| Generate tests | `/test-gen` | backend, ai, user |
| Review code | `/review` | all |
| Security audit | `/security-audit` | all |
| Optimize performance | `/perf-tune` | all |
| Write docs | `/write-docs` | all |
| Create ADR | `/adr` | all |
| Optimize prompts | `/prompt-eng` | ai |
| Orchestrate workflow | `/orchestrate` | all |
| Manage skills | `/skills` | meta |

---

## Need Help?

- **Skill details**: `/skills --action=info --skill=<skill-name>`
- **List all**: `/skills --action=list`
- **Validate**: `bash skills/validate-skills.sh`
- **Documentation**: `skills/README.md`
- **Examples**: `skills/EXAMPLES.md`
- **Constitution**: `.specify/memory/constitution.md`

---

## TDD Checklist Reminder

For every feature:

```markdown
- [ ] Spec reviewed (specs/<feature>/spec.md)
- [ ] Plan created (specs/<feature>/plan.md)
- [ ] ADR documented (if architectural decision)
- [ ] Tasks defined (specs/<feature>/tasks.md)
- [ ] Tests written first (/test-gen)
- [ ] Code implemented
- [ ] Code reviewed (/review)
- [ ] Security checked (/security-audit)
- [ ] Performance verified (/perf-tune if needed)
- [ ] Documentation complete (/write-docs)
- [ ] CI passing (pnpm test, pnpm lint)
```

---

**Next Steps**:

1. Try `/api-designer` for a simple endpoint
2. Run `/skills --action=list` to see all 13 skills
3. Read `skills/EXAMPLES.md` for real-world patterns
4. Start building your feature with `/orchestrate`

Happy coding! 🎉
