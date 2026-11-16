# Feature call-site findings — 2026-11-17

**Target:** Yandere Simulator, Unity `6000.2.8f1`  
**Input:** `Managed.zip` stored in this repository (15,784,535 bytes; Git blob SHA `a8845bc8c2726f5a524ffd690d07e1feaeed03d6`).  
**Analysis:** existing GitHub Actions workflow `Managed CIL call-site audit`, run #4, commit `20cf30215fa683e45ad9b906e955df5df4c16231`.  
**Run:** https://github.com/HelterFall/YandereSimulator/actions/runs/43979217454  
**Artifact:** `managed-cil-call-audit`, ID `14282757486`, 1,910,436 bytes, retention until 2026-11-30.

## Executive summary

The GitHub Actions pipeline successfully extracted the actual `Managed.zip`, built the Mono.Cecil scanner and analyzed all 143 DLLs. It produced 175,137 call-like IL instructions from `Assembly-CSharp.dll`, `Assembly-CSharp-firstpass.dll` and `XInputDotNetPure.dll`, with zero DLL parse errors. The scanner's feature-filtered CSV contains 1,630 rows. These are static call-site observations, not a runtime trace and not proof that every component is present or enabled in a shipped scene.

The most actionable findings:

1. **XInput is used by game-owned methods, not just by a demo script.** The main game assembly calls `XInputDotNetPure.GamePad.GetState` and `SetVibration` from rumble/vibration-related methods, including `HNS.Rumble`, `IntroScript`, `YandereScript`, `CameraEffectsScript`, `CounselorScript`, `HeartbrokenScript`, `MissionModeScript`, `SceneLoader` and `VibrationScript`. The XInput wrapper in turn calls native `XInputGamePadGetState` and `XInputGamePadSetState` from `XInputInterface`. The supplied native `XInputInterface.dll` is Windows x86-64, so it cannot be loaded by Android ARM64 as-is.
2. **There are two Discord integration paths in game-owned code.** `DiscordController.OnEnable` calls `DiscordRpc.Initialize`; `RichPresenceHelper.Start` and `RichPresenceHelper.UpdatePresence` call `DiscordRpc.UpdatePresence`. Separately, `DiscordRPC.Start` constructs `Discord.Discord`, starts activity updates and `DiscordRPC.Update` calls `RunCallbacks`. The first-pass assembly declares legacy `discord-rpc` and Game SDK `discord_game_sdk` native imports. The Game SDK DLL was not found in the supplied archives; the RPC DLL is Windows x86-64. Whether these MonoBehaviour components are attached/enabled in the first scene is not established by this scan.
3. **Selenium is concentrated in `YouTubeChat`.** The 34 direct WebDriver/Selenium call sites found in the main game assembly are all in `YouTubeChat` methods. `YouTubeChat.OnEnable` calls `StartDriver`, which reaches FirefoxDriver/WebDriver setup. This looks like a separable browser/chat feature, but scene attachment and whether it is enabled at launch still need checking.
4. **The game also has Unity Input System gamepad handling.** `GamepadSwitcherScript.Start/Update` checks `UnityEngine.InputSystem.Gamepad.current` and legacy joystick names. Other game scripts call Input System Gamepad APIs. That gives us a native Android input route to investigate separately from the Windows XInput haptics wrapper.
5. **The broken `StreamingAssets.zip` was not needed for this managed call-site scan.** The scan consumed only `Managed.zip`. A working StreamingAssets archive will matter later when auditing the Selenium/Firefox payload and game content; replace it before that stage, not as a prerequisite for this report.

## Verified workflow output

The successful workflow log reports:

| Metric | Result |
|---|---:|
| Managed DLL files parsed | 143 |
| Call-like IL instructions in selected assemblies | 175,137 |
| Feature-related call-site rows | 1,630 |
| DLL parse errors | 0 |
| Selected assemblies | Assembly-CSharp, Assembly-CSharp-firstpass, XInputDotNetPure |

The artifact contains:
- `SUMMARY.md`
- `game_callsites.csv` — all selected-assembly call sites (about 42 MB uncompressed)
- `feature_callsites.csv` — filtered feature-related call sites (about 484 KB uncompressed)

The full call-site CSVs are kept as a temporary Actions artifact rather than committed as large generated files. Download the artifact from the workflow run page above; GitHub Actions retention is 14 days for this run.

## Evidence details

### XInput / controller vibration

Direct call sites from `Assembly-CSharp.dll` to `XInputDotNetPure` include:

| Caller type | Methods / operations observed |
|---|---|
| `HNS.Rumble` | `Update`, `CheckControllerConnection`, `IsConnected`, `SetVibration` |
| `IntroScript` | `Update` → `GamePad.SetVibration` (8 call sites) |
| `YandereScript` | `LateUpdate`, `UpdateEffects` → `SetVibration` |
| `CameraEffectsScript` | `Update`, `Alarm`, `MurderWitnessed` → `SetVibration` |
| `CounselorScript` | `UpdateInterrogation` → `SetVibration` |
| `HeartbrokenScript` | `Update` → `SetVibration` |
| `MissionModeScript` | `Update` → `SetVibration` |
| `SceneLoader` | `Start` → `SetVibration` |
| `VibrationScript` | `Start`, `Update` → `SetVibration` |

The XInput wrapper's managed methods call native imports:
- `GamePad.GetState` → `XInputGamePadGetState`
- `GamePad.SetVibration` → `XInputGamePadSetState`

This points to an Android compatibility task for controller rumble/state polling. It does **not** yet prove that the game requires XInput to enter or play the first scene. A likely design candidate is an Android-side implementation backed by Unity Input System gamepad APIs, with a truthful unsupported/no-controller result when unavailable. That requires a tested shim or managed adaptation; it is not implemented yet.

The 68 call sites in `XInputTestCS` are a separate diagnostic/test component and should not be confused with the game-owned call sites above.

### Discord

Game-owned entrypoints and native boundaries observed:

| Caller | Direct call | Native boundary further down |
|---|---|---|
| `DiscordController.OnEnable` | `DiscordRpc.Initialize` | `Discord_Initialize` |
| `RichPresenceHelper.Start` | `DiscordRpc.UpdatePresence` | `Discord_UpdatePresence` |
| `RichPresenceHelper.UpdatePresence` | `DiscordRpc.UpdatePresence` | `Discord_UpdatePresence` |
| `DiscordRPC.Start` | `new Discord.Discord(...)`, then `UpdateActivity` | `DiscordCreate` from `discord_game_sdk` |
| `DiscordRPC.Update` | `Discord.Discord.RunCallbacks` | Discord Game SDK |

The first-pass metadata audit found seven imports from `discord-rpc` and one from `discord_game_sdk`. The repository's `Plugins.zip` contains the Windows x86-64 `discord-rpc.dll`; no `discord_game_sdk.dll` was found in the supplied archives. This is an unresolved portability boundary. Do not assume Discord is safely removable until scene/component presence and startup order are checked; do not treat it as a core gameplay requirement based only on call-site presence.

### Selenium / YouTube chat

The main game assembly contains 34 direct call sites whose targets are Selenium/WebDriver types, all under `YouTubeChat`. Observed methods include:
- `OnEnable` → `StartDriver`
- `StartDriver` → Firefox driver service / driver construction
- `ActivateDriver` → browser navigation and message update
- `UpdateMessagesList` → DOM element lookup and text access
- `OnDisable` / `OnApplicationQuit` → driver shutdown

This feature has an obvious Windows desktop dependency chain (Firefox/GeckoDriver/WebDriver). It is a strong candidate for an optional unsupported feature on Android, but the next step is to check whether any first-scene objects actually contain and enable `YouTubeChat` or related components.

### Unity Input System

The game-owned `GamepadSwitcherScript.Start/Update` methods query `UnityEngine.InputSystem.Gamepad.current` and legacy `Input.GetJoystickNames`. The class also contains `UseAndroidInputs`, but the method body observed by this scanner only logs a message; it is not evidence of a complete Android mapping implementation. Other game scripts query `Gamepad.current` and use `SetMotorSpeeds`. This is a better starting point for native Android controller input/haptics than attempting to load the Windows XInput DLL, but it still requires Unity API implementation in RamenUnity.

## What this changes for RamenUnity

- Prioritize an Android controller abstraction that implements the Input System gamepad calls used by the game.
- Treat XInput as a compatibility shim problem focused primarily on controller state and vibration, not as a general input backend.
- Keep Discord and YouTube chat outside the first compatibility slice unless scene inspection proves they are activated at startup.
- The next highest-value static-data task is to inspect the first scenes and identify which MonoBehaviour scripts are attached/enabled. That resolves the main uncertainty left by the call-site report.
- After scene membership is known, trace direct calls from the relevant component lifecycle methods and build a small dependency list for first-scene initialization.

## Limitations

- The scan decodes call-like IL instructions; it does not execute methods or observe runtime behavior.
- It does not build a whole-program call graph, prove reachability from Unity's scene lifecycle, or inspect serialized scene component references.
- Reflection, delegates, event registration, native callbacks, dynamic loading and conditional branches may affect actual behavior.
- A method body existing in an assembly does not prove its component exists or is enabled in a scene.
- No Windows or Android game launch was performed.
- The result reflects the exact `Managed.zip` blob used by the workflow run. Re-run the workflow after replacing that archive.

**Integrity statement:** all numeric scan results above come from the successful workflow log and its downloaded artifact. Feature interpretations are static-analysis hypotheses until checked against serialized scenes or runtime evidence.
