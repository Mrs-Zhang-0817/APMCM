param(
    [Parameter(Mandatory = $true)]
    [string]$InputDirectory
)

$ErrorActionPreference = 'Stop'
$root = Get-Item -LiteralPath $InputDirectory
if (-not $root.PSIsContainer) {
    throw "InputDirectory must point to a directory."
}

$files = @(Get-ChildItem -LiteralPath $root.FullName -File -Recurse -Force | Sort-Object FullName)
if ($files.Count -eq 0) {
    Write-Warning "No files found in the input directory."
    return
}

$rootPrefix = $root.FullName.TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
foreach ($file in $files) {
    [PSCustomObject]@{
        RelativePath = $file.FullName.Substring($rootPrefix.Length)
        Bytes        = $file.Length
        SHA256       = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
}
