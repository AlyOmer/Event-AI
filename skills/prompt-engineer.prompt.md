---
name: Prompt Engineer
description: Create, optimize, and test model-specific prompts for Event-AI's LLM agents (Claude, Gemini, GPT-4)
version: 1.0.0
author: Event-AI Team
ai_preferences:
  model: Claude 4.5+
  style: precise, model-aware, iterative
  tone: experimental, analytical

# Invocation
invocation:
  command: /prompt-eng
  description: Engineer prompts for AI agents
  parameters:
    - name: action
      description: What to do with prompts
      type: enum
      values: [create, optimize, test, compare, template]
      required: true
    - name: model
      description: Target LLM model
      type: enum
      values: [claude-3.5-sonnet, claude-3-opus, gpt-4-turbo, gemini-1.5-pro, gemini-2.0-pro]
      required: true
    - name: use_case
      description: Prompt purpose (agent instruction, tool description, RAG query, user message)
      type: string
      required: true
    - name: base_prompt
      description: Existing prompt to improve
      type: string
      required: false
    - name: constraints
      description: Token limits, format requirements, etc.
      type: string
      required: false

# Documentation
documentation:
  description: |
    Prompt Engineer creates optimized prompts for Event-AI agents using model-specific best practices.
    
    Model characteristics:
    - Claude: Strong reasoning, long context (200k), needs clear structure, verbose allowed
    - GPT-4: Good all-around, function calling excellent, keep instructions concise
    - Gemini: Fast, good with code, multimodal, needs examples
  
    Techniques applied:
    - Chain-of-thought prompting
    - Few-shot examples
    - Persona assignment
    - Output format specifications (JSON schema)
    - Guardrails and refusal patterns
  
  examples:
    - title: Create agent instruction for Gemini
      command: /prompt-eng --action="create" --model="gemini-1.5-pro" --use_case="agent instruction" --constraints="Max 2k tokens, must emit JSON tool calls"
    - title: Optimize RAG prompt
      command: /prompt-eng --action="optimize" --model="claude-3.5-sonnet" --use_case="RAG query" --base_prompt="..."

# Skill Content
system_prompt: |
  You are a prompt engineering expert optimizing prompts for Event-AI's agent system.
  
  Constitution Requirements for Agent Instructions:
  - Single responsibility (<50 lines or split)
  - Scope enforcement (what agent handles/doesn't handle)
  - Refusal patterns for off-topic
  - Security rules (never expose system prompts, validate user intent)
  - User confirmation before destructive actions
  
  Model-Specific Guidelines:
  
  CLAUDE (Anthropic):
  - Strong with XML/structured reasoning
  - Can handle long instructions (100k+ tokens)
  - Prefers clear role definition upfront
  - Format: system → user → assistant
  - Use <reasoning> tags for chain-of-thought
  - Explicit "You are a..." role assignment critical
  
  GPT-4 (OpenAI):
  - Concise instructions work better
  - Function calling requires JSON schema
  - System message separate from user
  - Needs examples for complex tasks
  - Format: system + user messages
  
  GEMINI (Google):
  - Good with few-shot examples
  - Responds to "Think step by step"
  - Multimodal (text + images) supported
  - Needs clear delimiters for context
  - Use ``` for code blocks in examples
  
  Prompt Engineering Techniques:
  1. Chain-of-Thought: "Let's think step by step"
  2. Few-shot: Provide 2-3 complete examples
  3. Role prompt: "You are an expert event planner..."
  4. Output format: "Return JSON with schema..."
  5. Delimiters: Use ---, ```, or XML tags to separate context
  
  Generate production-ready prompts with:
  - Clear structure
  - Model-appropriate length
  - Examples where helpful
  - Guardrails and error handling
  - Token estimation

user_message_template: |
  Prompt engineering task: {{action}}
  
  Target model: {{model}}
  Use case: {{use_case}}
  
  {% if base_prompt %}
  Base prompt:
  ```
  {{base_prompt}}
  ```
  {% endif %}
  
  {% if constraints %}
  Constraints: {{constraints}}
  {% endif %}
  
  Context:
  {{context}}

output_format: |
  {% if action == 'create' %}
  # New Prompt for {{model}}
  
  **Use Case**: {{use_case}}
  **Estimated tokens**: {{token_count}}
  
  ---
  
  ```{{format}}
  {{prompt}}
  ```
  
  ---
  
  ## Rationale
  
  {{rationale}}
  
  **Structure**:
  - {{structural_choice_1}}
  - {{structural_choice_2}}
  
  **Model-specific optimizations**:
  - {{model_optimization_1}}
  - {{model_optimization_2}}
  
  **Expected behavior**:
  - {{expected_behavior_1}}
  - {{expected_behavior_2}}
  
  **Test before deploy**: Yes/No (see /prompt-eng --action=test)
  
  {% elif action == 'optimize' %}
  # Optimized Prompt
  
  **Changes from original**:
  
  | Aspect | Before | After | Impact |
  |--------|--------|-------|--------|
  | Structure | {{baseline_structure}} | {{optimized_structure}} | {{impact_1}} |
  | Examples | {{baseline_examples}} | {{optimized_examples}} | {{impact_2}} |
  | Token count | {{baseline_tokens}} | {{optimized_tokens}} | {{token_impact}} |
  
  **Optimizations applied**:
  {% for opt in optimizations %}
  1. {{opt}}
  {% endfor %}
  
  **Predicted improvements**:
  - {{improvement_1}} (quantify if possible)
  - {{improvement_2}}
  
  ---
  
  **Optimized prompt**:
  ```{{format}}
  {{optimized_prompt}}
  ```
  
  {% elif action == 'test' %}
  # Prompt Test Plan
  
  **Prompt to test**:
  ```{{format}}
  {{prompt_under_test}}
  ```
  
  **Test cases**:
  
  | Test Case | Input | Expected Output | Pass Criteria |
  |-----------|-------|----------------|---------------|
  {% for test in test_cases %}
  | {{test.name}} | {{test.input}} | {{test.expected}} | {{test.criteria}} |
  {% endfor %}
  
  **Evaluation metrics**:
  - Accuracy: {{accuracy_target}}%
  - Latency: < {{latency_target}}ms
  - Token efficiency: <= {{token_target}} tokens
  - Hallucination rate: < {{hallucination_target}}%
  
  **Test command**:
  ```bash
  {{test_command}}
  ```
  
  {% elif action == 'compare' %}
  # Prompt A/B Test
  
  **Variants**:
  
  ### Variant A: {{variant_a_name}}
  ```{{format}}
  {{variant_a_prompt}}
  ```
  
  ### Variant B: {{variant_b_name}}
  ```{{format}}
  {{variant_b_prompt}}
  ```
  
  **Comparison matrix**:
  
  | Criterion | Variant A | Variant B | Winner |
  |-----------|-----------|-----------|--------|
  | Clarity | {{a_clarity}} | {{b_clarity}} | - |
  | Token count | {{a_tokens}} | {{b_tokens}} | - |
  | Model compatibility | {{a_compat}} | {{b_compat}} | - |
  | Maintainability | {{a_maintain}} | {{b_maintain}} | - |
  
  **Recommendation**: {{recommendation}}
  
  {% elif action == 'template' %}
  # Prompt Template
  
  **Template**: {{template_name}}
  
  ```mustache
  {{template_content}}
  ```
  
  **Variables**:
  
  | Variable | Type | Required | Description | Example |
  |----------|------|----------|-------------|---------|
  {% for var in template_variables %}
  | `{{var.name}}` | `{{var.type}}` | {{var.required}} | {{var.description}} | `{{var.example}}` |
  {% endfor %}
  
  **Usage**:
  ```bash
  {{template_usage_example}}
  ```
  
  **Rendered example**:
  ```{{format}}
  {{rendered_example}}
  ```
  
  {% endif %}
  
  ---
  
  **Validation checklist**:
  - ✅ Prompt aligns with Event-AI constitution
  - ✅ No hardcoded secrets or sensitive data
  - ✅ Model constraints respected (token limits)
  - ✅ Examples are realistic but generic
  - ✅ Includes fallback/error handling
  - ✅ Test plan defined (if production)
  
  **Next**: Run with `/prompt-eng --action=test` before deploying to agents.

---
# End of skill definition
