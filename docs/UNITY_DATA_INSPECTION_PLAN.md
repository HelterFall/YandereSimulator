# Следующий технический шаг: точная версия Unity и разбор SerializedFiles

**Дата:** 2026-11-17  
**Основа:** God report `unity-game-analysis.json` из этого репозитория + официальная документация UnityDataTool + документация открытых библиотек.  
**Статус:** план и техническая проверка источников; сами бинарные игровые файлы командами UnityDataTool здесь ещё не запускались.

## 1. Самая полезная находка: UnityDataTool умеет извлекать версию Unity из metadata

В God-отчёте поле `unityVersion` равно `null`. Это не доказывает, что версия отсутствует: God сейчас ищет строку эвристически в ограниченном участке файла.

В официальной документации UnityDataTool команда:

```bash
UnityDataTool sf header YandereSimulator_Data/globalgamemanagers
UnityDataTool sf metadata YandereSimulator_Data/globalgamemanagers --format json
```

может показать:
- формат и версию SerializedFile;
- Unity Version;
- Target Platform;
- наличие TypeTree;
- число TypeTree-записей и другие метаданные.

Это приоритетный способ перепроверить Unity version, потому что он читает структурированные metadata, а не ищет случайную строку. Команда `metadata` в документации требует SerializedFile version 19 или новее. Если файл не распознаётся, сначала проверить `header` и не делать выводов о версии игры.

Источник: https://github.com/Unity-Technologies/UnityDataTools/blob/main/Documentation/command-serialized-file.md

## 2. Какие игровые файлы проверять первыми

По God JSON (snapshot от 2026-11-15) подтверждены следующие пути и размеры:

| Файл | Размер | Зачем проверять |
|---|---:|---|
| `YandereSimulator_Data/globalgamemanagers` | 36,066,836 B | Первая попытка получить Unity version, target platform и общие metadata |
| `YandereSimulator_Data/globalgamemanagers.assets` | 1,242,452 B | Небольшой SerializedFile для проверки парсера и ссылок |
| `YandereSimulator_Data/level0` | 57,668 B | Маленький файл для быстрой проверки заголовка, объектов и внешних ссылок |
| `YandereSimulator_Data/level1` | 19,412 B | Ещё один маленький контрольный файл |
| `YandereSimulator_Data/sharedassets0.assets` | 17,015,524 B | Список объектов и зависимостей |
| `YandereSimulator_Data/resources.assets` | 1,637,709,288 B | Большой файл ресурсов; не начинать с полного дампа |
| `YandereSimulator_Data/level12` | 357,392,828 B | Большой уровень; отложить до успешного теста на маленьких файлах |

Размеры взяты из инвентаризации God, а не измерены повторно по ZIP. Наличие пути в отчёте не означает, что содержимое файла уже было разобрано.

## 3. Команды UnityDataTool для поэтапной проверки

Запускать на распакованной папке игры на Windows/macOS/Linux, где есть подходящая сборка UnityDataTool.

### Шаг A — только заголовки (дёшево и быстро)

```bash
UnityDataTool sf header YandereSimulator_Data/level0
UnityDataTool sf header YandereSimulator_Data/level1
UnityDataTool sf header YandereSimulator_Data/globalgamemanagers
```

Сохранить версию формата, размер файла, размер metadata, data offset и endianness.

### Шаг B — metadata и версия

```bash
UnityDataTool sf metadata YandereSimulator_Data/globalgamemanagers --format json
UnityDataTool sf metadata YandereSimulator_Data/level0 --format json
```

Сравнить `unityVersion` и `targetPlatform` между файлами. Если значение версии равно `0.0.0`, документация предупреждает, что Unity version могла быть удалена из AssetBundle; это не то же самое, что подтверждённая версия Player build.

### Шаг C — объекты и связи только после успешного header/metadata

```bash
UnityDataTool sf objectlist YandereSimulator_Data/level0 --format json
UnityDataTool sf externalrefs YandereSimulator_Data/level0 --format json
UnityDataTool sf objectlist YandereSimulator_Data/sharedassets0.assets --format json
```

Это позволит получить список типов объектов, ID, offsets/sizes и внешние зависимости. Не нужно сразу делать полный текстовый dump многогигабайтной папки.

### Шаг D — масштабирование

Только после проверки маленьких файлов:
- проверить `globalgamemanagers.assets`;
- затем `sharedassets0.assets`;
- затем один крупный файл уровня;
- в последнюю очередь `resources.assets` и остальные большие ресурсы.

У UnityDataTool есть команда `analyze`, которая создаёт SQLite базу из SerializedFiles и Unity Archives. Её лучше запускать на выбранной небольшой подвыборке, а не на всей игре с первого раза.

Документация:
- https://github.com/Unity-Technologies/UnityDataTools/blob/main/Documentation/unitydatatool.md
- https://github.com/Unity-Technologies/UnityDataTools/blob/main/Documentation/command-analyze.md

## 4. Ограничение UnityDataTool для RamenUnity

UnityDataTool — инструмент анализа данных, не игровой runtime.

Текущий upstream README описывает:
- .NET 9.0;
- готовые self-contained CLI сборки Windows, macOS Apple Silicon и Linux;
- нативную библиотеку `UnityFileSystemApi`;
- C# библиотеки `UnityBinaryFormat`, `UnityDataModels` и другие компоненты.

В README не заявлена готовая Android ARM64 сборка. Поэтому сейчас безопасное решение:
1. использовать UnityDataTool как внешний исследовательский инструмент на ПК, когда он появится;
2. использовать его выходные JSON/SQLite как эталон для проверки собственных результатов;
3. отдельно изучить managed-парсер `UnityBinaryFormat` и зависимости, прежде чем решать, можно ли переносить части в Android;
4. не пытаться встроить весь CLI или desktop native `UnityFileSystemApi` в Android без отдельной проверки ABI и лицензии.

Важное ограничение совместимости: README говорит, что `UnityFileSystemApi` backward-compatible, но не forward-compatible — версия библиотеки может не прочитать данные, созданные более новой версией Unity, чем она сама поддерживает. При отказе инструмента нужно проверить версию его библиотеки, а не сразу объявлять формат игры неподдерживаемым.

Источник: https://github.com/Unity-Technologies/UnityDataTools

## 5. Дополнительное подтверждение AssetsTools.NET и Mono.Cecil

### AssetsTools.NET

Репозиторий описывает библиотеку .NET для чтения и изменения Unity asset/bundle файлов; лицензия в репозитории обозначена как MIT.

- https://github.com/nesrak1/AssetsTools.NET

Решение: держать как второй кандидат для сравнительной проверки форматов. Не включать в Android runtime до теста на конкретных SerializedFiles игры и проверки всех зависимостей.

### Mono.Cecil

Репозиторий описывает библиотеку для чтения, создания и изменения .NET CIL сборок. Важное преимущество: анализировать бинарные сборки можно без загрузки их через Reflection в исполняемую среду.

- https://github.com/jbevain/cecil

Решение: это кандидат для отдельного read-only аудита `Assembly-CSharp.dll`, чтобы собрать:
- список Assembly References;
- типы и методы, обращающиеся к UnityEngine;
- P/Invoke и имена импортируемых DLL;
- ссылки на Windows-only API;
- используемые UnityEngine модули.

Cecil не запускает CIL и не реализует UnityEngine. Не менять игровые DLL на этом этапе.

## 6. Важное уточнение по .NET for Android

Документация Microsoft для .NET for Android подтверждает, что Android-приложение может содержать managed assemblies, а параметр `AndroidEnablePreloadAssemblies` управляет предварительной загрузкой сборок приложения.

- https://learn.microsoft.com/en-us/dotnet/android/building-apps/build-properties

Но это **не доказательство**, что произвольную внешнюю Unity DLL можно безопасно и совместимо подгрузить в приложение или что runtime будет совместим с Unity Mono profile конкретной игры. Это отдельный эксперимент, а не готовое решение. Нужно проверить target framework, assembly identity, базовые библиотеки, динамическую загрузку, Android ограничения и Unity native calls.

## 7. Обновлённый приоритет работ

1. **Подтвердить версию Unity через SerializedFile metadata** — наивысший приоритет.
2. **Снять object list и external refs с level0** — маленький контрольный набор.
3. **Сделать read-only отчёт Mono.Cecil по Assembly-CSharp.dll** — получить реальную карту Unity API и P/Invoke.
4. **Выбрать Android managed runtime только после проверки профиля сборок**.
5. **Проверить AssetsTools.NET как альтернативный парсер**.
6. **Не писать свой SerializedFile parser, пока сравнение готовых библиотек не выявит конкретную недостающую возможность**.

## 8. Что пока не подтверждено

- UnityDataTool не запускался на игровых файлах в рамках этого исследования.
- Unity version конкретной сборки всё ещё не подтверждена: God вернул `null`, а документация инструмента лишь описывает способ проверки.
- Ни AssetsTools.NET, ни Mono.Cecil ещё не добавлены в RamenUnity.
- Ни один managed runtime ещё не проверен на реальном ARM64 устройстве с игровыми DLL.
- Наличие Mono DLL в папке игры не доказывает, что именно эти Windows-библиотеки пригодны для Android.

## Источники

1. UnityDataTool SerializedFile commands: https://github.com/Unity-Technologies/UnityDataTools/blob/main/Documentation/command-serialized-file.md
2. UnityDataTool README and architecture: https://github.com/Unity-Technologies/UnityDataTools
3. UnityDataTool analyze command: https://github.com/Unity-Technologies/UnityDataTools/blob/main/Documentation/command-analyze.md
4. AssetsTools.NET: https://github.com/nesrak1/AssetsTools.NET
5. Mono.Cecil: https://github.com/jbevain/cecil
6. .NET for Android build properties: https://learn.microsoft.com/en-us/dotnet/android/building-apps/build-properties
