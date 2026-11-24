# Six Shifts in How to Work with More Capable Claude Models

## What this document is about

This is a reference guide on how to adjust the way you instruct Claude (system prompts, project instructions, CLAUDE.md files, skills, tool descriptions, specs) as models become more capable.

The core idea: techniques that kept earlier, weaker models on track (many rules, many examples, everything stated upfront, repeated instructions, hand-managed memory, simple specs) now tend to **overconstrain** newer, stronger models. The guide describes six shifts, each as "old approach → new approach."

It comes from Claude's official Instagram account. The team behind Claude Code reports that they removed over 80% of Claude Code's system prompt for more advanced models with no measurable loss in performance.

**How to use this file in another Claude project:** Treat it as a checklist when writing or reviewing any instruction set for Claude: a system prompt, project instructions, a CLAUDE.md, a skill, a tool description, or a spec. For each of the six shifts, ask whether your current setup still follows the old approach, and whether the new approach would work better.

- Source: Claude's official Instagram account
- Saved: 2026-11-05

---

## Original text

We removed over 80% of Claude Code's system prompt for more advanced models, with no measurable loss in performance. The context that kept earlier models on track now overconstrains more capable ones.

These are the six shifts we made:

### 1. Give Claude rules → Let Claude use judgement

Newer models read surrounding code and match its conventions on their own. Where do you have hard rules that could be principles instead?

### 2. Give Claude examples → Design interfaces

Instead of using examples, think more about the design of your tools, scripts, and files. What parameters does Claude have and how can they be more expressive?

### 3. Put it all upfront → Use progressive disclosure

Not everything belongs in the system prompt. What instructions could live in a skill Claude calls only when necessary?

### 4. Repeat yourself → Simple tool descriptions

If the same instruction lives in the system prompt and the tool description, cut it from the system prompt. Newer models no longer need repeated instructions.

### 5. Memory in CLAUDE.md → Auto-memory

Claude now saves relevant context automatically. No memory management needed.

### 6. Simple specs → Rich references

Claude can handle much more than a markdown file. Show it an HTML artifact, a test suite, or code from another codebase.

---

## Quick summary table

| # | Old approach (earlier models) | New approach (more capable models) |
|---|-------------------------------|------------------------------------|
| 1 | Give Claude rules | Let Claude use judgement |
| 2 | Give Claude examples | Design interfaces |
| 3 | Put it all upfront | Use progressive disclosure |
| 4 | Repeat yourself | Simple tool descriptions |
| 5 | Memory in CLAUDE.md | Auto-memory |
| 6 | Simple specs | Rich references |

## Self-audit questions

1. Where do I have hard rules that could be principles instead?
2. What parameters do my tools and scripts expose, and how could they be more expressive?
3. Which instructions could move into a skill that is only loaded when needed?
4. Is any instruction duplicated between the system prompt and a tool description?
5. Am I still hand-maintaining memory that Claude could save automatically?
6. Could I show Claude a richer reference (HTML artifact, test suite, existing code) instead of a plain markdown spec?
