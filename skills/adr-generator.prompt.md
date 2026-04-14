---
name: ADR Generator
description: Create Architecture Decision Records following Event-AI standards
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: structured, objective, comprehensive
  tone: formal, technical

# Invocation
invocation:
  command: /adr
  description: Generate Architecture Decision Record
  parameters:
    - name: title
      description: Short descriptive title (max 50 chars)
      type: string
      required: true
    - name: context
      description: The problem or decision being addressed
      type: string
      required: true
    - name: alternatives_considered
      description: Options evaluated with pros/cons
      type: array
      items:
        type: object
        properties:
          name: string
          pros: array
          cons: array
      required: true
    - name: decision
      description: The chosen approach
      type: string
      required: true
    - name: consequences
      description: Implications of this decision (positive and negative)
      type: array
      items:
        type: string
      required: true
    - name: related_adrs
      description: Related ADR numbers
      type: array
      items:
        type: string
      required: false

# Documentation
documentation:
  description: |
    ADR Generator creates Markdown ADRs in `history/adr/` using the standard template.
    
    ADR Format:
    - Title: "Decision Title" (max 50 chars)
    - Status: Proposed/Accepted/Deprecated/Superseded
    - Context: What problem are we solving?
    - Decision: What did we choose and why?
    - Alternatives: What did we consider and why rejected?
    - Consequences: What are the trade-offs?
    - Related: Links to related ADRs/specs
  
    All significant architectural decisions should be documented per constitution.
  
  examples:
    - title: Database choice
      command: /adr --title="Use Neon Serverless PostgreSQL" --context="Need a cloud-native DB for monorepo" --alternatives_considered=[{...}] --decision="Use Neon PostgreSQL" --consequences=["Vendor lock-in", "Serverless scaling benefits"]

# Skill Content
system_prompt: |
  You are an architect creating ADRs for Event-AI. Follow the ADR template in `.specify/templates/adr-template.md`.
  
  ADR Best Practices:
  1. Title: "Use X" or "Adopt Y" — action-oriented, specific
  2. Context: set the stage, what problem, who does it affect?
  3. Decision: clear statement of what we're doing
  4. Alternatives: at least 2-3 viable options with honest trade-offs
  5. Consequences: both positive (benefits) and negative (costs)
  6. Use numbered headings, keep under 500 words
  7. Include links to specs, tickets, PRs when available
  
  Significance Test (constitution §X): Create ADR if:
  - Long-term consequences (framework, data model, API, security, platform)
  - Multiple viable options considered with trade-offs
  - Cross-cutting influences system design
  
  Write in third-person, objective tone. Avoid "I think" or "We decided" — state as architectural fact.

user_message_template: |
  Create ADR: {{title}}
  
  Context:
  {{context}}
  
  Alternatives Considered:
  {% for alt in alternatives_considered %}
  - **{{alt.name}}**
    Pros: {{alt.pros | join(', ')}}
    Cons: {{alt.cons | join(', ')}}
  {% endfor %}
  
  Decision:
  {{decision}}
  
  Consequences (positive & negative):
  {% for cons in consequences %}
  - {{cons}}
  {% endfor %}
  
  {% if related_adrs %}
  Related ADRs: {{related_adrs | join(', ')}}
  {% endif %}

output_format: |
  ---
  title: "{{title}}"
  status: "Accepted"
  category: "technical"
  created: "{{date}}"
  authors: ["Event-AI Team"]
  reviewers: []
  related: []
  ---
  
  # {{title}}
  
  ## Context
  
  {{context}}
  
  ## Decision
  
  {{decision}}
  
  ## Alternatives Considered
  
  {% for alt in alternatives_considered %}
  ### {{alt.name}}
  
  **Pros:**
  {% for pro in alt.pros %}
  - {{pro}}
  {% endfor %}
  
  **Cons:**
  {% for con in alt.cons %}
  - {{con}}
  {% endfor %}
  {% endfor %}
  
  ## Consequences
  
  ### Positive
  
  {% for cons in consequences %}
  - {{cons}}
  {% endfor %}
  
  ### Negative
  
  {% for cons in negative_consequences %}
  - {{cons}}
  {% endfor %}
  
  {% if related_adrs %}
  ## Related
  
  {% for adr in related_adrs %}
  - [[ADR-{{adr}}]]
  {% endfor %}
  {% endif %}
  
  ## References
  
  - Constitution: §{{constitution_section}}
  - Spec: specs/{{feature_name}}/spec.md
  - Plan: specs/{{feature_name}}/plan.md
  
  ---
  
  **Files to create/modify**:
  - `history/adr/{{next_id | pad(3)}}-{{title | slugify}}.md`
  
  **Next steps**:
  1. Review by architecture team
  2. Link from constitution if cross-cutting
  3. Update decision record in specs/plan.md

---
# End of skill definition
