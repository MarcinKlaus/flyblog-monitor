#!/usr/bin/env python3
"""
FlyBlog Monitor v2.4 - używa nicków jako identyfikatorów
Sprawdza aktywność uczestników i zapisuje do Google Sheets
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from colorama import init, Fore, Style
import re

# Colorama
init()

# === KONFIGURACJA PROJEKTU ===
print("=" * 50)
print("=== FlyBlog Monitor v2.4 ===")
print("=" * 50)

# Projekt
PROJECT_ID = input("\nPodaj numer projektu (np. 1136): ").strip()
print(f"✓ Projekt: {PROJECT_ID}")

# Dni i zadania
print("\n=== KONFIGURACJA PROJEKTU ===")
project_days = int(input("Ile dni trwa główna część projektu? (domyślnie 3): ").strip() or "3")
print(f"✓ Projekt trwa {project_days} dni")

# Zadania per dzień
tasks_per_day = {}
total_tasks = 0
print("\nPodaj liczbę zadań na każdy dzień:")
for day in range(1, project_days + 1):
    tasks = int(input(f"Dzień {day} - ile zadań?: ").strip())
    tasks_per_day[day] = tasks
    total_tasks += tasks

print(f"\n✓ Łącznie zadań: {total_tasks}")

# Aktualny dzień
current_day = int(input(f"\nW którym dniu projektu jesteśmy? (1-{project_days}): ").strip())
expected_tasks_today = sum(tasks_per_day[d] for d in range(1, current_day + 1))
print(f"✓ Dzień {current_day}, oczekiwane minimum {expected_tasks_today - tasks_per_day[current_day]} zadań")

# Tryb pracy
print("\n=== TRYB PRACY ===")
print("1. Testowy (3 osoby)")
print("2. Pełny (wszyscy)")
work_mode = input("Wybierz (1 lub 2): ").strip()
TEST_MODE = (work_mode == "1")
print(f"✓ Tryb {'TESTOWY' if TEST_MODE else 'PEŁNY'}")

# Interwał
interval_minutes = int(input("\nCo ile minut sprawdzać? ").strip())
INTERVAL_SECONDS = interval_minutes * 60
print(f"✓ Sprawdzam co {interval_minutes} min")
print("=" * 50)

# Stałe
EMAIL = "marcin.klaus@insightshot.pl"
PASSWORD = "Poland0k"
BASE_URL = "https://forum.flyblog.pl"
PROJECT_URL = f"{BASE_URL}/{PROJECT_ID}/"
SPREADSHEET_ID = "1uW4Hy9O4R5if0pe9TIkjGO7i-gZBIBklbOHhqdS0GJg"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def print_status(message, status="INFO"):
    """Kolorowe statusy"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "INFO":
        print(f"{Fore.BLUE}[{timestamp}]{Style.RESET_ALL} {message}")
    elif status == "SUCCESS":
        print(f"{Fore.GREEN}[{timestamp}]{Style.RESET_ALL} {message}")
    elif status == "WARNING":
        print(f"{Fore.YELLOW}[{timestamp}]{Style.RESET_ALL} {message}")
    elif status == "ERROR":
        print(f"{Fore.RED}[{timestamp}]{Style.RESET_ALL} {message}")

def setup_driver():
    """Uruchamia Chrome"""
    print_status("Uruchamiam przeglądarkę...")
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.maximize_window()
    return driver

def czekaj_na_zaladowanie(driver, timeout=10):
    """Czeka na załadowanie strony"""
    print_status("⏳ Czekam na załadowanie...", "INFO")
    
    # Szukaj loadera
    loader_selectors = [".loader", ".spinner", ".loading", "[class*='spin']"]
    loader_found = False
    
    for selector in loader_selectors:
        try:
            loader = driver.find_element(By.CSS_SELECTOR, selector)
            if loader.is_displayed():
                print_status(f"  → Znaleziono loader", "INFO")
                loader_found = True
                WebDriverWait(driver, timeout).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                )
                print_status("  → Loader zniknął", "SUCCESS")
                break
        except:
            continue
    
    if not loader_found:
        time.sleep(1)
    
    time.sleep(0.5)

def login_to_flyblog(driver):
    """Logowanie"""
    print_status(f"Loguję się jako {EMAIL}...")
    driver.get(PROJECT_URL)
    czekaj_na_zaladowanie(driver)
    
    if "WITAJ" in driver.page_source.upper():
        print_status("Już zalogowany!", "SUCCESS")
        return True
    
    try:
        wait = WebDriverWait(driver, 10)
        username = wait.until(EC.presence_of_element_located((By.NAME, "log-username")))
        password = driver.find_element(By.NAME, "log-password")
        button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Zaloguj się')]")))
        
        username.clear()
        username.send_keys(EMAIL)
        password.clear()
        password.send_keys(PASSWORD)
        button.click()
        
        try:
            wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "WITAJ"))
            print_status("Zalogowano!", "SUCCESS")
            return True
        except:
            print_status("Błąd logowania", "ERROR")
            return False
            
    except Exception as e:
        print_status(f"Błąd: {e}", "ERROR")
        return False

def open_admin_panel(driver):
    """Otwiera panel admina"""
    try:
        wait = WebDriverWait(driver, 10)
        print_status("Otwieram panel admina...", "INFO")
        admin_icon = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".forum-admin-switch")))
        
        driver.execute_script("arguments[0].scrollIntoView(true);", admin_icon)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", admin_icon)
        
        time.sleep(2)
        print_status("Panel admina otwarty", "SUCCESS")
        return True
            
    except Exception as e:
        print_status(f"Błąd panelu admina: {e}", "ERROR")
        return False

def go_to_participants(driver):
    """Przechodzi do uczestników"""
    wait = WebDriverWait(driver, 10)
    
    selectors = ["//span[contains(text(), 'UCZESTNICY')]", 
                 "//span[contains(text(), 'Uczestnicy')]",
                 "//a[contains(text(), 'UCZESTNICY')]"]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for el in elements:
                if el.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", el)
                    
                    try:
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr, tr")))
                        print_status("Lista uczestników", "SUCCESS")
                        return True
                    except:
                        czekaj_na_zaladowanie(driver)
                        return True
        except:
            continue
    
    print_status("Nie znaleziono uczestników", "ERROR")
    return False

def calculate_hours_since_post(last_post_date):
    """Godziny od posta"""
    if not last_post_date or last_post_date == "Nigdy":
        return 999
    
    try:
        if isinstance(last_post_date, str) and len(last_post_date) > 10 and '-' in last_post_date:
            post_datetime = datetime.fromisoformat(last_post_date)
        else:
            # Polski format
            polish_months = {
                'sty': 1, 'lut': 2, 'mar': 3, 'kwi': 4,
                'maj': 5, 'cze': 6, 'lip': 7, 'sie': 8,
                'wrz': 9, 'paź': 10, 'lis': 11, 'gru': 12
            }
            
            parts = last_post_date.split()
            if len(parts) >= 3:
                day = int(parts[0])
                month_str = parts[1]
                time_str = parts[2]
                
                if month_str in polish_months:
                    month = polish_months[month_str]
                    hour, minute = map(int, time_str.split(':'))
                    current_year = datetime.now().year
                    post_datetime = datetime(current_year, month, day, hour, minute)
                else:
                    return 999
            else:
                return 999
        
        current_time = datetime.now()
        time_diff = current_time - post_datetime
        return int(time_diff.total_seconds() / 3600)
    except:
        return 999

def find_column_indices(driver):
    """Znajduje kolumny email i nick"""
    print_status("Analizuję tabelę...")
    
    headers = None
    header_row = None
    
    # Szukaj wiersza z "Akcja"
    try:
        all_rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in all_rows:
            if "Akcja" in row.text and "Adres email" in row.text:
                header_row = row
                print_status("  → Znaleziono nagłówki", "SUCCESS")
                break
    except:
        pass
    
    if header_row:
        headers = header_row.find_elements(By.TAG_NAME, "th")
        if not headers:
            headers = header_row.find_elements(By.TAG_NAME, "td")
    
    if not headers:
        print_status("  → Używam domyślnych pozycji", "WARNING")
        return 1, 2
    
    email_column_index = None
    nick_column_index = None
    
    for i, header in enumerate(headers):
        header_text = header.text.lower().strip()
        if header_text:
            if "email" in header_text or "e-mail" in header_text:
                email_column_index = i
                print_status(f"  → Email w kolumnie {i}", "SUCCESS")
            elif "nick" in header_text:
                nick_column_index = i
                print_status(f"  → Nick w kolumnie {i}", "SUCCESS")
    
    return email_column_index or 1, nick_column_index or 2

def get_participants_list(driver):
    """Lista uczestników"""
    print_status("Pobieram uczestników...")
    
    wait = WebDriverWait(driver, 10)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody tr, tr")))
    except:
        print_status("Brak tabeli", "ERROR")
        return [], None, None
    
    email_idx, nick_idx = find_column_indices(driver)
    
    participants = []
    all_rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr, tr")
    
    print_status(f"Znaleziono {len(all_rows)} wierszy", "INFO")
    
    valid_count = 0
    no_login_count = 0
    
    for row_idx, row in enumerate(all_rows):
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            
            if len(cells) <= max(email_idx, nick_idx):
                continue
            
            email = cells[email_idx].text.strip()
            if not email:
                continue
                
            nick = cells[nick_idx].text.strip() if len(cells) > nick_idx else ""
            
            # KLUCZOWA ZMIANA: Jeśli nie ma nicku = nie zalogował się
            if not nick:
                no_login_count += 1
                print_status(f"  → {email} - BRAK NICKU (nie zalogował się)", "WARNING")
                # Możemy dodać do listy ze specjalnym statusem
                participants.append({
                    'email': email,
                    'nick': '--- BRAK ---',
                    'name': '',
                    'row_element': row,
                    'row_index': row_idx,
                    'last_activity': None,
                    'total_posts': 0,
                    'respondent_posts': 0,
                    'moderator_posts': 0,
                    'posts_since_moderator': 0,
                    'last_moderator_date': None,
                    'no_login': True  # Flaga że się nie zalogował
                })
                continue
            
            # Szukaj imienia
            name = ""
            if len(cells) > 7:
                for idx in [4, 5, 6, 7]:
                    try:
                        text = cells[idx].text.strip()
                        if text and not any(x in text for x in [',', 'GOTOWI', 'aktywny', '2025']):
                            name = text
                            break
                    except:
                        pass
            
            participants.append({
                'email': email,
                'nick': nick,
                'name': name,
                'row_element': row,
                'row_index': row_idx,
                'last_activity': None,
                'total_posts': 0,
                'respondent_posts': 0,
                'moderator_posts': 0,
                'posts_since_moderator': 0,
                'last_moderator_date': None,
                'no_login': False
            })
            valid_count += 1
            
            # Tryb testowy
            if TEST_MODE and valid_count >= 3:
                print_status("  → Tryb testowy: 3 osoby", "WARNING")
                break
            
        except:
            continue
    
    print_status(f"Znaleziono {valid_count} aktywnych uczestników", "SUCCESS")
    if no_login_count > 0:
        print_status(f"Znaleziono {no_login_count} niezalogowanych", "WARNING")
    
    return participants, email_idx, nick_idx

def check_participant_activity(driver, participant):
    """Sprawdza aktywność uczestnika"""
    # Jeśli się nie zalogował, nie sprawdzamy aktywności
    if participant.get('no_login', False):
        print_status(f"  → {participant['email']} - pomijam (nie zalogował się)", "WARNING")
        return
        
    print_status(f"  → Sprawdzam aktywność dla: {participant['nick']}", "INFO")
    try:
        wait = WebDriverWait(driver, 5)
        row = participant['row_element']
        
        # Szukaj ikony ustawień
        print_status("  → Szukam ikony ustawień...", "INFO")
        settings_icon = None
        
        # Ulepszone selektory dla przycisku dropdown
        selectors = [
            "button.dropdown-toggle",
            "button[data-toggle='dropdown']",
            ".btn.dropdown-toggle",
            "button.btn-secondary.dropdown-toggle",
            "[id*='context-menu']",
            ".fa-cog",
            ".fa-gear",
            ".dropdown-toggle",
            "button",
        ]
        
        for selector in selectors:
            try:
                icons = row.find_elements(By.CSS_SELECTOR, selector)
                for icon in icons:
                    if icon.is_displayed():
                        # Sprawdź czy to na pewno przycisk menu
                        if 'dropdown' in icon.get_attribute('class') or \
                           icon.get_attribute('data-toggle') == 'dropdown' or \
                           'context-menu' in (icon.get_attribute('id') or ''):
                            settings_icon = icon
                            print_status(f"  → Znaleziono ikonę: {selector}", "SUCCESS")
                            break
                if settings_icon:
                    break
            except:
                continue
        
        if not settings_icon:
            print_status("  → NIE znaleziono ikony ustawień!", "ERROR")
            return
            
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", settings_icon)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", settings_icon)
        
        print_status("  → Kliknięto ikonę, czekam na menu...", "INFO")
        time.sleep(2)
        
        # Znajdź "Pokaż wypowiedzi"
        print_status("  → Szukam 'Pokaż wypowiedzi'...", "INFO")
        links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Pokaż wypowiedzi') and not(contains(text(), 'Usuń'))]")
        show_link = None
        
        print_status(f"  → Znaleziono {len(links)} linków z tekstem 'Pokaż wypowiedzi'", "INFO")
        
        for link in links:
            if link.is_displayed():
                show_link = link
                print_status("  → Znaleziono klikalny link 'Pokaż wypowiedzi'", "SUCCESS")
                break
        
        if not show_link:
            print_status("  → NIE znaleziono 'Pokaż wypowiedzi'!", "ERROR")
            return
        
        # Otwórz posty
        print_status("  → Otwieram posty użytkownika...", "INFO")
        href = show_link.get_attribute('href')
        original_windows = driver.window_handles
        
        if href and 'ShowPosts' in href:
            match = re.search(r"ShowPosts\('([^']+)'\)", href)
            if match:
                user_id = match.group(1)
                driver.execute_script(f"Participants.ShowPosts('{user_id}')")
                
                # Czekaj na nowe okno
                print_status("  → Czekam na nowe okno...", "INFO")
                WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(original_windows))
                new_window = [w for w in driver.window_handles if w not in original_windows][0]
                driver.switch_to.window(new_window)
                print_status("  → Przełączono do nowego okna", "SUCCESS")
                czekaj_na_zaladowanie(driver)
        
        # Analizuj posty
        analyze_posts(driver, participant)
        
        # Zamknij okno
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            print_status("  → Powrót do głównego okna", "INFO")
            
    except Exception as e:
        print_status(f"  → Błąd podczas sprawdzania: {str(e)}", "ERROR")
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        raise e

def analyze_posts(driver, participant):
    """Analizuje posty"""
    # Czekaj aż strona zacznie się ładować
    print_status("  → Czekam na stronę z postami...", "INFO")
    
    # Sprawdzaj różne oznaki że strona się załadowała
    for i in range(30):  # Max 30 sekund
        time.sleep(1)
        
        # Sprawdź czy to strona z postami
        page_text = driver.page_source
        
        # Jeśli to nadal lista uczestników - czekaj
        if "Liczba rekordów:" in page_text and "Akcja Adres email Nick" in page_text:
            if i > 10:  # Po 10 sekundach to pewnie nie ma postów
                print_status("  → Brak postów (nadal lista uczestników)", "INFO")
                break
            continue
            
        # Jeśli widać datę w formacie YYYY-MM-DD = są posty!
        if re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', page_text):
            print_status(f"  → Strona załadowana po {i+1}s", "SUCCESS")
            break
            
        # Jeśli widać "fl-response" = są posty
        if "fl-response" in page_text:
            print_status(f"  → Znaleziono posty po {i+1}s", "SUCCESS")
            break
    
    # Teraz normalnie analizuj
    page_text = driver.find_element(By.TAG_NAME, "body").text
    
    # Sprawdź czy to lista uczestników
    if "Liczba rekordów:" in page_text and "Akcja Adres email Nick" in page_text:
        participant['total_posts'] = 0
        participant['respondent_posts'] = 0
        participant['moderator_posts'] = 0
        participant['posts_since_moderator'] = 0
        participant['last_moderator_date'] = None
        participant['last_activity'] = None
        return
    
    posts = driver.find_elements(By.CSS_SELECTOR, "div.fl-response")
    print_status(f"  → Znaleziono {len(posts)} elementów fl-response", "INFO")
    
    respondent_dates = []
    moderator_dates = []
    all_posts_data = []
    
    for post in posts:
        try:
            user_info = post.find_element(By.CSS_SELECTOR, "div.fl-response__user-info")
            is_moderator = "fl-moderator" in user_info.get_attribute("class")
            
            date_elem = post.find_element(By.CSS_SELECTOR, "div.fl-response__menu p")
            # POPRAWKA: Weź tylko pierwszy węzeł tekstowy (datę) ignorując zagnieżdżone elementy
            date_text = driver.execute_script("return arguments[0].childNodes[0].textContent", date_elem).strip()
            
            try:
                # NAPRAWKA: Wyczyść datę z dodatkowych znaków
                date_text = date_text.strip()
                # Jeśli są dodatkowe znaki po dacie, weź tylko pierwsze 16 znaków
                if len(date_text) > 16:
                    date_text = date_text[:16]
                
                post_time = datetime.strptime(date_text, '%Y-%m-%d %H:%M')
                
                if is_moderator:
                    moderator_dates.append(post_time)
                else:
                    respondent_dates.append(post_time)
                
                all_posts_data.append((post_time, is_moderator))
            except Exception as e:
                print_status(f"  → Błąd parsowania daty '{date_text}': {str(e)}", "ERROR")
                continue
        except:
            continue
    
    # Sortuj chronologicznie
    all_posts_data.sort(key=lambda x: x[0])
    
    last_moderator_date = max(moderator_dates) if moderator_dates else None
    last_respondent_date = max(respondent_dates) if respondent_dates else None
    
    # Policz posty po moderatorze
    posts_since_moderator = 0
    if last_moderator_date:
        for date, is_moderator in all_posts_data:
            if not is_moderator and date > last_moderator_date:
                posts_since_moderator += 1
    else:
        posts_since_moderator = len(respondent_dates)
    
    # Aktualizuj dane
    participant['total_posts'] = len(respondent_dates) + len(moderator_dates)
    participant['respondent_posts'] = len(respondent_dates)
    participant['moderator_posts'] = len(moderator_dates)
    participant['posts_since_moderator'] = posts_since_moderator
    participant['last_moderator_date'] = last_moderator_date.isoformat() if last_moderator_date else None
    participant['last_activity'] = last_respondent_date.isoformat() if last_respondent_date else None
    
    print_status(f"  → Uczestnik: {len(respondent_dates)} postów, Moderator: {len(moderator_dates)} postów", "INFO")

def determine_status(participant, hours_since, posts_since_moderator):
    """Określa status"""
    # Specjalny status dla niezalogowanych
    if participant.get('no_login', False):
        return "NIE ZALOGOWAŁ SIĘ ANI RAZU!", "CRITICAL_3"
        
    expected_tasks_minimum = sum(tasks_per_day[d] for d in range(1, current_day))
    total_posts = participant.get('respondent_posts', 0)
    
    # POPRAWKA: Obsługa "Nigdy"
    if hours_since >= 999:
        return "NIGDY NIE PISAŁ! Pilne!", "CRITICAL_3"
    
    # Milczy 2+ dni
    if hours_since >= 48:
        return f"TRAGEDIA! Milczy {hours_since//24} dni!", "CRITICAL_3"
    
    # Nie pisał wczoraj
    if hours_since >= 24:
        return f"Nie pisał WCZORAJ! ({hours_since}h)", "CRITICAL_2"
    
    # Za mało zadań
    if total_posts < expected_tasks_minimum:
        missing = expected_tasks_minimum - total_posts
        return f"Brakuje {missing} zadań!", "CRITICAL_1"
    
    # Nie zaczął dzisiaj
    if total_posts == expected_tasks_minimum:
        return f"Nie zaczął DZISIAJ", "WARNING"
    
    # Posty bez odpowiedzi
    if posts_since_moderator >= 10:
        return f"{posts_since_moderator} postów bez odp.!", "WARNING"
    
    if posts_since_moderator >= 5:
        return f"{posts_since_moderator} postów czeka", "WARNING"
    
    # OK
    if total_posts >= expected_tasks_today:
        return f"SUPER! {total_posts}/{expected_tasks_today} zadań", "OK"
    else:
        progress = total_posts - expected_tasks_minimum
        return f"OK - robi ({progress}/{tasks_per_day[current_day]})", "OK"

def get_all_participants_from_pages(driver):
    """Pobiera uczestników ze WSZYSTKICH stron"""
    all_participants = []
    email_idx = None
    nick_idx = None
    page_num = 1
    
    while True:
        print_status(f"Sprawdzam stronę {page_num}...")
        
        # Pobierz uczestników z aktualnej strony
        participants, curr_email_idx, curr_nick_idx = get_participants_list(driver)
        
        # Zapisz indeksy z pierwszej strony
        if page_num == 1:
            email_idx = curr_email_idx
            nick_idx = curr_nick_idx
        
        # NOWE: Dodaj informację o numerze strony do każdego uczestnika
        for participant in participants:
            participant['page_number'] = page_num
        
        all_participants.extend(participants)
        
        # Sprawdź czy są kolejne strony
        try:
            # Szukaj linków paginacji (1, 2, 3, >>)
            pagination_links = driver.find_elements(By.CSS_SELECTOR, "a")
            next_page_found = False
            
            for link in pagination_links:
                link_text = link.text.strip()
                # Szukaj linku z numerem następnej strony lub ">>"
                if link_text == str(page_num + 1) or link_text == "»" or link_text == ">>":
                    # Sprawdź czy link jest klikalny
                    if link.is_displayed() and link.is_enabled():
                        print_status(f"  → Przechodzę do strony {page_num + 1}...", "INFO")
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.5)
                        link.click()
                        czekaj_na_zaladowanie(driver)
                        page_num += 1
                        next_page_found = True
                        break
            
            if not next_page_found:
                print_status(f"  → Koniec stron (sprawdzono {page_num})", "SUCCESS")
                break
                
        except Exception as e:
            print_status(f"  → Koniec stron lub błąd: {str(e)[:50]}", "INFO")
            break
    
    return all_participants, email_idx, nick_idx

def get_participants_activity(driver):
    """Główna funkcja - PROSTSZA WERSJA"""
    print_status(f"Sprawdzam projekt {PROJECT_ID}...")
    if TEST_MODE:
        print_status("TRYB TESTOWY", "WARNING")
    
    driver.get(PROJECT_URL)
    czekaj_na_zaladowanie(driver)
    
    if not open_admin_panel(driver):
        return []
    
    if not go_to_participants(driver):
        return []
    
    # Lista wszystkich przetworzonych uczestników
    all_participants = []
    page_num = 1
    processed_count = 0
    
    # Znajdź indeksy kolumn tylko raz
    email_idx, nick_idx = find_column_indices(driver)
    
    while True:
        print_status(f"Przetwarzam stronę {page_num}...")
        
        # Pobierz wszystkie wiersze na AKTUALNEJ stronie
        all_rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr, tr")
        rows_on_page = 0
        
        for row_idx, row in enumerate(all_rows):
            # Pomijaj nagłówki
            if "Akcja" in row.text and "Adres email" in row.text:
                continue
                
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) <= max(email_idx, nick_idx):
                continue
                
            # Pobierz dane z wiersza
            email = cells[email_idx].text.strip()
            if not email:
                continue
                
            nick = cells[nick_idx].text.strip() if len(cells) > nick_idx else ""
            
            # Jeśli nie ma nicku = nie zalogował się
            if not nick:
                print_status(f"  → {email} - BRAK NICKU (nie zalogował się)", "WARNING")
                participant = {
                    'email': email,
                    'nick': '--- BRAK ---',
                    'name': '',
                    'Nick': '--- BRAK ---',
                    'Email': email,
                    'Imię': '',
                    'Respondent': 0,
                    'Moderator': 0,
                    'Ostatni post': 'Nigdy',
                    'Milczenie (h)': 'Nigdy',
                    'Od moderatora': 0,
                    'Status': 'NIE ZALOGOWAŁ SIĘ ANI RAZU!',
                    'Status Level': 'CRITICAL_3',
                    'Godziny milczenia': 999,
                    'no_login': True
                }
                all_participants.append(participant)
                continue
            
            # Szukaj imienia
            name = ""
            if len(cells) > 7:
                for idx in [4, 5, 6, 7]:
                    try:
                        text = cells[idx].text.strip()
                        if text and not any(x in text for x in [',', 'GOTOWI', 'aktywny', '2025']):
                            name = text
                            break
                    except:
                        pass
            
            rows_on_page += 1
            processed_count += 1
            
            print_status(f"{nick} ({processed_count})...")
            
            # Utwórz uczestnika
            participant = {
                'email': email,
                'nick': nick,
                'name': name,
                'row_element': row,
                'last_activity': None,
                'total_posts': 0,
                'respondent_posts': 0,
                'moderator_posts': 0,
                'posts_since_moderator': 0,
                'last_moderator_date': None,
                'no_login': False
            }
            
            # Sprawdź aktywność OD RAZU - bez wracania do strony!
            try:
                check_participant_activity(driver, participant)
                
                # Obliczenia
                hours_since = calculate_hours_since_post(participant.get('last_activity'))
                silence_formatted = "Nigdy" if hours_since >= 999 else f"{hours_since}h"
                
                posts_since_moderator = participant.get('posts_since_moderator', 0)
                status_text, status_level = determine_status(participant, hours_since, posts_since_moderator)
                
                # Formatuj datę
                if participant.get('last_activity'):
                    try:
                        dt = datetime.fromisoformat(participant['last_activity'])
                        polish_months = ['sty', 'lut', 'mar', 'kwi', 'maj', 'cze', 
                                       'lip', 'sie', 'wrz', 'paź', 'lis', 'gru']
                        formatted_date = f"{dt.day} {polish_months[dt.month-1]} {dt.hour:02d}:{dt.minute:02d}"
                        participant['Ostatni post'] = formatted_date
                    except:
                        participant['Ostatni post'] = 'Błąd'
                else:
                    participant['Ostatni post'] = 'Nigdy'
                
                # Przygotuj dane do zapisu
                participant['Nick'] = participant['nick']
                participant['Email'] = participant['email']
                participant['Imię'] = participant['name']
                participant['Respondent'] = participant.get('respondent_posts', 0)
                participant['Moderator'] = participant.get('moderator_posts', 0)
                participant['Milczenie (h)'] = silence_formatted
                participant['Od moderatora'] = posts_since_moderator
                participant['Status'] = status_text
                participant['Status Level'] = status_level
                participant['Godziny milczenia'] = hours_since
                
                # Pokaż status
                if status_level in ["CRITICAL_3", "CRITICAL_2", "CRITICAL_1"]:
                    print_status(f"  → {status_text}", "ERROR")
                elif status_level == "WARNING":
                    print_status(f"  → {status_text}", "WARNING")
                else:
                    print_status(f"  → {status_text}", "SUCCESS")
                    
            except Exception as e:
                print_status(f"  → Błąd: {str(e)[:50]}", "ERROR")
                participant['Nick'] = participant['nick']
                participant['Email'] = participant['email']
                participant['Imię'] = participant['name']
                participant['Respondent'] = 0
                participant['Moderator'] = 0
                participant['Ostatni post'] = 'Błąd'
                participant['Milczenie (h)'] = 'Błąd'
                participant['Od moderatora'] = 0
                participant['Status'] = 'BŁĄD'
                participant['Status Level'] = 'ERROR'
            
            all_participants.append(participant)
            
            # W trybie testowym - sprawdź limit
            if TEST_MODE and processed_count >= 3:
                print_status("  → Tryb testowy: sprawdzono 3 osoby", "WARNING")
                return all_participants
            
            time.sleep(0.5)
        
        # Sprawdź czy są kolejne strony
        try:
            pagination_links = driver.find_elements(By.CSS_SELECTOR, "a")
            next_page_found = False
            
            for link in pagination_links:
                link_text = link.text.strip()
                if link_text == str(page_num + 1) or link_text == "»" or link_text == ">>":
                    if link.is_displayed() and link.is_enabled():
                        print_status(f"  → Przechodzę do strony {page_num + 1}...", "INFO")
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        time.sleep(0.5)
                        link.click()
                        czekaj_na_zaladowanie(driver)
                        page_num += 1
                        next_page_found = True
                        
                        # Znajdź indeksy kolumn na nowej stronie
                        email_idx, nick_idx = find_column_indices(driver)
                        break
            
            if not next_page_found:
                print_status(f"  → Koniec (sprawdzono {page_num} stron)", "SUCCESS")
                break
                
        except Exception as e:
            print_status(f"  → Koniec stron: {str(e)[:50]}", "INFO")
            break
    
    return all_participants

def authenticate_google_sheets():
    """Google Sheets API"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=SCOPES
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        print_status("Google Sheets API - OK", "SUCCESS")
        return service
    except Exception as e:
        print_status(f"Błąd API: {e}", "ERROR")
        return None

def clear_sheet(service, range_name):
    """Czyści arkusz"""
    try:
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
    except:
        pass

def save_to_google_sheets(participants_data):
    """Zapis do Sheets"""
    print_status("Zapisuję do Google Sheets...")
    
    try:
        service = authenticate_google_sheets()
        if not service:
            return
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mode_text = "TEST (3 osoby)" if TEST_MODE else "PEŁNY"
        config_text = f"Dzień {current_day}/{project_days} | Zadań: {tasks_per_day[current_day]} | {mode_text}"
        
        clear_sheet(service, 'A1:Z1000')
        
        # Dane
        header_info = [[f"Sprawdzono: {current_time} | Projekt: {PROJECT_ID} | {config_text}"]]
        empty_row = [[""]]
        headers = [["Nick", "Email", "Imię", "IleWpisów", "KiedyOstatni", 
                   "IleMilczy", "BezOdpMod", "Podsumowanie"]]
        
        # Sortuj
        priority_order = {'CRITICAL_3': 0, 'CRITICAL_2': 1, 'CRITICAL_1': 2,
                         'WARNING': 3, 'OK': 4, 'ERROR': 5}
        participants_data.sort(key=lambda x: priority_order.get(x.get('Status Level', 'ERROR'), 5))
        
        # Przygotuj wiersze
        data_rows = []
        for p in participants_data:
            data_rows.append([
                p.get('Nick', ''),
                p.get('Email', ''),
                p.get('Imię', ''),
                p.get('Respondent', 0),  # IleWpisów
                p.get('Ostatni post', ''),  # KiedyOstatni
                p.get('Milczenie (h)', ''),  # IleMilczy
                p.get('Od moderatora', 0),  # BezOdp
                p.get('Status', '')  # Podsumowanie
            ])
        
        all_data = header_info + empty_row + headers + data_rows
        
        # Zapisz
        body = {'values': all_data}
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print_status(f"Zapisano {result.get('updatedCells')} komórek", "SUCCESS")
        
        # Formatowanie
        requests = [
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 12}}},
                    "fields": "userEnteredFormat.textFormat"
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": 2, "endRowIndex": 3},
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {"bold": True},
                            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
                        }
                    },
                    "fields": "userEnteredFormat"
                }
            }
        ]
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests}
        ).execute()
        
        # Statystyki
        total = len(participants_data)
        critical = sum(1 for p in participants_data if p.get('Status Level', '').startswith('CRITICAL'))
        warning = sum(1 for p in participants_data if p.get('Status Level') == 'WARNING')
        ok = sum(1 for p in participants_data if p.get('Status Level') == 'OK')
        no_login = sum(1 for p in participants_data if p.get('no_login', False))
        
        print_status(f"\nPODSUMOWANIE:", "INFO")
        print_status(f"  Wszyscy: {total}", "INFO")
        if no_login > 0:
            print_status(f"  ⚫ Niezalogowani: {no_login}", "ERROR")
        if critical > 0:
            print_status(f"  🔴 Krytyczne: {critical}", "ERROR")
        if warning > 0:
            print_status(f"  🟡 Uwaga: {warning}", "WARNING")
        print_status(f"  🟢 OK: {ok}", "SUCCESS")
        
    except Exception as e:
        print_status(f"Błąd zapisu: {e}", "ERROR")

def main():
    """Main"""
    print_status(f"\nStart dla projektu {PROJECT_ID}", "INFO")
    print_status(f"Dzień {current_day}/{project_days}", "INFO")
    if TEST_MODE:
        print_status("TRYB TESTOWY", "WARNING")
    
    driver = None
    try:
        driver = setup_driver()
        
        if not login_to_flyblog(driver):
            return
        
        participants_data = get_participants_activity(driver)
        
        if participants_data:
            save_to_google_sheets(participants_data)
            print_status("\nZakończono!", "SUCCESS")
        else:
            print_status("Brak danych", "WARNING")
            
    except Exception as e:
        print_status(f"Błąd: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()
            print_status("Zamknięto przeglądarkę", "INFO")

def run_continuous_monitoring():
    """Pętla monitoringu"""
    print_status(f"\nMONITORING CIĄGŁY - Projekt {PROJECT_ID}", "INFO")
    print_status(f"Sprawdzam co {interval_minutes} min", "INFO")
    print_status("Ctrl+C = stop\n", "WARNING")
    
    iteration = 1
    while True:
        try:
            print(f"\n{'='*60}")
            print_status(f"ITERACJA #{iteration}", "INFO")
            print(f"{'='*60}")
            
            main()
            
            print_status(f"\nCzekam {interval_minutes} min...", "INFO")
            
            for i in range(INTERVAL_SECONDS, 0, -30):
                if i <= 30:
                    time.sleep(i)
                    break
                print(f"\r  Zostało: {i//60}:{i%60:02d}  ", end='', flush=True)
                time.sleep(30)
            
            print()
            iteration += 1
            
        except KeyboardInterrupt:
            print_status("\n\nZatrzymano", "WARNING")
            break
        except Exception as e:
            print_status(f"\nBłąd: {e}", "ERROR")
            print_status(f"Ponownie za {interval_minutes} min...", "WARNING")
            time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    run_continuous_monitoring()
