# 从 detail-conf-init.sql 提取 18 个 conf_json 生成 classpath 兜底 JSON
# 脚本内避免直接写中文路径（PS5.1 对无 BOM UTF-8 脚本按 ANSI 解析），用通配符定位
$ErrorActionPreference = 'Stop'
$sqlFile = Get-ChildItem -Path "c:\Users\caoxiaolin\Desktop\openlibing\openlibing-docs\spec\openlibing-ops\task_design" -Recurse -Filter "detail-conf-init.sql" | Select-Object -First 1
if (-not $sqlFile) { throw "detail-conf-init.sql not found" }
$outDir = "c:\Users\caoxiaolin\Desktop\openlibing\openlibing-ops\src\main\resources\security\detail-conf"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$content = [System.IO.File]::ReadAllText($sqlFile.FullName, [System.Text.Encoding]::UTF8)
$pattern = "VALUES \('(\w+)',\s*\r?\n'\{(.+?)\}',\s*\r?\n"
$regex = [regex]::new($pattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
$ms = $regex.Matches($content)
Write-Host "found $($ms.Count) conf rows"
foreach ($m in $ms) {
    $code = $m.Groups[1].Value
    $json = "{" + $m.Groups[2].Value + "}"
    $file = Join-Path $outDir "$code.json"
    [System.IO.File]::WriteAllText($file, $json, [System.Text.Encoding]::UTF8)
    Write-Host "$code.json ($($json.Length) chars)"
}
