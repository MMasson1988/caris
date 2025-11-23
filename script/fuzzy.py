import pandas as pd
import unicodedata
from rapidfuzz import process, fuzz

def commcare_match_person(
    df_reference: pd.DataFrame,
    df_commcare: pd.DataFrame,
    name_column: str = "nom_complet",
    threshold: int = 85,
    return_df: str = "reference",  # "reference" ou "commcare"
    scorer=fuzz.token_set_ratio
) -> pd.DataFrame:
    """
    Apparier flou sur une colonne de noms entre df_reference et df_commcare.

    Args:
        df_reference: DataFrame source de référence.
        df_commcare: DataFrame cible où l'on cherche la meilleure correspondance.
        name_column: Nom de la colonne contenant les noms à comparer (défaut: 'nom_complet').
        threshold: Score minimal [0..100] pour accepter une correspondance.
        return_df: 'reference' => retourne df_reference enrichi;
                   'commcare'     => retourne df_commcare enrichi (recherche inversée).
        scorer: fonction de similarité rapidfuzz (par défaut token_set_ratio).

    Returns:
        Le DataFrame demandé, avec 3 colonnes ajoutées:
          - 'best_match'    : le nom correspondant le plus proche
          - 'score'         : le score de similarité (0..100)
          - 'correspondance': 'yes' si score >= threshold, 'no' sinon
    """

    if "nom_complet" not in df_reference.columns or "nom_complet" not in df_commcare.columns:
        raise ValueError("Les deux DataFrames doivent contenir la colonne 'nom_complet'.")

    def _normalize(s: str) -> str:
        if pd.isna(s):
            return ""
        s = str(s).strip().lower()
        s = " ".join(s.split())  # collapse espaces multiples
        # retirer les accents
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s

    def _match(source_df: pd.DataFrame, target_df: pd.DataFrame) -> pd.DataFrame:
        # Prépare les choix (normalisés) et un mapping -> original
        target_norm = target_df[name_column].map(_normalize).fillna("")
        choices = target_norm.tolist()
        orig_by_norm = target_norm.to_frame("norm").join(
            target_df[name_column]
        ).drop_duplicates(subset=["norm"]).set_index("norm")[name_column].to_dict()

        # Calcul du meilleur match pour chaque source
        best_matches = []
        scores = []

        for name in source_df[name_column].fillna(""):
            q = _normalize(name)
            if not q:
                best_matches.append(None)
                scores.append(0)
                continue

            # extractOne renvoie (match_norm, score, index)
            match = process.extractOne(q, choices, scorer=scorer)
            if match is None:
                best_matches.append(None)
                scores.append(0)
                continue

            match_norm, score, _ = match
            if score >= threshold:
                best_matches.append(orig_by_norm.get(match_norm, None))
                scores.append(int(score))
            else:
                best_matches.append(None)
                scores.append(int(score))

        out = source_df.copy()
        out["best_match"] = best_matches
        out["score"] = scores
        out["correspondance"] = ["yes" if score >= threshold else "no" for score in scores]
        return out

    if return_df not in ("reference", "commcare"):
        raise ValueError("return_df doit être 'reference' ou 'commcare'.")

    if return_df == "reference":
        # cherche pour chaque nom du df_reference dans df_commcare
        return _match(df_reference, df_commcare)
    else:
        # cherche pour chaque nom du df_commcare dans df_reference
        return _match(df_commcare, df_reference)


df_reference = pd.DataFrame({
    "nom_complet": [
        "Jean Baptiste", "Moise Masson", "Marie-Claire Pierre",
        "Petion Ville", "Cap-Haitien"
    ],
    "id_ref": [1, 2, 3, 4, 5]
})

df_commcare = pd.DataFrame({
    "nom_complet": [
        "Jean-Baptiste", "Moise  MoSSan", "Marie Claire  PIERRE",
        "Pétion-Ville", "Cap Haïtien", "Masson Moise"
    ],
    "autre_info": ["A", "B", "C", "D", "E", "F"]
})

# 1) Retourner df_reference enrichi (match dans df_commcare)
res_ref = commcare_match_person(
    df_reference=df_reference,
    df_commcare=df_commcare,
    name_column="nom_complet",
    threshold=85,
    return_df="reference"
)
print("=== Résultat (return_df='reference') ===")
print(res_ref)

# 2) Retourner df_commcare enrichi (match dans df_reference)
res_commcare = commcare_match_person(
    df_reference=df_reference,
    df_commcare=df_commcare,
    name_column="nom_complet",
    threshold=85,
    return_df="commcare"
)
print("\n=== Résultat (return_df='commcare') ===")
print(res_commcare)
