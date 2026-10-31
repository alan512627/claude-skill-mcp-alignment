# One-command sync for Windows PowerShell 5.1+. Safe to re-run (it is also the "sync" command).
#   irm https://raw.githubusercontent.com/alan512627/claude-skill-mcp-alignment/main/setup.ps1 | iex
$ErrorActionPreference = 'Stop'
$RepoUrl = if ($env:REPO_URL) { $env:REPO_URL } else { 'https://github.com/alan512627/claude-skill-mcp-alignment.git' }
$Dir = if ($env:CLAUDE_SYNC_DIR) { $env:CLAUDE_SYNC_DIR } else { Join-Path $HOME 'claude-skill-mcp-alignment' }
$ClaudeDir = if ($env:CLAUDE_DIR) { $env:CLAUDE_DIR } else { Join-Path $HOME '.claude' }
$Begin = '<!-- claude-sync:begin -->'; $End = '<!-- claude-sync:end -->'
$utf8 = New-Object System.Text.UTF8Encoding($false)

if (Test-Path (Join-Path $Dir '.git')) { git -C $Dir pull --ff-only } else { git clone $RepoUrl $Dir }
New-Item -ItemType Directory -Force (Join-Path $Dir 'memory'), (Join-Path $ClaudeDir 'skills') | Out-Null
$mem = Join-Path $Dir 'memory\MEMORY.md'
if (-not (Test-Path $mem)) { [IO.File]::WriteAllText($mem, '', $utf8) }

# managed block in ~/.claude/CLAUDE.md (replace between markers, else append)
$f = Join-Path $ClaudeDir 'CLAUDE.md'
$old = if (Test-Path $f) { [IO.File]::ReadAllText($f) } else { '' }
$pattern = '(?s)' + [regex]::Escape($Begin) + '.*?' + [regex]::Escape($End) + '\r?\n?'
$old = [regex]::Replace($old, $pattern, '')
$block = [IO.File]::ReadAllText((Join-Path $Dir 'claude-block.md'))
[IO.File]::WriteAllText($f, $old + $Begin + "`n" + $block + "`n" + $End + "`n", $utf8)

# install skills (every top-level folder with SKILL.md)
Get-ChildItem $Dir -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') } | ForEach-Object {
  $dest = Join-Path $ClaudeDir ('skills\' + $_.Name)
  if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
  Copy-Item $_.FullName $dest -Recurse
  Write-Host "skill: $($_.Name)"
}
Write-Host 'done. Restart Claude Code so CLAUDE.md and skills reload.'
