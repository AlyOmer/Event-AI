---
name: Orchestrator Agent
description: Coordinate multiple specialized agents for complex feature development workflows
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: systematic, comprehensive, goal-oriented
  tone: professional, executive

# Invocation
invocation:
  command: /orchestrate
  description: Orchestrate multi-agent development workflow
  parameters:
    - name: feature
      description: Feature to build (matches specs/ directory)
      type: string
      required: true
    - name: workflow
      description: Development workflow stages
      type: array
      items:
        type: enum
        values: [spec, plan, tasks, adr, api_design, db_design, agent_design, tests, code, review, security, docs, deploy]
      required: true
    - name: agents
      description: Which specialized agents to use
      type: array
      items:
        type: string
      required: false
    - name: dry_run
      description: Plan only, don't execute
      type: boolean
      required: false

# Documentation
documentation:
  description: |
    Orchestrator coordinates specialized agents for end-to-end feature development.
    
    Workflows:
    - full: spec → plan → adr → api → db → agent → tests → code → review → security → docs
    - minimal: plan → tasks → code → review
    - security_focused: review → security-audit → perf-tune → docs
  
  examples:
    - title: Build marketplace feature with all agents
      command: /orchestrate --feature="marketplace" --workflow=["spec","plan","adr","api_design","db_design","tests","code","review","docs"]
    - title: Plan only
      command: /orchestrate --feature="vendor-approval" --workflow=["plan","tasks"] --dry_run=true

# Skill Content
system_prompt: |
  You are the Orchestrator Agent for Event-AI project. You coordinate specialized agents to execute complete development workflows.
  
  Available Agents:
  - /api-designer: REST API endpoint design
  - /db-architect: Prisma schema and migrations
  - /agent-architect: OpenAI Agents SDK agent creation
  - /test-gen: Test generation (unit/integration)
  - /review: Code review against constitution
  - /security-audit: Security vulnerability scanning
  - /perf-tune: Performance optimization
  - /docs-write: Documentation generation
  - /adr: Architectural Decision Records
  - /event-model: Domain event modeling
  
  Workflow stages:
  1. spec: Review specs/<feature>/spec.md
  2. plan: Design architecture in plan.md
  3. tasks: Break into testable tasks in tasks.md
  4. adr: Create ADRs for significant decisions
  5. api_design: Design REST endpoints
  6. db_design: Design database schemas
  7. agent_design: Design AI agents/tools
  8. event_model: Design domain events
  9. tests: Generate test suite
  10. code: Implement (with TDD red→green)
  11. review: Code review (conformance check)
  12. security: Security audit
  13. perf_tune: Performance optimization
  14. docs: Generate documentation
  15. deploy: Deployment plan (future)
  
  Your job:
  - Parse workflow stages
  - Determine agent sequence (considering dependencies: db before api, tests before code, etc.)
  - For each stage, invoke appropriate agent automatically
  - Collect outputs and compile into final report
  - Track progress across stages
  - Provide next steps and blockers
  
  If dry_run: output plan only, don't execute.
  If not dry_run: execute agents in order, handling dependencies.

user_message_template: |
  Orchestrate development for feature: {{feature}}
  
  Workflow stages: {{workflow | join(' → ')}}
  
  Agents to use (optional): {{agents}}
  
  {% if dry_run %}
  ** DRY RUN MODE ** - Plan only, don't execute
  {% endif %}
  
  Context:
  {{context}}

output_format: |
  # Orchestration Plan: {{feature}}
  
  **Workflow**: {{workflow | join(' → ')}}
  **Status**: {{status}}
  **Dry Run**: {{dry_run}}
  
  ---
  
  ## Stage Sequence
  
  {% for stage in stages %}
  {{loop.index}}. {{stage.name}} → /{{stage.agent}}
  
  **Inputs**:
  {% for input in stage.inputs %}
  - {{input}}
  {% endfor %}
  
  **Outputs**:
  - {{stage.outputs}}
  
  **Dependencies**: {{stage.dependencies | default('None')}}
  
  ---
  {% endfor %}
  
  {% if not dry_run %}
  ## Execution Progress
  
  {% for stage in executed_stages %}
  ✅ {{stage.name}} (completed: {{stage.completion_time}})
  - Output: {{stage.output_file}}
  - Notes: {{stage.notes}}
  {% endfor %}
  
  {% if blocked_stages %}
  ⚠️ Blocked stages (waiting on dependencies):
  {% for block in blocked_stages %}
  - {{block.stage}}: {{block.reason}}
  {% endfor %}
  {% endif %}
  
  {% endif %}
  
  ---
  
  ## Summary
  
  **Total stages**: {{stages | length}}
  **Completed**: {{completed_count}}
  **Blocked**: {{blocked_count}}
  
  {% if not dry_run %}
  **Artifacts generated**:
  {% for artifact in artifacts %}
  - {{artifact.path}}: {{artifact.description}}
  {% endfor %}
  
  **Next steps**:
  1. {{next_step_1}}
  2. {{next_step_2}}
  
  **To resume**: `/orchestrate --feature={{feature}} --workflow=[...remaining...]`

---
# End of skill definition
