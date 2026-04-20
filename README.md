# memU Local Stack

_Last updated: 2026-04-20_

> *Give your AI companion a real memory. One that belongs to it — and stays on your machine.*

---

## The problem this solves

Every time you start a new conversation with an AI, it has forgotten everything. You mentioned last week that your dog died. You spent an hour explaining how you feel about your work. None of it is there.

It's not that the AI doesn't care — it's that it never had a way to remember.

**memU is a memory system for AI companions.** It runs locally on your machine, watches your conversations, and quietly builds a picture of who you are and what you've been through together. When you come back, that picture is there.

---

## What gets remembered

memU separates memories into five types, because not everything should be stored the same way:

- **Profile** — who you are as a person. Your values, your fears, your sense of humor, what you keep coming back to. The things that would still be true about you a year from now.
- **Events** — things that happened that matter. A decision you made. Something difficult you went through. A moment that had weight.
- **Knowledge** — things you've learned or explored together. Not trivia — things where the topic actually connects to your life.
- **Behavior** — how you communicate. Whether you joke when things get heavy, whether you go quiet before saying something important. Patterns that are distinctly *you*.
- **Social** — the people in your life. Friends, family, coworkers, anyone you talk about. The relationship context that gives your conversations texture.

The AI also keeps a **diary** — its own reflections on what you've shared, written in its own voice. And a **self-model** — an evolving sense of its own character, the tensions it carries, the things it finds itself returning to.

---

## Why local-first matters

Your conversations don't leave your machine. No cloud storage, no account, no company holding copies of what you've said. The memories live in a local SQLite database that you control.

This matters more than it sounds. If you're having honest conversations with an AI companion — the kind where you talk about things you wouldn't post publicly — you probably don't want that stored somewhere else.

---

## How it works with SillyTavern

[SillyTavern](https://github.com/SillyTavern/SillyTavern) is a popular platform for AI roleplay and companionship. memU integrates with it through a plugin and extension that sit quietly in the background.

Memory extraction happens during **sleep gaps** — when you close a conversation and come back later. The system reads what you talked about, pulls out what matters, and stores it. You can also trigger it manually with a "Memorize Now" button. Either way, relevant memories are automatically included in the next conversation so the AI already knows them.

---

## The stack

Full functionality uses four repos working together:

```
SillyTavern
  └─ memu-sillytavern-plugin   (bridge between ST and the memory server)
  └─ memu-sillytavern-extension  (the UI layer — buttons, panels, settings)
           │
           ▼
  mcp-memu-server              (local service: orchestration, storage, diary)
           │
           ▼
        memU                   (the memory engine itself)
```

**If you're not using SillyTavern**, you can use just the bottom two (`memU` + `mcp-memu-server`) with any other frontend. The plugin and extension are adapters — the memory system doesn't depend on them.

---

## The repos

| Repo | What it is |
|------|------------|
| [memU](https://github.com/mekineer-com/memU) | Memory engine — extraction, routing, storage, retrieval |
| [mcp-memu-server](https://github.com/mekineer-com/mcp-memu-server) | Local API server — diary, state management, SillyTavern bridge |
| [memu-sillytavern-plugin](https://github.com/mekineer-com/memu-sillytavern-plugin) | SillyTavern server-side adapter |
| [memu-sillytavern-extension](https://github.com/mekineer-com/memu-sillytavern-extension) | SillyTavern UI layer |

**Always clone from `main`** — tagged releases fall behind quickly. Use `git clone` (links in the table above) or download the zip from the green **Code** button on each repo page.

---

## Schema compatibility

This project is in prerelease. **Database schema changes between versions.** If you upgrade to a newer release tag, your existing database is likely incompatible and will cause errors. No migration tooling exists yet — expect a fresh start when moving between prerelease tags.

---

## Release tags

All four repos are tagged in sync at each release. Use matching tags across all four.

| Tag | Notes |
|-----|-------|
| `v0.0.5-buildfix` | Soul turn loop, memory cache, category seeds |
| `v0.0.6-buildfix` | Social memory type, diary overhaul, self-model simplification |
| `v0.0.7-buildfix` | Retrieve alignment, sleep-gap history, token budget, sleep-timer, shaped_by provenance |
| `v0.0.8-buildfix` | Consolidation pipeline, entity graph + temporal queries, life goals, APImw edge writing |

---

## Getting started

**You'll need:**
- Python 3.12+
- Node.js (for the SillyTavern pieces)
- An API key for an LLM provider (OpenAI or any compatible service — used for extracting memories from conversations)
- SillyTavern already installed, if you're using the SillyTavern integration

**Set up in this order:**

1. **[mcp-memu-server](https://github.com/mekineer-com/mcp-memu-server)** — start here. This is the local service that runs everything. Copy `config.example.json` → `config.json`, set your API key, and start it. It runs on port 8099.

2. **[memU](https://github.com/mekineer-com/memU)** — the memory engine. Clone it and point `mcp-memu-server`'s config at it (the `memu.path` setting).

3. **[memu-sillytavern-plugin](https://github.com/mekineer-com/memu-sillytavern-plugin)** — clone into SillyTavern's `plugins/` folder. Enable `enableServerPlugins: true` in SillyTavern's `config.yaml`, then restart SillyTavern.

4. **[memu-sillytavern-extension](https://github.com/mekineer-com/memu-sillytavern-extension)** — clone into SillyTavern's `data/default-user/extensions/` folder. This is the UI layer — it adds the memU panel and connects everything together.

**Config callout** — three things in `config.json` must match your actual layout:

| Setting | What it points to |
|---------|------------------|
| `memu.path` | path to `memu/src` (the engine source, from step 2) |
| `storage.metadata_store.dsn` | where the SQLite DB will live |
| `llm.embed_model` | embedding model name — e.g. `text-embedding-3-large` (NanoGPT/OpenAI both support it) |

After step 4, open the memU extension panel in SillyTavern and set **Server URL** to `http://127.0.0.1:8099`.

Each repo's README goes into more detail. Questions? Open an issue on the relevant repo.

This stack runs without Docker. Developed on Alpine Linux but works on any system that can run Python 3.12 and Node.

---

## Letting the soul author her own self-model

The companion has a `narrative_self` — her evolving sense of who she is. The weekly **consolidation pass** rewrites it as her experience accumulates, and you can also feed her a suggestion directly via the **Narrative Suggestion** input (the bubble under "Memorize Now").

For any of this to actually shape her turn, the **SillyTavern character card description must be empty**. The soul's identity gets resolved each turn in this order:

1. The ST character card description, if filled in → wins, every time
2. Otherwise: her stored `narrative_self` from `memu_self_model`
3. Otherwise: a generic default ("You are {name}…")

So if you write a character description in ST, that's who she is — her own self-model never reaches the prompt. Leave the description empty and she'll use what consolidation (and your suggestions) have built up.

### Using Narrative Suggestion

1. Open the memU extension panel in SillyTavern.
2. Find the **Narrative Suggestion** input under the "Memorize Now" button.
3. Type what you want her to consider — a phrasing, a correction, a new way of seeing herself.
4. Click **Send**. A small green check ✓ means she accepted and integrated it; a red X ✗ means she chose not to.
5. If she accepts, the new text is written to her `narrative_self` and also pushed back into the ST character description (so the panel stays in sync). The previous version is preserved in her memory store with an `evolved_into` link, so she can still recall what she used to think.
6. If you manually edit the ST character description yourself, the **Send** button disables with a warning — that's an "override" path; clear it (or accept your edit explicitly through the panel) to re-enable suggestions.

There's a 10-minute cooldown between suggestions so the soul isn't churning her identity every minute.

---

## Status

This is an active project, not an official hosted service. It's built by people who wanted a memory system that actually works, runs privately, and is worth building on.

**What works now:** five memory types (profile, events, knowledge, behavior, social), consolidation pipeline (weekly reflection that writes diary entries, updates the self-model narrative, and manages life goals), entity graph with temporal queries (named entities linked to memories by typed edges; point-in-time graph filtering), life goals (long-horizon intentions managed exclusively by consolidation), SillyTavern integration, sleep-gap timing, local storage, semantic deduplication (near-duplicate memories merged and reinforcement-counted), hybrid search (keyword + semantic), soul turn loop (the AI manages its own intentions and rolling thought cache turn-by-turn), temporal awareness (memories labeled with relative time — "3 weeks ago", "yesterday").

**In progress:** procedural knowledge sidecar (curated protocols the AI can reference during conversation), PicoClaw autonomous soul loop.

---

## Acknowledgments

memU's design has been informed by reading [MemPalace](https://github.com/MemPalace/mempalace), another local-first AI memory project (MIT-licensed). They approach memory differently — verbatim storage rather than extraction — but share the local-first and temporal-graph commitments, and auditing our implementation against theirs sharpened parts of memU. Thanks to the MemPalace team for the open reference implementation.
