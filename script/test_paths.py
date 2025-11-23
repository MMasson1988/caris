#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier les chemins dans les scripts Python
"""

import os
import sys
from pathlib import Path

def test_paths():
    """Teste si tous les chemins sont correctement configurés"""
    
    # Changer vers le dossier script
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("=== TEST DES CHEMINS RELATIFS ===")
    print(f"Répertoire de travail: {os.getcwd()}")
    
    # Test des chemins relatifs
    paths_to_test = [
        "../data",
        "../outputs", 
        "../input",
        "../outputs/PTME",
        "../input/site_info.xlsx"
    ]
    
    results = []
    
    for path in paths_to_test:
        exists = os.path.exists(path)
        status = "✅" if exists else "❌"
        results.append((path, exists))
        print(f"{status} {path}")
        
        if not exists and path.endswith('.xlsx'):
            # Pour les fichiers Excel, vérifier si le dossier parent existe
            parent = Path(path).parent
            if parent.exists():
                print(f"   📁 Dossier parent existe: {parent}")
    
    # Test des imports
    print("\n=== TEST DES IMPORTS ===")
    try:
        from utils import today_str
        print("✅ import utils.today_str")
    except ImportError as e:
        print(f"❌ import utils.today_str: {e}")
    
    try:
        import pandas as pd
        print("✅ import pandas")
    except ImportError as e:
        print(f"❌ import pandas: {e}")
    
    # Créer les dossiers manquants si nécessaire
    print("\n=== CRÉATION DES DOSSIERS MANQUANTS ===")
    dirs_to_create = ["../outputs", "../outputs/PTME", "../outputs/OEV", "../outputs/MUSO", "../outputs/GARDEN"]
    
    for dir_path in dirs_to_create:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"✅ Créé: {dir_path}")
        else:
            print(f"📁 Existe déjà: {dir_path}")
    
    print("\n=== RÉSUMÉ ===")
    failed_paths = [path for path, exists in results if not exists]
    if failed_paths:
        print(f"❌ Chemins manquants: {len(failed_paths)}")
        for path in failed_paths:
            print(f"  - {path}")
    else:
        print("✅ Tous les chemins sont accessibles")
    
    return len(failed_paths) == 0

if __name__ == "__main__":
    success = test_paths()
    sys.exit(0 if success else 1)