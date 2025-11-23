import subprocess
import os
from pathlib import Path

def git_pull_data(repo_path: str = ".", branch: str = "main", folder: str = "data"):
    """
    Fetch and update only a specific folder (e.g. 'data/') from a remote Git repository.

    Parameters
    ----------
    repo_path : str, optional
        Path to the local Git repository (default is current directory).
    branch : str, optional
        Branch name to fetch from (default: 'main').
    folder : str, optional
        Folder to update from the remote branch (default: 'data').

    Returns
    -------
    None
    """
    try:
        # Résoudre le chemin absolu pour éviter les problèmes avec ~
        repo_path = os.path.abspath(os.path.expanduser(repo_path))
        git_dir = os.path.join(repo_path, ".git")
        
        print(f"🔍 Checking repository path: {repo_path}")
        
        # Vérifie que le dossier contient un dépôt Git
        if not os.path.exists(git_dir):
            raise FileNotFoundError(f"❌ '{repo_path}' is not a valid Git repository.")

        print(f"✅ Git repository found at: {repo_path}")
        print(f"📦 Updating folder '{folder}/' from remote branch '{branch}'...")

        # Étape 1 : git fetch origin
        subprocess.run(["git", "fetch", "origin"], cwd=repo_path, check=True)
        print("✅ Fetched latest changes from origin.")

        # Étape 2 : git checkout origin/main -- data/
        subprocess.run(
            ["git", "checkout", f"origin/{branch}", "--", folder],
            cwd=repo_path,
            check=True
        )
        print(f"✅ Folder '{folder}/' successfully updated from 'origin/{branch}'.")

    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git command failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    """
    Exécuter la fonction quand le script est lancé directement
    """
    print("🔄 Starting data synchronization...")
    git_pull_data()
    print("✅ Data synchronization completed.")   