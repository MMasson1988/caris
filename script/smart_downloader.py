# -*- coding: utf-8 -*-
"""
Version améliorée du téléchargeur CommCare.

Ce module fournit une version durcie du téléchargeur CommCare initial.  Il prend
en charge la détection des fichiers existants, l'optimisation des téléchargements
pour les fichiers volumineux et introduit une prise en charge étendue pour les
exports Nutrition récemment ajoutés.  Il est conçu pour être importé par un
script GUI sans modification de l'interface utilisateur.

Fonctionnalités clés :
  - Détection du répertoire de téléchargement en fonction de l'OS.
  - Liste des exports attendus mise à jour, incluant les nouvelles bases
    de données de nutrition (suivi, présence, household).
  - URL d'export associées pour chaque base.
  - Stratégie de retries ajustée pour les fichiers lourds et nutrition.
  - Fonctions utilitaires pour retrouver les fichiers téléchargés du jour.
  - Fonction `verify_existing_files` pour générer un rapport sur les fichiers
    présents et manquants, utilisable depuis une interface graphique.

Cette version est autonome et peut être exécutée directement en ligne de
commande (fonction `main`) ou importée dans une application graphique.
"""

import os
import re
import time
import glob
import math
import logging
import platform
from datetime import datetime
from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains

###############################################################################
# Configuration du répertoire de téléchargement
###############################################################################

def _default_downloads_dir() -> str:
    """Retourne le dossier « commcare_data » dans les téléchargements de l'utilisateur."""
    home = os.path.expanduser("~")
    if platform.system().lower().startswith("win"):
        return os.path.join(home, "Downloads", "commcare_data")
    return os.path.join(home, "Downloads", "commcare_data")

# Déterminer le répertoire de téléchargement à partir de l'environnement ou du répertoire courant
DOWNLOAD_DIR = os.environ.get("COMMCARE_DOWNLOAD_DIR") or os.path.join(os.getcwd(), "data")
if not os.path.isdir(DOWNLOAD_DIR):
    DOWNLOAD_DIR = _default_downloads_dir()

###############################################################################
# Définition des exports attendus et des URLs d'export
###############################################################################

# Liste des bases attendues (à jour avec les nouveaux fichiers nutrition)
EXPECTED_BASES = [
    "Caris Health Agent - Enfant - Visite Enfant",
    "Caris Health Agent - Enfant - APPELS OEV",
    "Caris Health Agent - Femme PMTE  - Visite PTME",
    "Caris Health Agent - Femme PMTE  - Ration & Autres Visites",
    "Caris Health Agent - Enfant - Ration et autres visites",
    "Caris Health Agent - Femme PMTE  - APPELS PTME",
    "muso_groupes",
    "muso_beneficiaries",
    "Household mother",
    "Ajout de menages ptme [officiel]",
    "PTME WITH PATIENT CODE",
    "household_child",
    "All_child_PatientCode_CaseID",
    "MUSO - Members - PPI Questionnaires",
    "muso_household_2022",
    "All Gardens",
    "Nutrition",
    "Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel",
    # Nouveaux fichiers nutrition
    "Caris Health Agent - Nutrition - Suivi nutritionel",
    "ht_nutrition_presence",
    "household_nutrition",
]

# Dictionnaire des URLs d'export pour chaque base
EXPORT_URLS = {
    "Caris Health Agent - Enfant - Visite Enfant": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/7d960d6c03d9d6c35a8d083c288e7c8d/",
    "Caris Health Agent - Enfant - APPELS OEV": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/f817d728df7d0070b29160e54a22765b/",
    "Caris Health Agent - Femme PMTE  - Visite PTME": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/4fde80e15e96e8214eb58d5761049f0f/",
    "Caris Health Agent - Femme PMTE  - Ration & Autres Visites": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/c5c5e2292ad223156f72620c6e0fd99f/",
    "Caris Health Agent - Enfant - Ration et autres visites": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/bc95b54ff93a6c62c22a2e2f17852a90/",
    "Caris Health Agent - Femme PMTE  - APPELS PTME": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/c1a3280f5e34a2b6078439f9b59ad72c/",
    "Household mother": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/3eb9f92d8d82501ebe5c8cb89b83dbba/",
    "Ajout de menages ptme [officiel]": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/269567f0b84da5a1767712e519ced62e/",
    "PTME WITH PATIENT CODE": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/af6c4186011182dfda68a84536231f68/",
    "household_child": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/f6ddce2133f8d233d9fbd9341220ed6f/",
    "All_child_PatientCode_CaseID": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/0379abcdafdf9979863c2d634792b5a8/",
    "muso_groupes": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/462626788779f3781f9b9ebcce200225/",
    "muso_beneficiaries": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/f831c9c92760a38d24b3829df5621d20/",
    "MUSO - Members - PPI Questionnaires": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/f5daab6b0cc722a5db175e9ad86d8cda/",
    "muso_household_2022": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/462626788779f3781f9b9ebcce2b1a37/",
    "All Gardens": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/789629a97bddd10b4648d5138d17908e/",
    "Nutrition": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/e557b6395b29e531d920e3dcd48028a4/",
    "Caris Health Agent - NUTRITON[HIDDEN] - Dépistage Nutritionnel": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/a6a53d717d2d0bcb0724ae93a3f38ec0/",
    # Nouvelles entrées nutrition
    "Caris Health Agent - Nutrition - Suivi nutritionel": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/form/download/fbb217d7a3cda8e72fb8ebf91f86ff12/",
    "ht_nutrition_presence": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/d58249fa8d705a9c5adb338c8ec5b16d/",
    "household_nutrition": "https://www.commcarehq.org/a/caris-test/data/export/custom/new/case/download/a6a53d717d2d0bcb0724ae93a3cbfd9f/",
}

# Fichiers considérés comme volumineux (timeout longs)
HEAVY_FILES = {
    "muso_beneficiaries",
    "muso_household_2022",
    "muso_groupes",
    "Household mother",
    "Nutrition",
    "All Gardens",
    # Nouveaux fichiers potentiellement volumineux
    "household_nutrition",
}

# Paramètres de retries et timeouts
MAX_RETRIES_PER_FILE = 1
MAX_RETRIES_HEAVY = 2
MAX_GLOBAL_PASSES = 2

VERIFICATION_TIMEOUT = 120
HEAVY_FILE_TIMEOUT = 900
NUTRITION_TIMEOUT = 600
NUTRITION_SUIVI_TIMEOUT = 300  # Timeout spécifique au suivi nutritionnel

HEADLESS = False  # Mode fenêtre pour Selenium; peut être changé par la GUI

###############################################################################
# Logging
###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(), logging.FileHandler("commcare_downloader.log", encoding="utf-8")],
)
log = logging.getLogger("commcare-downloader")

###############################################################################
# Fonctions utilitaires pour le système de fichiers
###############################################################################

def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def build_pattern_with_today(base: str) -> re.Pattern:
    date = today_str()
    base_esc = re.escape(base)
    pat = rf"^{base_esc}(?:\s*\([^)]*\))?\s*{re.escape(date)}(?:\s*\(\d+\))?\.xlsx$"
    return re.compile(pat, re.IGNORECASE)

def list_xlsx(folder: str) -> List[str]:
    return [os.path.basename(p) for p in glob.glob(os.path.join(folder, "*.xlsx"))]

def list_partial(folder: str) -> List[str]:
    return glob.glob(os.path.join(folder, "*.crdownload")) + glob.glob(os.path.join(folder, "*.partial"))

def file_for_base_today(base: str, folder: str) -> Optional[str]:
    pat = build_pattern_with_today(base)
    xlsx_files = list_xlsx(folder)
    for f in xlsx_files:
        if pat.match(f):
            return os.path.join(folder, f)
    # Recherche plus flexible pour les nouveaux fichiers nutrition
    today = today_str()
    base_normalized = base.lower().replace(" ", "").replace("-", "").replace("[", "").replace("]", "")
    for f in xlsx_files:
        if today not in f:
            continue
        f_norm = (
            f.lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("[", "")
            .replace("]", "")
            .replace("(", "")
            .replace(")", "")
        )
        # Cas spéciaux nutrition
        special_matches = {
            "caris health agent - nutrition - suivi nutritionel": ["suivi", "nutrition"],
            "ht_nutrition_presence": ["nutrition", "presence"],
            "household_nutrition": ["household", "nutrition"],
            "caris health agent - nutriton[hidden] - dépistage nutritionnel": ["depistage", "nutrition"],
        }
        base_lower = base.lower()
        for special_base, keywords in special_matches.items():
            if special_base in base_lower or base_lower in special_base:
                if all(keyword in f_norm for keyword in keywords):
                    return os.path.join(folder, f)
        # Recherche par mots clés
        base_words = [w for w in base_normalized.split() if len(w) > 3]
        if base_words:
            matches = sum(1 for word in base_words if word in f_norm)
            if matches >= min(2, len(base_words)):
                return os.path.join(folder, f)
    return None

def size_mb(path: str) -> float:
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except Exception:
        return 0.0

def is_stable(path: str, pause: float = 3.0) -> bool:
    if not os.path.exists(path):
        return False
    s1 = os.path.getsize(path)
    time.sleep(pause)
    if not os.path.exists(path):
        return False
    s2 = os.path.getsize(path)
    return abs(s2 - s1) <= 1024

def cleanup_stuck_partials(folder: str, older_than_sec: int = 300) -> int:
    now = time.time()
    removed = 0
    for p in list_partial(folder):
        try:
            mtime = os.path.getmtime(p)
            if now - mtime > older_than_sec:
                os.remove(p)
                removed += 1
                log.info(f"🧹 Partial supprimé (bloqué): {os.path.basename(p)}")
        except Exception:
            pass
    return removed

###############################################################################
# Fonctions Selenium (clic download, date, login)
###############################################################################

def unfreeze_ui(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        ActionChains(driver).move_by_offset(1, 1).click().perform()
        body.send_keys(Keys.ESCAPE)
    except Exception:
        pass

def set_date_range(driver, start_date="2020-01-01", end_date=None):
    end_date = end_date or today_str()
    try:
        el = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "id_date_range")))
        el.click()
        time.sleep(0.5)
        el.send_keys(Keys.CONTROL, "a")
        time.sleep(0.2)
        el.send_keys(Keys.DELETE)
        time.sleep(0.2)
        el.send_keys(f"{start_date} to {end_date}")
        el.send_keys(Keys.TAB)
        time.sleep(1)
    except Exception as e:
        log.warning(f"Date range non appliquée: {e}")

def click_download(driver, patience: int) -> bool:
    end = time.time() + patience
    selectors = [
        (By.CSS_SELECTOR, "#download-progress a[href$='.xlsx']"),
        (By.XPATH, "//div[@id='download-progress']//a[contains(@href,'.xlsx')]"),
        (By.CSS_SELECTOR, "#download-progress a[href*='download']"),
    ]
    while time.time() < end:
        for sel in selectors:
            links = driver.find_elements(*sel)
            for a in links:
                try:
                    if a.is_displayed() and a.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
                        time.sleep(0.5)
                        a.click()
                        return True
                except StaleElementReferenceException:
                    continue
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", a)
                        return True
                    except Exception:
                        continue
        time.sleep(2)
    return False

def trigger_download(base: str, driver) -> None:
    url = EXPORT_URLS[base]
    
    # PATCH: Nettoyer l'état du navigateur avant chaque téléchargement
    try:
        # Fermer les modales ou popups ouverts
        driver.execute_script("document.querySelectorAll('.modal, .popup').forEach(el => el.remove());")
        # Attendre que les téléchargements précédents se terminent
        time.sleep(3)
    except Exception:
        pass
    
    # Naviguer vers la nouvelle URL avec retry en cas d'échec
    max_nav_attempts = 3
    for attempt in range(max_nav_attempts):
        try:
            driver.get(url)
            # Attendre que la page soit complètement chargée
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            break
        except Exception as e:
            log.warning(f"Échec navigation tentative {attempt + 1}/{max_nav_attempts}: {e}")
            if attempt == max_nav_attempts - 1:
                raise
            time.sleep(2)
    
    time.sleep(3)  # Augmenté de 2 à 3 secondes
    set_date_range(driver, "2020-01-01")
    # Bouton Prepare
    btns = [
        (By.CSS_SELECTOR, "#download-export-form button[type='submit']"),
        (By.XPATH, "//form[@id='download-export-form']//button"),
    ]
    clicked = False
    for b in btns:
        try:
            el = WebDriverWait(driver, 30).until(EC.element_to_be_clickable(b))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.5)
            el.click()
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        raise TimeoutException("Bouton Prepare introuvable")
    # Attendre la modale
    try:
        WebDriverWait(driver, 900).until(EC.visibility_of_element_located((By.ID, "download-progress")))
    except TimeoutException:
        log.info("Modale non visible, poursuite…")
    # Patience en fonction du type de fichier
    patience = 30
    if base in HEAVY_FILES:
        patience = HEAVY_FILE_TIMEOUT
    elif base == "Nutrition":
        patience = NUTRITION_TIMEOUT
    elif base == "Caris Health Agent - Nutrition - Suivi nutritionel":
        patience = NUTRITION_SUIVI_TIMEOUT
    elif base in ["household_nutrition"]:
        patience = 450
    if not click_download(driver, patience):
        raise TimeoutException("Lien de téléchargement introuvable/inaccessible")

def start_chrome(download_dir: str, headless: bool = HEADLESS):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    prefs = {
        "download.default_directory": os.path.abspath(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    opts.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    return driver

def commcare_login(driver, email: str, password: str, first_url: str):
    driver.get(first_url)
    time.sleep(3)
    try:
        user = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "id_auth-username")))
        pwd = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "id_auth-password")))
        user.clear()
        user.send_keys(email)
        pwd.clear()
        pwd.send_keys(password)
        pwd.send_keys(Keys.RETURN)
        WebDriverWait(driver, 60).until(lambda d: "/login" not in d.current_url.lower())
    except TimeoutException:
        log.warning("Login: pas de page de connexion (peut-être déjà connecté)")

###############################################################################
# Téléchargement et vérification avec stats
###############################################################################

def wait_download_done(base: str, folder: str, timeout: int) -> Optional[str]:
    end = time.time() + timeout
    while time.time() < end:
        parts = list_partial(folder)
        if parts:
            time.sleep(2)
            continue
        f = file_for_base_today(base, folder)
        if f and is_stable(f, 3.0):
            return f
        time.sleep(2)
    return None

def download_one(base: str, driver, stats: dict) -> bool:
    already = file_for_base_today(base, DOWNLOAD_DIR)
    if already:
        log.info(f"⏩ Déjà présent: {os.path.basename(already)}")
        stats[base] = {"status": "present", "size_mb": size_mb(already), "seconds": 0.0, "mbps": None}
        return True
    cleanup_stuck_partials(DOWNLOAD_DIR, older_than_sec=300)
    verify_to = VERIFICATION_TIMEOUT
    if base in HEAVY_FILES:
        verify_to = HEAVY_FILE_TIMEOUT
    elif base == "Nutrition":
        verify_to = NUTRITION_TIMEOUT
    elif base == "Caris Health Agent - Nutrition - Suivi nutritionel":
        verify_to = NUTRITION_SUIVI_TIMEOUT
    elif base in ["household_nutrition"]:
        verify_to = 450
    attempts = MAX_RETRIES_HEAVY if base in HEAVY_FILES else MAX_RETRIES_PER_FILE
    ok = False
    last_path = None
    t0 = time.time()
    for k in range(1, attempts + 1):
        log.info(f"📥 {base} — tentative {k}/{attempts}")
        try:
            trigger_download(base, driver)
            path = wait_download_done(base, DOWNLOAD_DIR, verify_to)
            if path:
                ok = True
                last_path = path
                break
            else:
                log.warning(f"⏰ Timeout d'attente fin du téléchargement ({verify_to}s)")
        except Exception as e:
            log.warning(f"⚠️ Tentative échouée: {e}")
        
        # PATCH: Nettoyage et pause plus intelligente entre tentatives
        cleanup_stuck_partials(DOWNLOAD_DIR, older_than_sec=300)
        if k < attempts:  # Pas de pause après la dernière tentative
            pause_time = min(5 + (k * 2), 15)  # Pause progressive: 7s, 9s, 11s, max 15s
            log.info(f"⏸️ Pause de {pause_time}s avant tentative suivante...")
            time.sleep(pause_time)
    dt = time.time() - t0
    if ok and last_path:
        mb = size_mb(last_path)
        mbps = (mb / dt) if dt > 0 else None
        stats[base] = {"status": "downloaded", "size_mb": mb, "seconds": round(dt, 1), "mbps": None if mbps is None else round(mbps, 3)}
        log.info(f"🎉 OK {base} — {mb:.1f} MB en {dt:.1f}s (~{(mb/dt):.3f} MB/s)" if dt > 0 else f"🎉 OK {base}")
        return True
    else:
        stats[base] = {"status": "failed", "size_mb": None, "seconds": round(dt, 1), "mbps": None}
        log.error(f"❌ Échec {base} après {attempts} tentative(s)")
        return False

###############################################################################
# Rapports et fonction main
###############################################################################

def verify_existing_files() -> (int, int):
    """
    Vérifie les fichiers présents dans le répertoire de téléchargement pour la date du jour.
    Retourne un tuple `(present_count, missing_count)` pour usage dans la GUI.
    """
    log.info("🔍 VÉRIFICATION DES FICHIERS EXISTANTS")
    log.info("=" * 50)
    xlsx_files = list_xlsx(DOWNLOAD_DIR)
    today = today_str()
    log.info(f"📁 Dossier: {DOWNLOAD_DIR}")
    log.info(f"📅 Date recherchée: {today}")
    log.info(f"📊 Total fichiers Excel: {len(xlsx_files)}")
    log.info("-" * 50)
    found_today = 0
    for base in EXPECTED_BASES:
        found_file = file_for_base_today(base, DOWNLOAD_DIR)
        if found_file:
            file_size = size_mb(found_file)
            filename = os.path.basename(found_file)
            log.info(f"✅ {base}")
            log.info(f"   📄 {filename} ({file_size:.1f} MB)")
            found_today += 1
        else:
            log.info(f"❌ {base}")
    missing = len(EXPECTED_BASES) - found_today
    log.info("-" * 50)
    log.info(f"📈 RÉSUMÉ:")
    log.info(f"   Fichiers attendus: {len(EXPECTED_BASES)}")
    log.info(f"   Fichiers trouvés aujourd'hui: {found_today}")
    log.info(f"   Fichiers manquants: {missing}")
    return found_today, missing

def main() -> int:
    """
    Fonction principale exécutable : connecte à CommCare, déclenche les téléchargements pour
    toutes les bases attendues, puis fournit un rapport final.  Conçue pour être
    appelée en ligne de commande ou par une interface graphique.
    """
    from dotenv import load_dotenv
    import sys
    ensure_dir(DOWNLOAD_DIR)
    log.info("=" * 60)
    log.info(f"🚀 CommCare Smart Downloader")
    log.info(f"📁 Dossier: {os.path.abspath(DOWNLOAD_DIR)}")
    log.info("=" * 60)
    # Vérifier ce qui manque aujourd'hui
    missing = [b for b in EXPECTED_BASES if not file_for_base_today(b, DOWNLOAD_DIR)]
    found_count, missing_count = verify_existing_files()
    if not missing:
        log.info("✅ Rien à télécharger — tout est déjà présent.")
        return 0
    log.info("")
    log.info("🚀 DÉBUT DES TÉLÉCHARGEMENTS")
    log.info("=" * 60)
    driver = start_chrome(DOWNLOAD_DIR, HEADLESS)
    try:
        load_dotenv("id_cc.env")
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD") or os.getenv("PASSWORD_CC")
        if not email or not password:
            raise RuntimeError("Identifiants CommCare manquants (EMAIL / PASSWORD)")
        first_url = EXPORT_URLS[missing[0]]
        commcare_login(driver, email, password, first_url)
        stats = {}
        total_ok = 0
        passes = 0
        to_download = list(missing)
        while to_download and passes < MAX_GLOBAL_PASSES:
            passes += 1
            log.info(f"================= PASSE #{passes} =================")
            next_round = []
            for base in to_download:
                if file_for_base_today(base, DOWNLOAD_DIR):
                    log.info(f"⏩ Déjà présent (skip): {base}")
                    existing_file = file_for_base_today(base, DOWNLOAD_DIR)
                    stats.setdefault(base, {"status": "present", "size_mb": size_mb(existing_file), "seconds": 0.0, "mbps": None})
                    total_ok += 1
                    continue
                
                # PATCH: Nettoyage entre téléchargements
                log.info(f"🧹 Préparation pour {base}...")
                try:
                    # Nettoyer les téléchargements partiels plus anciens
                    cleanup_stuck_partials(DOWNLOAD_DIR, older_than_sec=120)
                    # Pause courte pour stabiliser le navigateur
                    time.sleep(2)
                except Exception as e:
                    log.warning(f"Nettoyage pré-téléchargement échoué: {e}")
                
                ok = download_one(base, driver, stats)
                if ok:
                    total_ok += 1
                    # PATCH: Pause plus longue après succès pour stabiliser
                    log.info(f"✅ Succès! Pause de stabilisation...")
                    time.sleep(3)
                else:
                    if not file_for_base_today(base, DOWNLOAD_DIR):
                        next_round.append(base)
                    # PATCH: Pause après échec pour reset l'état
                    log.warning(f"❌ Échec! Pause de récupération...")
                    time.sleep(5)
            to_download = next_round
            if to_download and passes < MAX_GLOBAL_PASSES:
                log.info("⏸️ Pause avant relance des échecs…")
                time.sleep(20)
        log.info("")
        log.info("================= VÉRIFICATION FINALE =================")
        final_found, final_missing = verify_existing_files()
        log.info("")
        log.info("================= RAPPORT FINAL =================")
        total = len(EXPECTED_BASES)
        failed = [b for b in EXPECTED_BASES if not file_for_base_today(b, DOWNLOAD_DIR)]
        log.info(f"Fichiers attendus : {total}")
        log.info(f"Téléchargés/présents : {final_found}")
        log.info(f"Manquants : {final_missing}")
        if failed:
            log.info("Fichiers échoués:")
            for f in failed:
                log.info(f"   ❌ {f}")
        if stats:
            log.info("")
            log.info("================= STATISTIQUES =================")
            total_mb = 0.0
            total_time = 0.0
            for b, s in stats.items():
                sz = s.get("size_mb") or 0.0
                tm = s.get("seconds") or 0.0
                total_mb += sz
                total_time += tm
                mbps_str = f"{s['mbps']:.3f} MB/s" if s['mbps'] else '-' 
                log.info(f"{b[:45]:<45} | {s['status']:<10} | {sz:6.1f} MB | {tm:6.1f} s | {mbps_str}")
            if total_mb > 0 and total_time > 0:
                log.info(f"📊 Volume total: {total_mb:.1f} MB — Temps: {total_time:.1f} s — Débit moyen: {total_mb/total_time:.3f} MB/s")
        return 0 if not failed else 1
    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log.info("⏹️ Interruption utilisateur (Ctrl+C)")
        raise