#!/usr/bin/env python3
"""
FlyBlog Monitor - Dashboard v3 - wersja kompaktowa
- Jedna linia na uczestnika
- Bez zbędnych elementów
- Maksymalna ilość info na ekranie
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import re

# Konfiguracja strony
st.set_page_config(
    page_title="FlyBlog Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"  # Domyślnie schowany sidebar
)

# ID arkusza Google Sheets
GOOGLE_SHEETS_ID = "1uW4Hy9O4R5if0pe9TIkjGO7i-gZBIBklbOHhqdS0GJg"

# Funkcja do wczytywania danych z Google Sheets
@st.cache_data(ttl=60)  # Cache na 60 sekund
def load_data_from_sheets():
    """Wczytuje dane z publicznego arkusza Google Sheets"""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv"
        df = pd.read_csv(url, header=2)  # Nagłówki są w 3 wierszu
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Błąd wczytywania danych: {str(e)}")
        return None

# Funkcja do parsowania czasu milczenia
def parse_silence_hours(silence_str):
    """Konwertuje string '339h' na liczbę godzin"""
    if pd.isna(silence_str) or silence_str == 'Nigdy':
        return 999
    try:
        return int(str(silence_str).replace('h', ''))
    except:
        return 0

# Funkcja do określania priorytetu emoji
def get_priority_emoji(row):
    """Zwraca emoji priorytetu na podstawie statusu"""
    try:
        status = str(row.get('Status', '')).upper()
        
        if 'NIGDY NIE PISAŁ' in status or 'TRAGEDIA' in status:
            return "🔴🔴🔴"
        elif 'NIE PISAŁ WCZORAJ' in status or 'KRYTYCZNE' in status:
            return "🔴🔴"
        elif 'BRAKUJE' in status and 'ZADAŃ' in status:
            return "🔴"
        elif 'NIE ZACZĄŁ DZISIAJ' in status or 'POSTÓW' in status:
            return "🟡"
        elif 'SUPER' in status or 'OK' in status:
            return "🟢"
        else:
            return "⚪"
    except:
        return "⚪"

# CSS dla kompaktowego wyświetlania
st.markdown("""
<style>
    .stApp {
        max-width: 100%;
    }
    .user-line {
        font-family: monospace;
        font-size: 14px;
        line-height: 1.8;
        padding: 2px 0;
    }
    .nick {
        font-weight: bold;
        min-width: 150px;
        display: inline-block;
    }
    .separator {
        color: #666;
        margin: 0 8px;
    }
</style>
""", unsafe_allow_html=True)

# Tytuł
st.title("🔍 FlyBlog Monitor")

# Wczytaj dane
df = load_data_from_sheets()

if df is not None and not df.empty:
    # Pobierz informacje z pierwszego wiersza
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv"
        df_header = pd.read_csv(url, nrows=1, header=None)
        last_check = df_header.iloc[0, 0] if not df_header.empty else "Nieznany"
        
        # Wyciągnij numer projektu
        project_match = re.search(r'Projekt:\s*(\d+)', last_check)
        project_id = project_match.group(1) if project_match else "1139"
        
        # Nagłówek z linkiem
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"⏰ {last_check}")
        with col2:
            st.markdown(f"[🔗 Otwórz FlyBlog {project_id}](https://forum.flyblog.pl/{project_id}/)")
    except:
        st.subheader("⏰ Dane z Google Sheets")
    
    # Przygotuj dane
    df['Priority'] = df.apply(get_priority_emoji, axis=1)
    
    # Konwertuj kolumny numeryczne
    numeric_columns = ['Zadania', 'Moderator', 'Bez odp.']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Statystyki
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Wszyscy", len(df))
    with col2:
        critical = len(df[df['Priority'].isin(['🔴🔴🔴', '🔴🔴'])])
        st.metric("🔴 Krytyczne", critical)
    with col3:
        warning = len(df[df['Priority'] == '🟡'])
        st.metric("🟡 Uwaga", warning)
    with col4:
        ok = len(df[df['Priority'] == '🟢'])
        st.metric("🟢 OK", ok)
    
    st.markdown("---")
    
    # Filtry w sidebarze (opcjonalne)
    with st.sidebar:
        st.header("🔧 Filtry")
        
        # Filtr statusu
        all_priorities = df['Priority'].unique().tolist()
        status_filter = st.multiselect(
            "Status",
            options=all_priorities,
            default=all_priorities
        )
        
        # Filtr milczenia
        silence_min = st.slider("Milczy minimum (h)", 0, 168, 0)
        
        # Filtr postów
        posts_min = st.slider("Bez odpowiedzi min", 0, 50, 0)
    
    # Zastosuj filtry
    filtered_df = df[df['Priority'].isin(status_filter)].copy()
    
    # Filtruj po milczeniu
    if 'Milczenie' in filtered_df.columns:
        filtered_df['silence_hours_num'] = filtered_df['Milczenie'].apply(parse_silence_hours)
        filtered_df = filtered_df[filtered_df['silence_hours_num'] >= silence_min]
        filtered_df = filtered_df.drop('silence_hours_num', axis=1)
    
    # Filtruj po postach
    if 'Bez odp.' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Bez odp.'] >= posts_min]
    
    # Sortuj według priorytetu
    priority_order = {'🔴🔴🔴': 0, '🔴🔴': 1, '🔴': 2, '🟡': 3, '🟢': 4, '⚪': 5}
    filtered_df['priority_order'] = filtered_df['Priority'].map(priority_order)
    filtered_df = filtered_df.sort_values('priority_order').drop('priority_order', axis=1)
    
    # Nagłówek listy
    st.subheader(f"📊 Uczestnicy ({len(filtered_df)} z {len(df)})")
    
    # KOMPAKTOWA LISTA - wszystko w jednej linii
    st.markdown("```")
    for _, row in filtered_df.iterrows():
        # Przygotuj części
        emoji = row['Priority']
        nick = str(row.get('Nick', 'brak'))[:15].ljust(15)  # Wyrównaj do 15 znaków
        status = row.get('Status', 'Brak statusu')[:30]  # Max 30 znaków
        zadania = f"Zadań: {row.get('Zadania', 0)}"
        milczenie = f"Milczy: {row.get('Milczenie', '?')}"
        bez_odp = f"Bez odp: {row.get('Bez odp.', 0)}" if row.get('Bez odp.', 0) > 0 else ""
        
        # Złóż linię
        parts = [emoji, nick, status, zadania, milczenie]
        if bez_odp:
            parts.append(bez_odp)
        
        line = " | ".join(parts)
        st.text(line)
    st.markdown("```")
    
    # Krytyczne przypadki - opcjonalnie na dole
    critical_df = filtered_df[filtered_df['Priority'].isin(['🔴🔴🔴', '🔴🔴'])]
    if not critical_df.empty and len(critical_df) > 5:
        st.markdown("---")
        st.subheader(f"🚨 Top 5 najpilniejszych:")
        st.markdown("```")
        for _, case in critical_df.head(5).iterrows():
            nick = case.get('Nick', 'brak').ljust(15)
            email = case.get('Identyfikator', '')[:30]
            st.text(f"❗ {nick} ({email}) - {case.get('Status', '')}")
        st.markdown("```")
    
    # Przyciski na dole
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Odśwież dane"):
            st.cache_data.clear()
            st.rerun()
    with col2:
        st.caption("Dane odświeżają się co 60 sekund")
    
else:
    st.error("❌ Nie można załadować danych z Google Sheets")

# Minimalistyczny footer
st.markdown("---")
st.caption("FlyBlog Monitor v3.0 - wersja kompaktowa")
