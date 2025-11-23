#!/usr/bin/env bash
set -euo pipefail

echo "=== MISE EN PLACE DES ENVIRONNEMENTS R & PYTHON POUR LE PROJET MUSO ==="

########################################
# 1. Vérifier les dépendances système
########################################
echo "Vérification des dépendances système..."

# Vérifier si Python3 est installé
if ! command -v python3 &> /dev/null; then
    echo "Python3 n'est pas installé. Installation requise."
    exit 1
fi

# Vérifier si R est installé
if ! command -v R &> /dev/null; then
    echo "R n'est pas installé. Installation requise."
    exit 1
fi

echo "Python3 version: $(python3 --version)"
echo "R version: $(R --version | head -1)"

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

echo "Création du fichier requirements.txt..."
pip freeze > requirements.txt

deactivate

########################################
# 3. Installer les packages R essentiels
########################################
echo "=== Installation des packages R essentiels ==="

R -e "
packages <- c('dplyr', 'DBI', 'viridis', 'ggplot2', 'ggrepel', 
              'plotly', 'stringr', 'RColorBrewer', 'tidytext', 'purrr', 
              'lubridate', 'tidyr', 'scales', 'forcats', 'DT', 
              'data.table', 'readxl', 'writexl', 'reticulate',
              'rmarkdown', 'knitr', 'quarto')
              
for (pkg in packages) {
  if (!require(pkg, character.only = TRUE, quietly = TRUE)) {
    cat('Installation de:', pkg, '\n')
    install.packages(pkg, repos='https://cloud.r-project.org')
  } else {
    cat('Déjà installé:', pkg, '\n')
  }
}
cat('Installation des packages R terminée.\n')
"

echo "=== Installation terminée ==="
echo " - Python venv : venv/"
echo " - Packages R installés dans l'environnement renv"
echo ""
echo "Pour utiliser Python :"
echo "  source venv/bin/activate"
echo ""
echo "Pour tester le document Quarto :"
echo "  quarto render tracking-muso.qmd"