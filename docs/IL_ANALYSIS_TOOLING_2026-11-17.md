# IL method-body analysis tooling — 2026-11-17

**Target:** Yandere Simulator, Unity `6000.2.8f1`, Mono-managed assemblies  
**Purpose:** choose a reliable way to inspect method bodies and trace feature call sites after the metadata-only audit.  
**Status:** tool research and workflow design only. No method-body call graph has been produced yet.

## Why this is the next step

The [managed assembly dependency audit](ASSEMBLY_DEPENDENCY_AUDIT_2026-11-17.md) established assembly references, TypeRef/MemberRef metadata and P/Invoke declarations across 143 managed DLLs. Metadata references do not show whether a method is called, when it is called, or whether it lies on the path to the first scene.

The next analysis must inspect CIL method bodies and resolve call/callvirt/newobj/function-pointer operands back to method and type names. It should start with game-owned code and the concrete boundaries already found:

- Discord calls in `Assembly-CSharp-firstpass.dll`;
- XInput calls through `XInputDotNetPure.dll`;
- Selenium/WebDriver references in `Assembly-CSharp.dll`;
- Unity AMD/NVIDIA module imports;
- calls from game startup/initialization methods into Unity APIs.

A static call graph is still only an approximation: reflection, delegates, event registration, native callbacks, runtime-generated code and conditional branches can hide or alter reachability. A trace on a running compatible player would be stronger evidence, but is not currently available.

## Tool comparison

### 1. ICSharpCode.Decompiler (ILSpy engine) — preferred first evaluation

- Project: https://github.com/icsharpcode/ILSpy
- Package documentation: https://github.com/icsharpcode/ILSpy/blob/master/ICSharpCode.Decompiler/PackageReadme.md
- Architecture: https://github.com/icsharpcode/ILSpy/blob/master/doc/DecompilerArchitecture.html
- License: MIT (verify the exact release and transitive dependencies before redistribution).

The ILSpy repository describes `ICSharpCode.Decompiler` as the decompiler engine used by ILSpy and documents using it as a library. Its APIs can decompile a specific method or type, and its internal IL reader processes method bodies. This is a strong candidate for producing readable C# from selected game methods and manually checking call paths.

**Use:** development-time desktop/offline analysis, not a dependency in the Android runtime. Start with one or two named methods and confirm that the exact Unity/Mono-produced assemblies load correctly.

**Caution:** the package's current target frameworks and dependencies must be checked against the chosen analysis host. Its AOT/trimming notes do not mean it is suitable for embedding in RamenUnity or Android.

### 2. Mono.Cecil — preferred metadata and instruction-query API

- Project: https://github.com/jbevain/cecil
- API overview: https://www.mono-project.com/docs/tools+libraries/libraries/Mono.Cecil/faq/

Mono.Cecil exposes assembly/module/type/method definitions and CIL instructions through method bodies. It is well suited to a small deterministic report generator that scans selected method bodies for call operands, P/Invoke declarations and referenced APIs.

**Use:** evaluate as the simplest way to produce a machine-readable call-site inventory, if a compatible .NET/Mono host can be provisioned.

**Caution:** the cited FAQ is older documentation; pin a current release and verify its API, target framework and ability to read this exact Unity assembly set. Cecil reads and writes assemblies; do not rewrite game files during this audit.

### 3. .NET System.Reflection.Metadata — lower-level alternative

ILSpy's documentation and source show use of the .NET metadata APIs to retrieve method definitions and method bodies. The lower-level API exposes the IL byte stream, but decoding instruction operands and resolving metadata tokens requires more implementation work than a library with an instruction model.

**Use:** only if we need a small custom read-only scanner with tightly controlled dependencies. Do not repeat the custom PE/CLI parser effort unless there is a concrete need.

## Recommended workflow

1. Preserve the existing metadata audit as the baseline; do not reinterpret a declared reference as proof of runtime use.
2. Obtain a working local analysis environment with a current .NET SDK or another supported host. Record tool versions and hashes.
3. Run a read-only inspection on `Assembly-CSharp.dll` and `Assembly-CSharp-firstpass.dll`; confirm method counts and successfully decode a sample of method bodies.
4. Enumerate all methods that contain call-like instructions. Resolve tokens to declaring type, method name and assembly. Preserve unresolved tokens as unresolved rather than guessing.
5. Prioritize methods related to startup and first-scene initialization. Follow direct calls within the game assemblies, then record external calls by subsystem.
6. Specifically locate call sites for Discord, XInput, Selenium/WebDriver, and AMD/NVIDIA interop. Distinguish direct calls from mere TypeRef/MemberRef presence.
7. Record evidence categories separately:
   - **Observed in method body:** a call instruction references the method/member.
   - **Reachable in static approximation:** found by traversing known direct calls from a selected root.
   - **Runtime observed:** confirmed during execution on a compatible player.
   - **Unknown:** reflection, delegate, native callback, unresolved token or dynamic path prevents a conclusion.
8. Only after this audit decide whether a feature can be deferred for the first scene. Do not remove assemblies or patch methods based only on a static guess.

## Output schema for the eventual report

For each call site, capture:

| Field | Meaning |
|---|---|
| Caller assembly/type/method | Exact source method containing the instruction |
| IL offset and opcode | Position and call form (`call`, `callvirt`, `newobj`, etc.) |
| Target assembly/type/method | Resolved target, or explicit unresolved marker |
| Target category | Game code, Unity API, framework, P/Invoke/native boundary |
| Root/reachability note | Why this method was selected and whether a static path was found |
| Confidence | Metadata-only, body-observed, static-reachable, or runtime-observed |

The report should include the tool version, input file hashes, decode failures and unresolved references so another person can reproduce it.

## Implemented scanner and CI execution (2026-11-17)

A first implementation has now been added to the repository:

- Scanner project: `tools/ManagedCallAudit/ManagedCallAudit.csproj`
- Scanner source: `tools/ManagedCallAudit/Program.cs`
- Workflow: `.github/workflows/managed-call-audit.yml`

The scanner uses Mono.Cecil 0.11.6 and reads the method bodies of `Assembly-CSharp.dll`, `Assembly-CSharp-firstpass.dll` and `XInputDotNetPure.dll`. It inventories `call`, `callvirt`, `newobj`, `jmp`, `ldftn` and `ldvirtftn` instructions, writing a complete call-site CSV and a filtered CSV for Discord, XInput, Selenium/WebDriver, Firefox and AMD/NVIDIA native boundaries. It does not attempt to infer startup reachability.

The workflow extracts `Managed.zip` on a GitHub-hosted runner, runs the scanner and uploads only the CSV/summary report as a short-lived Actions artifact. It does not upload decompiled source code.

Execution status at the time of this update:

- Run `43979007593` failed because the shell path-discovery command accidentally appended a literal newline escape to the extracted directory name. The ZIP download, extraction and DLL discovery steps succeeded.
- The workflow path handling was corrected to use `find -print -quit` plus `dirname`.
- Corrected run `43979084371` has started; its extraction step completed and the scanner step is still running. A successful report is **not yet confirmed**.
- The initial run exposed an environment/automation issue, not a game compatibility result. No conclusions about the game's call paths should be drawn until the report artifact exists and has been inspected.

## Remaining limits

The previous metadata parser and uploaded ZIPs were available in the earlier analysis workspace, but they are not present in the current execution workspace. The repository contains the audit report and archive inventory; the binary ZIP contents cannot be treated as freshly re-read in this step. Therefore **no new IL body scan, decompilation, call-site list or startup call graph is claimed here**.

The immediate practical next action is to restore access to the existing `Managed.zip` binary in an analysis environment, then test ILSpy or Mono.Cecil against the two game assemblies. No re-upload should be requested unless the existing repository copy cannot be retrieved by a suitable binary-capable workflow.

## Sources

- ILSpy repository and project overview: https://github.com/icsharpcode/ILSpy
- ICSharpCode.Decompiler package README: https://github.com/icsharpcode/ILSpy/blob/master/ICSharpCode.Decompiler/PackageReadme.md
- ILSpy decompiler architecture: https://github.com/icsharpcode/ILSpy/blob/master/doc/DecompilerArchitecture.html
- Mono.Cecil FAQ: https://www.mono-project.com/docs/tools+libraries/libraries/Mono.Cecil/faq/
- ECMA-335 CLI specification: https://ecma-international.org/publications-and-standards/standards/ecma-335/

**Integrity note:** this is a tooling decision record, not a claim that ILSpy/Cecil has been run against the target assemblies. No runtime compatibility or first-scene readiness is established.
