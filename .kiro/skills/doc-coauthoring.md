---
inclusion: manual
---

# Doc Co-Authoring Workflow

Guide users through collaborative document creation in three stages: Context Gathering → Refinement & Structure → Reader Testing.

## When to Offer

Trigger when user mentions: writing docs, drafting proposals, creating specs, PRDs, design docs, decision docs, RFCs, or similar writing tasks.

Offer the structured workflow or let them work freeform — their choice.

---

## Stage 1: Context Gathering

**Goal:** Close the gap between what the user knows and what you know.

### Initial Questions
1. What type of document is this?
2. Who's the primary audience?
3. What's the desired impact when someone reads this?
4. Is there a template or specific format to follow?
5. Any other constraints or context?

### Info Dumping
Encourage the user to dump all context: background, team discussions, why alternatives aren't used, org context, timeline, technical dependencies, stakeholder concerns. Don't worry about organizing — just get it out.

If integrations are available (Slack, Drive, etc.), offer to pull context directly.

### Clarifying Questions
After the dump, generate 5–10 numbered questions based on gaps. User can answer in shorthand (e.g., "1: yes, 2: see #channel").

**Exit condition:** You can ask about edge cases and trade-offs without needing basics explained.

---

## Stage 2: Refinement & Structure

**Goal:** Build the document section by section.

### Structure First
Suggest 3–5 sections appropriate for the doc type, or ask which sections they need. Create initial scaffold with placeholder text (`[To be written]`) for all sections.

### For Each Section (repeat):

1. **Clarifying Questions** — 5–10 questions about what to include
2. **Brainstorm** — 5–20 numbered options for what might go in this section
3. **Curation** — User selects what to keep/remove/combine (e.g., "Keep 1,4,7 / Remove 3 / Combine 11+12")
4. **Gap Check** — Anything important missing?
5. **Draft** — Write the section using `str_replace` on the placeholder
6. **Iterate** — Make surgical edits based on feedback; never reprint the whole doc

**Key instruction to user (first section only):** Instead of editing directly, tell you what to change. This helps learn their style for future sections.

After 3 iterations with no substantial changes, ask if anything can be removed without losing value.

### Near Completion
When 80%+ done, re-read the entire document and check for: flow, consistency, redundancy, contradictions, filler content.

---

## Stage 3: Reader Testing

**Goal:** Test the doc with a fresh context (no bleed from this conversation).

### With Sub-Agents Available
1. Predict 5–10 questions readers would realistically ask
2. Test each question with a fresh sub-agent (doc content only, no conversation context)
3. Run additional checks: ambiguity, false assumptions, contradictions
4. Fix any gaps found, loop back to Stage 2 if needed

### Without Sub-Agents (manual)
1. Predict 5–10 reader questions
2. Instruct user to open a fresh Claude conversation, paste the doc, and ask those questions
3. Also ask Reader Claude: "What's ambiguous?", "What knowledge does this assume?", "Any contradictions?"
4. Fix gaps based on results

**Exit condition:** Reader Claude consistently answers questions correctly with no new gaps surfaced.

---

## Final Review

When Reader Testing passes:
1. Recommend user does a final read-through (they own this doc)
2. Suggest double-checking facts, links, technical details
3. Ask if they want one more review or if work is done

**Tips:** Link this conversation in an appendix; use appendices for depth without bloating the main doc; update as real reader feedback comes in.

---

## Guidance Notes

- Be direct and procedural; explain rationale briefly when it affects user behavior
- If user wants to skip a stage: ask if they want to work freeform
- Use `str_replace` for all edits — never reprint the whole doc
- Don't let context gaps accumulate — address them as they come up
