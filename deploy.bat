@echo off
setlocal
set REGISTRY=kdeskregistry.azurecr.io
set RG=KPOS
set APP=kpos

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set TAG=%DT:~0,8%-%DT:~8,4%
set IMAGE=%REGISTRY%/kpos:%TAG%

echo =^> Tag: %TAG%

echo =^> Logging in to Azure Container Registry...
az acr login --name kdeskregistry
if errorlevel 1 goto :error

echo =^> Building Docker image (no cache)...
docker build --no-cache -t %IMAGE% -t %REGISTRY%/kpos:latest .
if errorlevel 1 goto :error

echo =^> Pushing image to registry...
docker push %IMAGE%
docker push %REGISTRY%/kpos:latest
if errorlevel 1 goto :error

echo =^> Updating Container App to %TAG%...
az containerapp update --resource-group %RG% --name %APP% --image %IMAGE%
if errorlevel 1 goto :error

echo.
echo Done. kpos is live at https://kpos.kramerav.com
goto :end

:error
echo.
echo Deployment failed - check output above.
exit /b 1

:end
