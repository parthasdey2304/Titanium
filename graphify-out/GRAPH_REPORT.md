# Graph Report - Titanium  (2026-11-20)

## Corpus Check
- 23 files · ~12,766 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 8 file(s) not represented in the graph (top: .bat 3, (none) 2, .example 1)

## Summary
- 362 nodes · 626 edges · 18 communities (5 shown, 13 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 49 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `281d86b6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- TitaniumApp
- AgentRouter
- SiriOrbWidget
- GeminiLiveClient
- TitaniumMusicPlayer
- MemoryManager
- CompactSubtitlePill
- WindowsInstaller
- WakeWordListener
- ElevenLabsTTS
- TitaniumTrayIcon
- CircleToSearchOverlay
- 🌌 Titanium — Autonomous Agentic Virtual Assistant
- WindowsAppLauncher
- CodeViewerWindow
- main

## God Nodes (most connected - your core abstractions)
1. `TitaniumApp` - 33 edges
2. `SiriOrbWidget` - 29 edges
3. `ElevenLabsTTS` - 19 edges
4. `MemoryManager` - 18 edges
5. `TitaniumMusicPlayer` - 18 edges
6. `GeminiLiveClient` - 16 edges
7. `CircleToSearchOverlay` - 15 edges
8. `WakeWordListener` - 14 edges
9. `AgentRouter` - 13 edges
10. `SystemNavigator` - 13 edges

## Surprising Connections (you probably didn't know these)
- `TitaniumApp` --uses--> `AgentRouter`  [INFERRED]
  main.py → titanium/core/agent_router.py
- `TitaniumApp` --uses--> `ElevenLabsTTS`  [INFERRED]
  main.py → titanium/core/elevenlabs_tts.py
- `TitaniumApp` --uses--> `GeminiLiveClient`  [INFERRED]
  main.py → titanium/core/live_client.py
- `TitaniumApp` --uses--> `WakeWordListener`  [INFERRED]
  main.py → titanium/core/wake_listener.py
- `TitaniumApp` --uses--> `MemoryManager`  [INFERRED]
  main.py → titanium/memory/sqlite_memory.py

## Import Cycles
- None detected.

## Communities (18 total, 13 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.08
Nodes (3): get_system_info(), lock_workstation(), set_system_volume()

### Community 1 - "TitaniumApp"
Cohesion: 0.06
Nodes (5): TitaniumApp, worker(), on_done(), worker(), finish_cb()

### Community 2 - "AgentRouter"
Cohesion: 0.11
Nodes (3): AgentRouter, get_user_directories(), SystemNavigator

### Community 13 - "🌌 Titanium — Autonomous Agentic Virtual Assistant"
Cohesion: 0.22
Nodes (8): 1. Installation, 2. Configuration, 3. Running Titanium, 🎮 Controls & Shortcuts, ✨ Key Features, 📄 License, 🚀 Quick Start, 🌌 Titanium — Autonomous Agentic Virtual Assistant

### Community 16 - "main"
Cohesion: 0.29
Nodes (4): acquire_single_instance_lock(), cleanup_stale_processes(), main(), notify_existing_instance()

## Knowledge Gaps
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TitaniumApp` connect `TitaniumApp` to `main.py`, `AgentRouter`, `SiriOrbWidget`, `GeminiLiveClient`, `TitaniumMusicPlayer`, `MemoryManager`, `CompactSubtitlePill`, `WindowsInstaller`, `WakeWordListener`, `ElevenLabsTTS`, `TitaniumTrayIcon`, `CircleToSearchOverlay`, `main`?**
  _High betweenness centrality (0.302) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `TitaniumApp` (e.g. with `AgentRouter` and `ElevenLabsTTS`) actually correct?**
  _`TitaniumApp` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07909604519774012 - nodes in this community are weakly interconnected._
- **Why does `SiriOrbWidget` connect `SiriOrbWidget` to `main.py`, `TitaniumApp`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ElevenLabsTTS` (e.g. with `TitaniumApp` and `GeminiLiveClient`) actually correct?**
  _`ElevenLabsTTS` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `TitaniumApp` be split into smaller, more focused modules?**
  _Cohesion score 0.058673469387755105 - nodes in this community are weakly interconnected._
- **Why does `TitaniumMusicPlayer` connect `TitaniumMusicPlayer` to `main.py`, `TitaniumApp`, `AgentRouter`?**
  _High betweenness centrality (0.121) - this node is a cross-community bridge._