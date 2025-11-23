#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple pour supprimer tous les fichiers Excel (.xlsx) 
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import glob

def run_git_command(command):
    """Exécute une commande Git"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur Git: {e}")
        return None, e.stderr

def find_all_xlsx_files():
    """Trouve tous les fichiers .xlsx"""
    print("🔍 Recherche des fichiers Excel (.xlsx)...")
    
    # Utiliser glob pour trouver les fichiers
    xlsx_files = []
    
    # Chercher dans tous les sous-dossiers
    patterns = [
        "*.xlsx",
        "*/*.xlsx", 
        "*/*/*.xlsx",
        "*/*/*/*.xlsx"
    ]
    
    for pattern in patterns:
        xlsx_files.extend(glob.glob(pattern, recursive=False))
    
    # Nettoyer et normaliser les chemins
    xlsx_files = list(set([f.replace('\\', '/') for f in xlsx_files]))
    xlsx_files.sort()
    
    # Vérifier quels fichiers sont trackés par Git
    stdout, stderr = run_git_command("git ls-files")
    tracked_files = set(stdout.split('\n')) if stdout else set()
    
    tracked_xlsx = [f for f in xlsx_files if f in tracked_files]
    untracked_xlsx = [f for f in xlsx_files if f not in tracked_files]
    
    print(f"📊 Trouvé {len(xlsx_files)} fichiers Excel:")
    print(f"  📁 Trackés par Git: {len(tracked_xlsx)}")
    print(f"  📄 Non-trackés: {len(untracked_xlsx)}")
    
    # Afficher quelques exemples
    if xlsx_files:
        print("\n📋 Exemples de fichiers trouvés:")
        for i, file in enumerate(xlsx_files[:10], 1):
            status = "📁" if file in tracked_files else "📄"
            print(f"  {i:2d}. {status} {file}")
        
        if len(xlsx_files) > 10:
            print(f"  ... et {len(xlsx_files) - 10} autres fichiers")
    
    return xlsx_files, tracked_xlsx, untracked_xlsx

def confirm_deletion(xlsx_files):
    """Demande confirmation"""
    if not xlsx_files:
        print("✅ Aucun fichier Excel trouvé")
        return False
    
    print(f"\n⚠️  ATTENTION: Supprimer {len(xlsx_files)} fichiers Excel!")
    print("Cette action supprimera les fichiers du disque ET du repository Git distant!")
    print("Cette action est IRRÉVERSIBLE!")
    
    response = input(f"\nTapez 'SUPPRIMER {len(xlsx_files)} FICHIERS' pour confirmer: ")
    return response == f"SUPPRIMER {len(xlsx_files)} FICHIERS"

def create_backup():
    """Crée une branche de sauvegarde"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_branch = f"backup_xlsx_{timestamp}"
    
    print(f"📝 Création de la branche de sauvegarde: {backup_branch}")
    
    # Ajouter tous les fichiers Excel au Git d'abord
    stdout, stderr = run_git_command("git add *.xlsx */*.xlsx */*/*.xlsx 2>/dev/null || true")
    
    # Créer la branche de sauvegarde
    stdout, stderr = run_git_command(f"git checkout -b {backup_branch}")
    if stdout is None:
        print("❌ Impossible de créer la branche de sauvegarde")
        return False, None
    
    # Commiter les fichiers Excel dans la branche de sauvegarde
    stdout, stderr = run_git_command(f'git commit -m "Sauvegarde des fichiers Excel avant suppression"')
    
    # Push la branche de sauvegarde
    stdout, stderr = run_git_command(f"git push origin {backup_branch}")
    if stdout is None:
        print("⚠️  Attention: Impossible de pusher la branche de sauvegarde")
    else:
        print("✅ Branche de sauvegarde pushée vers le remote")
    
    # Revenir à main
    stdout, stderr = run_git_command("git checkout main")
    
    return True, backup_branch

def delete_files(xlsx_files, tracked_xlsx, untracked_xlsx):
    """Supprime les fichiers"""
    deleted_count = 0
    
    print(f"\n🗑️  Début de la suppression de {len(xlsx_files)} fichiers...")
    
    # Supprimer tous les fichiers du disque
    for file in xlsx_files:
        try:
            if os.path.exists(file):
                os.remove(file)
                print(f"✅ Supprimé: {file}")
                deleted_count += 1
            else:
                print(f"⚠️  Fichier non trouvé: {file}")
        except Exception as e:
            print(f"❌ Erreur lors de la suppression de {file}: {e}")
    
    # Supprimer du Git (même si les fichiers physiques sont supprimés)
    if tracked_xlsx or deleted_count > 0:
        print("🔄 Suppression des références Git...")
        
        # Utiliser git add -A pour staged les suppressions
        stdout, stderr = run_git_command("git add -A")
        if stdout is None:
            print("⚠️  Problème avec git add")
    
    return deleted_count

def commit_and_push(deleted_count, backup_branch):
    """Commit et push les changements"""
    if deleted_count == 0:
        print("ℹ️  Aucun fichier supprimé")
        return True
    
    print(f"\n💾 Création du commit de suppression...")
    
    commit_msg = f"cleanup: suppression de {deleted_count} fichiers Excel (.xlsx) - backup: {backup_branch}"
    
    stdout, stderr = run_git_command(f'git commit -m "{commit_msg}"')
    if stdout is None:
        print("❌ Erreur lors du commit")
        return False
    
    print("✅ Commit créé")
    
    # Push vers remote
    print("🚀 Push vers repository distant...")
    stdout, stderr = run_git_command("git push origin main")
    if stdout is None:
        print("❌ Erreur lors du push")
        return False
    
    print("✅ Push réussi!")
    return True

def update_gitignore():
    """Met à jour .gitignore"""
    gitignore_content = """
# Fichiers Excel - ajouté automatiquement
*.xlsx
*.xls
*.xlsm
*.xlsb

# Fichiers Excel dans les dossiers de données
data/*.xlsx
outputs/*.xlsx
temp/*.xlsx
"""
    
    with open(".gitignore", "a", encoding="utf-8") as f:
        f.write(gitignore_content)
    
    run_git_command("git add .gitignore")
    run_git_command('git commit -m "gitignore: ajout des fichiers Excel"')
    run_git_command("git push origin main")
    print("✅ .gitignore mis à jour")

def main():
    print("=" * 60)
    print("🗑️  SUPPRESSION DES FICHIERS EXCEL")
    print("=" * 60)
    
    # Vérifier qu'on est dans un repo Git
    if not Path(".git").exists():
        print("❌ Pas un repository Git")
        return
    
    # Étapes
    xlsx_files, tracked_xlsx, untracked_xlsx = find_all_xlsx_files()
    
    if not confirm_deletion(xlsx_files):
        print("❌ Opération annulée")
        return
    
    success, backup_branch = create_backup()
    if not success:
        print("❌ Impossible de créer la sauvegarde")
        return
    
    deleted_count = delete_files(xlsx_files, tracked_xlsx, untracked_xlsx)
    
    if not commit_and_push(deleted_count, backup_branch):
        print("❌ Erreur lors du commit/push")
        return
    
    update_gitignore()
    
    print("\n" + "=" * 60)
    print(f"✅ SUCCÈS: {deleted_count} fichiers Excel supprimés")
    print(f"📦 Sauvegarde créée: {backup_branch}")
    print(f"🌐 Repository distant mis à jour")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Opération interrompue")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()