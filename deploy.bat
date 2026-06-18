@echo off
setlocal
set REGISTRY=kdeskregistry.azurecr.io
set IMAGE=%REGISTRY%/kpos:latest
set RG=KPOS
set APP=kpos

echo =^> Logging in to Azure Container Registry...
az acr login --name kdeskregistry
if errorlevel 1 goto :error

echo =^> Building Docker image...
docker build -t %IMAGE% .
if errorlevel 1 goto :error

echo =^> Pushing image to registry...
docker push %IMAGE%
if errorlevel 1 goto :error

echo =^> Updating Container App...
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
