#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour supprimer tous les fichiers Excel (.xlsx) du repository Git distant
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_git_command(command, cwd=None):
    """Exécute une commande Git et retourne le résultat"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd,
            check=True
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur Git: {e}")
        print(f"Sortie d'erreur: {e.stderr}")
        return None, e.stderr

def find_xlsx_files():
    """Trouve tous les fichiers .xlsx dans le repository"""
    print("🔍 Recherche des fichiers Excel (.xlsx)...")
    
    # Utiliser git ls-files pour trouver tous les fichiers trackés
    stdout, stderr = run_git_command("git ls-files")
    
    if stdout is None:
        print("❌ Impossible de lister les fichiers Git")
        return []
    
    all_files = stdout.split('\n') if stdout else []
    xlsx_files = [f for f in all_files if f.endswith('.xlsx')]
    
    print(f"📊 Trouvé {len(xlsx_files)} fichiers Excel:")
    for i, file in enumerate(xlsx_files[:10], 1):  # Afficher les 10 premiers
        print(f"  {i:2d}. {file}")
    
    if len(xlsx_files) > 10:
        print(f"  ... et {len(xlsx_files) - 10} autres fichiers")
    
    return xlsx_files

def confirm_deletion(xlsx_files):
    """Demande confirmation avant suppression"""
    if not xlsx_files:
        print("✅ Aucun fichier Excel trouvé dans le repository")
        return False
    
    print(f"\n⚠️  ATTENTION: Vous êtes sur le point de supprimer {len(xlsx_files)} fichiers Excel du repository distant!")
    print("Cette action est IRRÉVERSIBLE!")
    
    response = input("\nÊtes-vous sûr de vouloir continuer? (tapez 'OUI' en majuscules): ")
    return response == "OUI"

def delete_files_from_git(xlsx_files):
    """Supprime les fichiers du repository Git"""
    if not xlsx_files:
        return True
    
    print(f"\n🗑️  Suppression de {len(xlsx_files)} fichiers Excel...")
    
    # Créer un commit de sauvegarde avant suppression
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_branch = f"backup_before_xlsx_deletion_{timestamp}"
    
    print(f"📝 Création d'une branche de sauvegarde: {backup_branch}")
    stdout, stderr = run_git_command(f"git checkout -b {backup_branch}")
    if stdout is None:
        print("❌ Impossible de créer la branche de sauvegarde")
        return False
    
    # Revenir à la branche principale
    stdout, stderr = run_git_command("git checkout main")
    if stdout is None:
        print("❌ Impossible de revenir à la branche main")
        return False
    
    # Supprimer les fichiers par lots pour éviter les problèmes de ligne de commande trop longue
    batch_size = 50
    total_deleted = 0
    
    for i in range(0, len(xlsx_files), batch_size):
        batch = xlsx_files[i:i + batch_size]
        
        # Échapper les noms de fichiers avec des espaces
        escaped_files = [f'"{file}"' for file in batch]
        files_str = ' '.join(escaped_files)
        
        print(f"📂 Suppression du lot {i//batch_size + 1}/{(len(xlsx_files)-1)//batch_size + 1} ({len(batch)} fichiers)...")
        
        # Supprimer du Git index
        stdout, stderr = run_git_command(f"git rm {files_str}")
        
        if stdout is None:
            print(f"❌ Erreur lors de la suppression du lot {i//batch_size + 1}")
            continue
        
        total_deleted += len(batch)
        print(f"✅ Lot {i//batch_size + 1} supprimé ({len(batch)} fichiers)")
    
    return total_deleted

def commit_and_push_changes(deleted_count):
    """Commit et push les changements"""
    if deleted_count == 0:
        print("ℹ️  Aucun fichier à commiter")
        return True
    
    print(f"\n💾 Création du commit pour {deleted_count} fichiers supprimés...")
    
    commit_message = f"cleanup: suppression de {deleted_count} fichiers XLSX (run {datetime.now().strftime('%Y%m%d%H%M%S')})"
    
    stdout, stderr = run_git_command(f'git commit -m "{commit_message}"')
    if stdout is None:
        print("❌ Erreur lors du commit")
        return False
    
    print("✅ Commit créé avec succès")
    
    # Push vers le repository distant
    print("🚀 Push vers le repository distant...")
    stdout, stderr = run_git_command("git push origin main")
    if stdout is None:
        print("❌ Erreur lors du push")
        return False
    
    print("✅ Push réussi vers le repository distant")
    return True

def cleanup_gitignore():
    """Ajoute les fichiers Excel au .gitignore pour éviter qu'ils soient re-ajoutés"""
    gitignore_path = Path(".gitignore")
    
    excel_patterns = [
        "# Fichiers Excel",
        "*.xlsx",
        "*.xls",
        "*.xlsm",
        "*.xlsb",
        ""  # Ligne vide
    ]
    
    # Lire le contenu existant
    existing_content = ""
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    
    # Vérifier si les patterns sont déjà présents
    if "*.xlsx" in existing_content:
        print("✅ Les fichiers Excel sont déjà dans .gitignore")
        return True
    
    print("📝 Ajout des patterns Excel au .gitignore...")
    
    # Ajouter les patterns
    with open(gitignore_path, 'a', encoding='utf-8') as f:
        f.write('\n' + '\n'.join(excel_patterns))
    
    # Commiter le .gitignore
    stdout, stderr = run_git_command("git add .gitignore")
    if stdout is None:
        print("❌ Erreur lors de l'ajout de .gitignore")
        return False
    
    stdout, stderr = run_git_command('git commit -m "gitignore: ajout des fichiers Excel (.xlsx, .xls, .xlsm, .xlsb)"')
    if stdout is None:
        print("ℹ️  .gitignore déjà à jour ou erreur de commit")
    else:
        print("✅ .gitignore mis à jour et commité")
        
        # Push le .gitignore
        stdout, stderr = run_git_command("git push origin main")
        if stdout is None:
            print("❌ Erreur lors du push du .gitignore")
        else:
            print("✅ .gitignore pushé avec succès")
    
    return True

def main():
    """Fonction principale"""
    print("=" * 60)
    print("🗑️  SUPPRESSION DES FICHIERS EXCEL DU REPOSITORY DISTANT")
    print("=" * 60)
    
    # Vérifier qu'on est dans un repository Git
    if not Path(".git").exists():
        print("❌ Ce répertoire n'est pas un repository Git")
        print("Veuillez exécuter ce script depuis la racine de votre repository")
        sys.exit(1)
    
    # Vérifier le statut Git
    stdout, stderr = run_git_command("git status --porcelain")
    if stdout is None:
        print("❌ Impossible de vérifier le statut Git")
        sys.exit(1)
    
    if stdout.strip():
        print("⚠️  Attention: Il y a des modifications non commitées")
        print("Statut Git:")
        print(stdout)
        
        response = input("\nVoulez-vous continuer malgré tout? (y/N): ")
        if response.lower() != 'y':
            print("❌ Opération annulée")
            sys.exit(1)
    
    # Étape 1: Trouver les fichiers Excel
    xlsx_files = find_xlsx_files()
    
    # Étape 2: Demander confirmation
    if not confirm_deletion(xlsx_files):
        print("❌ Opération annulée par l'utilisateur")
        sys.exit(0)
    
    # Étape 3: Supprimer les fichiers
    deleted_count = delete_files_from_git(xlsx_files)
    if deleted_count is False:
        print("❌ Erreur lors de la suppression")
        sys.exit(1)
    
    # Étape 4: Commiter et pusher
    if not commit_and_push_changes(deleted_count):
        print("❌ Erreur lors du commit/push")
        sys.exit(1)
    
    # Étape 5: Mettre à jour .gitignore
    cleanup_gitignore()
    
    print("\n" + "=" * 60)
    print(f"✅ SUCCÈS: {deleted_count} fichiers Excel supprimés du repository distant")
    print("🔒 Fichiers Excel ajoutés au .gitignore")
    print("📦 Branche de sauvegarde créée pour récupération si nécessaire")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Opération interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)