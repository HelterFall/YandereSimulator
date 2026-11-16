# Scene component inventory — 2026-11-17

**Target:** Yandere Simulator, Unity `6000.2.8f1`  
**Input:** repository `YandereSimulator_Data.zip` (partial Player Data archive)  
**Workflow:** [Unity scene script inventory, run](https://github.com/HelterFall/YandereSimulator/actions/runs/43980565062)  
**Artifact:** `unity-scene-script-inventory`, ID `14283595272`, SHA-256 `5b5d55c71b11428fa628e4eb127733232a016b83eb834c211ce145463ed4fd14`, retained until 2026-11-30.

## Executive summary

The official UnityDataTool 2.4.0 header/metadata commands successfully read the available SerializedFiles and confirmed Unity `6000.2.8f1`, target platform `19` (Windows Standalone x64), SerializedFile format version `22`, and no embedded TypeTrees.

UnityDataTool's full SQLite analyzer skipped all five SerializedFiles because TypeTrees are absent. This is expected for many Player builds: the object data cannot be generically decoded without TypeTrees. See the official [SerializedFile documentation](https://github.com/Unity-Technologies/UnityDataTools/blob/v2.4.0/Documentation/command-serialized-file.md) and [dump/TypeTree notes](https://github.com/Unity-Technologies/UnityDataTools/blob/v2.4.0/Documentation/command-dump.md).

A fallback inventory was completed with UnityPy 1.25.4. It decoded only the built-in MonoBehaviour header and followed each `m_Script` reference to the MonoScript object; it did not decode custom serialized fields. Result:

| Metric | Result |
|---|---:|
| SerializedFiles loaded | 5 |
| `level0` MonoBehaviour objects | 102 |
| `level1` MonoBehaviour objects | 30 |
| MonoScript references resolved | 132 / 132 |
| Parse/reference errors | 0 |

The archive is incomplete, so references to files outside the supplied set may still be unavailable. However, all 132 MonoScript references in these two scene files resolved in this run.

## What is in level0

The `level0` scene contains a title/menu-style UI (including GameObjects named `Title Screen`, `Start`, `School Scene`, `Post-Amai Scene`, and `Street Scene`) and these relevant components:

| GameObject | Script component | GameObject active | Component enabled |
|---|---|---:|---:|
| `Discord` | `DiscordRPC` | Yes | Yes |
| `GamepadSwitcher` | `GamepadSwitcherScript` | Yes | Yes |
| `Main Camera` | `InputManagerScript` | Yes | Yes |
| `Main Camera` | `InputDeviceScript` | Yes | Yes |
| `ControllerTestPanel` | `ControllerTestScript` | No | Yes |
| `YouTubeCheck` | `YouTubeCheckScript` | Yes | Yes |
| `UpdateChecker` | `UpdateCheckScript` | Yes | Yes |
| `PlaytimeTracker` | `PlaytimeTrackerScript` | Yes | Yes |

Other scene scripts include `PromptSwapScript`, `CustomUniformScript`, `AchievementPopUpScript`, `OutlineRemovalScript`, `ConsoleLogScript`, `DetectReloadScript`, `AnimatedTextureScript`, and the UI scripts `UISprite`, `UILabel`, `UIPanel`, and `UITexture`.

### Discord is now a first-scene compatibility priority

This is stronger evidence than the earlier managed-reference-only result:

- `level0` contains a GameObject named `Discord`.
- Its `DiscordRPC` component is enabled and its GameObject is active in the serialized scene data.
- In the managed IL scan, `DiscordRPC.Start()` constructs `Discord.Discord`, calls `UpdateActivity()`, and starts a rich-presence coroutine.
- The `Discord.Discord` constructor calls the imported `DiscordCreate` method from `discord_game_sdk`.
- The earlier archive cross-check did not find `discord_game_sdk.dll` in the supplied ZIP set.

**Serialized component configuration was subsequently decoded.** The active component has a non-empty numeric `_applicationID`, `_updateRichPresence = 1`, and `_updateRate = 10.0`. Its GameObject is active and the component is enabled. The managed IL inventory shows `DiscordRPC.Start()` performs a string inequality check, parses a 64-bit application ID, then constructs `Discord.Discord`; the constructor reaches the imported `DiscordCreate` entry point. Together these observations make the Game SDK path a **high-confidence first-scene compatibility risk**, not merely a dormant assembly reference. A focused IL dump is being used to verify the exact conditional operand. The missing `discord_game_sdk.dll` finding remains limited to the supplied archive set, so the complete original player package could still contain it elsewhere.

The older `DiscordController` / `DiscordRpc` P/Invoke path and `RichPresenceHelper` are not listed as components in `level0` or `level1`. Do not conflate those legacy wrappers with the active `DiscordRPC` Game SDK component.

### Controller input

- `GamepadSwitcherScript` is active and enabled in `level0`.
- `InputManagerScript` and `InputDeviceScript` are also active on `Main Camera`.
- `ControllerTestScript` exists in the scene but is attached to an inactive `ControllerTestPanel` GameObject.
- The managed call-site scan shows `GamepadSwitcherScript` uses Unity Input System's `Gamepad.current` and legacy joystick-name queries.
- The `UseAndroidInputs()` method body only logs a message; it is not a completed Android input implementation.

This makes the Unity Input System surface a first-scene priority. The scene inventory does not prove that Android controller mapping is implemented.

### Selenium / YouTube chat

There is no `YouTubeChat` MonoBehaviour in `level0` or `level1`. The active `YouTubeCheckScript` is a separate component and is not the Selenium browser automation class. The 34 direct Selenium/WebDriver call sites from the managed scan all belong to `YouTubeChat`.

This lowers Selenium/Firefox priority for the first two scenes, but does not prove the feature is absent from later scenes.

### XInput / rumble

There is no `HNS.Rumble`, `VibrationScript`, or `IntroScript` component in `level0` or `level1`. The managed scan found XInput state/vibration calls in these and other gameplay scripts, so the XInput boundary remains relevant for later scenes. It is not currently evidenced as a component in these two scene files.

## What is in level1

The `level1` scene has 30 MonoBehaviour objects. Relevant components include:

- `WelcomeScript` on active GameObject `WelcomeScene`;
- `JsonScript` on active GameObject `JSON`;
- `PostProcessingBehaviour` on active GameObject `Camera`;
- UI objects including `WelcomeToYandereSimulator` and `PressAnyButtonToBegin`.

No `DiscordRPC`, `GamepadSwitcherScript`, `YouTubeChat`, or `HNS.Rumble` component was found in this scene file.

## Technical method and limitations

1. The workflow downloads UnityDataTool 2.4.0 and verifies the published Linux x64 release SHA-256 before running it.
2. UnityDataTool `sf header` and `sf metadata` inspect `level0`, `level1`, `globalgamemanagers`, and `globalgamemanagers.assets`.
3. UnityDataTool `analyze` cannot build its object/reference database because these Player files have no embedded TypeTrees; the workflow records this limitation.
4. UnityPy 1.25.4 loads the five supplied SerializedFiles and enumerates scene objects.
5. For each MonoBehaviour, the scanner calls `parse_monobehaviour_head()` to read the built-in header, follows `m_Script`, and reads the referenced MonoScript's class, namespace and assembly names.
6. The scanner records the component's GameObject name, GameObject active flag and Behaviour enabled flag.

No custom MonoBehaviour fields were decoded. The UnityPy TypeTreeGenerator path was deliberately not used for this first inventory; UnityPy's issue tracker records an alignment issue in generated MonoBehaviour TypeTrees, so full custom-field parsing needs a separate validation step.

The workflow and scanner do not modify game files. The generated artifact contains metadata JSON, a scene script CSV, object-type counts, a summary and any parse errors. It does not contain extracted game assets or decompiled source.

## Next steps

1. Finish validating the exact `DiscordRPC.Start()` branch operand against the decoded non-empty application ID and enabled rich-presence flag.
2. Check whether the complete original game package contains `discord_game_sdk.dll`; the current archive set is incomplete.
3. Plan an explicit Android compatibility response for Discord Game SDK (e.g. optional unsupported feature with a clean no-op path); do not silently claim Discord support.
4. Implement/test the Unity Input System calls used by the active `GamepadSwitcherScript`, `InputManagerScript` and `InputDeviceScript`.
5. Obtain a complete Player Data archive before concluding that later scenes do not contain additional dependencies.
6. Revisit XInput and Selenium when later scene inventories are available.

**Integrity statement:** counts and scene membership above come from the successful GitHub Actions artifact. Native-library reachability is an inference combining serialized component presence with static IL call sites; no game runtime was launched.
