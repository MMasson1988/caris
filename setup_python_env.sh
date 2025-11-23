#!/usr/bin/env bash
set -euo pipefail

echo "=== CONFIGURATION ENVIRONNEMENT PYTHON POUR LE PROJET MUSO ==="

########################################
# 1. Vérifier que Python3 est installé
########################################

if ! command -v python3 &> /dev/null; then
    echo "Erreur: Python3 n'est pas installé"
    exit 1
fi

echo "Python3 version: $(python3 --version)"

########################################
# 2. Créer/recréer venv Python
########################################

echo "=== Création virtualenv Python 'venv' ==="

# Supprimer l'ancien venv s'il existe
if [ -d "venv" ]; then
    echo "Suppression de l'ancien environnement virtuel..."
    rm -rf venv
fi

# Créer le nouvel environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

echo "Environnement virtuel activé: $VIRTUAL_ENV"

# Mettre à jour pip
pip install --upgrade pip

# Installer les packages Python requis
echo "Installation des packages Python..."
pip install \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    plotly \
    itables \
    ipython \
    openpyxl \
    xlsxwriter \
    pymysql \
    sqlalchemy \
    selenium \
    webdriver-manager \
    python-dotenv \
    python-dateutil

# Créer un fichier requirements.txt
pip freeze > requirements.txt

echo "=== Installation Python terminée ==="
echo "Environnement virtuel créé dans: ./venv/"
echo "Fichier requirements.txt mis à jour"
echo ""
echo "Pour activer l'environnement virtuel:"
echo "  source venv/bin/activate"
echo ""
echo "Pour désactiver l'environnement virtuel:"
echo "  deactivate"