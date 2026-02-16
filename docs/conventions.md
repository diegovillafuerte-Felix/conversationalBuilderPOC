# Conventions

## Tool Naming

- **Pattern**: `verb_noun` format (e.g., `get_exchange_rate`, `create_transfer`)
- **Navigation tools**: `enter_<agent>`, `up_one_level`, `go_home`, `escalate_to_human`
- **Flow tools**: `start_flow_<flowname>` triggers stateful subflows
- **Allowed verbs**: get, list, create, update, delete, send, cancel, calculate, detect, validate, check, pay, save, link, make, submit, add, start, enter, up, go, escalate, set, change

## Agent Configs

- JSON files in `backend/app/config/agents/` define tools, prompts, navigation
- Required fields: `id`, `name`, `description`, `tools`
- Each tool requires: `name`, `description`
- Routing targets validated at startup (fail-fast on invalid configs)

## Service-Presentation Separation

- **Service Layer** (`services/*.py`): Returns ONLY raw data (JSON objects/arrays) — NO formatting, NO `_message` fields
- **Presentation Layer** (`orchestrator.py`, `template_renderer.py`, agent configs): Handles all formatting via response templates or LLM
- **No `_message` backdoor**: Orchestrator does NOT check for `_message` fields — all formatting must go through proper channels
- **Benefits**: Services are UI-agnostic, can be used by chat, web, mobile, or direct API

## i18n (Simplified)

ALL prompts and configs are in English. The ONLY language-related code is:
1. User's `language` attribute stored in their profile (default: "es")
2. Language directive injected at the end of every system prompt telling the LLM what language to respond in

This means: LLM gets English instructions, responds in user's preferred language. No localized config files, no `get_localized()` calls, no bilingual dictionaries.

## Models

- GUID primary keys, JSON columns for flexible configs
- Sample users defined in `config/sample_data/users.json`, seeded at startup if not present

## Frontend

- Zustand stores in `react-app/src/store/`
- React Flow for interactive agent/flow visualization
