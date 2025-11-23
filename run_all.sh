#!/bin/bash

# ================================
# 🚀 SCRIPT D'EXÉCUTION AUTOMATIQUE
# - 3 scripts Python
# - 3 fichiers Quarto
# - Opérations Git automatiques
# - Gestion des erreurs par fichier
# ================================

echo "🔁 Début de l'exécution globale"
echo "📅 Date : $(date)"
echo "-------------------------------"

# ========== PYTHON ==========
echo "🐍 [1/3] Exécution des scripts Python..."

# Vérifier si un environnement virtuel existe et l'activer
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    echo "🔧 Activation de l'environnement virtuel..."
    source venv/bin/activate
    echo "✅ Environnement virtuel activé"
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Aucun interpréteur Python trouvé"
    exit 1
fi

echo "🐍 Utilisation de: $PYTHON_CMD"

PY_SCRIPTS=("oev_pipeline.py" "ptme_pipeline.py" "garden_pipeline.py" "muso_pipeline.py")
FAILED_PY=()

for file in "${PY_SCRIPTS[@]}"; do
    if [ -f "$file" ]; then
        echo "⚙️ Exécution : $file"
        
        $PYTHON_CMD "$file"
        
        if [ $? -ne 0 ]; then
            echo "❌ Échec : $file"
            FAILED_PY+=("$file")
        else
            echo "✅ Succès : $file"
        fi
    else
        echo "⚠️ Fichier introuvable : $file - ignoré"
    fi
done

# ========== QUARTO ==========
echo ""
echo "📝 [2/3] Rendu des fichiers Quarto..."

QMD_FILES=("tracking-ptme.qmd" "tracking-oev.qmd" "tracking-gardening.qmd" "tracking-muso.qmd")
FAILED_QMD=()

for file in "${QMD_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "📄 Rendu : $file"
        
        # Rendu direct sans nettoyage
        quarto render "$file" --quiet
        
        if [ $? -ne 0 ]; then
            echo "⚠️ Première tentative échouée pour $file, nouvelle tentative..."
            
            # Deuxième tentative
            echo "🔄 Deuxième tentative pour $file..."
            quarto render "$file" --quiet
            
            if [ $? -ne 0 ]; then
                echo "❌ Échec définitif : $file"
                FAILED_QMD+=("$file")
            else
                echo "✅ Succès (2ème tentative) : $file"
            fi
        else
            echo "✅ Succès : $file"
        fi
    else
        echo "⚠️ Fichier introuvable : $file - ignoré"
    fi
    
    # Petit délai entre les fichiers
    sleep 1
done

# ========== GIT OPERATIONS ==========
echo ""
echo "📝 [3/3] Opérations Git..."

# Vérifier si on est dans un repository Git
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "✅ Repository Git détecté"
    
    # Obtenir la date du jour
    DATE_TODAY=$(date +"%Y-%m-%d")
    COMMIT_MESSAGE="Update automatique du $DATE_TODAY"

    # ------ Corrections: pull, commit & push fiables ------
    
    # 1) Vérifier si on est à jour avec origin
    echo "🔍 Vérification du statut avec origin..."
    git fetch origin
    
    CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
    if [ -z "$CURRENT_BRANCH" ]; then
        CURRENT_BRANCH="main"
    fi
    
    # 2) Pull automatique si nécessaire
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/$CURRENT_BRANCH 2>/dev/null || echo "")
    
    if [ "$LOCAL" != "$REMOTE" ] && [ -n "$REMOTE" ]; then
        echo "📥 Mise à jour nécessaire - git pull..."
        if git pull origin "$CURRENT_BRANCH"; then
            echo "✅ git pull réussi"
        else
            echo "❌ Échec de 'git pull' - possible conflit"
            echo "💡 Résolvez les conflits manuellement et relancez le script"
            FAILED_GIT=true
        fi
    else
        echo "✅ Branche à jour avec origin"
    fi
    
    # 3) Stager tous les changements (ajouts/suppressions/modifs)
    git add -A
    if [ $? -ne 0 ]; then
        echo "❌ Échec de 'git add -A'"
        FAILED_GIT=true
    else
        echo "✅ git add -A réussi"

        # 4) Commiter uniquement s'il y a des changements indexés
        if git diff --cached --quiet; then
            echo "ℹ️ Aucun changement à commiter"
            FAILED_GIT=false
        else
            echo "💾 Commit avec le message: '$COMMIT_MESSAGE'"
            if git commit -m "$COMMIT_MESSAGE"; then
                echo "✅ Git commit réussi"
                echo "📝 Message: $COMMIT_MESSAGE"
                COMMIT_HASH=$(git rev-parse --short HEAD)
                echo "🔗 Hash du commit: $COMMIT_HASH"

                # 5) Push automatique
                if git push origin "$CURRENT_BRANCH"; then
                    echo "✅ git push réussi vers origin/$CURRENT_BRANCH"
                    FAILED_GIT=false
                else
                    echo "❌ Échec de 'git push'"
                    FAILED_GIT=true
                fi
            else
                echo "❌ Échec du git commit"
                FAILED_GIT=true
            fi
        fi
    fi
    # ------ Fin corrections ------
else
    echo "⚠️ Pas un repository Git - opérations Git ignorées"
    echo "💡 Pour initialiser un repo Git, exécutez: git init"
    FAILED_GIT=false  # Pas une vraie erreur
fi

# ========== RAPPORT FINAL ==========
echo ""
echo "==============================="
echo "📋 RAPPORT D'EXÉCUTION FINALE"
echo "==============================="

# Compter les succès et échecs
TOTAL_SUCCESS=true

if [ ${#FAILED_PY[@]} -eq 0 ] && [ ${#FAILED_QMD[@]} -eq 0 ] && [ "$FAILED_GIT" != true ]; then
    echo "🎉 Tous les processus ont été exécutés avec succès!"
    echo ""
    echo "📊 Résumé:"
    echo "   ✅ Scripts Python: ${#PY_SCRIPTS[@]} réussis"
    echo "   ✅ Fichiers Quarto: ${#QMD_FILES[@]} rendus"
    echo "   ✅ Opérations Git: terminées"
else
    TOTAL_SUCCESS=false
    echo "⚠️ Certains processus ont échoué:"
    echo ""
    
    if [ ${#FAILED_PY[@]} -gt 0 ]; then
        echo "❌ Scripts Python échoués (${#FAILED_PY[@]}/${#PY_SCRIPTS[@]}):"
        for f in "${FAILED_PY[@]}"; do echo "   - $f"; done
        echo ""
    else
        echo "✅ Scripts Python: tous réussis (${#PY_SCRIPTS[@]}/${#PY_SCRIPTS[@]})"
    fi
    
    if [ ${#FAILED_QMD[@]} -gt 0 ]; then
        echo "❌ Fichiers Quarto échoués (${#FAILED_QMD[@]} / ${#QMD_FILES[@]}):"
        for f in "${FAILED_QMD[@]}"; do echo "   - $f"; done
        echo ""
    else
        echo "✅ Fichiers Quarto: tous réussis (${#QMD_FILES[@]} / ${#QMD_FILES[@]})"
    fi
    
    if [ "$FAILED_GIT" = true ]; then
        echo "❌ Opérations Git: échouées"
    else
        echo "✅ Opérations Git: réussies"
    fi
fi

echo ""
echo "📅 Fin d'exécution: $(date)"
echo "🔚 Script terminé."

# Code de sortie basé sur le succès global
if [ "$TOTAL_SUCCESS" = true ]; then
    exit 0
else
    exit 1
fi
