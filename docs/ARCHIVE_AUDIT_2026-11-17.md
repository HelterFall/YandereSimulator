# Archive audit: Yandere Simulator snapshot

**Audit date:** 2026-11-17  
**Scope:** ZIP files present in the current analysis workspace; selected managed/native binaries; Unity SerializedFile header strings and two runtime JSON manifests.  
**Method:** ZIP directory enumeration and CRC testing; extraction of selected DLLs; PE/CLR header inspection; import-table inspection; limited ASCII string inspection. This is not a full decompilation, full asset parse, or complete-game audit.

## Executive findings

1. **Unity version is now confirmed from the supplied game data:** `6000.2.8f1`. The string appears in the headers/metadata area of `globalgamemanagers`, `globalgamemanagers.assets`, `level0`, and `level1`. This resolves the earlier `unityVersion: null` from God: that value was a limitation of the scanner's heuristic, not evidence that the game version is absent.
2. **The game code is managed Mono/CIL, but the bundled runtime is Windows x86-64.** `Assembly-CSharp.dll` and `Assembly-CSharp-firstpass.dll` are PE32 CLR assemblies with the IL-only flag. The supplied `mono-2.0-bdwgc.dll` and `MonoPosixHelper.dll` are native PE32+ x86-64 Windows DLLs.
3. **The native plug-ins supplied here are Windows x86-64.** The 40 DLL files in `Plugins.zip` are under `Plugins/x86_64`; the inspected PE headers identify them as x86-64 native binaries. `D3D13(1).zip` contains `D3D13/D3D12Core.dll`, also x86-64 native.
4. **There are likely optional/platform-specific integration areas to audit:** the managed assembly string tables contain Discord RPC, XInput, and Selenium/WebDriver/Firefox names. `StreamingAssets(1).zip` contains a WebDriver package and Windows Firefox/GeckoDriver binaries. These strings and files establish presence, not that every feature is mandatory at startup.
5. **The uploaded data is incomplete as a full game snapshot.** The readable `YandereSimulator_Data.zip` contains only 11 files, including `globalgamemanagers`, `level0`, `level1`, and a small selection of shared assets. The separate `StreamingAssets.zip` cannot be opened because it has no readable ZIP central directory. No `YandereSimulator.zip` main-player archive is present in this workspace snapshot.

## ZIP integrity and coverage

| Archive | Entries / files | Uncompressed size | Result |
|---|---:|---:|---|
| `Managed.zip` | 144 / 143 | 45,207,136 B | ZIP CRC test passed |
| `MonoBleedingEdge.zip` | 31 / 20 | 9,124,710 B | ZIP CRC test passed |
| `Plugins.zip` | 42 / 40 | 5,532,064 B | ZIP CRC test passed |
| `YandereSimulator_Data.zip` | 11 / 11 | 53,436,238 B | ZIP CRC test passed |
| `StreamingAssets(1).zip` | 589 / 463 | 65,930,624 B | ZIP CRC test passed |
| `Resources.zip` | 3 / 2 | 7,038,988 B | ZIP CRC test passed |
| `GI.zip` | 37 / 30 | 4,996,010 B | ZIP CRC test passed |
| `D3D13(1).zip` | 2 / 1 | 5,908,408 B | ZIP CRC test passed |
| `StreamingAssets.zip` | unavailable | 24,804,835 B | Failed: no end-of-central-directory record; contents could not be enumerated or CRC-tested |

The `Managed.zip` archive stores its entries under `Managed - Копия/` (including the Cyrillic word for “copy”). That is the archive's actual internal path; it should not be silently treated as a canonical `Managed/` directory.

The data archive contains these files: `app.info`, `boot.config`, `globalgamemanagers`, `globalgamemanagers.assets`, `level0`, `level1`, `RuntimeInitializeOnLoads.json`, `ScriptingAssemblies.json`, `sharedassets43.resource`, `sharedassets44.assets`, and `sharedassets44.assets.resS`. It is not the complete `YandereSimulator_Data` directory represented in the earlier God inventory.

## Confirmed Unity version and startup manifests

The literal version string `6000.2.8f1` was found in four supplied SerializedFile-like files:

- `globalgamemanagers`
- `globalgamemanagers.assets`
- `level0`
- `level1`

The supplied `ScriptingAssemblies.json` has **120 assembly names** and 120 matching type entries. The supplied `RuntimeInitializeOnLoads.json` has **25 startup initialization records**. This is useful for building an initial assembly-load and startup-callback inventory, but it does not by itself reveal all runtime dependencies.

## Managed assemblies versus native runtime

### Managed code

- `Managed.zip` contains 143 DLL files.
- `Assembly-CSharp.dll`: 5,169,664 B; PE32; CLR header present; CLR flags `0x1` (IL-only).
- `Assembly-CSharp-firstpass.dll`: 414,208 B; PE32; CLR header present; CLR flags `0x1` (IL-only).
- The inspected UnityEngine and game managed DLLs use PE32/CLR containers. PE32 here does **not** mean the managed IL is tied to a 32-bit Android CPU; the IL-only flag is the relevant observation. Runtime/profile/API compatibility still needs to be tested.

### Bundled Mono runtime

`MonoBleedingEdge.zip` contains:

- `MonoBleedingEdge/EmbedRuntime/mono-2.0-bdwgc.dll` — native PE32+ x86-64 Windows DLL.
- `MonoBleedingEdge/EmbedRuntime/MonoPosixHelper.dll` — native PE32+ x86-64 Windows DLL.
- Mono configuration and framework configuration files.

The inspected Mono runtime imports Windows libraries including `KERNEL32.dll`, `USER32.dll`, `ADVAPI32.dll`, `WS2_32.dll`, `WINMM.dll`, `SHELL32.dll`, `ole32.dll`, `OLEAUT32.dll`, `VERSION.dll`, and `bcrypt.dll`. These exact DLLs cannot be loaded as Android ARM64 native libraries. The CIL assemblies may be portable; the bundled Windows runtime binaries are not.

## Native plug-in inventory and compatibility implications

- `Plugins.zip`: 40 native DLLs, all located under `Plugins/x86_64/`; inspected PE headers identify them as x86-64 native Windows DLLs.
- Notable names include `XInputInterface.dll`, `discord-rpc.dll`, `lib_burst_generated.dll`, `libEGL.dll`, accessibility DLLs, and Windows CRT/API-set DLLs.
- `D3D13(1).zip` contains `D3D13/D3D12Core.dll`, an x86-64 native DLL. Despite the archive folder name, the file is named `D3D12Core.dll`.
- `StreamingAssets(1).zip` contains `WebDriver.dll`, a Selenium WebDriver package, Firefox/GeckoDriver executables, and many accompanying Windows DLLs.
- String inspection of `Assembly-CSharp.dll` found names including `OpenQA.Selenium`, `OpenQA.Selenium.Firefox`, `WebDriver`, `XInputDotNetPure`, `DiscordRPC`, `DiscordVerificationScript`, `Unity.InputSystem`, and `UnityWebRequest`. `Assembly-CSharp-firstpass.dll` includes Discord SDK/RPC symbols and XInput-related symbols.

**Interpretation:** these are real portability risks, but not proof that every plugin must be ported. Some may only serve optional Discord, controller, browser automation, editor/debug, or other feature paths. We need a metadata-level P/Invoke and method-reference report before assigning priority or writing replacements.

Unity's Android documentation describes native plug-ins as shared `.so` libraries (and, depending on backend, static libraries/source); its backend compatibility table says Mono supports shared libraries, not static libraries or C/C++ source plug-ins. The Windows `.dll` files found in this snapshot are not Android `.so` binaries. Only dependencies shown to be used on the required game path should be replaced.

## ARM64 runtime risk

Unity's published scripting-backend support table for Unity 6.0 lists Mono on Android **ARMv7**, while Android **ARM64** is enabled only with IL2CPP in its Android Player settings. This means we cannot assume Unity's standard Mono Android player backend provides the ARM64 runtime we need.

The upstream Mono project documents Android support and lists ARM architectures, including an interpreter entry marked for arm64. That is useful evidence that an Android Mono port exists, but it does **not** prove that the exact Unity-bundled Mono fork/profile used by this game is available as a compatible ARM64 JIT runtime. RamenUnity still needs its own ARM64 runtime feasibility test and must record the exact Mono version, ABI, runtime mode (JIT/interpreter), and framework profile.

This is a constraint on our custom host/runtime plan, not proof that standalone ARM64 Mono is impossible.

## What was not done

- No full decompilation of `Assembly-CSharp.dll` or `Assembly-CSharp-firstpass.dll`.
- No Mono.Cecil, ILSpy, monodis, or equivalent assembly metadata tool was available in this analysis environment, so the full AssemblyRef/P/Invoke tables have not yet been extracted.
- No UnityDataTool or AssetsTools.NET parse was run against the serialized assets.
- No Android ARM64 runtime was built or executed.
- No Unity scene, asset bundle, or complete level was reconstructed.
- No game launch was attempted.
- The missing main-player archive and incomplete `StreamingAssets.zip` prevent a complete file/dependency inventory.

## Next work, in priority order

1. Obtain the missing main-player archive and a complete `YandereSimulator_Data` snapshot; replace the unreadable `StreamingAssets.zip` with a verified copy only if that file is needed.
2. Run a read-only Mono.Cecil audit on `Assembly-CSharp.dll` and `Assembly-CSharp-firstpass.dll`: AssemblyRef, TypeRef, P/Invoke module names, imported entry points, and calls into UnityEngine modules.
3. Cross-check the assembly audit against `ScriptingAssemblies.json` and `RuntimeInitializeOnLoads.json` to build a minimal startup dependency graph.
4. Separate native integrations into required, optional, and unknown. Investigate Discord, XInput, and Selenium/Firefox before assuming any must be implemented for first launch.
5. Prove a standalone ARM64 managed runtime on Android with a tiny test assembly before attempting the game's assemblies.
6. Inspect SerializedFile metadata with UnityDataTool/AssetsTools.NET on a machine or build environment where those tools are available.

## External references

- Mono supported platforms: https://www.mono-project.com/docs/about-mono/supported-platforms/
- Mono embedding API: https://www.mono-project.com/docs/advanced/embedding/
- Unity 6.0 scripting backend support: https://docs.unity.com/en-us/engine/6000.0/manual/programming-environment/scripting-backends/intro
- Unity Android Player settings: https://docs.unity.com/en-us/engine/6000.0/manual/platform-specific/android/getting-started/class-player-settings
- Unity Android native plug-ins: https://docs.unity.com/en-us/engine/6000.7/manual/platform-specific/android/developing/plugins-for/plugin-types/native-plugins/introducing
- Mono.Cecil overview: https://www.mono-project.com/docs/tools+libraries/libraries/Mono.Cecil/

**Integrity rule:** archive listings, CRC results, PE headers, JSON manifests, and string matches are reported as direct observations. Inferences about whether a feature is required are explicitly marked as such. No compatibility or launch success is claimed.
