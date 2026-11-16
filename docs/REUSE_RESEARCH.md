# Reuse research: Unity Mono → Android

**Research date:** 2026-11-17  
**Target game:** Yandere Simulator (Windows Unity Mono build)  
**Purpose:** identify existing projects and libraries that can replace custom implementation work.  
**Status:** initial research; candidates are not yet integrated or validated against this game's exact build.

## Executive summary

Do not build every parser or runtime subsystem from scratch.

1. **Unity asset inspection:** evaluate Unity Technologies' UnityDataTool and the open-source AssetsTools.NET / UABEA ecosystem before writing a SerializedFile or AssetBundle parser.
2. **Managed assembly inspection:** evaluate Mono.Cecil for reading assembly metadata, references, method bodies and P/Invoke declarations. This is directly relevant to the game's `Assembly-CSharp.dll` and UnityEngine modules.
3. **Managed execution:** use an Android-native ARM64 Mono/.NET runtime as a research candidate, not the Windows `MonoBleedingEdge` binaries from the game. Mono supports embedding in principle, but this does not provide Unity's engine implementation.
4. **Unity API / native bridge:** this remains the largest custom-work risk. A CLR can execute managed IL, but game code still expects UnityEngine APIs, engine objects, native/internal calls, rendering, input, physics, audio, scene lifecycle and platform services.
5. **IL2CPP tools:** Cpp2IL is not a solution for this current Mono build. Keep it as a later separate research tool if an IL2CPP game is targeted.

The quickest useful milestone is a small Android ARM64 proof-of-concept that loads a harmless test CIL assembly and calls a few managed methods. Do not begin by trying to launch the whole game.

---

## Candidate projects and libraries

### 1. UnityDataTool — official Unity data inspection tool

- Repository: https://github.com/Unity-Technologies/UnityDataTools
- Documentation: https://github.com/Unity-Technologies/UnityDataTools/tree/main/Documentation
- Useful capabilities documented by the project:
  - inspect Unity SerializedFiles and archives;
  - list archive contents;
  - dump serialized data to readable text;
  - analyze files into SQLite;
  - inspect object lists, metadata and external references;
  - inspect AssetBundles and Addressables containers.
- Why it helps: gives us a reference implementation and a ready-made way to inspect game data structures instead of inventing a format parser.
- Important limitation: it is a command-line analysis tool, not a Unity runtime and not an Android game player. Its native dependencies/build targets must be checked before considering embedding it in the Android app.
- Proposed use: run it during development on extracted game data (or use its source/docs as a format reference); compare its output with God’s inventory. Do not assume it can run inside RamenUnity on Android.

### 2. AssetsTools.NET — reusable .NET library for Unity assets

- Repository: https://github.com/nesrak1/AssetsTools.NET
- License shown by repository: MIT.
- Project description: .NET library for reading and writing Unity asset and bundle files.
- Why it helps: a more promising library candidate than implementing SerializedFile / AssetBundle parsing from zero.
- Proposed use: evaluate read-only parsing first. Identify which parts are portable to Android and whether the required Unity versions and formats match this game's data.
- Limitation: parsing assets is not the same as creating Unity GameObjects, running scripts or rendering scenes. Writing/modifying files is not needed for the first milestone.

### 3. UABEA — existing Unity asset research tool

- Repository: https://github.com/nesrak1/UABEA
- Project description: cross-platform AssetBundle / SerializedFile reader and writer.
- Its README points users to AssetRipper when the goal is extraction rather than editing.
- The project lists dependencies including AssetsTools.NET, Mono.Cecil and texture/audio-related libraries.
- Why it helps: useful as a working reference for asset formats and an ecosystem map. Its dependencies help identify reusable building blocks.
- Limitation: desktop GUI application; do not assume the complete GUI can be embedded in an Android app. Prefer evaluating the underlying libraries.

### 4. AssetRipper — Unity asset extraction and conversion

- Repository: https://github.com/AssetRipper/AssetRipper
- Project description: extracts assets from Unity serialized files and AssetBundles and can convert them to a native Unity project format.
- Why it helps: can help inspect what content exists and how assets relate, without writing a custom extractor first.
- Limitation: it is an asset extraction/conversion tool, not an Android runtime. Its GPL-3.0 license has implications if code is incorporated or distributed; review the license before reuse. Using it as a separate development tool is different from copying its code into RamenUnity.

### 5. Mono.Cecil — inspect and rewrite managed assemblies

- Repository: https://github.com/jbevain/cecil
- Why it helps: provides a .NET library for inspecting and modifying ECMA CIL assemblies. It can help us:
  - enumerate types, methods, fields and assembly references;
  - inspect method bodies and metadata;
  - locate P/Invoke declarations and external dependencies;
  - identify references to UnityEngine modules and Windows-specific APIs;
  - generate a structured compatibility report.
- Proposed use: evaluate it for a future RamenUnity assembly audit tool. First make the audit read-only.
- Limitation: Mono.Cecil does not execute the game and does not implement UnityEngine. Rewriting assemblies should only be considered after a specific, tested compatibility issue is identified.

### 6. Mono runtime embedding — execution foundation candidate

- Runtime overview: https://www.mono-project.com/docs/advanced/runtime/
- Embedding guide: https://www.mono-project.com/docs/advanced/embedding/
- Android platform page: https://www.mono-project.com/docs/about-mono/supported-platforms/android/
- What the documentation establishes:
  - Mono implements the CLI virtual machine and executes managed CIL;
  - Mono can be embedded in a native application;
  - the embedding API supports loading assemblies and calling managed methods;
  - Mono has an Android port.
- Why it helps: it means we should investigate an existing managed runtime rather than writing a CLR ourselves.
- Critical architecture warning:
  - the game's `MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll` and `MonoPosixHelper.dll` are Windows game files; they are not Android ARM64 libraries;
  - an Android build needs compatible ARM64 native runtime binaries and Android integration;
  - loading CIL successfully is only one layer. UnityEngine native/internal calls and Windows P/Invoke dependencies still need compatible implementations or replacements.
- Proposed use: build a tiny ARM64 Android host that initializes the chosen runtime, loads a test assembly, invokes a method, and reports exceptions. Only after that passes should we test a harmless method from the game's managed assemblies.
- Version caution: the Mono documentation describes the runtime and embedding concepts, but it does not prove that an arbitrary modern Mono build is binary-compatible with this game's Unity-bundled Mono profile. Exact framework/profile compatibility remains to be tested.

### 7. Cpp2IL — later / IL2CPP-only investigation

- Repository: https://github.com/SamboyCoding/Cpp2IL
- License shown by repository: MIT.
- Purpose: reverse/analyze Unity IL2CPP builds and recover managed structure from IL2CPP metadata and native binaries.
- Why it is not a current shortcut: the supplied Yandere Simulator inventory has strong Mono indicators (`Assembly-CSharp.dll`, `Assembly-CSharp-firstpass.dll`, `MonoBleedingEdge`) and no reported `GameAssembly.dll` / `global-metadata.dat` pair. Cpp2IL therefore does not solve the current Mono runtime problem.
- Keep it in the toolbox only for a separate IL2CPP target or if later evidence changes the backend assessment.

---

## Managed assembly audit update (2026-11-17)

A read-only PE/CLI metadata-table audit has now been completed for all 143 DLLs in the supplied `Managed.zip`. It extracted direct AssemblyRef, TypeRef, MemberRef, ModuleRef and P/Invoke (ImplMap) metadata; no metadata parse errors occurred. This was a custom parser, not Mono.Cecil, and it did not decompile method bodies or build a call graph.

Key findings: `Assembly-CSharp.dll` has 37 direct assembly references, all matched in `Managed.zip`, and no P/Invoke declarations. `Assembly-CSharp-firstpass.dll` has 18 direct references (all matched) and eight Discord native imports. `XInputDotNetPure.dll` imports `XInputInterface`; Unity AMD/NVIDIA modules import `AMDUnityPlugin` / `NVUnityPlugin`. The two vendor plug-ins and `discord_game_sdk.dll` were not found in the supplied archives; `XInputInterface.dll` and `discord-rpc.dll` were found as Windows x86-64 binaries. The game assembly also directly references Selenium/WebDriver types. These are declarations and references, not proof that each feature is called during startup.

Full tables and limitations: [Managed assembly dependency audit](ASSEMBLY_DEPENDENCY_AUDIT_2026-11-17.md).

## IL method-body analysis follow-up

The metadata-only audit is not enough to decide whether optional native integrations are reached during startup. The next step is to inspect CIL method bodies and call sites. The current tooling comparison and reproducible workflow are recorded in [IL method-body analysis tooling](IL_ANALYSIS_TOOLING_2026-11-17.md). This is a research plan only; no method-body scan or call graph has yet been run.

## IL call-site scan results (2026-11-17)

The existing GitHub Actions workflow successfully ran Mono.Cecil over all 143 Managed.zip DLLs. It decoded 175,137 call-like instructions from the two game assemblies and XInputDotNetPure, with zero DLL parse errors. The scan identified game-owned XInput vibration/state calls, two Discord integration paths, and Selenium/WebDriver use concentrated in YouTubeChat. Full curated findings and the unresolved scene-membership questions are documented in [Feature call-site findings](FEATURE_CALLSITE_FINDINGS_2026-11-17.md). This remains static analysis, not a runtime trace or proof of first-scene reachability.

## First-scene component inventory (2026-11-17)

The partial Player Data archive was successfully inspected with UnityPy 1.25.4 after UnityDataTool's full analyzer skipped the files because their TypeTrees were stripped. All 132 MonoBehaviour script references in `level0` and `level1` resolved. `level0` contains an active, enabled `DiscordRPC` component on GameObject `Discord`, as well as active input-manager and gamepad-switcher components. This connects the managed IL finding for `DiscordCreate` to a component present in the title/menu-style scene. The serialized Discord component has now been decoded: its numeric application ID is non-empty and rich-presence updates are enabled. The focused IL dump confirms the non-empty application ID branch constructs `Discord.Discord`, whose constructor calls `DiscordCreate`. Because the active level0 component has a non-empty ID, this is a first-scene native dependency. The missing DLL finding remains limited to the supplied archive set. See [the scene component audit](SCENE_COMPONENT_AUDIT_2026-11-17.md).

## What this means for this Yandere Simulator snapshot

The God report (generated 2026-11-15) records:

- backend assessment: **Mono — strong structural indicators**;
- `Assembly-CSharp.dll` and `Assembly-CSharp-firstpass.dll`;
- many UnityEngine managed modules;
- Windows Mono runtime files;
- many Windows x86-64 plugins and imports, including Windows system libraries;
- Unity version was not detected by the current heuristic (`unityVersion: null`).

**Update from direct archive inspection (2026-11-17):** the supplied `YandereSimulator_Data.zip` contains `6000.2.8f1` in `globalgamemanagers`, `globalgamemanagers.assets`, `level0`, and `level1`. The version is therefore confirmed for this supplied snapshot; the earlier null was a scanner limitation. See [the archive audit](ARCHIVE_AUDIT_2026-11-17.md) for exact scope and integrity results.

The archive audit also confirmed that the bundled Mono runtime DLLs and supplied native plug-ins are Windows x86-64 binaries, while the game assemblies are IL-only managed PE files. Unity's published Unity 6.0 scripting-backend support table lists Android Mono as ARMv7; ARM64 Android Player builds require IL2CPP. This does not rule out hosting a separate standalone ARM64 runtime, but it means RamenUnity cannot assume Unity's standard Mono Android player runtime is available for ARM64. Upstream Mono's platform table separately lists Android ARM support and an ARM64 interpreter entry; exact JIT/runtime/profile compatibility remains unproven.

These observations do **not** prove Android compatibility. The report also warns that PE analysis was limited to the first 150 EXE/DLL files. The archive audit covers only the ZIPs actually available in the workspace; the full main-player archive was not present and one `StreamingAssets.zip` was unreadable.

### Reuse map

| RamenUnity subsystem | First candidate | Expected reuse | What remains custom |
|---|---|---|---|
| Unity serialized data reader | UnityDataTool / AssetsTools.NET | High for parsing/reference knowledge; platform integration unknown | Android integration, supported-version tests, game-specific handling |
| Asset extraction for development | AssetRipper | High as an external development tool | Decide which extracted assets are actually needed |
| Managed assembly audit | Mono.Cecil | High for metadata and IL inspection | Game-specific compatibility report and test harness |
| Managed CIL execution | Android ARM64 Mono runtime | Potentially high for CLR execution | Select/build compatible runtime, Android host, profile validation |
| UnityEngine API surface | Existing Unity modules as reference | Low-to-medium | Engine object model, native calls, lifecycle and API compatibility |
| Windows native plugin replacement | Android platform APIs / per-feature alternatives | Low | Identify and replace each required Windows dependency |
| IL2CPP analysis | Cpp2IL | Not needed for current Mono-first target | Separate IL2CPP path only |

## Recommended order of work

### Phase A — avoid duplicate analysis

1. Keep God as the source of the initial file inventory.
2. Improve the Unity version detection separately; do not infer the version from a null result.
3. Use Mono.Cecil (or another proven metadata reader) to produce a deeper report of:
   - assembly references;
   - P/Invoke methods and imported DLL names;
   - UnityEngine type/member usage;
   - framework/profile dependencies.
4. Do not repeat God’s directory scan inside RamenUnity unless a specific missing capability requires it.

### Phase B — prove the runtime independently

1. Choose an Android ARM64-compatible managed runtime candidate.
2. Build a minimal Android native host around it.
3. Load a tiny test CIL assembly and invoke a simple managed method.
4. Test file access, threading, exceptions, reflection and assembly loading.
5. Record exact runtime version, ABI, build configuration and test results.
6. Only then attempt to load the game's managed assemblies without starting Unity gameplay.

### Phase C — measure Unity compatibility

1. Use the game's assemblies to list the UnityEngine APIs and native calls it expects.
2. Group dependencies by subsystem: object lifecycle, scenes, transforms, rendering, input, physics, audio, UI, resources and platform services.
3. Pick one very small vertical slice and implement/test it end-to-end.
4. Replace Windows-only native dependencies only when evidence shows the game actually needs them.
5. Keep unsupported calls explicit; do not silently return fake success.

## Decisions and non-goals

- **Do not** write a custom CLR.
- **Do not** write a Unity asset parser before evaluating AssetsTools.NET and UnityDataTool.
- **Do not** assume the game's Windows Mono DLL can run on Android ARM64.
- **Do not** treat a successful CIL method call as proof that Unity gameplay works.
- **Do not** port every Windows plugin pre-emptively; first establish which ones are loaded and required.
- **Do not** start with IL2CPP tooling for this Mono-indicated snapshot.
- **Do not** promise a first playable build until the runtime and a Unity-dependent test scene have passed on a real Android device.

## Verification checklist for each candidate

Before adopting a dependency, record:

- exact repository and pinned commit/release;
- license and redistribution obligations;
- supported Unity/game data versions;
- supported Android ABI and minimum Android API, if applicable;
- native dependencies and build requirements;
- whether it is a parser, extractor, runtime, engine, or reference tool;
- a minimal test against files from this exact Yandere Simulator snapshot;
- measured result, limitations and fallback.

## Sources

- Mono runtime overview: https://www.mono-project.com/docs/advanced/runtime/
- Mono embedding: https://www.mono-project.com/docs/advanced/embedding/
- Mono on Android: https://www.mono-project.com/docs/about-mono/supported-platforms/android/
- Mono supported architectures: https://www.mono-project.com/docs/about-mono/supported-platforms/
- Unity 6.0 scripting backend platform support: https://docs.unity.com/en-us/engine/6000.0/manual/programming-environment/scripting-backends/intro
- Unity Android native plug-ins: https://docs.unity.com/en-us/engine/6000.7/manual/platform-specific/android/developing/plugins-for/plugin-types/native-plugins/introducing
- UnityDataTool: https://github.com/Unity-Technologies/UnityDataTools
- UnityDataTool SerializedFile docs: https://github.com/Unity-Technologies/UnityDataTools/blob/main/Documentation/command-serialized-file.md
- AssetsTools.NET: https://github.com/nesrak1/AssetsTools.NET
- UABEA: https://github.com/nesrak1/UABEA
- AssetRipper: https://github.com/AssetRipper/AssetRipper
- Mono.Cecil: https://github.com/jbevain/cecil
- Cpp2IL: https://github.com/SamboyCoding/Cpp2IL

**Research integrity note:** this document records documented project capabilities and engineering hypotheses. None of these candidates has yet been built into RamenUnity or validated on the target Android device with Yandere Simulator. Re-check upstream documentation, releases and licenses before integration.
