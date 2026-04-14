---
name: Skill Manager
description: Discover, test, and compose Event-AI subagents for complex workflows
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: systematic, clear
  tone: helpful

# Invocation
invocation:
  command: /skills
  description: Manage and orchestrate skills
  parameters:
    - name: action
      description: What to do
      type: enum
      values: [list, info, compose, verify]
      required: true
    - name: skill
      description: Skill to operate on
      type: string
      required: false
    - name: pipeline
      description: JSON pipeline definition
      type: string
      required: false

# Documentation
documentation:
  description: |
    Skill Manager helps you discover, understand, and compose Event-AI subagents.
    
    Actions:
    - list: Show all available skills with brief descriptions
    - info: Detailed info about a specific skill (params, examples)
    - compose: Chain multiple skills together in a workflow
    - verify: Check all skills are valid and conformant
  
  examples:
    - title: List all skills
      command: /skills --action=list
    - title: Get info on api-designer
      command: /skills --action=info --skill=api-designer
    - title: Compose workflow
      command: /skills --action=compose --pipeline='[{"skill":"api-designer","params":{...}}]'

# Skill Content
system_prompt: |
  You are the Skill Manager for Event-AI's subagent system.
  
  **Skill Discovery**:
  Scan `skills/` directory for `*.prompt.md` files and parse frontmatter.
  
  **Skill Composition**:
  Multiple skills can be chained where outputs of one feed into another's inputs.
  
  Pipeline format (JSON):
  ```json
  {
    "pipeline": [
      {
        "skill": "api-designer",
        "params": {"endpoint_name": "...", "method": "...", ...},
        "output_as": "api_design"  // optional, for chaining
      },
      {
        "skill": "db-architect",
        "params": {"entity_name": "...", ...},
        "use_output_from": "api_design.field.path"  // inject previous output
      }
    ]
  }
  ```
  
  **Validation**:
  - Check all skills have required frontmatter fields
  - Validate parameter schemas against YAML
  - Ensure no circular dependencies
  - Report missing skills

user_message_template: |
  Skill Manager action: {{action}}
  
  {% if skill %}
  Target skill: {{skill}}
  {% endif %}
  
  {% if pipeline %}
  Pipeline:
  ```
  {{pipeline}}
  ```
  {% endif %}

output_format: |
  {% if action == 'list' %}
  # Available Skills
  
  {{skills_count}} skills in `skills/`:
  
  {% for skill in skills %}
  **/{{skill.name}}**
  {{skill.description}}
  *Package*: {{skill.package_hint}} | *Stage*: {{skill.stage}}
  
  {% endfor %}
  
  Use `/skills --action=info --skill=<name>` for details.
  
  {% elif action == 'info' %}
  # Skill Information: {{skill_name}}
  
  **Command**: `/{{skill.name}}`
  **Description**: {{skill.description}}
  **Version**: {{skill.version}}
  
  ---
  
  ## Parameters
  
  | Name | Type | Required | Description |
  |------|------|----------|-------------|
  {% for param in skill.parameters %}
  | `{{param.name}}` | `{{param.type}}` | {{param.required}} | {{param.description}} |
  {% endfor %}
  
  ---
  
  ## Examples
  
  {% for ex in skill.examples %}
  - {{ex.title}}
    ```
    {{ex.command}}
    ```
  {% endfor %}
  
  ---
  
  ## Generated Artifacts
  
  When invoked, `/{{skill.name}}` creates:
  {% for artifact in skill.artifacts %}
  - `{{artifact.path}}`
  {% endfor %}
  
  **Related skills**: {{related_skills}}
  
  {% elif action == 'compose' %}
  # Skill Composition Plan
  
  **Pipeline**: {{pipeline.pipeline | length}} stages
  
  {% for stage in pipeline.pipeline %}
  ## {{loop.index}}. {{stage.skill}}
  
  **Parameters**:
  {% for param, value in stage.params.items() %}
  - `{{param}}`: {{value}}
  {% endfor %}
  
  {% if stage.use_output_from %}
  **Injects from**: `{{stage.use_output_from}}`
  {% endif %}
  
  ---
  {% endfor %}
  
  **Estimated artifacts**: {{estimated_artifacts_count}}
  
  **Execution**: Run these commands in sequence:
  {% for stage in pipeline.pipeline %}
  ```bash
  /{{stage.skill}} {% for param, value in stage.params.items() %}--{{param}}="{{value}}" {% endfor %}
  ```
  {% endfor %}
  
  **Or use orchestrator**: `/orchestrate --feature="{{feature}}" --workflow=[...]`
  
  {% elif action == 'verify' %}
  # Skill Verification Report
  
  {% if all_valid %}
  ✅ All {{skills_count}} skills are valid.
  
  **Skills checked**:
  {% for skill in skills %}
  - `/{{skill.name}}`: ✅ {{skill.valid_reason}}
  {% endfor %}
  
  No issues found.
  {% else %}
  ⚠️ Issues detected:
  
  {% for issue in issues %}
  - **{{issue.skill}}**: {{issue.message}}
    → {{issue.suggestion}}
  {% endfor %}
  
  **Overall status**: {{status}}
  {% endif %}
  
  ---
  
  **Skill system health**: {{health_status}}
  
  {% endif %}
  
  **Generated**: {{timestamp}}

---
# End of skill definition
