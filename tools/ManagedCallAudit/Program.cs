using System.Reflection;
using System.Text;
using Mono.Cecil;
using Mono.Cecil.Cil;

if (args.Length < 2)
{
    Console.Error.WriteLine("Usage: ManagedCallAudit <managed-directory> <output-directory>");
    return 2;
}

var input = Path.GetFullPath(args[0]);
var output = Path.GetFullPath(args[1]);
Directory.CreateDirectory(output);
var allRows = new List<string>();
var featureRows = new List<string>();
var errors = new List<string>();
// Static inventory only: this tool does not infer startup reachability or execute game code.
var parsed = 0;

static IEnumerable<TypeDefinition> AllTypes(IEnumerable<TypeDefinition> types)
{
    foreach (var type in types)
    {
        yield return type;
        foreach (var nested in AllTypes(type.NestedTypes))
            yield return nested;
    }
}

static string Csv(string? value) => "\"" + (value ?? "").Replace("\"", "\"\"") + "\"";

var headers = "caller_assembly,caller_type,caller_method,il_offset,opcode,target_assembly,target_type,target_method,target_signature";
allRows.Add(headers);
featureRows.Add(headers);

foreach (var file in Directory.EnumerateFiles(input, "*.dll", SearchOption.AllDirectories))
{
    AssemblyDefinition asm;
    try
    {
        asm = AssemblyDefinition.ReadAssembly(file, new ReaderParameters
        {
            ReadingMode = ReadingMode.Immediate,
            InMemory = true,
            ReadSymbols = false
        });
    }
    catch (Exception ex)
    {
        errors.Add($"{Path.GetFileName(file)}: {ex.GetType().Name}: {ex.Message}");
        continue;
    }

    using (asm)
    {
        parsed++;
        var assemblyName = asm.Name.Name;
        if (assemblyName != "Assembly-CSharp" &&
            assemblyName != "Assembly-CSharp-firstpass" &&
            assemblyName != "XInputDotNetPure")
            continue;

        foreach (var type in AllTypes(asm.MainModule.Types))
        foreach (var method in type.Methods)
        {
            if (!method.HasBody) continue;
            foreach (var ins in method.Body.Instructions)
            {
                if (ins.Operand is not MethodReference target) continue;
                var op = ins.OpCode.Code;
                if (op is not (Code.Call or Code.Callvirt or Code.Newobj or Code.Jmp or Code.Ldftn or Code.Ldvirtftn))
                    continue;

                var targetAsm = target.DeclaringType.Scope switch
                {
                    AssemblyNameReference anr => anr.Name,
                    ModuleDefinition md => md.Assembly?.Name.Name ?? "",
                    ModuleReference mr => mr.Name,
                    _ => target.DeclaringType.Scope?.Name ?? ""
                };
                var targetType = target.DeclaringType.FullName;
                var targetMethod = target.Name;
                var row = string.Join(",", new[]
                {
                    Csv(assemblyName), Csv(type.FullName), Csv(method.FullName),
                    Csv($"0x{ins.Offset:X4}"), Csv(ins.OpCode.Name),
                    Csv(targetAsm), Csv(targetType), Csv(targetMethod), Csv(target.FullName)
                });
                allRows.Add(row);

                var searchable = $"{targetAsm} {targetType} {targetMethod} {method.FullName}";
                if (new[] { "discord", "xinput", "gamepad", "selenium", "webdriver", "firefox",
                             "amdunityplugin", "nvunityplugin" }
                    .Any(term => searchable.Contains(term, StringComparison.OrdinalIgnoreCase)))
                    featureRows.Add(row);
            }
        }
    }
}

File.WriteAllLines(Path.Combine(output, "game_callsites.csv"), allRows, new UTF8Encoding(false));
File.WriteAllLines(Path.Combine(output, "feature_callsites.csv"), featureRows, new UTF8Encoding(false));

var summary = new StringBuilder()
    .AppendLine("# Managed CIL call-site scan")
    .AppendLine()
    .AppendLine($"- Managed DLL files parsed: {parsed}")
    .AppendLine($"- Call-like instructions in selected game assemblies: {allRows.Count - 1}")
    .AppendLine($"- Feature-related call sites: {featureRows.Count - 1}")
    .AppendLine($"- DLL parse errors: {errors.Count}")
    .AppendLine("- Selected assemblies: Assembly-CSharp, Assembly-CSharp-firstpass, XInputDotNetPure")
    .AppendLine("- Instruction forms: call, callvirt, newobj, jmp, ldftn, ldvirtftn")
    .AppendLine("- This is a static call-site inventory, not a reachability proof or runtime trace.")
    .ToString();
File.WriteAllText(Path.Combine(output, "SUMMARY.md"), summary + (errors.Count == 0 ? "" : "\n## Parse errors\n\n" + string.Join("\n", errors.Select(e => "- " + e))), new UTF8Encoding(false));

Console.WriteLine(summary);
return 0;
