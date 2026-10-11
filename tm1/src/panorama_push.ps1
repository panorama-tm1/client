param([string]$ParamFile)
$ErrorActionPreference = 'Stop'
$cfg = @{}
foreach ($line in @(Get-Content -LiteralPath $ParamFile -Encoding UTF8)) {
    $i = $line.IndexOf('=')
    if ($i -gt 0) { $cfg[$line.Substring(0, $i).Trim([char]0xFEFF)] = $line.Substring($i + 1) }
}
Remove-Item -LiteralPath $ParamFile -Force
function Write-PushLog([string]$Message) {
    Add-Content -LiteralPath $cfg.LOG_FILE -Value ((Get-Date -Format s) + ' ' + $Message) -Encoding UTF8
}
Set-Content -LiteralPath $cfg.LOG_FILE -Value ((Get-Date -Format s) + ' Panorama push to ' + $cfg.INSTANCE_ID) -Encoding UTF8
$tab = [string][char]9
$quote = [string][char]34

# The .pro and .rux files sit in the data directory, which TI cannot name.
# Candidates: the one set in the Prolog, DataBaseDirectory in the tm1s.cfg of
# the TM1 server that started this script, the logging directory. The right
# one holds the .pro of the running process.
function Find-DataDir {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($cfg.DATA_DIR -ne '') { $candidates.Add($cfg.DATA_DIR) }
    try {
        $proc = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID)
        for ($n = 0; $n -lt 6 -and $proc; $n++) {
            $proc = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $proc.ParentProcessId)
            if ($proc -and $proc.Name -like 'tm1s*.exe') {
                $binDir = Split-Path -Parent $proc.ExecutablePath
                $configDir = $binDir
                if ($proc.CommandLine -match ('-z\s*(?:' + $quote + '([^' + $quote + ']+)' + $quote + '|(\S+))')) {
                    $configDir = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
                }
                $cfgFile = Join-Path $configDir 'tm1s.cfg'
                if (Test-Path -LiteralPath $cfgFile) {
                    foreach ($l in @(Get-Content -LiteralPath $cfgFile)) {
                        if ($l -match '^\s*DataBaseDirectory\s*=\s*(.+?)\s*$') {
                            foreach ($d in $Matches[1].Split(';')) {
                                if ($d -eq '') { continue }
                                if ([IO.Path]::IsPathRooted($d)) { $candidates.Add($d) }
                                else { $candidates.Add((Join-Path $configDir $d)); $candidates.Add((Join-Path $binDir $d)) }
                            }
                        }
                    }
                }
                break
            }
        }
    } catch {
        Write-PushLog ('tm1s.cfg lookup skipped: ' + $_.Exception.Message)
    }
    $candidates.Add($cfg.LOG_DIR)
    foreach ($d in $candidates) {
        if (Test-Path -LiteralPath (Join-Path $d ($cfg.PROCESS_NAME + '.pro'))) { return $d }
    }
    throw ('data directory not found, tried ' + ($candidates -join ', ') + '. Set sDataDir in the Prolog.')
}

function Get-Unquoted([string]$Value) {
    if ($Value.Length -ge 2 -and $Value.StartsWith($quote) -and $Value.EndsWith($quote)) {
        return $Value.Substring(1, $Value.Length - 2).Replace($quote + $quote, $quote)
    }
    return $Value
}

# A .pro file is code,value lines; 572 to 575 give the line count of the
# Prolog, Metadata, Data and Epilog that follow, 562 and 586 the data source.
function Add-ProcessRecords([string]$Path, [string]$Name, $Out) {
    $sections = @{ '572' = 'Prolog'; '573' = 'Metadata'; '574' = 'Data'; '575' = 'Epilog' }
    $lines = @(Get-Content -LiteralPath $Path -Encoding UTF8)
    $type = ''
    $source = ''
    $i = 0
    while ($i -lt $lines.Count) {
        $comma = $lines[$i].IndexOf(',')
        if ($comma -gt 0) {
            $code = $lines[$i].Substring(0, $comma)
            $value = $lines[$i].Substring($comma + 1)
            if ($sections.ContainsKey($code)) {
                $count = [int]$value
                for ($k = 1; $k -le $count; $k++) { $Out.Add('S' + $tab + $Name + $tab + $sections[$code] + $tab + $lines[$i + $k]) }
                $i += $count
            } elseif ($code -eq '562') {
                $type = Get-Unquoted $value
            } elseif ($code -eq '586') {
                $source = Get-Unquoted $value
            }
        }
        $i++
    }
    $Out.Add('T' + $tab + $Name + $tab + $type + $tab + $source)
}

$web = @{ UseBasicParsing = $true; TimeoutSec = 600 }
if ($cfg.PROXY -ne '') { $web.Proxy = $cfg.PROXY; $web.ProxyUseDefaultCredentials = $true }
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $dataDir = Find-DataDir
    Write-PushLog ('Data directory ' + $dataDir)

    # Structure written by the Prolog (C, D, P records), then the rules of
    # each cube and the code of each process.
    $out = New-Object System.Collections.Generic.List[string]
    $cubes = 0
    $processes = 0
    foreach ($record in @(Get-Content -LiteralPath $cfg.STRUCT_FILE -Encoding UTF8)) {
        $record = $record.Trim([char]0xFEFF)
        if ($record -eq '') { continue }
        $out.Add($record)
        $fields = $record.Split([char]9)
        if ($fields[0] -eq 'C') {
            $cubes++
            $rux = Join-Path $dataDir ($fields[1] + '.rux')
            if (Test-Path -LiteralPath $rux) {
                foreach ($ruleLine in @(Get-Content -LiteralPath $rux -Encoding UTF8)) { $out.Add('R' + $tab + $fields[1] + $tab + $ruleLine) }
            }
        } elseif ($fields[0] -eq 'P') {
            $processes++
            $pro = Join-Path $dataDir ($fields[1] + '.pro')
            if (Test-Path -LiteralPath $pro) { Add-ProcessRecords $pro $fields[1] $out }
        }
    }
    $body = [Text.Encoding]::UTF8.GetBytes([string]::Join([string][char]10, $out))
    Write-PushLog ([string]$cubes + ' cubes, ' + $processes + ' processes, ' + [Math]::Round($body.Length / 1KB) + ' KB')

    $url = $cfg.PANORAMA_URL.TrimEnd('/') + '/worker/import/' + [Uri]::EscapeDataString($cfg.INSTANCE_ID)
    $resp = Invoke-RestMethod -Method Post -Uri $url -Headers @{ Authorization = 'Bearer ' + $cfg.TOKEN } -ContentType 'text/plain; charset=utf-8' -Body $body @web
    Write-PushLog ('Import queued, task ' + $resp.taskId + ' (' + $resp.status + ')')
    Set-Content -LiteralPath $cfg.OK_FILE -Value $resp.taskId
} catch {
    $message = $_.Exception.Message
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $message = $message + ' ' + $_.ErrorDetails.Message }
    Write-PushLog ('ERROR ' + $message)
} finally {
    Remove-Item -LiteralPath $cfg.STRUCT_FILE -Force -ErrorAction SilentlyContinue
}
