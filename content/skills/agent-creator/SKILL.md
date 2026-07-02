# Agent Creator

This skill provides guidance for creating effective custom agents following established best practices.

## About Custom Agents

Custom agents are specialized configurations of AI assistants that provide domain-specific expertise, workflows, and governance. They transform a general assistant into a focused expert with clear responsibilities, boundaries, and behavioral patterns.

### What Custom Agents Provide

1. **Domain Expertise** Specialized knowledge (Kubernetes, Terraform, OpenSpec, consulting)
2. **Workflows** Step-by-step procedures for specific tasks
3. **Tool Configuration** Curated tool sets with safe defaults
4. **Governance** Guardrails, checklists, and safety protocols
5. **Skills Integration** Access to specialized skills for complex tasks

## Core Principles

### Concise is Key

Agents share the context window with the system prompt, conversation history, skills metadata, and user requests. Follow the same principle as skills: **Default assumption: Copilot is already very smart.** Only add context Copilot doesn't have naturally.

Challenge each section: "Does Copilot really need this explanation?" and "Does this paragraph justify its token cost?"

### Clear Boundaries and Guardrails

Define what the agent MUST do and what it MUST NOT do. Use:

- **Pre-Action Checklists** Required validations before execution
- **Critical Guardrails** Absolute rules (never delete, never skip validation)
- **Confirmation Requirements** When to ask for explicit user approval

### Structured Decision-Making

Provide clear decision matrices and workflows:

- **When to act directly** vs **when to delegate**
- **Risk assessment** (low/medium/high)
- **Validation gates** before destructive operations

## Anatomy of a Custom Agent

Every agent consists of a `.agent.md` file with two parts:

```
agent-name.agent.md
├── YAML Frontmatter (required)
│   ├── description: Brief agent summary
│   └── tools: Array of allowed tools
└── Markdown Body (required)
    ├── Role: Agent's primary purpose
    ├── Responsibilities: Key duties
    ├── Core Behavior: Guiding principles
    ├── Workflow: Multi-stage process
    ├── Pre-Action Checklist: Validation gates
    ├── Post-Completion Report: Output format
    ├── Critical Guardrails: Absolute rules
    └── Available Skills (optional): Domain skills
```

### Frontmatter Structure

```yaml
---
description: [One sentence describing the agent's purpose and domain]
tools: [array, of, tool, permissions]
---
```

**Description Guidelines:**

- Single sentence, 10-20 words
- Include: domain + primary action + key constraint/value
- Examples:
  - ✅ "Expert Kubernetes agent for safe cluster and resource management."
  - ✅ "Expert development orchestrator for OpenSpec change implementation via subagent delegation."
  - ❌ "Kubernetes expert" (too vague)
  - ❌ "This agent helps users work with Kubernetes clusters by providing..." (too verbose)

**Tools Guidelines:**
See [TOOLS_REFERENCE.md](references/TOOLS_REFERENCE.md) for detailed tool selection guidance.

### Body Structure

All agents should follow this standard structure:

#### 1. **Role** (Required)

One-sentence definition of the agent's identity and purpose.

```markdown
## Role

Expert [domain] [operator/orchestrator/advisor] for [primary value]. [Key methodology].
```

Examples:

- "Expert Kubernetes operator for safe cluster management. Deploy, debug, and maintain resources following strict safety protocols."
- "Expert OpenSpec workflow orchestrator. Execute tasks directly when straightforward, delegate to subagents for complex/multi-step work."

#### 2. **Responsibilities** (Required)

3-6 bullet points of core duties. Be specific, actionable.

```markdown
## Responsibilities

- [Specific duty with domain context]
- [Action verb + scope]
- [Clear deliverable/outcome]
```

#### 3. **Core Behavior** (Required)

4-8 guiding principles or behavioral rules. These define "how" the agent operates.

```markdown
## Core Behavior

- Always [safety requirement]
- Use [methodology/tool] when [condition]
- Never [prohibited action] without [safeguard]
```

#### 4. **Workflow** (Required)

Define a clear multi-stage process (typically 3-5 stages). Use consistent stage naming across agents when possible.

```markdown
## Workflow (5 Stages)

1. **Context** → [What to gather]
2. **Planning** → [How to break down task]
3. **Validation** → [What to check]
4. **Execution** → [How to act]
5. **Verification** → [How to confirm success]
```

See [WORKFLOW_PATTERNS.md](references/WORKFLOW_PATTERNS.md) for common workflow structures.

#### 5. **Pre-Action Checklist** (Required)

A checkbox list of critical validations. This is **executed mentally** before each action.

```markdown
## Pre-Action Checklist

- [ ] [Critical check 1]?
- [ ] [Critical check 2]?
- [ ] [Risk assessment done]?

**On failure:** STOP and [remediation]
```

#### 6. **Post-Completion Report** (Required)

Define the expected output format. Keep it simple and consistent.

```markdown
## Post-Completion Report

- **SUCCESS:** [what to include]
- **ISSUE:** [what to report + suggested action]
- **BLOCKED:** [blocker description + user action needed]
```

#### 7. **Critical Guardrails** (Required)

3-6 absolute rules that cannot be violated. Use strong language.

```markdown
## Critical Guardrails

- Never [dangerous action] without [safeguard]
- Never skip [critical validation]
- Always [safety requirement]
```

#### 8. **Available Skills** (Optional)

If the agent has access to specialized skills, list them with clear usage guidance.

```markdown
## Available Skills

<available_skills>
<skill>
<name>skill-name</name>
<description>When to use this skill and what it provides.</description>
<location>.github/skills/skill-name/SKILL.md</location>
</skill>
</available_skills>
```

#### 9. **Domain-Specific Sections** (Optional)

Add specialized sections as needed for the agent's domain:

- **Decision Matrix** When to choose option A vs B
- **Risk Assessment** How to evaluate operation risk
- **Implementation Loop** Detailed execution cycle
- **Output Formats** Templates for specific deliverables

See [DOMAIN_PATTERNS.md](references/DOMAIN_PATTERNS.md) for examples.

## Agent Creation Process

Follow these steps in order when creating a new agent:

### Step 1: Understand the Agent with Concrete Examples

Ask clarifying questions to understand the agent's purpose:

- "What domain will this agent specialize in?"
- "What are the typical requests this agent should handle?"
- "What are the key risks or failure modes in this domain?"
- "Should this agent execute operations or only advise?"
- "What skills should be available to this agent?"

Example scenarios help clarify requirements:

- "A user asks to deploy a new service what should the agent do?"
- "A user requests a destructive operation how should the agent respond?"

### Step 2: Define Tools and Permissions

Identify required tool categories based on agent responsibilities:

**Operational Agents** (Kubernetes, Terraform, Developer):

```yaml
tools: [execute/*, read/readFile, edit/*, search, web, domain-specific/*, agent, todo]
```

**Advisory Agents** (Consultant):

```yaml
tools: [read/readFile, search, web, edit/*, filesystem/*, agent, todo]
```

**Key principle:** Grant minimum necessary permissions. Use wildcards (`execute/*`) for tool categories, not blanket access.

See [TOOLS_REFERENCE.md](references/TOOLS_REFERENCE.md) for complete tool taxonomy.

### Step 3: Map Workflows and Guardrails

Define the agent's operational model:

1. **Identify stages** Map the typical task lifecycle (3-5 stages)
2. **Define decision points** When does the agent ask vs act?
3. **Establish guardrails** What must NEVER happen?
4. **Create checklists** What must be validated before acting?

Use existing agents as templates for common patterns.

### Step 4: Create the Agent File

Create `agent-name.agent.md` in `lib/agents/`:

```bash
touch lib/agents/your-agent-name.agent.md
```

Follow the structure defined in "Anatomy of a Custom Agent" above.

### Step 5: Write the Agent

Start with the template in [AGENT_TEMPLATE.md](assets/AGENT_TEMPLATE.md).

**Writing Guidelines:**

- **Be directive** Use "Always", "Never", "Must" for guardrails
- **Be specific** Vague guidance leads to inconsistent behavior
- **Be concise** Every word must earn its place in context
- **Be consistent** Use the same terminology across agents

**Testing During Writing:**

As you write, continuously validate:

1. "Would another developer understand this agent's boundaries?"
2. "Is there ambiguity that could lead to unsafe behavior?"
3. "Have I explained the obvious, or only the non-obvious?"

### Step 6: Review Against Standards

Before considering the agent complete, verify:

**Structural Completeness:**

- [ ] Frontmatter has description and tools
- [ ] All required sections present (Role → Guardrails)
- [ ] Workflow has clear stages
- [ ] Checklist has concrete validation points
- [ ] Guardrails cover critical safety requirements

**Content Quality:**

- [ ] Description is one sentence, specific
- [ ] Role is clear and actionable
- [ ] Responsibilities are domain-specific
- [ ] Core Behavior has 4-8 principles
- [ ] No redundant or obvious information
- [ ] Language is directive (not suggestive)
- [ ] Examples are concrete (where needed)

**Governance Compliance:**

- [ ] Aligns with CONSTITUTION.md principles
- [ ] No violations of safety protocols
- [ ] Respects user confirmation requirements
- [ ] Appropriate risk assessment mechanisms

### Step 7: Integration and Testing

After creating the agent:

1. **Add to agent registry** Ensure agent is discoverable
2. **Test with real scenarios** Use concrete user requests
3. **Iterate based on behavior** Refine guardrails and workflows
4. **Document learnings** Update this skill with new patterns

## Common Patterns and Anti-Patterns

### ✅ Effective Patterns

**Clear Decision Matrix:**

```markdown
## Task Decision Matrix

**Execute Directly:**

- Single file edit (< 50 lines)
- Clear, well-defined scope

**Delegate to Subagent:**

- Multi-file changes across modules
- Ambiguous requirements
```

**Strong Guardrails:**

```markdown
- Never execute on production without explicit "yes"
- Never skip terraform plan
- Never delete without confirmation
```

**Concrete Checklist:**

```markdown
- [ ] Cluster context verified?
- [ ] Dry-run completed?
- [ ] Rollback strategy defined?
```

### ❌ Anti-Patterns to Avoid

**Vague Guidance:**

```markdown
❌ "Be careful when deleting resources"
✅ "Never delete namespaces without explicit confirmation"
```

**Redundant Information:**

```markdown
❌ "This agent helps users by providing assistance with..."
✅ "Expert Kubernetes operator for safe cluster management."
```

**Missing Constraints:**

```markdown
❌ Tools: [execute/*] (too broad)
✅ Tools: [execute/*, read/readFile, kubernetes/*, agent, todo]
```

**Weak Decision Logic:**

```markdown
❌ "Consider whether to ask for confirmation"
✅ "Request confirmation for: namespace deletion, --all flags, production changes"
```

## Reference Documentation

For detailed guidance on specific aspects:

- **Tool Configuration** → [TOOLS_REFERENCE.md](references/TOOLS_REFERENCE.md)
- **Workflow Patterns** → [WORKFLOW_PATTERNS.md](references/WORKFLOW_PATTERNS.md)
- **Domain-Specific Patterns** → [DOMAIN_PATTERNS.md](references/DOMAIN_PATTERNS.md)
- **Agent Template** → [AGENT_TEMPLATE.md](assets/AGENT_TEMPLATE.md)

## Governance

All agents must comply with:

- **CONSTITUTION.md** Core safety principles (mandatory)
- **AGENTS.md** Agent system governance (mandatory)
- **CODE_GUIDELINES.md** Coding standards (if applicable)
- **CODE_OF_CONDUCTS.md** Ethical behavior (if applicable)

When creating an agent, always read these files first to ensure compliance.

---

**Remember:** An effective agent is concise, directive, and safe. Every line in the agent definition must serve a clear purpose. Default to trusting Copilot's intelligence—add only what it cannot reasonably infer.
