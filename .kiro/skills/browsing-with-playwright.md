---
inclusion: manual
---

# Browser Automation (Playwright)

Automate browser interactions via Playwright MCP server.

## Server Lifecycle

### Start Server
```bash
bash .claude/skills/browsing-with-playwright/scripts/start-server.sh
# Or manually: npx @playwright/mcp@latest --port 8808 --shared-browser-context &
```

### Stop Server
```bash
bash .claude/skills/browsing-with-playwright/scripts/stop-server.sh
# Or manually: python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call -u http://localhost:8808 -t browser_close -p '{}'
```

**Important:** The `--shared-browser-context` flag is required to maintain browser state across multiple calls.

## Quick Reference

All commands use: `python3 .claude/skills/browsing-with-playwright/scripts/mcp-client.py call -u http://localhost:8808`

### Navigation
```bash
-t browser_navigate -p '{"url": "https://example.com"}'
-t browser_navigate_back -p '{}'
```

### Get Page State
```bash
-t browser_snapshot -p '{}'                          # accessibility snapshot (returns element refs)
-t browser_take_screenshot -p '{"type": "png", "fullPage": true}'
```

### Interact with Elements (use `ref` from snapshot)
```bash
-t browser_click -p '{"element": "Submit button", "ref": "e42"}'
-t browser_type -p '{"element": "Search input", "ref": "e15", "text": "hello", "submit": true}'
-t browser_fill_form -p '{"fields": [{"ref": "e10", "value": "john@example.com"}]}'
-t browser_select_option -p '{"element": "Country", "ref": "e20", "values": ["US"]}'
```

### Wait & Execute
```bash
-t browser_wait_for -p '{"text": "Success"}'
-t browser_wait_for -p '{"time": 2000}'
-t browser_evaluate -p '{"function": "return document.title"}'
```

### Multi-Step (atomic)
```bash
-t browser_run_code -p '{"code": "async (page) => { await page.goto(\"https://example.com\"); return await page.title(); }"}'
```

## Workflows

**Form Submission:** Navigate → snapshot → fill fields → click submit → wait for confirmation → screenshot

**Data Extraction:** Navigate → snapshot (contains text) → browser_evaluate for complex extraction

## Verification
```bash
python3 .claude/skills/browsing-with-playwright/scripts/verify.py
# Expected: ✓ Playwright MCP server running
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Element not found | Run browser_snapshot first to get current refs |
| Click fails | Try browser_hover first, then click |
| Form not submitting | Use `"submit": true` with browser_type |
| Server not responding | Stop and restart server scripts |
