# Implementation Plan: Constitution-Spec Generator

**Branch**: `feature/constitution-spec-generator` | **Date**: 2026-04-07 | **Spec**: [spec.md](file:///home/ali/Desktop/Event-AI-Latest/specs/001-constitution-spec-generator/spec.md)
**Input**: Feature specification from `/specs/001-constitution-spec-generator/spec.md`

## Summary

Implements an automated CLI tool that generates constitution-aware feature specifications. The tool parses `constitution.md`, maps feature descriptions to relevant constitutional sections, and produces complete `spec.md` files with user stories, functional requirements (incorporating constitutional mandates), success criteria, and edge cases. Supports batch generation and compliance validation of existing specs.

## Technical Context

**Language/Version**: Node.js ≥ 20 or Python ≥ 3.12 (standalone CLI script)
**Primary Dependencies**: Markdown parser, LLM API (Gemini), Zod/Pydantic for structured output
**Storage**: Filesystem (specs directory)
**Testing**: Unit tests for parser + constitution matching logic
**Performance Goals**: Single spec < 10s; batch of 10 < 2 min
**Constraints**: Output must match `.specify/templates/spec-template.md` format exactly

## Constitution Check

- [x] **Spec-Driven Development**: The tool enforces SDD by automating spec creation.
- [x] **Constitutional Compliance**: Every generated spec references applicable constitutional mandates.
- [x] **No Banned Practices**: Tool follows package structure, no `sys.path.insert` or hardcoded secrets.

## Project Structure

```text
.specify/
├── scripts/
│   └── generate-spec.ts           # [NEW] Main CLI entrypoint
├── templates/
│   └── spec-template.md           # Existing template
├── memory/
│   └── constitution.md            # Source of truth
└── lib/
    ├── constitution-parser.ts     # [NEW] Parse constitution into structured sections
    ├── domain-mapper.ts           # [NEW] Map feature description → constitutional domains
    └── spec-writer.ts             # [NEW] Generate spec.md from template + constitution data
```

## Phase 1: Constitution Parser

**Tasks**:
1. Parse `constitution.md` into structured data: extract each numbered section (I–X), sub-rules, anti-patterns table, technology stack tables.
2. Index sections by domain tags: `auth`, `database`, `api`, `testing`, `security`, `eda`, `agent`, `frontend`.
3. Extract performance standards table as key-value pairs.

## Phase 2: Domain Mapper

**Tasks**:
1. Analyze a feature description string to identify affected domains (keyword matching + optional LLM classification).
2. Return ranked list of constitutional sections relevant to the feature.
3. Extract specific mandates (e.g., "bcrypt ≥ 12 rounds") as injectable requirements.

## Phase 3: Spec Writer

**Tasks**:
1. Load `spec-template.md` and populate all sections.
2. Inject constitutional mandates into Functional Requirements as `FR-XXX: System MUST ...` items.
3. Generate user stories with Given/When/Then acceptance criteria.
4. Generate success criteria aligned with constitution performance standards.
5. Limit `[NEEDS CLARIFICATION]` markers to ≤ 3 per spec.
6. Write output to `specs/NNN-short-name/spec.md`.

## Phase 4: Batch & Validation Modes

**Tasks**:
1. Accept YAML/JSON input with multiple feature descriptions for batch processing.
2. Compliance validation mode: scan existing spec.md against constitution, report addressed/missing mandates.
3. Output JSON with `{ branchName, specFile }` for each generated spec.

## Phase 5: Testing

**Tasks**:
1. Parser tests: verify all 10 constitution sections are extracted correctly.
2. Domain mapper tests: known feature descriptions map to expected sections.
3. Spec writer tests: output matches template structure, contains injected mandates.
4. Integration test: end-to-end generation from description to complete spec file.
