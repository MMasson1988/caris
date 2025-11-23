#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour supprimer tous les fichiers Excel (.xlsx) du repository Git local et distant
Inclut les fichiers non-trackés
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

def find_all_xlsx_files():
    """Trouve tous les fichiers .xlsx (trackés et non-trackés)"""
    print("🔍 Recherche des fichiers Excel (.xlsx)...")
    
    xlsx_files = []
    
    # Trouver tous les fichiers .xlsx dans le répertoire avec find
    try:
        result = subprocess.run(
            ["find", ".", "-name", "*.xlsx", "-type", "f"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            all_xlsx = result.stdout.strip().split('\n')
            xlsx_files = [f.replace('./', '') for f in all_xlsx if f.strip()]
        
    except Exception as e:
        print(f"❌ Erreur avec find: {e}")
        
        # Fallback: utiliser Python pour chercher les fichiers
        try:
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file.endswith('.xlsx'):
                        file_path = os.path.join(root, file)
                        # Normaliser le chemin et enlever le './'
                        normalized_path = os.path.normpath(file_path).replace('\\', '/').replace('./', '')
                        xlsx_files.append(normalized_path)
        except Exception as e2:
            print(f"❌ Erreur avec os.walk: {e2}")
            return [], [], []
    
    # Séparer les fichiers trackés et non-trackés
    stdout, stderr = run_git_command("git ls-files")
    if stdout:
        tracked_files = set(stdout.split('\n'))
    else:
        tracked_files = set()
    
    tracked_xlsx = [f for f in xlsx_files if f in tracked_files]
    untracked_xlsx = [f for f in xlsx_files if f not in tracked_files]
    
    print(f"📊 Trouvé {len(xlsx_files)} fichiers Excel au total:")
    print(f"  📁 Trackés par Git: {len(tracked_xlsx)}")
    print(f"  📄 Non-trackés: {len(untracked_xlsx)}")
    
    if len(xlsx_files) <= 15:
        for i, file in enumerate(xlsx_files, 1):
            status = "📁" if file in tracked_files else "📄"
            print(f"  {i:2d}. {status} {file}")
    else:
        for i, file in enumerate(xlsx_files[:10], 1):
            status = "📁" if file in tracked_files else "📄"
            print(f"  {i:2d}. {status} {file}")
        print(f"  ... et {len(xlsx_files) - 10} autres fichiers")
    
    return xlsx_files, tracked_xlsx, untracked_xlsx

def confirm_deletion(xlsx_files, tracked_xlsx, untracked_xlsx):
    """Demande confirmation avant suppression"""
    if not xlsx_files:
        print("✅ Aucun fichier Excel trouvé")
        return False
    
    print(f"\n⚠️  ATTENTION: Vous êtes sur le point de supprimer {len(xlsx_files)} fichiers Excel!")
    print(f"  📁 {len(tracked_xlsx)} fichiers seront supprimés du Git ET du disque")
    print(f"  📄 {len(untracked_xlsx)} fichiers seront supprimés uniquement du disque")
    print("Cette action est IRRÉVERSIBLE!")
    
    response = input("\nÊtes-vous sûr de vouloir continuer? (tapez 'OUI' en majuscules): ")
    return response == "OUI"

def create_backup_branch():
    """Crée une branche de sauvegarde"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_branch = f"backup_before_xlsx_deletion_{timestamp}"
    
    print(f"📝 Création d'une branche de sauvegarde: {backup_branch}")
    stdout, stderr = run_git_command(f"git checkout -b {backup_branch}")
    if stdout is None:
        print("❌ Impossible de créer la branche de sauvegarde")
        return False, None
    
    # Revenir à la branche principale
    stdout, stderr = run_git_command("git checkout main")
    if stdout is None:
        print("❌ Impossible de revenir à la branche main")
        return False, backup_branch
    
    return True, backup_branch

def delete_files(xlsx_files, tracked_xlsx, untracked_xlsx):
    """Supprime les fichiers Excel"""
    total_deleted = 0
    
    # 1. Supprimer les fichiers trackés de Git
    if tracked_xlsx:
        print(f"🗑️  Suppression de {len(tracked_xlsx)} fichiers trackés de Git...")
        
        batch_size = 50
        for i in range(0, len(tracked_xlsx), batch_size):
            batch = tracked_xlsx[i:i + batch_size]
            escaped_files = [f'"{file}"' for file in batch]
            files_str = ' '.join(escaped_files)
            
            print(f"📂 Suppression du lot {i//batch_size + 1}/{(len(tracked_xlsx)-1)//batch_size + 1}...")
            
            stdout, stderr = run_git_command(f"git rm {files_str}")
            if stdout is None:
                print(f"❌ Erreur lors de la suppression du lot {i//batch_size + 1}")
                continue
            
            total_deleted += len(batch)
    
    # 2. Supprimer les fichiers non-trackés du disque
    if untracked_xlsx:
        print(f"🗑️  Suppression de {len(untracked_xlsx)} fichiers non-trackés du disque...")
        
        for file in untracked_xlsx:
            try:
                os.remove(file)
                print(f"✅ Supprimé: {file}")
                total_deleted += 1
            except OSError as e:
                print(f"❌ Erreur lors de la suppression de {file}: {e}")
    
    return total_deleted

def commit_and_push_changes(deleted_count, backup_branch):
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
    
    # Push la branche de sauvegarde d'abord
    print(f"🔄 Push de la branche de sauvegarde {backup_branch}...")
    stdout, stderr = run_git_command(f"git push origin {backup_branch}")
    if stdout is None:
        print("⚠️  Attention: Impossible de pusher la branche de sauvegarde")
    else:
        print("✅ Branche de sauvegarde pushée")
    
    # Push vers le repository distant
    print("🚀 Push vers le repository distant...")
    stdout, stderr = run_git_command("git push origin main")
    if stdout is None:
        print("❌ Erreur lors du push")
        return False
    
    print("✅ Push réussi vers le repository distant")
    return True

def update_gitignore():
    """Ajoute les fichiers Excel au .gitignore"""
    gitignore_path = Path(".gitignore")
    
    excel_patterns = [
        "",
        "# Fichiers Excel - Générés automatiquement",
        "*.xlsx",
        "*.xls", 
        "*.xlsm",
        "*.xlsb",
        "data/*.xlsx",
        "outputs/*.xlsx",
        ""
    ]
    
    existing_content = ""
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
    
    if "*.xlsx" in existing_content:
        print("✅ Les fichiers Excel sont déjà dans .gitignore")
        return True
    
    print("📝 Ajout des patterns Excel au .gitignore...")
    
    with open(gitignore_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(excel_patterns))
    
    stdout, stderr = run_git_command("git add .gitignore")
    if stdout is None:
        return False
        
    stdout, stderr = run_git_command('git commit -m "gitignore: ajout des fichiers Excel pour éviter les re-ajouts accidentels"')
    if stdout is None:
        print("ℹ️  .gitignore déjà à jour")
    else:
        print("✅ .gitignore mis à jour et commité")
        
        stdout, stderr = run_git_command("git push origin main")
        if stdout is None:
            print("❌ Erreur lors du push du .gitignore")
        else:
            print("✅ .gitignore pushé avec succès")
    
    return True

def main():
    """Fonction principale"""
    print("=" * 70)
    print("🗑️  SUPPRESSION DES FICHIERS EXCEL DU REPOSITORY ET DISQUE LOCAL")
    print("=" * 70)
    
    # Vérifier qu'on est dans un repository Git
    if not Path(".git").exists():
        print("❌ Ce répertoire n'est pas un repository Git")
        sys.exit(1)
    
    # Étape 1: Trouver tous les fichiers Excel
    xlsx_files, tracked_xlsx, untracked_xlsx = find_all_xlsx_files()
    
    # Étape 2: Demander confirmation
    if not confirm_deletion(xlsx_files, tracked_xlsx, untracked_xlsx):
        print("❌ Opération annulée par l'utilisateur")
        sys.exit(0)
    
    # Étape 3: Créer une branche de sauvegarde
    backup_success, backup_branch = create_backup_branch()
    if not backup_success:
        print("❌ Impossible de créer une sauvegarde")
        sys.exit(1)
    
    # Étape 4: Supprimer les fichiers
    deleted_count = delete_files(xlsx_files, tracked_xlsx, untracked_xlsx)
    
    # Étape 5: Commiter et pusher
    if not commit_and_push_changes(len(tracked_xlsx), backup_branch):
        print("❌ Erreur lors du commit/push")
        sys.exit(1)
    
    # Étape 6: Mettre à jour .gitignore
    update_gitignore()
    
    print("\n" + "=" * 70)
    print(f"✅ SUCCÈS: {deleted_count} fichiers Excel supprimés")
    print(f"  📁 {len(tracked_xlsx)} fichiers supprimés du repository Git")
    print(f"  📄 {len(untracked_xlsx)} fichiers supprimés du disque local")
    print(f"🔒 Fichiers Excel ajoutés au .gitignore")
    print(f"📦 Branche de sauvegarde créée: {backup_branch}")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Opération interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)