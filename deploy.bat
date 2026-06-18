@echo off
setlocal
set REGISTRY=kdeskregistry.azurecr.io
set RG=KPOS
set APP=kpos

for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set DATE=%%c%%b%%a
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set TIME=%%a%%b
set TAG=%DATE%-%TIME: =%
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
