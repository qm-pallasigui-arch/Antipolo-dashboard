# Preview by default. Use -Apply to remove only disposable local test output.
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$prefix = $workspace.TrimEnd('\') + '\'
$targets = @(Get-ChildItem -LiteralPath $workspace -Force -Directory | Where-Object {
    $_.Name -in @('.artifacts', '.pytest_cache', '__pycache__', '.test-confirm-fix') -or
    $_.Name -like '.test-reconciliation-*' -or $_.Name -like '.pytest-tmp-*' -or
    $_.Name -like 'pytest-cache-files-*'
})
foreach ($subdir in @('dashboard', 'tests', 'tools')) {
    $directory = Join-Path $workspace $subdir
    $targets += @(Get-ChildItem -LiteralPath $directory -Directory -Recurse -Force -Filter '__pycache__')
}
# Check every target before deleting anything. Never clean app state or environments.
$total = 0L
foreach ($target in $targets) {
    $absolute = [IO.Path]::GetFullPath($target.FullName)
    if (-not $absolute.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Outside workspace: $absolute"
    }
    if ($target.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing linked directory: $absolute"
    }
    $relative = $absolute.Substring($prefix.Length).Replace('\', '/')
    $tracked = @(git -C $workspace ls-files -- "$relative/")
    if ($LASTEXITCODE -ne 0 -or $tracked.Count -gt 0) {
        throw "Cannot clean directory containing tracked files: $relative"
    }
    $entries = @(Get-ChildItem -LiteralPath $absolute -Recurse -Force)
    if (@($entries | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count) {
        throw "Refusing directory containing links: $relative"
    }
    $bytes = ($entries | Where-Object { -not $_.PSIsContainer } | Measure-Object Length -Sum).Sum
    $total += [long]$bytes
    Write-Output ('{0,9:N2} MB  {1}' -f ($bytes / 1MB), $relative)
}
if ($Apply) {
    foreach ($target in $targets) {
        Remove-Item -LiteralPath $target.FullName -Recurse -Force
    }
    Write-Output ('Removed {0} directories; {1:N2} MB of file contents.' -f $targets.Count, ($total / 1MB))
} else {
    Write-Output ('Preview: {0} directories; {1:N2} MB. Run with -Apply to remove.' -f $targets.Count, ($total / 1MB))
}
