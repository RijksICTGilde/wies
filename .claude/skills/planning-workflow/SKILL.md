---
name: planning-workflow
description: Multi-agent planning workflow for complex tasks. Use when tasks affect multiple subsystems, require extensive codebase exploration, or when context limits may become an issue.
---

# Planning Workflow Skill

## Purpose
Workflow for complex plans requiring multiple iterations and context management.

## When to use
- Tasks affecting multiple subsystems
- Plans requiring extensive codebase exploration
- Situations where context limits may become an issue

## Workflow

### Phase 1: Initial Understanding (Explore agents)
1. Launch 1-3 Explore agents in parallel
2. Give each agent a specific focus:
   - Agent 1: Current implementation and patterns
   - Agent 2: Related components/dependencies
   - Agent 3: Test patterns and edge cases
3. Agents report findings with file locations

### Phase 2: Design (Plan agents)
1. Launch Plan agent(s) with context from Phase 1
2. Provide:
   - Findings from Explore agents
   - Specific requirements
   - Constraints and preconditions
3. Agent produces implementation plan

### Phase 3: Consolidation
1. Read critical files yourself
2. Combine agent findings
3. Ask clarifying questions to user
4. Write final plan to plan file

### Phase 4: Plan Refinement Iterations
For complex plans, perform iterative self-review until stable:

**Iteration 1 - Completeness Review:**
1. Clear current context (start fresh agent)
2. Provide agent with:
   - Original user request
   - Current plan file contents
3. Agent reviews plan for:
   - Completeness (all requirements covered?)
   - Correctness (implementation details accurate?)
   - Edge cases (error handling, validation?)
4. Agent updates plan with improvements
5. Agent reports: "Improvements found: yes/no"

**Iteration 2 - Quality Review:**
1. Clear context again (fresh agent)
2. Provide agent with:
   - Original user request
   - Updated plan from iteration 1
3. Agent reviews for:
   - Code quality (patterns, best practices?)
   - Testing strategy (coverage, scenarios?)
   - Verification steps (how to validate?)
4. Agent updates plan with improvements
5. Agent reports: "Improvements found: yes/no"

**Iteration 3+ - Stability Check (if improvements were found):**
1. Clear context (fresh agent)
2. Provide agent with:
   - Original user request
   - Current plan version
3. Agent reviews for any remaining improvements
4. If improvements found:
   - Update plan
   - Trigger another iteration
5. If no improvements found:
   - Plan is stable, proceed to user review

**Convergence criteria:**
- Maximum 10 iterations to prevent infinite loops
- Stop when agent reports "no improvements found"
- Stop when changes are only cosmetic (formatting, wording)

### Phase 5: User Review
1. Present final plan to user
2. Discuss each section
3. Adjust based on feedback
4. Document decisions and rationale

## Context management tips
- Agents start with clean context (no prior conversation)
- Provide agents with sufficient background info in the prompt
- Use agents for broad exploration, do targeted reads yourself
- Summarize agent output before proceeding

## Example agent prompts

**Explore agent:**
> Search for all places where [X] is used. Focus on:
> 1. Direct calls
> 2. Related configuration
> 3. Test coverage
> Report filename:line_number for each finding.

**Plan agent:**
> Design implementation for [feature]. Context:
> - Current implementation: [summary]
> - Involved files: [list]
> - Requirements: [list]
> Produce step-by-step plan with concrete code changes.
