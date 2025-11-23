#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour automatiser un 'git pull' sécurisé.
Usage :
    python git_pull_auto.py
"""

import subprocess
import sys

def run_command(command: list):
    """Exécute une commande shell et affiche proprement les résultats."""
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution : {' '.join(command)}")
        print(e.stderr)
        sys.exit(1)

def main():
    print("🔄 Mise à jour du dépôt local depuis le dépôt distant...")
    run_command(["git", "pull"])
    print("✅ Dépôt mis à jour avec succès !")

if __name__ == "__main__":
    main()
