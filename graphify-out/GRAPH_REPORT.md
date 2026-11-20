# Graph Report - Titanium  (2026-11-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 526 nodes · 863 edges · 27 communities (9 shown, 18 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `08e2c129`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- TitaniumApp
- orb.rs
- ElevenLabsTTS
- key_prompt.rs
- SiriOrbWidget
- AgentRouter
- MusicPlayer
- TitaniumMusicPlayer
- TitaniumInstallerWindow
- ApiKeySetupDialog
- CompactSubtitlePill
- MemoryManager
- gemini.rs
- WakeWordListener
- WindowsInstaller
- TitaniumTrayIcon
- CircleToSearchOverlay
- 🌌 Titanium — Autonomous Agentic Virtual Assistant
- CodeViewerWindow
- titanium-rust

## God Nodes (most connected - your core abstractions)
1. `TitaniumApp` - 34 edges
2. `SiriOrbWidget` - 29 edges
3. `ElevenLabsTTS` - 19 edges
4. `MemoryManager` - 18 edges
5. `TitaniumMusicPlayer` - 18 edges
6. `GeminiLiveClient` - 16 edges
7. `CircleToSearchOverlay` - 15 edges
8. `WakeWordListener` - 14 edges
9. `MusicPlayer` - 14 edges
10. `TitaniumTrayIcon` - 13 edges

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

## Communities (27 total, 18 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.07
Nodes (4): WindowsAppLauncher, get_system_info(), lock_workstation(), set_system_volume()

### Community 1 - "TitaniumApp"
Cohesion: 0.05
Nodes (5): TitaniumApp, worker(), on_done(), worker(), finish_cb()

### Community 2 - "orb.rs"
Cohesion: 0.06
Nodes (9): analyze_audio_block(), BandpassFilter, Biquad, WakeListener, SINGLE_INSTANCE_PORT, MARGIN_X, MARGIN_Y, NativeOrb (+1 more)

### Community 3 - "ElevenLabsTTS"
Cohesion: 0.07
Nodes (3): ElevenLabsTTS, GeminiLiveClient, ScreenStreamer

### Community 6 - "AgentRouter"
Cohesion: 0.11
Nodes (3): AgentRouter, get_user_directories(), SystemNavigator

### Community 9 - "TitaniumInstallerWindow"
Cohesion: 0.13
Nodes (3): InstallWorker, main(), TitaniumInstallerWindow

### Community 10 - "ApiKeySetupDialog"
Cohesion: 0.11
Nodes (6): acquire_single_instance_lock(), cleanup_stale_processes(), main(), notify_existing_instance(), ApiKeySetupDialog, KeyValidationWorker

### Community 13 - "gemini.rs"
Cohesion: 0.18
Nodes (9): GeminiCandidate, GeminiClient, GeminiContent, GeminiPart, GeminiRequest, GeminiResponse, GeminiResponseContent, GeminiResponsePart (+1 more)

### Community 18 - "🌌 Titanium — Autonomous Agentic Virtual Assistant"
Cohesion: 0.22
Nodes (8): 1. Installation, 2. Configuration, 3. Running Titanium, 🎮 Controls & Shortcuts, ✨ Key Features, 📄 License, 🚀 Quick Start, 🌌 Titanium — Autonomous Agentic Virtual Assistant

## Knowledge Gaps
- **1 isolated node(s):** `titanium-rust`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 245 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MusicPlayer` connect `MusicPlayer` to `orb.rs`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `TitaniumApp` (e.g. with `AgentRouter` and `ElevenLabsTTS`) actually correct?**
  _`TitaniumApp` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `titanium-rust` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0733162830349531 - nodes in this community are weakly interconnected._
- **Why does `TitaniumApp` connect `TitaniumApp` to `main.py`, `ElevenLabsTTS`, `SiriOrbWidget`, `AgentRouter`, `TitaniumMusicPlayer`, `ApiKeySetupDialog`, `CompactSubtitlePill`, `MemoryManager`, `WakeWordListener`, `WindowsInstaller`, `TitaniumTrayIcon`, `CircleToSearchOverlay`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ElevenLabsTTS` (e.g. with `TitaniumApp` and `GeminiLiveClient`) actually correct?**
  _`ElevenLabsTTS` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `TitaniumApp` be split into smaller, more focused modules?**
  _Cohesion score 0.05411764705882353 - nodes in this community are weakly interconnected._