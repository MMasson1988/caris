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
from utils import is_screened_in_period,today_str,detect_duplicates_with_groups,load_excel_to_df,extraire_data, age_range,get_age_in_year, get_age_in_months, clean_column_names,creer_colonne_match_conditional,combine_columns, commcare_match_person
#=========================================================================================================
# PIPE-FRIENDLY WRAPPER FUNCTIONS
#=========================================================================================================


def save_to_excel(df, filename, index=False, **kwargs):
    """Fonction pipe-friendly pour sauvegarder un DataFrame en Excel."""
    df.to_excel(filename, index=index, **kwargs)
    print(f"Nombre de patients dans le fichier {filename}: {df.shape[0]}")
    print(f"✅ File saved: {filename}")
    return df

def rename_cols(df, mapping: dict):
    """Renomme les colonnes de manière pipe-friendly"""
    return df.rename(columns=mapping)


def assign_age_range(df, months_col="age_months"):
    """Assigne la tranche d'âge de manière pipe-friendly"""
    df['age_range'] = df[months_col].map(age_range)
    return df



def detect_duplicates(df, colonnes, threshold=95):
    """Détecte les doublons de manière pipe-friendly"""
    return detect_duplicates_with_groups(df, colonnes=colonnes, threshold=threshold)

def select_columns(df, cols):
    """Sélectionne les colonnes spécifiées de manière pipe-friendly"""
    available_cols = [col for col in cols if col in df.columns]
    if len(available_cols) != len(cols):
        missing = [col for col in cols if col not in df.columns]
        print(f"Warning: Missing columns {missing}")
    return df[available_cols]

def print_shape(df, message="DataFrame shape"):
    """Affiche la forme du DataFrame et le retourne (pipe-friendly)"""
    print(f"{message}: {df.shape[0]} lignes")
    return df

def print_message(df, message="Message"):
    """Affiche un message et le retourne (pipe-friendly)"""
    print(f"{message}")
    return df

def assign_age_range_from_months(df, months_col="age_months", out="age_range"):
    """Assigne age_range à partir de age_months de manière pipe-friendly"""
    df.loc[:, out] = df[months_col].map(age_range)
    return df

def capitalize_column(df, column_name):
    """Capitalise une colonne de type string de manière pipe-friendly"""
    df.loc[:, column_name] = df[column_name].astype(str).str.capitalize()
    return df

def load_excel_pipe(filename, usecols=None, parse_dates=True, **kwargs):
    """Charge un fichier Excel de manière pipe-friendly - retourne le DataFrame"""
    return pd.read_excel(filename, usecols=usecols, parse_dates=parse_dates, **kwargs)

def convert_datetime_column(df, column_name, errors='coerce', format=None):
    """Convertit une colonne en datetime de manière pipe-friendly"""
    import warnings
    
    # Supprimer temporairement les warnings pour cette conversion
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        
        if format:
            # Si un format est spécifié, l'utiliser
            df.loc[:, column_name] = pd.to_datetime(df[column_name], format=format, errors=errors)
        else:
            # Essayer de détecter automatiquement le format ou utiliser infer_datetime_format
            df.loc[:, column_name] = pd.to_datetime(df[column_name], errors=errors, infer_datetime_format=True)
    
    return df

def copy_dataframe(df, name="DataFrame", var_name=None):
    """Copie le DataFrame de manière pipe-friendly avec nom de variable optionnel"""
    if var_name:
        print(f"Copie du {name} → Nouveau DataFrame: {var_name}")
    else:
        print(f"Copie du {name} effectuée")
    return df.copy()

def clean_raison_sortie_column(df, column_name='raison_pour_la_sortie', fill_value='no_info'):
    """Nettoie la colonne raison_pour_la_sortie de manière pipe-friendly"""
    df.loc[:, column_name] = (df[column_name]
                              .fillna(fill_value)
                              .replace({'---': fill_value, '': fill_value}))
    return df

def convert_numeric_column(df, column_name, fill_value=0, replace_value='---'):
    """Convertit une colonne en numérique et remplace les valeurs manquantes"""
    df.loc[:, column_name] = (pd.to_numeric(df[column_name], errors='coerce')
                              .fillna(fill_value)
                              .replace(replace_value, fill_value))
    return df

def create_mamba_given_column(df, quantity_col='mamba_quantity', output_col='mamba_given'):
    """Crée la colonne mamba_given basée sur mamba_quantity"""
    df.loc[:, output_col] = np.where(df[quantity_col] > 0, 'yes', 'no')
    return df

def create_conditional_column(df, condition_col, output_col, condition_value, true_value, false_value):
    """Fonction pipe-friendly générique utilisant np.where pour créer une colonne conditionnelle"""
    df.loc[:, output_col] = np.where(df[condition_col] == condition_value, true_value, false_value)
    return df

def create_numeric_conditional_column(df, condition_col, output_col, threshold, true_value, false_value, operator='>'):
    """Fonction pipe-friendly utilisant np.where avec conditions numériques"""
    if operator == '>':
        condition = df[condition_col] > threshold
    elif operator == '>=':
        condition = df[condition_col] >= threshold
    elif operator == '<':
        condition = df[condition_col] < threshold
    elif operator == '<=':
        condition = df[condition_col] <= threshold
    elif operator == '==':
        condition = df[condition_col] == threshold
    elif operator == '!=':
        condition = df[condition_col] != threshold
    else:
        raise ValueError("Operator must be one of: '>', '>=', '<', '<=', '==', '!='")
    
    df.loc[:, output_col] = np.where(condition, true_value, false_value)
    return df

def create_multiple_conditions_column(df, output_col, conditions_dict, default_value='other'):
    """Fonction pipe-friendly utilisant np.where avec conditions multiples"""
    result = pd.Series([default_value] * len(df), index=df.index)
    
    for condition_func, value in conditions_dict.items():
        mask = condition_func(df)
        result = np.where(mask, value, result)
    
    df.loc[:, output_col] = result
    return df

def fill_missing_values_by_type(df, col_date=None, col_numeric=None):
    """Remplit les valeurs manquantes selon le type de données de chaque colonne
    
    Args:
        df: DataFrame à traiter
        col_date: Liste des colonnes à traiter comme des dates (optionnel)
        col_numeric: Liste des colonnes à traiter comme numériques (optionnel)
    """
    df_filled = df.copy()
    
    # Initialiser les listes si elles ne sont pas fournies
    if col_date is None:
        col_date = []
    if col_numeric is None:
        col_numeric = []
    
    for col in df_filled.columns:
        if col in col_date or df_filled[col].dtype == 'datetime64[ns]':
            # Pour les colonnes datetime, remplir avec 1901-01-01
            df_filled[col] = df_filled[col].fillna(pd.Timestamp('1901-01-01'))
        elif col in col_numeric or pd.api.types.is_numeric_dtype(df_filled[col]):
            # Pour les colonnes numériques, remplir avec 0
            df_filled[col] = df_filled[col].fillna(0)
        else:
            # Pour les autres types (string/object), remplir avec 'no_info'
            df_filled[col] = df_filled[col].fillna('no_info')
    
    return df_filled

def convert_date_columns(df, date_cols, format=None):
    """Convertit les colonnes de date de manière pipe-friendly"""
    for col in date_cols:
        if col in df.columns:
            if format:
                df.loc[:, col] = pd.to_datetime(df[col], format=format, errors='coerce')
            else:
                df.loc[:, col] = pd.to_datetime(df[col], errors='coerce')
    return df

def filter_enrolled_with_visits(df, date_threshold="2025-05-01", enrolled_col="is_enrolled", 
                                   visit_col="nbr_visit_succeed", date_col1="enrollement_date_de_visite", 
                                   date_col2="date_admission"):
    """Filtre les patients enrôlés avec visites de manière pipe-friendly"""
    # Convert visit column to numeric
    df.loc[:, visit_col] = pd.to_numeric(df[visit_col], errors='coerce').fillna(0)
    
    # Define date limit
    date_limite = pd.to_datetime(date_threshold)
    
    # Filter condition
    condition = (
        ((df[enrolled_col] == "yes") | (df[visit_col] > 0))
        &
        ((df[date_col1] >= date_limite) | (df[date_col2] >= date_limite))
    )
    
    return df[condition]

def clean_enrolled_where(df, col="enrrolled_where", old_value="---", new_value="community"):
    """Nettoie la colonne enrrolled_where de manière pipe-friendly"""
    if col in df.columns:
        df.loc[:, col] = df[col].replace(old_value, new_value).fillna(new_value)
    return df

def extract_user_mamba(df, username_col='username', output_col='user_mamba'):
    """Extrait les chiffres du nom d'utilisateur de manière pipe-friendly"""
    if username_col in df.columns:
        df.loc[:, output_col] = df[username_col].str.extract(r'(\d+)')
    else:
        print(f'Warning: {username_col} column not found')
        df.loc[:, output_col] = None
    return df

def merge_with_depistage(df, depistage_df, cols=None):
    """Merge DataFrame with depistage data, handling missing columns"""
    if cols is None:
        cols = ['caseid']
    
    # Only select columns that exist in both DataFrames
    available_cols = [col for col in cols if col in depistage_df.columns]
    missing_cols = [col for col in cols if col not in depistage_df.columns]
    
    if missing_cols:
        print(f"Warning: Missing columns in depistage_df: {missing_cols}")
    
    if not available_cols:
        print("Error: No common columns found for merge")
        return df
    
    print(f"Merging on columns: {available_cols}")
    return pd.merge(df, depistage_df[available_cols], on='caseid', how='left')

def create_date_enrollement(df, col1="enrollement_date_de_visite", col2="date_admission", out_col="date_enrollement"):
    """Crée la colonne date_enrollement avec le max des deux dates"""

    df.loc[:, out_col] = df[[col1, col2]].max(axis=1)
    return df

def replace_dates_before(df, date_col="date_enrollement", threshold="2025-05-01", replacement="2025-09-30"):
    """Remplace les dates antérieures au seuil de manière pipe-friendly"""

    threshold_date = pd.to_datetime(threshold)
    replacement_date = pd.to_datetime(replacement)
    mask = df[date_col] < threshold_date
    df.loc[mask, date_col] = replacement_date
    return df

def match_conditional(df, other_df, on="caseid", new_col="has_visit", 
                         mapping={'both': 'yes', 'left_only': 'no', 'right_only': 'no'}):
    """Crée une colonne de match conditionnel de manière pipe-friendly"""
    return creer_colonne_match_conditional(df1=df, df2=other_df, on=on, nouvelle_colonne=new_col, mapping=mapping)

def numeric_conversion(df, col, fill_value=0):
    """Convertit une colonne en numérique de manière pipe-friendly"""

    df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(fill_value)
    return df

def filter_open_cases(df, closed_col='closed_date', closed_value='---'):
    """Filtre les cas non fermés de manière pipe-friendly"""
    return df.loc[df[closed_col] == closed_value]

def fix_datetime_columns(df, *columns, format='%Y-%m-%d'):
    """Corrige le format des colonnes datetime de manière pipe-friendly"""

    for col in columns:
        if col in df.columns:
            df.loc[:, col] = pd.to_datetime(df[col], format=format, errors='coerce')
    return df

def create_status_column(df, col1, col2, col3, threshold=0, operator='!=', 
                        output_col='status', true_value='exeat', false_value='enrole'):
    """
    Crée une colonne de statut basée sur la formule Excel =IF(OR(O2<>0, P2<>0, R2<>0), "exeat", "enrole")
    
    Args:
        df: DataFrame
        col1, col2, col3: Noms des colonnes à vérifier
        threshold: Valeur seuil pour la comparaison (par défaut 0)
        operator: Opérateur de comparaison ('!=', '>', '<', '>=', '<=', '==')
        output_col: Nom de la colonne de sortie
        true_value: Valeur si condition vraie (par défaut 'exeat')
        false_value: Valeur si condition fausse (par défaut 'enrole')
    
    Returns:
        DataFrame avec la nouvelle colonne
    """
    # Convertir les colonnes en numérique
    for col in [col1, col2, col3]:
        if col in df.columns:
            df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Définir la condition selon l'opérateur
    if operator == '!=':
        condition = (
            (df[col1] != threshold) | 
            (df[col2] != threshold) | 
            (df[col3] != threshold)
        )
    elif operator == '>':
        condition = (
            (df[col1] > threshold) | 
            (df[col2] > threshold) | 
            (df[col3] > threshold)
        )
    elif operator == '<':
        condition = (
            (df[col1] < threshold) | 
            (df[col2] < threshold) | 
            (df[col3] < threshold)
        )
    elif operator == '>=':
        condition = (
            (df[col1] >= threshold) | 
            (df[col2] >= threshold) | 
            (df[col3] >= threshold)
        )
    elif operator == '<=':
        condition = (
            (df[col1] <= threshold) | 
            (df[col2] <= threshold) | 
            (df[col3] <= threshold)
        )
    elif operator == '==':
        condition = (
            (df[col1] == threshold) | 
            (df[col2] == threshold) | 
            (df[col3] == threshold)
        )
    else:
        raise ValueError("Operator must be one of: '!=', '>', '<', '>=', '<=', '=='")
    
    # Appliquer la condition avec np.where
    df.loc[:, output_col] = np.where(condition, true_value, false_value)
    
    print(f"Colonne '{output_col}' créée:")
    print(f"  - {true_value}: {(df[output_col] == true_value).sum()}")
    print(f"  - {false_value}: {(df[output_col] == false_value).sum()}")
    
    return df

def filter_enrolled_patients(
    df: pd.DataFrame,
    date_threshold: str = "2025-05-01",
    enrolled_col: str = "is_enrolled",
    visit_col: str = "nbr_visit_succeed",
    date_col1: str = "enrollement_date_de_visite",
    date_col2: str = "date_admission"
) -> pd.DataFrame:
        # Définir la date limite
    date_limite = pd.to_datetime(date_threshold)
    
    # Convertir le nombre de visites en numérique
    df.loc[:, visit_col] = pd.to_numeric(df[visit_col], errors='coerce').fillna(0)
    df.loc[:, date_col1] = pd.to_datetime(df[date_col1], errors='coerce')
    df.loc[:, date_col2] = pd.to_datetime(df[date_col2], errors='coerce')
    
    # Condition de filtrage
    condition = (
        ((df[enrolled_col] == "yes") | (df[visit_col] > 0))
        &
        ((df[date_col1] >= date_limite) | (df[date_col2] >= date_limite))
    )
    
    # Application du filtre
    filtered_df = df[condition]
    print(f"Nombre d'enrollement avec doublons possibles {filtered_df.shape[0]} lignes")
    
    return filtered_df

def fix_multiple_datetime_columns(df, col1, col2, format=None):
    """Corrige les colonnes datetime avec format explicite et .loc[]"""

    df.loc[:, col1] = pd.to_datetime(df[col1], format=format, errors="coerce")
    df.loc[:, col2] = pd.to_datetime(df[col2], format=format, errors="coerce")
    return df

def replace_dates_before_threshold(
    df: pd.DataFrame,
    date_col: str = "date_enrollement",
    threshold_date: str = "2025-05-01",
    replacement_date: str = "2025-09-30"
) -> pd.DataFrame:
         
    if date_col not in df.columns:
        raise KeyError(f"La colonne '{date_col}' est absente du DataFrame.")
    
    threshold = pd.Timestamp(threshold_date)
    replacement = pd.Timestamp(replacement_date)
    
    mask = df[date_col] < threshold
    df.loc[mask, date_col] = replacement
    
    return df

def filter_by_user_mamba(
    df: pd.DataFrame,
    user_mamba_col: str = 'user_mamba',
    exclude_values: list = ['5', '1', '6']
) -> pd.DataFrame:
    """
    Filtre un DataFrame en excluant certaines valeurs de la colonne user_mamba.
    
    Args:
        df (pd.DataFrame): DataFrame à filtrer.
        user_mamba_col (str): Nom de la colonne user_mamba.
        exclude_values (list): Liste des valeurs à exclure.
    
    Returns:
        pd.DataFrame: DataFrame filtré.
    """
    if user_mamba_col not in df.columns:
        raise KeyError(f"La colonne '{user_mamba_col}' est absente du DataFrame.")
    
    # Créer la condition d'exclusion
    condition = ~df[user_mamba_col].isin(exclude_values)
    #nut_filtered = pd.concat([condition_avant_septembre, condition_apres_septembre], ignore_index=True)
    
    return df[condition]

def filter_by_mamba_given(
    df: pd.DataFrame,
    mamba_given_col: str = 'mamba_given',
    exclude_values: list = ['no', '---']
) -> pd.DataFrame:
    """
    Filtre un DataFrame en excluant certaines valeurs de la colonne user_mamba.
    
    Args:
        df (pd.DataFrame): DataFrame à filtrer.
        mamba_given_col (str): Nom de la colonne mamba_given.
        exclude_values (list): Liste des valeurs à exclure.
    
    Returns:
        pd.DataFrame: DataFrame filtré.
    """
    if mamba_given_col not in df.columns:
        raise KeyError(f"La colonne '{mamba_given_col}' est absente du DataFrame.")
    
    # Créer la condition d'exclusion
    condition = ~df[mamba_given_col].isin(exclude_values)
    return df[condition]

# Créer une copie intermédiaire pour réutilisation
def create_backup_and_continue(df, backup_var_name="backup"):
    # Cette fonction crée une copie ET continue le pipeline
    globals()[backup_var_name] = df.copy()
    print(f"✅ Backup créé: {backup_var_name}")
    return df

def create_mamba_period_column(df, user_mamba_col='user_mamba', date_col='date_enrollement', 
                               output_col='mamba_period_eligible', 
                               target_values=[1, 5, 6], 
                               start_date='2025-05-01', end_date='2025-10-30'):
    """Crée une colonne conditionnelle basée sur user_mamba et période de dates"""
    # Convertir les dates en Timestamp
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    
    # Convertir user_mamba en numérique si nécessaire
    df.loc[:, user_mamba_col] = pd.to_numeric(df[user_mamba_col], errors='coerce')
    
    # Créer la condition combinée
    condition = (
        df[user_mamba_col].isin(target_values) & 
        (df[date_col] >= start_ts) & 
        (df[date_col] <= end_ts)
    )
    
    # Appliquer la condition
    df.loc[:, output_col] = np.where(condition, 'yes', 'no')
    
    print(f"Colonne {output_col} créée:")
    print(df[output_col].value_counts())
    
    return df


def calculate_visits_remaining(df):
    """Calcule les visites restantes selon la logique IFS Excel"""
    # Initialiser avec la valeur par défaut
    df['visits_remaining'] = 'out_of_visit'
    
    # Condition 1: MAM avec total_suivi_mamba <= 12 -> 8 - total_suivi_mamba
    mam_condition = (df['manutrition_type'] == 'MAM') & (df['total_suivi_mamba'] <= 12)
    df.loc[mam_condition, 'visits_remaining'] = 8 - df.loc[mam_condition, 'total_suivi_mamba']
    
    # Condition 2: MAS avec total_suivi_mamba <= 18 -> 12 - total_suivi_mamba
    mas_condition = (df['manutrition_type'] == 'MAS') & (df['total_suivi_mamba'] <= 18)
    df.loc[mas_condition, 'visits_remaining'] = 12 - df.loc[mas_condition, 'total_suivi_mamba']
    
    return df

def groupby_keep_all_columns(df, group_col='caseid'):
    """Groupe par caseid en gardant toutes les colonnes avec des agrégations appropriées"""
    # Identifier les types de colonnes pour l'agrégation
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime64[ns]']).columns.tolist()
    string_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
    
    # Retirer la colonne de groupement des listes
    if group_col in numeric_cols:
        numeric_cols.remove(group_col)
    if group_col in date_cols:
        date_cols.remove(group_col)
    if group_col in string_cols:
        string_cols.remove(group_col)
    
    # Créer le dictionnaire d'agrégation
    agg_dict = {}
    
    # Pour les colonnes numériques: somme
    for col in numeric_cols:
        agg_dict[col] = 'sum'
    
    # Pour les colonnes de dates: maximum (dernière date)
    for col in date_cols:
        agg_dict[col] = 'max'
    
    # Pour les colonnes string: première valeur
    for col in string_cols:
        agg_dict[col] = 'first'
    
    return df.groupby(group_col, as_index=False).agg(agg_dict)

def create_smart_aggregation_dict(df, group_col='caseid'):
    """Crée un dictionnaire d'agrégation intelligent selon le type de colonnes"""
    agg_dict = {}
    
    for col in df.columns:
        if col == group_col:
            continue  # Skip la colonne de groupement
        elif col == 'formid':
            agg_dict[col] = 'count'  # Compter les visites
        elif col == 'date_of_visit':
            agg_dict[col] = ['min', 'max']  # Première ET dernière date de visite
        elif col == 'nbr_visit_succeed_suivi':
            agg_dict[col] = 'last'  # Dernière valeur pour nbr_visit_succeed_suivi
        elif df[col].dtype == 'datetime64[ns]':
            agg_dict[col] = 'max'    # Dernière date pour les autres colonnes datetime
        elif pd.api.types.is_numeric_dtype(df[col]):
            # Pour les colonnes numériques (incluant les dummies 0/1)
            if df[col].isin([0, 1]).all():
                agg_dict[col] = 'sum'  # Sommer les variables dummy
            else:
                agg_dict[col] = 'sum'  # Sommer les quantités/mesures
        else:
            # Pour les colonnes string/object
            agg_dict[col] = 'first'  # Prendre la première valeur
    
    return agg_dict


# Cette ligne est maintenant inutile car le filtrage est déjà fait dans la fonction
# condition_avant_septembre = condition_avant_septembre[condition_user_mamba]
#=========================================================================================================
# etape_enroled #16


#=======================================================================================================
# PERIOD PIPELINE
# Définir start_date avec une valeur par défaut si None
start_date = pd.Timestamp("2025-05-01")
end_date = pd.Timestamp.now()

start_date_janv = pd.Timestamp("2021-01-01")
end_date_avril = pd.Timestamp("2025-04-30")
start_date_nut = pd.Timestamp("2025-05-01")
end_date_nut = pd.Timestamp(datetime.today().date())
#=========================================================================================================
print("="*60)
print(f"DEBUT DE LA PIPELINE DE NUTRITION à {today_str}")
print(f"DE {start_date} à {end_date}")
print("="*60)
#=====================================================================================================================
# etape_depistage #1 - PIPELINE STYLE
dep_col = [
    "form.depistage.date_de_visite", "form.depistage.last_name", "form.depistage.first_name", "form.depistage.gender",
    "form.depistage.date_of_birth", "form.depistage.muac", "form.depistage.weight_kg", "form.depistage.height",
    
    "form.depistage.edema", "form.depistage.lesion_cutane", "form.depistage.diarrhea", "form.depistage.autres_symptomes",
    "form.depistage.phone_number", "form.depistage.photo_depistage", "form.depistage.office", "form.depistage.departement",

    "form.depistage.commune", "form.depistage.fullname", "form.depistage.eligible",
    "form.depistage.manutrition_type", "form.case.@case_id", "completed_time", "started_time",
    
    "username", "received_on", "form_link"
]

depistage = (
    pd.read_excel(f"../data/Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel (created 2025-06-26) {today_str}.xlsx", parse_dates=True)
    .pipe(select_columns, dep_col)
    .pipe(print_shape, "dépistage télechargés avec succes")
    .pipe(rename_cols, {'form.case.@case_id': 'caseid','form.depistage.date_de_visite':'date_de_depistage'})
    .pipe(clean_column_names, 'form.depistage.')
    .pipe(get_age_in_year, 'date_of_birth')
    .pipe(get_age_in_months, 'date_of_birth')
    .pipe(assign_age_range_from_months, months_col="age_months", out="age_range")
    .pipe(convert_numeric_column, 'muac', fill_value=0, replace_value='---')
    .pipe(lambda df: df.assign(depistage_code=(
        "NUT-" + df['caseid'].astype(str).str[:3] + "-" + df['caseid'].astype(str).str[-4:]
    ).str.upper()))
    .pipe(print_message, "Nombre depistage de mai 2025 à aujourd'hui")
    .pipe(extraire_data, start_date=start_date, end_date=end_date, date_col='date_de_depistage')
    .pipe(capitalize_column, 'departement')
    .pipe(print_shape, "dépistage réalisés pour la periode")
    .pipe(save_to_excel, "../outputs/depistage_normal_mai_a_aujourdhui.xlsx", sheet_name="Mai_a_aujourdhui", index=False)
)
#==========================================================================================================
# SECTION SUIVI - TRANSFORMATION AVEC PIPE
#==========================================================================================================
print("=== TRAITEMENT DES DONNÉES DE SUIVI ===")

# Transformation de la section suivi avec pipe
suivi_nut = (
    load_excel_pipe(
        f"../data/Caris Health Agent - Nutrition - Suivi nutritionel (created 2025-06-26) {today_str}.xlsx",
        usecols=[
            "formid", "form.date_of_visit", "form.type_of_visit", 
            "form.is_available_at_time_visit", "form.enfant_absent", 
            "form.nbr_visit", "form.nbr_visit_succeed", "form.case.@case_id",
            "username", "form_link", "form.discharge.raison_pour_la_sortie",
            "form.discharge.last_weight", "form.discharge.last_height", 
            "form.discharge.last_muac", 
            "form.followup_visit.Medicaments_Administres.mamba_quantity_given"
        ],
        parse_dates=True
    )
    .pipe(clean_column_names, expr_to_remove='form.')
    .pipe(rename_cols, {
        "case.@case_id": "caseid",
        "nbr_visit_succeed": "nbr_visit_succeed_suivi",
        "nbr_visit": "nbr_visit_suivi",
        "username": "username_suivi",
        "followup_visit.Medicaments_Administres.mamba_quantity_given": "mamba_quantity"
    })
    .pipe(convert_datetime_column, 'date_of_visit', errors='coerce')
    .pipe(clean_column_names, expr_to_remove='discharge.')
    .pipe(select_columns, [
        'formid', 'type_of_visit', 'date_of_visit', 'caseid', 'username_suivi', 
        'is_available_at_time_visit', 'enfant_absent', 'raison_pour_la_sortie',
        'last_weight', 'last_height', 'last_muac', 'nbr_visit_succeed_suivi', 
        'mamba_quantity'
    ])
    .pipe(clean_raison_sortie_column, 'raison_pour_la_sortie', 'no_info')
    .pipe(convert_numeric_column, 'mamba_quantity', fill_value=0, replace_value='---')
    .pipe(convert_numeric_column, 'last_weight', fill_value=0, replace_value='---')
    .pipe(convert_numeric_column, 'last_height', fill_value=0, replace_value='---')
    .pipe(convert_numeric_column, 'last_muac', fill_value=0, replace_value='---')
    .pipe(create_mamba_given_column, 'mamba_quantity', 'mamba_given')
    .pipe(extraire_data, start_date=start_date_nut, end_date=end_date_nut, date_col='date_of_visit')
    .pipe(print_shape, f"Nombre de suivi nutritionnel de mai 2025 à aujourd'hui")
    .pipe(save_to_excel, "../outputs/suivi_nutritionel.xlsx", sheet_name="Mai_a_aujourdhui", index=False)
)
#=================================================================================================================
# Appliquer get_dummies sur tout le DataFrame en spécifiant la colonne
suivi_with_dummies = pd.get_dummies(
    suivi_nut, 
    columns=['type_of_visit','raison_pour_la_sortie','mamba_given'], 
    dummy_na=True,
    prefix=['type_of_visit', 'raison_pour_la_sortie', 'mamba_given']  # Pas de préfixe pour type_of_visit
)
suivi_with_dummies.to_excel('../outputs/suivi_with_dummies.xlsx', index=False)

# Agrégation avec la fonction aggregate par caseid - GARDER TOUTES LES COLONNES
# Créer un dictionnaire d'agrégation intelligent selon le type de données

# Appliquer l'agrégation intelligente
agg_dict = create_smart_aggregation_dict(suivi_with_dummies)
suivi_aggregated = suivi_with_dummies.groupby('caseid', as_index=False).agg(agg_dict)

# Gérer les colonnes avec plusieurs agrégations (date_of_visit)
if ('date_of_visit', 'min') in suivi_aggregated.columns:
    # Aplatir les colonnes multi-niveau et créer des colonnes séparées
    suivi_aggregated = suivi_aggregated.copy()
    suivi_aggregated['first_visit_date'] = suivi_aggregated[('date_of_visit', 'min')]
    suivi_aggregated['last_visit_date'] = suivi_aggregated[('date_of_visit', 'max')]
    
    # Supprimer les colonnes multi-niveau
    suivi_aggregated.drop(columns=[('date_of_visit', 'min'), ('date_of_visit', 'max')], inplace=True)
    
    # Aplatir le reste des colonnes
    suivi_aggregated.columns = [col[0] if isinstance(col, tuple) else col for col in suivi_aggregated.columns]

# Renommer pour plus de clarté
suivi_aggregated = suivi_aggregated.rename(columns={
    'formid': 'total_visits'
})
print(f"Agrégation terminée: {suivi_aggregated.shape[0]} patients uniques avec {suivi_aggregated.shape[1]} colonnes")
suivi_aggregated.to_excel('../outputs/suivi_aggregated_complete.xlsx', index=False)
print("✅ Fichier sauvegardé: ../outputs/suivi_aggregated_complete.xlsx")
print(f"✅ Toutes les {suivi_aggregated.shape[1]} colonnes ont été conservées avec l'agrégation appropriée")

# Créer la colonne user_mamba en extrayant les chiffres du username
print("\n=== CRÉATION DE LA COLONNE USER_MAMBA ===")
suivi_aggregated['user_mamba_suivi'] = suivi_aggregated['username_suivi'].astype(str).str.extract(r'(\d+)')
suivi_aggregated['user_mamba_suivi'] = suivi_aggregated['user_mamba_suivi'].fillna('1').replace('', '2')

# Sauvegarder le fichier final avec user_mamba
suivi_aggregated.to_excel('../outputs/suivi_aggregated_final.xlsx', index=False)
print("✅ Fichier final sauvegardé: ../outputs/suivi_aggregated_final.xlsx")
#=========================================================================================================
#===============================================================================================
# etape_enroled #1 - PIPELINE STYLE

enroled_col = [
    "caseid", "name", "eligible", "manutrition_type", "date_of_birth",
    "gender", "muac", "nbr_visit", "is_alive", "death_date",
    "death_reason", "nbr_visit_succeed", "admission_muac", "office", "commune",
    "departement", "household_collection_date", "household_number", "has_household", "closed",
    "closed_date", "last_modified_date", "opened_date", "case_link", "enrollement_date_de_visite",
    "enrollment_date", "enrollment_eligibility", "enrollment_manutrition_type", "is_enrolled", "hiv_test_done",
    "hiv_test_result", "club_id", "club_name","date_admission", "child_often_sick", "exclusive_breastfeeding_6months",
    "breastfeeding_received", "enrrolled_where", "has_mamba", "last_mamba_date", "nut_code","last_date_of_visit","is_approve_by_manager","raison_de_non_approbation",
    "last_modified_by_user_username","closed_by_username"
]
start_date_janv = pd.Timestamp("2021-01-01")
end_date_avril = pd.Timestamp("2025-04-30")
start_date_nut = pd.Timestamp("2025-05-01")
end_date_nut = pd.Timestamp(datetime.today().date())
#==========================================================================================================
# Pipeline d'enrôlement avec .pipe()
nut_filtered = (
    pd.read_excel(f"../data/Nutrition (created 2025-04-25) {today_str}.xlsx", parse_dates=True)
    .pipe(select_columns, enroled_col)
    .pipe(convert_datetime_column, "last_mamba_date", errors='coerce')
    .pipe(print_shape, "Fichier enrollement Télechargé avec succès")
    .pipe(convert_datetime_column, "enrollement_date_de_visite", errors='coerce')
    .pipe(convert_datetime_column, "date_admission", errors='coerce')
    .pipe(combine_columns, "enrollement_date_de_visite", "date_admission", col3="date_enrollement", na_value=None)
    .pipe(clean_enrolled_where,
          col="enrrolled_where", 
          old_value="---", 
          new_value="community")
    .pipe(capitalize_column, 'departement')
    .pipe(get_age_in_year, 'date_of_birth')
    .pipe(get_age_in_months, 'date_of_birth')
    .pipe(assign_age_range, months_col="age_months")
    .pipe(merge_with_depistage, depistage, ['date_de_depistage','caseid','username'])
    .pipe(extract_user_mamba, username_col='username', output_col='user_mamba')
    .pipe(create_mamba_period_column, 
          user_mamba_col='user_mamba', 
          date_col='date_enrollement',
          output_col='mamba_period_eligible',
          target_values=[1, 5, 6],
          start_date='2025-05-01', 
          end_date='2025-10-30')
    .pipe(create_backup_and_continue, backup_var_name="depistage_backup")
    .pipe(save_to_excel, f"../outputs/enrolés_mai_a_aujourdhui_{today_str}.xlsx", index=False)
    .pipe(lambda df: df.drop_duplicates(subset=['caseid'], keep='first'))
    .pipe(merge_with_depistage, suivi_aggregated, cols=None)
    .pipe(save_to_excel, "../outputs/suivi_aggregated_enrole.xlsx", index=False)
)
#=========================================================================================================
