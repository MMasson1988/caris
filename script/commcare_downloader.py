# -*- coding: utf-8 -*-
"""
CommCare Smart Downloader — Version durcie
- Attente Knockout (isDownloadReady, downloadUrl) + fallback progress bar
- Timeouts réalistes & backoff exponentiel
- set_date_range robuste (multi-ID + 'change' event + attente overlay)
- Regex nommage export tolérante + fallback par mtime
- Aucune fuite de cookies/PII
- stats.json écrit en fin d'exécution (pour CI)
"""

import os
import re
import json
import time
import glob
import logging
import platform
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

# Selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

def _default_downloads_dir() -> str:
    """Détecte le dossier 'Téléchargements' selon l'OS."""
    home = os.path.expanduser("~")
    return os.path.join(home, "Downloads", "commcare_data")

# Dossier téléchargements (env > cwd/data > OS Downloads/commcare_data)
DOWNLOAD_DIR = os.environ.get("COMMCARE_DOWNLOAD_DIR") or os.path.join(os.getcwd(), "data")
if not os.path.isdir(DOWNLOAD_DIR):
    DOWNLOAD_DIR = _default_downloads_dir()

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

# Profils « gros fichiers » → patience élevée
HEAVY_FILES = {
    "muso_beneficiaries", 
    "muso_household_2022", 
    "muso_groupes", 
    "Household mother", 
    "Nutrition", 
    "All Gardens",
    # Nouveaux fichiers potentiellement volumineux
    "household_nutrition",
    "ht_nutrition_presence"
}

# Stratégie de retries
MAX_RETRIES_PER_FILE = 2
MAX_RETRIES_HEAVY = 3
MAX_GLOBAL_PASSES = 2

# Timeouts (secondes)
VERIFICATION_TIMEOUT = 1800   # 30 min
HEAVY_FILE_TIMEOUT    = 5400  # 90 min
NUTRITION_TIMEOUT     = 5400  # 90 min

HEADLESS = os.getenv("HEADLESS", "false").lower() in {"1", "true", "yes"}

# -------------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(), logging.FileHandler("commcare_downloader.log", encoding="utf-8")]
)
log = logging.getLogger("commcare-downloader")

# -------------------------------------------------------------------
# HELPERS (filesystem & noms)
# -------------------------------------------------------------------
def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path

def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def build_pattern_with_today(base: str) -> re.Pattern:
    """
    Gère (tolérant) :
      Base (created YYYY-MM-DD) YYYY-MM-DD.xlsx
      Base (created YYYY-MM-DD at HH.MM) YYYY-MM-DD.xlsx
      Base YYYY-MM-DD.xlsx
      + suffixes (1)
    """
    date = today_str()
    base_esc = re.escape(base)
    pat = rf"^{base_esc}\s*(?:\("
    pat += rf"created\s+\d{{4}}-\d{{2}}-\d{{2}}(?:\s+at\s+\d{{2}}\.\d{{2}})?"
    pat += rf"\)\s*)?{re.escape(date)}(?:\s+\(\d+\))?\.xlsx$"
    return re.compile(pat, re.IGNORECASE)

def list_xlsx(folder: str) -> List[str]:
    return [os.path.basename(p) for p in glob.glob(os.path.join(folder, "*.xlsx"))]

def list_partial(folder: str) -> List[str]:
    # Chrome .crdownload ; Edge .partial
    return glob.glob(os.path.join(folder, "*.crdownload")) + glob.glob(os.path.join(folder, "*.partial"))

def file_for_base_today(base: str, folder: str) -> Optional[str]:
    pat = build_pattern_with_today(base)
    candidates = list_xlsx(folder)
    # 1) match par regex
    for f in candidates:
        if pat.match(f):
            return os.path.join(folder, f)
    # 2) fallback: même base en préfixe + mtime du jour
    for f in candidates:
        if f.lower().startswith(base.lower()):
            p = os.path.join(folder, f)
            try:
                ts = datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d")
                if ts == today_str():
                    return p
            except Exception:
                continue
    return None

def size_mb(path: str) -> float:
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except Exception:
        return 0.0

def is_stable(path: str, pause: float = 3.0) -> bool:
    if not os.path.exists(path): return False
    s1 = os.path.getsize(path)
    time.sleep(pause)
    if not os.path.exists(path): return False
    s2 = os.path.getsize(path)
    return abs(s2 - s1) <= 1024  # ~1KB

def cleanup_stuck_partials(folder: str, older_than_sec: int = 300) -> int:
    """Nettoyage des téléchargements partiels « bloqués »."""
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

# -------------------------------------------------------------------
# SELENIUM CORE (VM Knockout helpers)
# -------------------------------------------------------------------
def _get_download_vm(driver):
    try:
        return driver.execute_script("""
            try {
              var el = document.getElementById('download-progress');
              if (!el) return null;
              if (window.ko && ko.dataFor) { return ko.dataFor(el) || null; }
              return null;
            } catch(e) { return null; }
        """)
    except Exception:
        return None

def _vm_is_ready(driver) -> bool:
    try:
        return bool(driver.execute_script("""
            try {
              var el = document.getElementById('download-progress');
              if (!el || !window.ko || !ko.dataFor) return false;
              var vm = ko.dataFor(el);
              return vm && vm.isDownloadReady && vm.isDownloadReady();
            } catch(e) { return false; }
        """))
    except Exception:
        return False

def _vm_download_url(driver) -> Optional[str]:
    try:
        url = driver.execute_script("""
            try {
              var el = document.getElementById('download-progress');
              if (!el || !window.ko || !ko.dataFor) return '';
              var vm = ko.dataFor(el);
              if (vm && vm.downloadUrl) { return vm.downloadUrl() || ''; }
              return '';
            } catch(e) { return ''; }
        """)
        return url if url else None
    except Exception:
        return None

def _progress_pct(driver) -> int:
    try:
        return int(driver.execute_script("""
            try {
              var bar = document.getElementById('download-progress-bar');
              if (!bar) return 0;
              var t = bar.textContent || '';
              var m = t.match(/(\\d+)%/);
              if (m) return parseInt(m[1], 10);
              var w = (bar.style && bar.style.width) ? bar.style.width : '0%';
              var n = w.replace('%','');
              return parseInt(n || '0', 10);
            } catch(e){ return 0; }
        """))
    except Exception:
        return 0

def unfreeze_ui(driver):
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        ActionChains(driver).move_by_offset(1, 1).click().perform()
        body.send_keys(Keys.ESCAPE)
    except Exception:
        pass

def set_date_range(driver, start_date="2024-01-01", end_date=None):
    end_date = end_date or today_str()
    try:
        # Attendre que l’overlay "downloadInProgress" disparaisse si présent
        try:
            WebDriverWait(driver, 30).until_not(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".form-notice[data-bind*='downloadInProgress']"))
            )
        except Exception:
            pass

        # IDs alternatifs / CSS fallback
        try:
            el = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.ID, "id_date_range")))
        except TimeoutException:
            try:
                el = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "date_range")))
            except TimeoutException:
                el = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='date_range'], input[data-bind*='dateRange']"))
                )

        el.click()
        time.sleep(0.5)
        el.send_keys(Keys.CONTROL, "a")
        time.sleep(0.2)
        el.send_keys(Keys.DELETE)
        time.sleep(0.2)
        el.send_keys(f"{start_date} to {end_date}")
        el.send_keys(Keys.TAB)
        time.sleep(0.8)

        # Déclenche explicitement un 'change' pour les bindings Knockout
        try:
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}))", el)
        except Exception:
            pass

        try:
            value = el.get_attribute("value")
            log.info(f"Valeur du champ date après set_date_range: {value}")
        except Exception:
            log.warning("Impossible de lire la valeur du champ date après set_date_range")
    except Exception as e:
        log.warning(f"Date range non appliquée: {e}")

def click_download(driver, patience: int) -> bool:
    """
    Attend que l’export soit prêt côté Knockout (isDownloadReady),
    récupère downloadUrl() et le déclenche.
    Fallback: surveille la barre à 100% puis tente le lien primaire (agnostique).
    """
    end = time.time() + patience
    # S’assurer que la modale est visible
    try:
        WebDriverWait(driver, 300).until(EC.visibility_of_element_located((By.ID, "download-progress")))
        log.info("Modale #download-progress détectée (visible)")
    except Exception as e:
        log.warning(f"Modale #download-progress introuvable/retardée: {e}")

    last_pct = -1
    while time.time() < end:
        # 1) Signal “ready” du ViewModel
        if _vm_is_ready(driver):
            url = _vm_download_url(driver)
            if url:
                # URL parfois relative -> absolutiser
                if url.startswith("/"):
                    url = urljoin(driver.current_url, url)
                log.info(f"Download prêt (VM). URL détectée: {url}")
                try:
                    driver.execute_script("window.location = arguments[0];", url)
                    return True
                except Exception as e:
                    log.warning(f"Echec déclenchement par URL: {e}")
            else:
                log.info("VM prêt mais downloadUrl() vide; on patiente 2s…")
                time.sleep(2)
                continue

        # 1-bis) Fallback très court : s'il existe déjà un <a> primaire visible avec href, utilise-le
        try:
            a_now = driver.find_element(By.CSS_SELECTOR, "#download-progress a.btn-primary[href]")
            href_now = a_now.get_attribute("href") or ""
            if href_now:
                if href_now.startswith("/"):
                    href_now = urljoin(driver.current_url, href_now)
                log.info(f"URL directe détectée sans VM: {href_now}")
                driver.execute_script("window.location = arguments[0];", href_now)
                return True
        except Exception:
            pass

        # 2) Fallback: suivre la progression
        pct = _progress_pct(driver)
        if pct != last_pct:
            log.info(f"Progression export: {pct}%")
            last_pct = pct
        if pct >= 100:
            # Après 100%, reprendre le lien primaire (agnostique du suffixe)
            try:
                a = WebDriverWait(driver, 60).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "#download-progress a.btn-primary[href]"))
                )
                href = a.get_attribute("href") or ""
                if href:
                    if href.startswith("/"):
                        href = urljoin(driver.current_url, href)
                    # Navigation directe (plus fiable en CI)
                    try:
                        driver.execute_script("window.location = arguments[0];", href)
                        return True
                    except Exception:
                        pass
                    log.info(f"Lien de téléchargement visible après 100% — href={href}")
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", a)
                        a.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", a)
                    return True
            except Exception:
                # Certains écrans gardent le lien caché; on réessaie via VM
                url = _vm_download_url(driver)
                if url:
                    if url.startswith("/"):
                        url = urljoin(driver.current_url, url)
                    log.info(f"URL détectée après 100% via VM: {url}")
                    driver.execute_script("window.location = arguments[0];", url)
                    return True
        time.sleep(2)

    # Dump HTML si échec
    try:
        modale = driver.find_element(By.ID, "download-progress")
        html = modale.get_attribute("outerHTML")
        log.error(f"HTML modale download-progress:\n{html}")
        try:
            error_elem = modale.find_element(By.CSS_SELECTOR, ".alert strong[data-bind*='downloadError']")
            if error_elem.is_displayed():
                log.error(f"Message d’erreur dans la modale: {error_elem.text}")
        except Exception:
            pass
    except Exception as e:
        log.error(f"Impossible de capturer le HTML de la modale: {e}")
    return False

def trigger_download(base: str, driver) -> None:
    """
    Déclenche « Prepare » puis laisse click_download gérer le "ready".
    """
    url = EXPORT_URLS[base]
    driver.get(url)
    time.sleep(2)
    set_date_range(driver, "2021-01-01")

    # bouton Prepare — sélecteurs tolérants (form/case)
    btns = [
        (By.CSS_SELECTOR, "form#download-export-form button[type='submit']"),
        (By.CSS_SELECTOR, "form.download-form button[type='submit']"),
        (By.XPATH, "//form[contains(@id,'download-export-form')]//button"),
        (By.XPATH, "//form[contains(@class,'download-form')]//button"),
        (By.XPATH, "//button[.//span[contains(normalize-space(),'Prepare')]]"),
        (By.XPATH, "//button[contains(., 'Prepare')]"),
    ]
    clicked = False
    for b in btns:
        try:
            el = WebDriverWait(driver, 30).until(EC.element_to_be_clickable(b))
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.3)
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)
            clicked = True
            break
        except Exception:
            continue
    if not clicked:
        raise TimeoutException("Bouton Prepare introuvable")

    # attendre la modale (si affichée)
    try:
        WebDriverWait(driver, 900).until(EC.visibility_of_element_located((By.ID, "download-progress")))
    except TimeoutException:
        log.info("Modale non visible, poursuite…")

def start_chrome(download_dir: str, headless: bool = HEADLESS):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
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
        log.info(f"URL avant login: {driver.current_url}")
        log.info(f"Titre de la page avant login: {driver.title}")
        user = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "id_auth-username")))
        pwd = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "id_auth-password")))
        user.clear(); user.send_keys(email)
        pwd.clear(); pwd.send_keys(password)
        pwd.send_keys(Keys.RETURN)
        WebDriverWait(driver, 60).until(lambda d: "/login" not in d.current_url.lower())
        log.info(f"URL après login: {driver.current_url}")
        log.info(f"Titre de la page après login: {driver.title}")

        # (Sécurité) On NE logge PAS les cookies
        try:
            user_elem = driver.find_element(By.CSS_SELECTOR, "#navbar-profile-menu .username")
            if user_elem and user_elem.text:
                log.info("Utilisateur connecté détecté.")
        except Exception:
            log.warning("Impossible de détecter le nom d’utilisateur après login")
    except TimeoutException:
        log.warning("Login: pas de page de connexion (peut-être déjà connecté)")

# -------------------------------------------------------------------
# TÉLÉCHARGEMENT + VÉRIF (avec stats)
# -------------------------------------------------------------------
def wait_download_done(base: str, folder: str, timeout: int) -> Optional[str]:
    """
    Attend la fin du téléchargement : pas de partials, fichier stable & pattern du jour match.
    """
    end = time.time() + timeout
    while time.time() < end:
        # partials ?
        parts = list_partial(folder)
        if parts:
            time.sleep(2)
            continue

        # fichier final du jour ?
        f = file_for_base_today(base, folder)
        if f and is_stable(f, 3.0):
            return f
        time.sleep(2)
    return None

def download_one(base: str, driver, stats: dict) -> bool:
    """
    Télécharge « 1 fois » si absent. Relance seulement si non terminé/échoué.
     - Utilise Knockout VM ou lien primaire pour déclencher le téléchargement quand prêt.
    """
    already = file_for_base_today(base, DOWNLOAD_DIR)
    if already:
        log.info(f"⏩ Déjà présent: {os.path.basename(already)}")
        stats[base] = {"status": "present", "size_mb": size_mb(already), "seconds": 0.0, "mbps": None}
        return True

    # partial bloqué ?
    cleanup_stuck_partials(DOWNLOAD_DIR, older_than_sec=300)

    # timeouts selon type
    verify_to = VERIFICATION_TIMEOUT
    if base in HEAVY_FILES: verify_to = HEAVY_FILE_TIMEOUT
    if base == "Nutrition": verify_to = NUTRITION_TIMEOUT

    attempts = MAX_RETRIES_HEAVY if base in HEAVY_FILES else MAX_RETRIES_PER_FILE

    ok = False
    last_path = None
    t0 = time.time()
    for k in range(1, attempts + 1):
        log.info(f"📥 {base} — tentative {k}/{attempts}")
        try:
            trigger_download(base, driver)

            # patience pour la phase “ready” + déclenchement
            patience = 900
            if base in HEAVY_FILES or base == "Nutrition":
                patience = 3600
            if not click_download(driver, patience):
                raise TimeoutException("Lien de téléchargement introuvable/inaccessible")

            # attend la fin d'écriture disque
            path = wait_download_done(base, DOWNLOAD_DIR, verify_to)
            if path:
                ok = True
                last_path = path
                break
            else:
                log.warning(f"⏰ Timeout d'attente fin du téléchargement ({verify_to}s)")
        except Exception as e:
            log.warning(f"⚠️ Tentative échouée: {e}")

        # backoff exponentiel
        sleep_sec = min(60, 5 * (2 ** (k - 1)))
        log.info(f"⏳ Backoff avant relance: {sleep_sec}s")
        time.sleep(sleep_sec)

    # entre tentatives, on nettoie les partials bloqués
    cleanup_stuck_partials(DOWNLOAD_DIR, older_than_sec=300)
    time.sleep(2)

    dt = time.time() - t0
    if ok and last_path:
        mb = size_mb(last_path)
        mbps = (mb / dt) if dt > 0 else None
        stats[base] = {
            "status": "downloaded",
            "size_mb": mb,
            "seconds": round(dt, 1),
            "mbps": None if mbps is None else round(mbps, 3)
        }
        log.info(
            f"🎉 OK {base} — {mb:.1f} MB en {dt:.1f}s (~{(mb/dt):.3f} MB/s)" if dt > 0 else f"🎉 OK {base}"
        )
        return True
    else:
        stats[base] = {"status": "failed", "size_mb": None, "seconds": round(dt, 1), "mbps": None}
        log.error(f"❌ Échec {base} après {attempts} tentative(s)")
        return False

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def main():
    from dotenv import load_dotenv
    ensure_dir(DOWNLOAD_DIR)
    log.info("=" * 60)
    log.info(f"🚀 Téléchargements vers: {os.path.abspath(DOWNLOAD_DIR)}")
    log.info("=" * 60)

    # état initial : quoi manque aujourd’hui ?
    missing = []
    for b in EXPECTED_BASES:
        if not file_for_base_today(b, DOWNLOAD_DIR):
            missing.append(b)
    log.info(f"📋 Manquants aujourd’hui: {len(missing)}")

    if not missing:
        log.info("✅ Rien à télécharger — tout est déjà présent.")
        return 0

    # Démarrage Selenium
    driver = start_chrome(DOWNLOAD_DIR, HEADLESS)
    stats: Dict[str, Dict] = {}
    try:
        load_dotenv("id_cc.env")
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD") or os.getenv("PASSWORD_CC")
        if not email or not password:
            raise RuntimeError("Identifiants CommCare manquants (EMAIL / PASSWORD)")

        # Login sur le premier export manquant
        first_url = EXPORT_URLS[missing[0]]
        commcare_login(driver, email, password, first_url)

        total_ok = 0
        passes = 0
        to_download = list(missing)

        while to_download and passes < MAX_GLOBAL_PASSES:
            passes += 1
            log.info(f"================= PASSE #{passes} =================")
            next_round = []

            for base in to_download:
                # Skip si le fichier est apparu entre-temps
                if file_for_base_today(base, DOWNLOAD_DIR):
                    log.info(f"⏩ Déjà présent (skip): {base}")
                    stats.setdefault(
                        base,
                        {"status": "present", "size_mb": size_mb(file_for_base_today(base, DOWNLOAD_DIR)), "seconds": 0.0, "mbps": None}
                    )
                    total_ok += 1
                    continue

                ok = download_one(base, driver, stats)
                if ok:
                    total_ok += 1
                else:
                    # On ne re-tentera que ceux réellement échoués (non présents)
                    if not file_for_base_today(base, DOWNLOAD_DIR):
                        next_round.append(base)

            to_download = next_round
            if to_download and passes < MAX_GLOBAL_PASSES:
                log.info("⏸️ Pause avant relance des échecs…")
                time.sleep(20)

        # Rapport final
        log.info("================= RAPPORT =================")
        total = len(EXPECTED_BASES)
        done_today = sum(1 for b in EXPECTED_BASES if file_for_base_today(b, DOWNLOAD_DIR))
        failed = [b for b in EXPECTED_BASES if not file_for_base_today(b, DOWNLOAD_DIR)]
        log.info(f"Fichiers attendus : {total}")
        log.info(f"Téléchargés présents aujourd’hui : {done_today}")
        log.info(f"Échoués : {len(failed)} — {failed if failed else ''}")

        total_mb = 0.0
        total_time = 0.0
        for b, s in stats.items():
            sz = s.get("size_mb") or 0.0
            tm = s.get("seconds") or 0.0
            total_mb += sz
            total_time += tm
            log.info(f" - {b:40s} | {s['status']:<10s} | {sz:6.1f} MB | {tm:6.1f} s | {('%.3f MB/s' % s['mbps']) if s['mbps'] else '-'}")

        if total_mb > 0 and total_time > 0:
            log.info(f"📊 Volume total: {total_mb:.1f} MB — Temps cumulé: {total_time:.1f} s — Débit moyen ~ {total_mb/total_time:.3f} MB/s")

        # Écrire stats.json pour CI
        run_summary = {
            "expected": total,
            "present_today": done_today,
            "failed_count": len(failed),
            "failed_list": failed,
            "total_mb": round(total_mb, 2),
            "total_time_sec": round(total_time, 1),
            "avg_mbps": round((total_mb / total_time), 3) if total_time > 0 else None,
            "run_date": datetime.now().isoformat(timespec="seconds")
        }
        payload = {"per_file": stats, "run_summary": run_summary}
        try:
            with open("stats.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"Impossible d'écrire stats.json: {e}")

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
