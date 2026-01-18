# Claude Code Configuration

This project uses Claude Code with custom configuration.

## Directory Structure
```
.claude/
├── settings.json       # Shared team settings (hooks, permissions)
├── settings.local.json # Personal settings (gitignored)
├── rules/              # Auto-loaded context (always active)
├── skills/             # On-demand knowledge (Claude-invoked)
├── agents/             # Specialized agents
└── commands/           # User-invoked slash commands
```

## Rules vs Skills
- **Rules** (`rules/`): Always loaded as context. Use for coding standards, security, testing requirements.
- **Skills** (`skills/`): Claude loads when relevant. Use for domain knowledge, workflows, component patterns.

## Available Skills
- `jinja-roos-components` - UI component patterns
- `wies-domain` - Project domain knowledge (plaatsingen, opdrachten, roles)
- `django` - Django development patterns
- `model-workflow` - Model change checklist

## Hooks
Post-edit hook reminds about `dummy_data.json` when `models.py` is modified.

## When to Use Skills
Claude should automatically load relevant skills based on context:
- Working on templates → `jinja-roos-components`
- Working on models → `model-workflow`, `django`
- Questions about business logic → `wies-domain`
