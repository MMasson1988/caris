@echo off
REM Script d'installation des dépendances Python pour le projet CARIS-MEAL-APP
REM Usage: install_venv.bat

setlocal enabledelayedexpansion

echo ======================================
echo CARIS MEAL APP - Installation Python
echo ======================================

set VENV_NAME=venv
set PYTHON_CMD=python

REM Fonction pour afficher les messages
echo [INFO] Vérification de Python...

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python n'est pas installé. Veuillez installer Python 3.8+ d'abord.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python détecté: !PYTHON_VERSION!

REM Supprimer l'ancien venv s'il existe
if exist "%VENV_NAME%" (
    echo [INFO] Suppression de l'ancien environnement virtuel...
    rmdir /s /q "%VENV_NAME%"
)

REM Créer un nouvel environnement virtuel
echo [INFO] Création de l'environnement virtuel...
python -m venv "%VENV_NAME%"
if errorlevel 1 (
    echo [ERROR] Échec de la création de l'environnement virtuel
    pause
    exit /b 1
)

REM Activer l'environnement virtuel
echo [INFO] Activation de l'environnement virtuel...
call "%VENV_NAME%\Scripts\activate.bat"

echo [SUCCESS] Environnement virtuel activé

REM Mettre à jour pip
echo [INFO] Mise à jour de pip...
python -m pip install --upgrade pip

REM Installer les dépendances depuis requirements.txt
echo [INFO] Installation des dépendances depuis requirements.txt...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo [WARNING] Certaines dépendances ont échoué. Installation manuelle...
    
    REM Installation manuelle des packages critiques
    echo [INFO] Installation des packages critiques...
    python -m pip install pandas numpy openpyxl xlsxwriter matplotlib seaborn plotly pymysql sqlalchemy python-dateutil python-dotenv
)

echo [SUCCESS] Installation terminée

REM Afficher le résumé
echo.
echo ======================================
echo ✅ INSTALLATION TERMINÉE AVEC SUCCÈS
echo ======================================
echo.
echo Packages installés:
echo - pandas: Manipulation de données
echo - numpy: Calculs numériques
echo - openpyxl, xlsxwriter: Lecture/écriture Excel
echo - matplotlib, seaborn, plotly: Visualisation
echo - pymysql, sqlalchemy: Base de données
echo - python-dateutil: Gestion des dates
echo - python-dotenv: Variables d'environnement
echo.
echo Pour activer l'environnement virtuel:
echo   venv\Scripts\activate
echo.
echo Pour lancer votre script:
echo   python rapport.py
echo.
echo Pour désactiver l'environnement:
echo   deactivate
echo.
echo ======================================

pause