# Managed assembly dependency audit — 2026-11-17

**Target:** supplied Yandere Simulator snapshot, Unity `6000.2.8f1`  
**Input:** `Managed.zip`, `YandereSimulator_Data.zip`, `Plugins.zip`, `StreamingAssets(1).zip`, and the other ZIP archives currently attached in this workspace.  
**Method:** custom read-only PE/CLI metadata-table parser. It read the CLI metadata streams in all 143 DLLs in `Managed.zip`, extracted AssemblyRef, ModuleRef, ImplMap (P/Invoke map), TypeRef and MemberRef tables, then cross-checked names against the supplied ZIP file lists and Unity manifests. This was **not** Mono.Cecil; no third-party metadata library was available in the environment.

## Executive summary

1. **The two game assemblies' direct managed references are complete in the supplied Managed.zip.** `Assembly-CSharp.dll` has 37 AssemblyRef entries and `Assembly-CSharp-firstpass.dll` has 18. Every referenced assembly name has a matching DLL in the archive. This only confirms file presence, not that every assembly is loadable or API-compatible on Android.
2. **The main game assembly declares no P/Invoke imports.** `Assembly-CSharp.dll` has zero ModuleRef rows and zero ImplMap rows. Its metadata does directly reference browser automation (Selenium/WebDriver), Discord wrapper types, and XInput types; whether these code paths are required at startup is not yet established.
3. **The first-pass assembly declares eight Discord native imports.** Seven target `discord-rpc`; one targets `discord_game_sdk`. The supplied Plugins archive contains `discord-rpc.dll` but none of the supplied archives contains `discord_game_sdk.dll`.
4. **XInput has a clear native boundary.** `XInputDotNetPure.dll` declares two imports from `XInputInterface`; `Plugins.zip` contains `Plugins/x86_64/XInputInterface.dll`. That file is a Windows x86-64 native DLL, not an Android ARM64 library.
5. **Unity's AMD and NVIDIA managed modules declare native plug-in imports.** `UnityEngine.AMDModule.dll` declares nine imports from `AMDUnityPlugin`; `UnityEngine.NVIDIAModule.dll` declares twelve from `NVUnityPlugin`. Neither native DLL was found in any supplied archive. Both managed modules are named in `ScriptingAssemblies.json`. This is a compatibility issue to investigate, but the metadata does not prove the game calls these APIs on its normal startup path.
6. **A large portion of the remaining P/Invoke declarations are in framework libraries** (`mscorlib`, `System.dll`, `System.Core.dll`, `System.Drawing.dll`, `System.Data.dll`, etc.). These libraries contain platform-specific implementations and fallback paths. Their declarations are not proof that the game invokes every imported Windows API.
7. **The 120 names in the supplied `ScriptingAssemblies.json` all have matching DLL files in Managed.zip.** The supplied `RuntimeInitializeOnLoads.json` contains 25 initialization records across 11 assemblies. None of those records alone proves whether Discord, XInput, or GPU vendor plug-ins are required by the first scene.

## Direct references from the game assemblies

### `Assembly-CSharp.dll`

- AssemblyRef rows: **37**
- TypeRef rows: **477**
- MemberRef rows: **2,934**
- ModuleRef rows: **0**
- ImplMap / P/Invoke rows: **0**
- Missing direct AssemblyRef DLLs in Managed.zip: **0**

Direct references include:

- Unity engine modules: Core, ParticleSystem, Audio, UI, Animation, Video, IMGUI, Physics, Physics2D, TextRendering, InputLegacy, UIElements, Director, Cloth, SpriteMask, Vehicles, AI, JSON serialization, ScreenCapture, ImageConversion and UnityWebRequest modules.
- Other game/runtime assemblies: `Assembly-CSharp-firstpass`, `AstarPathfindingProject`, `Unity.InputSystem`, `Unity.TextMeshPro`, `Bayat.SaveSystem.Runtime`, `Newtonsoft.Json`, `WebDriver`, `XInputDotNetPure`, and `Unity.Cinemachine`.
- Framework assemblies: `mscorlib`, `System`, `System.Core`, and `System.Xml`.

The TypeRef table contains these feature-related types:

- Selenium: `OpenQA.Selenium.WebDriver`, `FirefoxOptions`, `FirefoxDriverService`, `IWebElement`, `DriverService`, `By`, `ISearchContext`, `INavigation`, `FirefoxDriver`.
- Discord: `Discord.Discord`, `Discord.ActivityManager`, `Discord.Activity`, `Discord.Result`, `DiscordController`, `Discord.ActivityAssets`, `DiscordRpc`.
- XInput: `XInputDotNetPure.PlayerIndex`, `GamePadState`, `GamePad`.

This proves the game assembly has metadata references to these APIs. It does **not** establish when they are called, whether they are behind feature checks, or whether they are needed before the first playable scene.

### `Assembly-CSharp-firstpass.dll`

- Direct AssemblyRef rows: **18**
- ModuleRef rows: **2**
- ImplMap / P/Invoke rows: **8**
- Missing direct AssemblyRef DLLs in Managed.zip: **0**

The eight P/Invoke declarations are:

| Managed method | Native library | Native entry point |
|---|---|---|
| InitializeInternal | discord-rpc | Discord_Initialize |
| Shutdown | discord-rpc | Discord_Shutdown |
| RunCallbacks | discord-rpc | Discord_RunCallbacks |
| UpdatePresenceNative | discord-rpc | Discord_UpdatePresence |
| ClearPresence | discord-rpc | Discord_ClearPresence |
| Respond | discord-rpc | Discord_Respond |
| UpdateHandlers | discord-rpc | Discord_UpdateHandlers |
| DiscordCreate | discord_game_sdk | DiscordCreate |

Archive cross-check:

- `discord-rpc.dll`: present in `Plugins.zip`, under `Plugins/x86_64/`.
- `discord_game_sdk.dll`: not found in any supplied ZIP archive.

The second missing library may be relevant if the corresponding Discord SDK path is actually used. It is not evidence that the game cannot start without Discord: call sites and startup control flow have not been audited.

## P/Invoke inventory across all 143 managed DLLs

The metadata parser found **1,358 P/Invoke declarations across 13 assemblies** in the 143-DLL Managed.zip:

| Managed DLL | P/Invoke declarations | Referenced native module names |
|---|---:|---|
| `Assembly-CSharp-firstpass.dll` | 8 | discord-rpc, discord_game_sdk |
| `XInputDotNetPure.dll` | 2 | XInputInterface |
| `UnityEngine.NVIDIAModule.dll` | 12 | NVUnityPlugin |
| `UnityEngine.AMDModule.dll` | 9 | AMDUnityPlugin |
| `System.ServiceModel.Internals.dll` | 19 | advapi32, kernel32 |
| `System.Xml.dll` | 3 | kernel32 |
| `System.IO.Compression.dll` | 11 | __Internal |
| `System.Core.dll` | 27 | advapi32, kernel32 |
| `mscorlib.dll` | 100 | BCrypt, Kernel32, __Internal, advapi32, api-ms-win-core-heap, api-ms-win-core-threadpool, api-ms-win-core-timezone, ntdll, ole32, oleaut32, user32, libc |
| `System.Security.dll` | 7 | advapi32, crypt32, kernel32 |
| `System.Drawing.dll` | 696 | Windows, macOS and Linux native module names |
| `System.dll` | 387 | Windows, macOS and Linux native module names, including MonoPosixHelper |
| `System.Data.dll` | 77 | kernel32, odbc32, sni.dll |

**Important distinction:** these are declarations found in managed metadata, not a runtime trace. Framework libraries frequently contain multiple operating-system implementations in one assembly. Do not treat the total P/Invoke count as a list of functions that the game necessarily executes.

## Native module availability cross-check

| Native module name | Managed declaration source | Found in supplied archives? | Initial interpretation |
|---|---|---|---|
| `XInputInterface` | XInputDotNetPure | Yes: x86_64 Windows DLL | Controller integration requires an Android-side alternative or feature omission |
| `discord-rpc` | Assembly-CSharp-firstpass | Yes: x86_64 Windows DLL | Discord integration is not directly portable as-is |
| `discord_game_sdk` | Assembly-CSharp-firstpass | No | Missing in this snapshot; determine whether that SDK path is called |
| `NVUnityPlugin` | UnityEngine.NVIDIAModule | No | Vendor-specific native integration; likely not a universal first-launch dependency, but unverified |
| `AMDUnityPlugin` | UnityEngine.AMDModule | No | Vendor-specific native integration; likely not a universal first-launch dependency, but unverified |
| `sni.dll` | System.Data | No | SQL/network framework native dependency; game use not established |
| `__Internal` | System.IO.Compression, mscorlib | Not a standalone DLL | Runtime-internal binding; must be provided by the chosen managed runtime |

The supplied `ScriptingAssemblies.json` names both AMD and NVIDIA Unity modules, as well as `XInputDotNetPure.dll` and `Assembly-CSharp-firstpass.dll`. The absence of a corresponding native DLL from the current ZIP set is therefore a concrete unresolved compatibility item, not a reason to assume those code paths are definitely invoked.

## Startup manifest cross-check

- `ScriptingAssemblies.json`: 120 assembly names; **all 120** have matching DLLs in `Managed.zip`.
- `RuntimeInitializeOnLoads.json`: 25 records across 11 assemblies.
- The 11 initialization assemblies are: `Bayat.Core.Runtime`, `Unity.AI.Navigation`, `Unity.Burst`, `Unity.Cinemachine`, `Unity.Collections`, `Unity.InputSystem`, `Unity.InputSystem.ForUI`, `Unity.MemoryProfiler`, `Unity.RenderPipelines.Core.Runtime`, `Unity.RenderPipelines.GPUDriven.Runtime`, and `Unity.Rendering.LightTransport.Runtime`.

The manifest gives an initial managed initialization inventory. It is not a complete native plug-in load trace, and it does not tell us whether game scripts later call Discord, XInput, Selenium, or vendor-specific APIs.

## Engineering consequences for RamenUnity

### Highest-value early work

1. Keep the main game assembly's direct managed references as the first assembly-load checklist. All 37 referenced DLLs are present in the current Managed.zip.
2. Treat `Assembly-CSharp-firstpass` Discord imports as a separately testable feature. Do not implement Discord just to get the first scene running unless a call-path audit shows it is required.
3. Replace or omit the XInput native boundary with Android input APIs if the game actually uses it. Do not try to load the Windows x86_64 plug-in on ARM64.
4. Add explicit no-op/unsupported reporting for vendor GPU extensions only after confirming the Unity module initialization behavior. Do not silently fake success for graphics operations.
5. Investigate Selenium references and the bundled Firefox/WebDriver package. Identify call sites and whether browser automation is a debug/test/optional feature before deciding if it belongs in the first compatibility slice.
6. Audit the game assembly's method bodies and call sites next. This is needed to distinguish “assembly references a feature” from “feature is called during startup.”

### Runtime platform constraint

Unity's Unity 6.0 documentation states that its standard Mono backend supports Android ARMv7, while Android ARM64 is enabled only with IL2CPP in the Android Player settings. This is a constraint on using the stock Unity Mono player backend. It does not by itself rule out a separate ARM64 managed runtime hosted by RamenUnity, but that alternative still requires a real device proof-of-concept and exact profile/runtime validation.

## Limitations and reproducibility

- The parser reads PE/CLI metadata tables; it does not decompile C# source or execute code.
- The parser completed all 143 DLLs without metadata parse errors.
- The report extracts AssemblyRef, TypeRef, MemberRef, ModuleRef and ImplMap metadata. It does not decode method bodies into a call graph.
- P/Invoke declarations are not proof of invocation.
- A reference present in the manifest is not proof that its associated native plug-in is loaded on every device.
- ZIP availability is limited to the files currently attached in this workspace. The incomplete/missing archive caveats in `ARCHIVE_AUDIT_2026-11-17.md` still apply.
- No Android build, runtime load, scene launch, or gameplay test was performed.

## External references

- Unity 6.0 scripting backend platform support: https://docs.unity.com/en-us/engine/6000.0/manual/programming-environment/scripting-backends/intro
- Unity 6.0 Android Player settings: https://docs.unity.com/en-us/engine/6000.0/manual/platform-specific/android/getting-started/class-player-settings
- ECMA-335 CLI metadata specification: https://ecma-international.org/publications-and-standards/standards/ecma-335/

**Integrity statement:** direct metadata observations, archive presence checks, and engineering inferences are separated above. No Unity gameplay compatibility is claimed.
