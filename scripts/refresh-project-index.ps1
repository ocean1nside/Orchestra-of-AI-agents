$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Индекс проекта (SocratiCode / Cursor MCP) ===" -ForegroundColor Cyan
Write-Host "Индекс для быстрого поиска по коду обновляется через MCP-сервер `socraticode` в Cursor."
Write-Host "Из PowerShell напрямую вызвать MCP нельзя — сделайте в Cursor одно из действий:"
Write-Host "  - codebase_update (инкрементально)"
Write-Host "  - codebase_index (полная переиндексация, если нужно)"
Write-Host "  - codebase_watch action=start (авто-обновление при изменениях файлов)"
Write-Host ""
Write-Host "Project path: c:\1CP\orkester_gleba"
Write-Host ""

Write-Host "=== Docker (runtime стек) ===" -ForegroundColor Cyan
Write-Host "Из корня репозитория:"
Write-Host "  docker compose -f infra/docker-compose.dev.yml --profile devtools up -d --build"
Write-Host ""
