#!/bin/bash

# Script d'installation des dépendances Python pour le projet CARIS-MEAL-APP
# Usage: bash install_venv.sh

set -e  # Arrêter le script en cas d'erreur

echo "======================================"
echo "CARIS MEAL APP - Installation Python"
echo "======================================"

# Variables
VENV_NAME="venv"
PYTHON_CMD="python"

# Fonction pour afficher les messages
print_message() {
    echo ">>> $1"
}

print_error() {
    echo "❌ ERREUR: $1"
}

print_success() {
    echo "✅ $1"
}

# Vérifier si Python est installé
print_message "Vérification de Python..."
if ! command -v python &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        print_error "Python n'est pas installé. Veuillez installer Python 3.8+ d'abord."
        exit 1
    else
        PYTHON_CMD="python3"
    fi
fi

print_success "Python détecté: $($PYTHON_CMD --version)"

# Supprimer l'ancien venv s'il existe
if [ -d "$VENV_NAME" ]; then
    print_message "Suppression de l'ancien environnement virtuel..."
    rm -rf "$VENV_NAME"
fi

# Créer un nouvel environnement virtuel
print_message "Création de l'environnement virtuel..."
$PYTHON_CMD -m venv "$VENV_NAME"

# Activer l'environnement virtuel
print_message "Activation de l'environnement virtuel..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash, Cygwin, etc.)
    source "$VENV_NAME/Scripts/activate"
else
    # Linux/macOS
    source "$VENV_NAME/bin/activate"
fi

print_success "Environnement virtuel activé"

# Mettre à jour pip
print_message "Mise à jour de pip..."
python -m pip install --upgrade pip

# Installer les dépendances principales
print_message "Installation des dépendances principales..."

# Packages de base
python -m pip install pandas numpy

# Gestion de fichiers Excel
python -m pip install openpyxl xlsxwriter

# Visualisation et graphiques
python -m pip install matplotlib seaborn plotly

# Base de données
python -m pip install pymysql sqlalchemy

# Traitement de dates
python -m pip install python-dateutil

# Variables d'environnement
python -m pip install python-dotenv

# Autres utilitaires
python -m pip install pathlib-ng

print_success "Dépendances principales installées"

# Packages supplémentaires optionnels
print_message "Installation des packages supplémentaires..."

# Jupyter et notebooks (optionnel)
python -m pip install jupyter ipython

# Packages de développement
python -m pip install black flake8 pytest

print_success "Packages supplémentaires installés"

# Créer un fichier requirements.txt
print_message "Génération du fichier requirements.txt..."
python -m pip freeze > requirements.txt

print_success "Fichier requirements.txt créé"

# Afficher le résumé
echo ""
echo "======================================"
echo "✅ INSTALLATION TERMINÉE AVEC SUCCÈS"
echo "======================================"
echo ""
echo "Packages installés:"
echo "- pandas: Manipulation de données"
echo "- numpy: Calculs numériques" 
echo "- openpyxl, xlsxwriter: Lecture/écriture Excel"
echo "- matplotlib, seaborn, plotly: Visualisation"
echo "- pymysql, sqlalchemy: Base de données"
echo "- python-dateutil: Gestion des dates"
echo "- python-dotenv: Variables d'environnement"
echo ""
echo "Pour activer l'environnement virtuel:"
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "  source venv/Scripts/activate"
else
    echo "  source venv/bin/activate"
fi
echo ""
echo "Pour lancer votre script:"
echo "  python rapport.py"
echo ""
echo "Pour désactiver l'environnement:"
echo "  deactivate"
echo ""
echo "======================================"