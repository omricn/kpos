@echo off
echo Starting Kramer POS Analytics...
echo Open: http://localhost:8001
echo Admin: http://localhost:8001/admin  (admin / admin)
echo.
cd /d %~dp0
python manage.py runserver 8001
