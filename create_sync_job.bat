@echo off
:: One-time setup: creates an Azure Container Apps Job that runs sync_all daily at 06:00 UTC.
:: Run this once after deploying the new image. Safe to re-run.
setlocal enabledelayedexpansion

set REGISTRY=kdeskregistry.azurecr.io
set RG=KPOS
set APP=kpos
set JOB=kpos-sync

echo =^> Logging in to ACR...
az acr login --name kdeskregistry
if errorlevel 1 goto :error

echo =^> Looking up Container Apps environment...
for /f "delims=" %%e in ('az containerapp show --resource-group %RG% --name %APP% --query "properties.managedEnvironmentId" -o tsv') do set ENV_ID=%%e
if "%ENV_ID%"=="" goto :error
echo    Environment: %ENV_ID%

echo =^> Creating scheduled sync job (daily 06:00 UTC)...
az containerapp job create ^
    --name %JOB% ^
    --resource-group %RG% ^
    --environment "%ENV_ID%" ^
    --trigger-type Schedule ^
    --cron-expression "0 6 * * *" ^
    --replica-timeout 600 ^
    --replica-retry-limit 1 ^
    --replica-completion-count 1 ^
    --parallelism 1 ^
    --image %REGISTRY%/kpos:latest ^
    --registry-server %REGISTRY% ^
    --cpu 0.5 --memory 1.0Gi ^
    --command "python" "manage.py" "sync_all"
if errorlevel 1 (
    echo    Updating existing job image...
    az containerapp job update --name %JOB% --resource-group %RG% --image %REGISTRY%/kpos:latest
)

echo.
echo =^> Copying environment variables from %APP% to %JOB%...
echo    (open Azure Portal ^> Container Apps ^> %APP% ^> Settings ^> Environment variables,
echo     then paste the same values into %JOB% ^> Settings ^> Environment variables)
echo.
echo    Or run this command to copy them via CLI (fill in your actual values):
echo    az containerapp job update --name %JOB% --resource-group %RG% --set-env-vars ^
echo      DB_HOST=your-db-host DB_NAME=your-db-name DB_USER=your-db-user ^
echo      DB_PASSWORD=your-db-password SECRET_KEY=your-secret-key ^
echo      ADFS_TENANT_ID=your-tenant-id
echo.
echo Done. After copying env vars, test with:
echo   az containerapp job start --name %JOB% --resource-group %RG%
echo.
echo View execution logs:
echo   az containerapp job execution list --name %JOB% --resource-group %RG% -o table
goto :end

:error
echo.
echo Failed — check output above. Make sure you ran: az login
exit /b 1

:end
