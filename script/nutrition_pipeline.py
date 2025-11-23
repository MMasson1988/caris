"""
RAPPORT NUTRITION - Script Python exécutable avec python {MODULE}.py
"""
from __future__ import annotations

import pandas as pd
# from _helpers import ensure_dirs, read_excel, write_json, write_excel, print_context  # Module non disponible

import pandas as pd
import numpy as np
import os
import re
import time
import warnings
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import openpyxl
import xlsxwriter
import pymysql
from sqlalchemy import create_engine
from difflib import SequenceMatcher
import unicodedata
from typing import List
#from utils import today_str, load_excel_to_df, creer_colonne_match_conditional, commcare_match_person
from pathlib import Path
#=========================================================================================================
# Functions modules
from utils import today_str,detect_duplicates_with_groups,load_excel_to_df,extraire_data, age_range,get_age_in_year, get_age_in_months, clean_column_names,creer_colonne_match_conditional,combine_columns, commcare_match_person
#=========================================================================================================
print("="*60)
today_date = pd.to_datetime('today')
print(f"DEBUT DE LA PIPELINE DE NUTRITION à {today_date}")
print("="*60)
#=========================================================================================================
#=======================================================================================================================
depistage = pd.read_excel(f"../data/Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel (created 2025-06-26) {today_str}.xlsx",
                          parse_dates=True)
dep_col = [
    "form.depistage.date_de_visite", "form.depistage.last_name", "form.depistage.first_name", "form.depistage.gender",
    "form.depistage.date_of_birth", "form.depistage.muac", "form.depistage.weight_kg", "form.depistage.height",
    
    "form.depistage.edema", "form.depistage.lesion_cutane", "form.depistage.diarrhea", "form.depistage.autres_symptomes",
    "form.depistage.phone_number", "form.depistage.photo_depistage", "form.depistage.office", "form.depistage.departement",

    "form.depistage.commune", "form.depistage.fullname", "form.depistage.eligible",
    "form.depistage.manutrition_type", "form.case.@case_id", "completed_time", "started_time",
    
    "username", "received_on", "form_link"
]
depistage = depistage[dep_col]
print(f"dépistage télechargés avec {depistage.shape[0]} lignes")
#========================================================================================================================
#Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel (created 2025-06-26) 2025-09-23
depistage = depistage.rename(columns={'form.case.@case_id': 'caseid','form.depistage.date_de_visite':'date_de_depistage'})
depistage = clean_column_names(depistage, expr_to_remove='form.depistage.')
# Ajouter l'âge au DataFrame de dépistage
depistage = get_age_in_year(depistage, 'date_of_birth')
depistage = get_age_in_months(depistage, 'date_of_birth')
depistage['age_range'] = depistage['age_months'].map(age_range)

end_date_week = pd.to_datetime('today')
# Date de début = 7 jours avant
start_date_week = end_date_week - timedelta(days=7)

start_date = pd.Timestamp("2025-05-01")
end_date = pd.Timestamp(datetime.today().date())

start_date_registre = pd.Timestamp("2021-01-01")
print("=== Nombre depistage pour la semaine ===")

depistage_week = extraire_data(df=depistage, start_date=start_date_week, end_date=end_date_week, date_col='date_de_depistage')
print(f"{depistage_week.shape[0]} dépistage réalisés pour la semaine")
print("=== Nombre depistage de mai 2025 à aujourd'hui ===")
depistage_nut = extraire_data(df=depistage, start_date=start_date, end_date=end_date, date_col='date_de_depistage')
print(f"{depistage_nut.shape[0]} dépistage réalisés pour la periode")
depistage_nut.to_excel("depistage_nutritionel.xlsx", sheet_name="Mai_a_aujourdhui", index=False)
#===============================================================================================

# Load Enrollement Data
enroled = pd.read_excel(f"data/Nutrition (created 2025-04-25) {today_str}.xlsx",
                          parse_dates=True)
enroled_col = [
    "caseid", "name", "eligible", "manutrition_type", "date_of_birth",
    "gender", "muac", "nbr_visit", "is_alive", "death_date",
    "death_reason", "nbr_visit_succeed", "admission_muac", "office", "commune",
    "departement", "household_collection_date", "household_number", "has_household", "closed",
    "closed_date", "last_modified_date", "opened_date", "case_link", "enrollement_date_de_visite",
    "enrollment_date", "enrollment_eligibility", "enrollment_manutrition_type", "is_enrolled", "hiv_test_done",
    "hiv_test_result", "club_id", "club_name","date_admission", "child_often_sick", "exclusive_breastfeeding_6months",
    "breastfeeding_received", "enrrolled_where", "has_mamba", "last_mamba_date", "nut_code"
]
enroled = enroled[enroled_col]
print(f"Fichier enrollement Télechargé avec {enroled.shape[0]} lignes")
#=========================================================================================================
start_date_nut = pd.Timestamp("2025-01-01")
end_date_nut = pd.Timestamp(datetime.today().date())

# Correction des warnings avec format explicite et .loc[]
enroled.loc[:, "enrollement_date_de_visite"] = pd.to_datetime(
    enroled["enrollement_date_de_visite"], 
    format='%Y-%m-%d', 
    errors="coerce"
)
enroled.loc[:, "date_admission"] = pd.to_datetime(
    enroled["date_admission"], 
    format='%Y-%m-%d', 
    errors="coerce"
)


enroled = combine_columns(enroled, "enrollement_date_de_visite", "date_admission", col3="date_enrollement", na_value=None)

enroled = extraire_data(df=enroled, start_date=start_date_nut, end_date=end_date_nut, date_col='date_enrollement').copy()

# Définition du seuil
date_limite = pd.to_datetime("2025-05-01")
# Convert to numeric first
enroled["nbr_visit_succeed"] = pd.to_numeric(enroled["nbr_visit_succeed"], errors='coerce').fillna(0)
# Condition
condition = (
    ((enroled["is_enrolled"] == "yes") | (enroled["nbr_visit_succeed"] > 0))
    &
    ((enroled["enrollement_date_de_visite"] >= date_limite) | (enroled["date_admission"] >= date_limite))
)
# Application du filtre
nut_filtered = enroled[condition]
print(f"Nombre d'enrollement avec doublons possibles {nut_filtered.shape[0]} lignes")
# 2️⃣ Remplacer toutes les dates > 2025-05-01 par 2025-09-30
mask = nut_filtered["date_enrollement"] < pd.Timestamp("2025-05-01")
nut_filtered.loc[mask, "date_enrollement"] = pd.Timestamp("2025-09-30")

nut_filtered['enrrolled_where'] = (
    nut_filtered['enrrolled_where']
    .replace('---', 'community')
    .fillna('community')
)

# Vous pouvez aussi l'appliquer au DataFrame enroled
nut_filtered = get_age_in_year(nut_filtered, 'date_of_birth')
nut_filtered = get_age_in_months(nut_filtered, 'date_of_birth')
nut_filtered['age_range'] = nut_filtered['age_months'].map(age_range)

depistage = depistage.rename(columns={'form.case.@case_id': 'caseid','form.depistage.date_de_visite':'date_de_depistage'})
nut_filtered = pd.merge(nut_filtered, depistage[['date_de_depistage','caseid','username']])

if 'username' in nut_filtered.columns:
    nut_filtered['user_mamba'] = nut_filtered['username'].str.extract(r'(\d+)')
else:
    print('Warning: username column not found')
    nut_filtered['user_mamba'] = None  # \d+ = une ou plusieurs chiffres
    
# Filtrer les patients avec visites ET cas non fermés (FALSE = ouvert)
nut_filtered = nut_filtered.loc[nut_filtered['closed_date'] == '---'].copy()

print(f"Nombre d'enfants enrolés : {nut_filtered.shape[0]} lignes")
nut_filtered.to_excel(f"enrolés_{today_str}.xlsx", index=False)
print(f"✅ Fichier des cas enrolés sauvegardé: enrolés_{today_str}.xlsx")
#=========================================================================================================
# CRÉATION DE LA COLONNE mamba_quantity
#=========================================================================================================
print("=== TRAITEMENT DES CAS DE CAP-GON-PDP SANS MAMBA ===")

# Définir les dates de référence
date_debut_mamba = pd.Timestamp("2025-05-01")
date_fin_mamba = pd.Timestamp("2025-09-30")

# Condition 1: Entre 1 mai et 30 septembre 2025 ET utilisateurs valides (déjà filtré)
periode_sans_mamba = (
    (nut_filtered["date_enrollement"] >= date_debut_mamba) & 
    (nut_filtered["date_enrollement"] <= date_fin_mamba)
)

condition_avant_septembre = nut_filtered.loc[periode_sans_mamba]

# Condition 2: apres 30 septembre 2025 ET non utilisateurs valides
periode_avec_mamba = (
    nut_filtered["date_enrollement"] > date_fin_mamba
)

condition_apres_septembre = nut_filtered.loc[periode_avec_mamba]

# First create user_mamba if it doesn't exist
if 'user_mamba' not in condition_avant_septembre.columns:
    print("Creating user_mamba column from username...")
    condition_avant_septembre['user_mamba'] = condition_avant_septembre['username'].astype(str).str.extract(r'(\d+)')
    condition_avant_septembre['user_mamba'] = condition_avant_septembre['user_mamba'].fillna('1').replace('', '1')

# Then use the DataFrame to access the column
condition_user_mamba = (
    (condition_avant_septembre['user_mamba'] != '5') & 
    (condition_avant_septembre['user_mamba'] != '1') & 
    (condition_avant_septembre['user_mamba'] != '6')
)

# Apply the condition to the DataFrame
condition_avant_septembre = condition_avant_septembre[condition_user_mamba]

# Répartition par période
periode_mamba = len(condition_avant_septembre)
apres_septembre = len(condition_apres_septembre)

condition_apres_septembre.to_excel(f"apres_septembre_{today_str}.xlsx")

print(f"  - Période 1 mai - 30 sept 2025: {periode_mamba}")
print(f"  - Après 30 septembre 2025: {apres_septembre}")

nut_filtered = pd.concat([condition_avant_septembre, condition_apres_septembre], ignore_index=True).copy()

print(f"Total d'enrollement: {len(nut_filtered)}")
nut_filtered.to_excel(f"Nutrition_all_{today_str}.xlsx")

print(f"Nombre d'enrollement avec doublons possibles {nut_filtered.shape[0]} lignes")
nutrition_clean = nut_filtered.copy()
#=========================================================================================================
suivi = pd.read_excel(f"data/Caris Health Agent - Nutrition - Suivi nutritionel (created 2025-06-26) {today_str}.xlsx", usecols=["formid","form.date_of_visit", "form.type_of_visit", "form.is_available_at_time_visit","form.enfant_absent", "form.nbr_visit", "form.nbr_visit_succeed", "form.case.@case_id","username","form_link","form.discharge.raison_pour_la_sortie","form.discharge.last_weight","form.discharge.last_height","form.discharge.last_muac","form.followup_visit.Medicaments_Administres.mamba_quantity_given"],
                          parse_dates=True)

suivi_clean = clean_column_names(suivi, expr_to_remove='form.')

suivi_clean =suivi_clean.rename(columns={"case.@case_id": "caseid","nbr_visit_succeed": "nbr_visit_succeed_suivi","nbr_visit": "nbr_visit_suivi","username": "username_suivi","followup_visit.Medicaments_Administres.mamba_quantity_given": "mamba_quantity"})
suivi_clean['date_of_visit'] = pd.to_datetime(suivi_clean['date_of_visit'], errors='coerce')
suivi_nut=suivi_clean.copy()
#suivi_nut = extraire_data(df=suivi_clean, start_date=start_date, end_date=end_date, date_col='date_of_visit')

suivi_nut = clean_column_names(suivi_nut, expr_to_remove='discharge.')
suivi_nut = suivi_nut[['formid','type_of_visit','date_of_visit','caseid','username_suivi', 'is_available_at_time_visit','enfant_absent','raison_pour_la_sortie','last_weight','last_height','last_muac','nbr_visit_succeed_suivi','mamba_quantity']]
suivi_nut['raison_pour_la_sortie'] = suivi_nut['raison_pour_la_sortie'].fillna('no_info')
suivi_nut['raison_pour_la_sortie'] = (suivi_nut['raison_pour_la_sortie']
                                        .replace({'---': 'no_info', '': 'no_info'})
                                        .fillna('no_info'))
suivi_nut['mamba_quantity'] = pd.to_numeric(suivi_nut['mamba_quantity'], errors='coerce').fillna(0).replace('---', 0)
suivi_nut['mamba_given']=np.where(suivi_nut['mamba_quantity']>0,'yes','no')
suivi_nut = extraire_data(df=suivi_nut, start_date=start_date, end_date=end_date, date_col='date_of_visit').copy()
print(f"Nombre de suivi nutritionnel de mai 2025 à aujourd'hui {suivi_nut.shape[0]} lignes")
suivi_nut.to_excel("suivi_nutritionel.xlsx", sheet_name="Mai_a_aujourdhui", index=False)
#=========================================================================================================
# CRÉATION DE VARIABLES DUMMY POUR TYPE_OF_VISIT
#=========================================================================================================
print("=== CRÉATION DES VARIABLES DUMMY POUR TYPE_OF_VISIT ===")

# Étape 1: Analyser les valeurs uniques dans type_of_visit
print("Valeurs uniques dans type_of_visit:")
print(suivi_nut['type_of_visit'].value_counts(dropna=False))
print()

# Étape 2: Créer des variables dummy avec pd.get_dummies()
# Méthode 1: Variables dummy simples
type_visit_dummies = pd.get_dummies(suivi_nut['type_of_visit'], dummy_na=True)
print(f"Variables dummy créées: {list(type_visit_dummies.columns)}")

# Méthode 2: Ajouter les dummies au DataFrame original
suivi_with_dummies = pd.concat([suivi_nut, type_visit_dummies], axis=1)
print(f"DataFrame avec dummies: {suivi_with_dummies.shape[0]} lignes, {suivi_with_dummies.shape[1]} colonnes")

# Étape 3: Exemple d'agrégation avec les variables dummy par caseid
suivi_dummy_grouped = suivi_with_dummies.groupby('caseid', as_index=False).agg({
    # Variables existantes
    'formid': 'count',
    'date_of_visit': 'max',
    # Variables dummy - somme pour compter les occurrences de chaque type
    **{col: 'sum' for col in type_visit_dummies.columns}
})

# Renommer la colonne formid pour plus de clarté
suivi_dummy_grouped = suivi_dummy_grouped.rename(columns={'formid': 'total_visits'})
suivi_dummy_grouped = suivi_dummy_grouped[['caseid','Visite_de_Suivi', 'derniere_visite', 'suivi_post_exeat','total_visits']]
print(f"Agrégation avec dummies: {suivi_dummy_grouped.shape[0]} patients uniques")

suivi_exeat = suivi_nut[['caseid', 'date_of_visit','raison_pour_la_sortie','mamba_quantity','mamba_given']]
# Sauvegarder les résultats
suivi_with_dummies.to_excel("suivi_avec_dummies.xlsx", index=False)
suivi_dummy_grouped.to_excel("suivi_dummy_aggregated.xlsx", index=False)

print("✅ Variables dummy créées et sauvegardées!")

#=========================================================================================================
# MERGE SUIVI_DUMMY_GROUPED AVEC NUTRITION_CLEAN
#=========================================================================================================
print("\n=== MERGE SUIVI DUMMY AVEC NUTRITION CLEAN ===")

# Application de creer_colonne_match_conditional entre menage_counts et nut_filtered par caseid
mapping_match = {'both': 'yes', 'left_only': 'no', 'right_only': 'no'}
nutrition_suivi = creer_colonne_match_conditional(
    df1=nutrition_clean, 
    df2=suivi_dummy_grouped, 
    on='caseid', 
    nouvelle_colonne='has_visit', 
    mapping=mapping_match
)
# Filtrer les patients avec visites ET cas non fermés (FALSE = ouvert)
nutrition_suivi = nutrition_suivi.loc[
    (nutrition_suivi['has_visit'] == 'yes') & 
    (nutrition_suivi['closed_date'] == '---')
].copy()

# Filtrer les patients avec visites ET cas non fermés (FALSE = ouvert)
nutrition_no_suivi = nutrition_suivi.loc[
    (nutrition_suivi['has_visit'] == 'no') & 
    (nutrition_suivi['closed_date'] == '---')
].copy()

# Statistiques finales
print(f"\n=== STATISTIQUES FINALES ===")
print(f"Patients avec au moins une visite: {(nutrition_suivi['total_visits'] > 0).sum()}")
print(f"Patients sans visite: {(nutrition_suivi['total_visits'] == 0).sum()}")

# Sauvegarder le résultat final
nutrition_suivi.to_excel(f"nutrition_avec_suivi_{today_str}.xlsx", index=False)
print(f"✅ Fichier final sauvegardé: nutrition_avec_suivi_{today_str}.xlsx")
nutrition_no_suivi.to_excel(f"nutrition_sans_suivi_{today_str}.xlsx", index=False)
nutrition_clean = nutrition_suivi.copy()
#=========================================================================================================
# 1) Doublons fuzzy sur ['name', 'commune', 'username'], ne retourner que les doublons
df_dups = detect_duplicates_with_groups(nutrition_clean, ["name", "commune", "username"],
                                         threshold=95, return_only_duplicates=1)
print(f"Nombre de doublons possibles {df_dups.shape[0]} lignes")
df_dups.to_excel(f"doublons_enrollement_{today_str}.xlsx")

# 2) Fuzzy 95% sur ["name", "commune", "username"], retourner TOUT (uniques + doublons)
df_all = detect_duplicates_with_groups(nutrition_clean, ["name", "commune", "username"],
                                        threshold=95, return_only_duplicates=2)
print(f"Enrollement avec doublons possibles {df_all.shape[0]} lignes")
df_all.to_excel(f"enrollement_avec_doublons_{today_str}.xlsx")

# 2) Fuzzy 95% sur ["name", "commune", "username"], retourner sans doublons ou uniques
df_uniques = detect_duplicates_with_groups(nutrition_clean, ["name", "commune", "username"],
                                        threshold=95, return_only_duplicates=0)
print(f"Enrollement sans doublons {df_uniques.shape[0]} lignes")
df_uniques.to_excel(f"enrollement_sans_doublons_{today_str}.xlsx")
# Nutrition Final sans doublons
df_dups = df_dups.drop_duplicates(subset=['duplicate_group_id'], keep='first').copy()
print(f"uniques après suppression des duplicatas parmi les doublons: {df_dups.shape[0]}")
nutrition_final = pd.concat([df_uniques, df_dups], ignore_index=True).copy()
print(f"Nutrition Final après addition des duplicatas : {nutrition_final.shape[0]} lignes")
nutrition_final.to_excel(f"nutrition_final_{today_str}.xlsx", index=False)
print(f"✅ Fichier final sauvegardé: nutrition_final_{today_str}.xlsx")
#=========================================================================================================
# Obtenir les listes de caseid uniques
nutrition_caseids = nutrition_final['caseid'].unique().tolist()
depistage_caseids = depistage_nut['caseid'].unique().tolist()

# Trouver les caseid qui sont dans nutrition mais PAS dans depistage
nutrition_pas_depistage = [caseid for caseid in nutrition_caseids if caseid not in depistage_caseids]

print(f"Caseid dans nutrition mais PAS dans depistage: {len(nutrition_pas_depistage)}")

# Filtrer nutrition_final pour ne garder que ces caseid
nutrition_casi = nutrition_final[nutrition_final['caseid'].isin(nutrition_pas_depistage)].copy()

print(f"Patients nutrition pas dans dépistage: {nutrition_casi.shape[0]} lignes")
nutrition_casi.to_excel(f"nutrition_sans_depistage_{today_str}.xlsx", index=False)
print(f"✅ Fichier des cas nutrition sans dépistage sauvegardé: nutrition_sans_depistage_{today_str}.xlsx")
depistage_supp = depistage[depistage['caseid'].isin(nutrition_casi['caseid'])].copy()
depistage_total = pd.concat([depistage_nut, depistage_supp]).copy().reset_index(drop=True) # depistage_nut

print(f"Nombre d'enfants dépistés : {depistage_total.shape[0]} lignes")
depistage_total.to_excel(f"depistage_total_{today_str}.xlsx", index=False)
print(f"✅ Fichier des cas dépistage total sauvegardé: depistage_total_{today_str}.xlsx")
#=========================================================================================================
# VERIFICATION DES ENROLLEMENTS AVANT MAI 2025
#=========================================================================================================
print("=== VÉRIFICATION DES ENROLLEMENTS AVANT MAI 2025 ===")
# Filtrer les enrollements entre 1 er janvier et le 1er mai 2025
enrollements_avant_mai = enroled[(enroled['date_enrollement'] >= pd.Timestamp("2025-01-01")) & (enroled['date_enrollement'] < pd.Timestamp("2025-05-01"))].copy()
print(f"Nombre d'enrollements avant mai 2025: {enrollements_avant_mai.shape[0]} lignes")
enrollements_avant_mai.to_excel(f"enrollements_avant_mai_2025_{today_str}.xlsx", index=False)
print(f"✅ Fichier des enrollements avant mai 2025 sauvegardé: enrollements_avant_mai_{today_str}.xlsx")

# est-ce que ces enrollements sont dans le suivi_nut ?
enrollements_caseids = enrollements_avant_mai['caseid'].unique().tolist()
suivi_caseids = suivi_nut['caseid'].unique().tolist()
suivi_apres_mai = [caseid for caseid in enrollements_caseids if caseid in suivi_caseids]
print(f"Enrollements avant mai sans suivi: {len(suivi_apres_mai)}")
after_mai = enrollements_avant_mai[enrollements_avant_mai['caseid'].isin(suivi_apres_mai)].copy()
after_mai.to_excel(f"enrollements_avant_mai_suivi_apres_{today_str}.xlsx", index=False)
print(f"✅ Fichier des enrollements avant mai avec suivi sauvegardé: enrollements_avant_mai_avec_suivi_{today_str}.xlsx")

# est-ce que ces enrollements sont dans le depistage_total ?
enrollements_caseids = enrollements_avant_mai['caseid'].unique().tolist()
depistage_caseids_total = depistage_total['caseid'].unique().tolist()
enrollements_pas_depistage = [caseid for caseid in enrollements_caseids if caseid not in depistage_caseids_total]
print(f"Enrollements avant mai 2025 sans depistage: {len(enrollements_pas_depistage)}")
#=======================================================================================================
# ENROLLEMENT POUR LE MOIS D'OCTOBRE 2025
#=========================================================================================================
print("=== ENROLLEMENTS POUR LE MOIS D'OCTOBRE 2025 ===")
# Filtrer les enrollements entre 1 er octobre et le 31 octobre 2025
enrollements_octobre = nutrition_final[(nutrition_final['date_enrollement'] >= pd.Timestamp("2025-05-01")) & (nutrition_final['date_enrollement'] <= pd.Timestamp("2025-10-31"))].copy()
print(f"Nombre d'enrollements pour octobre 2025: {enrollements_octobre.shape[0]} lignes")
enrollements_octobre.to_excel(f"enrollements_octobre_2025_{today_str}.xlsx", index=False)
print(f"✅ Fichier des enrollements pour octobre 2025 sauvegardé: enrollements_octobre_2025_{today_str}.xlsx")

# est-ce que ces enrollements sont dans le depistage ?
enrollements_caseids_oct = enrollements_octobre['caseid'].unique().tolist()
depistage_caseids_total = depistage['caseid'].unique().tolist()
enrollements_depistage_oct = [caseid for caseid in enrollements_caseids_oct if caseid in depistage_caseids_total]
enrollements_depistage_octobre = depistage[depistage['caseid'].isin(enrollements_octobre['caseid'])].copy()
enrollements_depistage_octobre.to_excel(f"enrollements_depistage_octobre_{today_str}.xlsx", index=False)
print(f"Enrollements pour octobre 2025 avec depistage: {len(enrollements_depistage_octobre)}")

# Filtrer les depistages entre 1 er octobre et le 31 octobre 2025
depistages_octobre = depistage[(depistage['date_de_depistage'] >= pd.Timestamp("2025-05-01")) & (depistage['date_de_depistage'] <= pd.Timestamp("2025-10-31"))].copy()
print(f"Nombre de depistages pour octobre 2025: {depistages_octobre.shape[0]} lignes")
depistages_octobre.to_excel(f"depistages_octobre_2025_{today_str}.xlsx", index=False)
print(f"✅ Fichier des depistages pour octobre 2025 sauvegardé: depistages_octobre_2025_{today_str}.xlsx")
# depistage_total_octobre = enrollements_depistage_octobre+depistages_octobre
depistage_total_octobre = pd.concat([enrollements_depistage_octobre, depistages_octobre]).copy().reset_index(drop=True)
print(f"Nombre total de depistages pour octobre 2025: {depistage_total_octobre.shape[0]} lignes")
depistage_total_octobre.to_excel(f"depistage_total_octobre_2025_{today_str}.xlsx", index=False)
print(f"✅ Fichier des depistages total pour octobre 2025 sauvegardé: depistage_total_octobre_2025_{today_str}.xlsx")

#========================================================================================================================
# 1) Doublons fuzzy sur ['fullname', 'commune', 'username'], ne retourner que les doublons
df_dups_oct = detect_duplicates_with_groups(depistage_total_octobre, ["fullname", "commune", "username"],
                                         threshold=95, return_only_duplicates=1)
print(f"Nombre de doublons possibles {df_dups_oct.shape[0]} lignes")
df_dups_oct.to_excel(f"doublons_depistage_{today_str}.xlsx")

# 2) Fuzzy 95% sur ["fullname", "commune", "username"], retourner TOUT (uniques + doublons)
df_all_oct = detect_duplicates_with_groups(depistage_total_octobre, ["fullname", "commune", "username"],
                                        threshold=95, return_only_duplicates=2)
print(f"depistage avec doublons possibles {df_all_oct.shape[0]} lignes")
df_all_oct.to_excel(f"depistage_avec_doublons_{today_str}.xlsx")

# 2) Fuzzy 95% sur ["fullname", "commune", "username"], retourner sans doublons ou uniques
df_uniques_oct = detect_duplicates_with_groups(depistage_total_octobre, ["fullname", "commune", "username"],
                                        threshold=95, return_only_duplicates=0)
print(f"depistage sans doublons {df_uniques_oct.shape[0]} lignes")
df_uniques_oct.to_excel(f"depistage_sans_doublons_{today_str}.xlsx")
# depistage Final sans doublons
df_dups_oct = df_dups_oct.drop_duplicates(subset=['duplicate_group_id'], keep='first').copy()
print(f"uniques après suppression des duplicatas parmi les doublons: {df_dups_oct.shape[0]}")
depistage_final = pd.concat([df_uniques_oct, df_dups_oct], ignore_index=True).copy()
print(f"depistage Final après addition des duplicatas : {depistage_final.shape[0]} lignes")
depistage_final.to_excel(f"depistage_final_{today_str}.xlsx", index=False)
print(f"✅ Fichier final sauvegardé: depistage_final_{today_str}.xlsx")
#=========================================================================================================
# USE CREER_COLONNE_MATCH_CONDITIONAL POUR MERGE ENTRE DEPISTAGE_FINAL ET NUTRITION_FINAL
#=========================================================================================================
# end_date_month = pd.to_datetime('today')
enrollements_octobre = get_age_in_year(enrollements_octobre, 'date_of_birth')
enrollements_octobre = get_age_in_months(enrollements_octobre, 'date_of_birth')
enrollements_octobre['age_range'] = enrollements_octobre['age_months'].map(age_range)

df1=depistage_final[['caseid','eligible','manutrition_type','departement','commune','age_range','date_de_depistage']]
df2=enrollements_octobre[['caseid']]
#df2['eligible']='yes'

nutrition_and_depistage = creer_colonne_match_conditional(
    df1=df1, 
    df2=df2,
    on='caseid', 
    nouvelle_colonne='enroled', 
    mapping=mapping_match
)
nutrition_and_depistage['manutrition_type'] = nutrition_and_depistage['manutrition_type'].fillna('Normal')

# Capitaliser la première lettre des départements (OUEST -> Ouest)
nutrition_and_depistage['departement'] = nutrition_and_depistage['departement'].astype(str).str.capitalize()

#nutrition_depistage = nutrition_and_depistage[nutrition_and_depistage['depistage_match']=='yes']
print(f"Nombre d'enfants avec depistage et nutrition: {nutrition_and_depistage.shape[0]} lignes")
nutrition_and_depistage.to_excel(f"nutrition_avec_depistage_{today_str}.xlsx")

