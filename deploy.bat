@echo off
setlocal
set REGISTRY=kdeskregistry.azurecr.io
set RG=KPOS
set APP=kpos

for /f "delims=" %%i in ('powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd-HHmm'"') do set SUFFIX=r%%i

echo =^> Revision suffix: %SUFFIX%

echo =^> Logging in to Azure Container Registry...
az acr login --name kdeskregistry
if errorlevel 1 goto :error

echo =^> Building Docker image (no cache)...
docker build --no-cache -t %REGISTRY%/kpos:latest .
if errorlevel 1 goto :error

echo =^> Pushing image...
docker push %REGISTRY%/kpos:latest
if errorlevel 1 goto :error

echo =^> Deploying new revision %SUFFIX%...
az containerapp update --resource-group %RG% --name %APP% --image %REGISTRY%/kpos:latest --revision-suffix %SUFFIX%
if errorlevel 1 goto :error

echo.
echo Done. kpos is live at https://kpos.kramerav.com
goto :end

:error
echo.
echo Deployment failed - check output above.
exit /b 1

:end
