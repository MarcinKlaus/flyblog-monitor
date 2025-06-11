#!/usr/bin/env python3
"""
ReflexLab™ Monitor - Dashboard v4.0
- Czcionka Manrope
- Guzik odświeżania w nagłówku
- ReflexLab™ zamiast FlyBlog Monitor
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import re

# Konfiguracja strony
st.set_page_config(
    page_title="ReflexLab™ Monitor",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ID arkusza Google Sheets
GOOGLE_SHEETS_ID = "1uW4Hy9O4R5if0pe9TIkjGO7i-gZBIBklbOHhqdS0GJg"

# Funkcja do wczytywania danych z Google Sheets
@st.cache_data(ttl=60)
def load_data_from_sheets():
    """Wczytuje dane z publicznego arkusza Google Sheets"""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv"
        df = pd.read_csv(url, header=2)
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

# CSS dla czcionki Manrope i stylów
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@200;300;400;500;600;700;800&display=swap');
    
    /* Aplikuj czcionkę Manrope globalnie */
    html, body, [class*="css"] {
        font-family: 'Manrope', sans-serif;
    }
    
    .stApp {
        max-width: 100%;
        font-family: 'Manrope', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
    }
    
    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 5px;
    }
    
    /* Stylizacja tytułu */
    h1 {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* Stylizacja wszystkich elementów tekstowych */
    h2, h3, h4, h5, h6, p, span, div, label {
        font-family: 'Manrope', sans-serif !important;
    }
    
    /* Stylizacja metryk */
    [data-testid="metric-container"] {
        font-family: 'Manrope', sans-serif !important;
    }
    
    /* Stylizacja guzika odświeżania */
    .refresh-button {
        display: inline-block;
        margin-left: 20px;
        vertical-align: middle;
    }
    
    /* Ukryj domyślny padding nagłówka */
    .main-header {
        display: flex;
        align-items: center;
        gap: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Nagłówek z guzikiem odświeżania
col_title, col_refresh = st.columns([6, 1])

with col_title:
    st.markdown("# 🔬 ReflexLab™ Monitor by Insight Shot")

with col_refresh:
    if st.button("🔄 Odśwież", key="refresh_top", help="Kliknij aby odświeżyć dane"):
        st.cache_data.clear()
        st.rerun()

# Wczytaj dane
df = load_data_from_sheets()

if df is not None and not df.empty:
    # Pobierz informacje z pierwszego wiersza
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv"
        df_header = pd.read_csv(url, nrows=1, header=None)
        header_text = df_header.iloc[0, 0] if not df_header.empty else ""
        
        # Parsuj informacje z nagłówka
        project_match = re.search(r'Projekt:\s*(\d+)', header_text)
        project_id = project_match.group(1) if project_match else "1139"
        
        day_match = re.search(r'Dzień\s*(\d+)/(\d+)', header_text)
        day_info = f"Dzień {day_match.group(1)}/{day_match.group(2)}" if day_match else ""
        
        tasks_match = re.search(r'Zadań:\s*(\d+)', header_text)
        tasks_info = f"Zadań: {tasks_match.group(1)}" if tasks_match else ""
        
        time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', header_text)
        check_time = time_match.group(1) if time_match else "Nieznany czas"
        
        # Nagłówek z linkiem
        parts = [f"⏰ {check_time}"]
        if day_info:
            parts.append(day_info)
        if tasks_info:
            parts.append(tasks_info)
        
        header_line = " | ".join(parts) + f" | [🔗 Otwórz FlyBlog {project_id}](https://forum.flyblog.pl/{project_id}/)"
        st.subheader(header_line)
        
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
    
    # Filtry w sidebarze
    with st.sidebar:
        st.header("🔧 Filtry")
        
        all_priorities = df['Priority'].unique().tolist()
        status_filter = st.multiselect(
            "Status",
            options=all_priorities,
            default=all_priorities
        )
        
        silence_min = st.slider("Milczy minimum (h)", 0, 168, 0)
        posts_min = st.slider("Bez odpowiedzi min", 0, 50, 0)
    
    # Zastosuj filtry
    filtered_df = df[df['Priority'].isin(status_filter)].copy()
    
    if 'Milczenie' in filtered_df.columns:
        filtered_df['silence_hours_num'] = filtered_df['Milczenie'].apply(parse_silence_hours)
        filtered_df = filtered_df[filtered_df['silence_hours_num'] >= silence_min]
        filtered_df = filtered_df.drop('silence_hours_num', axis=1)
    
    if 'Bez odp.' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Bez odp.'] >= posts_min]
    
    # Sortuj według priorytetu
    priority_order = {'🔴🔴🔴': 0, '🔴🔴': 1, '🔴': 2, '🟡': 3, '🟢': 4, '⚪': 5}
    filtered_df['priority_order'] = filtered_df['Priority'].map(priority_order)
    filtered_df = filtered_df.sort_values('priority_order').drop('priority_order', axis=1)
    
    # Nagłówek listy
    st.subheader(f"📊 Uczestnicy ({len(filtered_df)} z {len(df)})")
    
    # DWIE KOLUMNY UCZESTNIKÓW
    # Podziel dane na dwie części
    half = len(filtered_df) // 2
    left_df = filtered_df.iloc[:half]
    right_df = filtered_df.iloc[half:]
    
    # Utwórz dwie kolumny
    col_left, col_right = st.columns(2)
    
    # Funkcja do formatowania linii
    def format_line(row):
        emoji = row['Priority']
        nick = str(row.get('Nick', 'brak'))[:12].ljust(12)
        status = str(row.get('Status', 'Brak'))[:25]
        zadania = f"Z:{row.get('Zadania', 0)}"
        milczenie = str(row.get('Milczenie', '?'))
        
        parts = [emoji, nick, status, zadania, milczenie]
        return " | ".join(parts)
    
    # Lewa kolumna
    with col_left:
        st.markdown("```")
        for _, row in left_df.iterrows():
            st.text(format_line(row))
        st.markdown("```")
    
    # Prawa kolumna
    with col_right:
        st.markdown("```")
        for _, row in right_df.iterrows():
            st.text(format_line(row))
        # Jeśli nieparzysta liczba, dodaj pustą linię
        if len(right_df) < len(left_df):
            st.text("")
        st.markdown("```")
    
    # Top 5 najpilniejszych
    critical_df = filtered_df[filtered_df['Priority'].isin(['🔴🔴🔴', '🔴🔴'])]
    if not critical_df.empty and len(critical_df) > 5:
        st.markdown("---")
        st.subheader(f"🚨 Top 5 najpilniejszych:")
        st.markdown("```")
        for _, case in critical_df.head(5).iterrows():
            nick = str(case.get('Nick', 'brak'))[:15].ljust(15)
            email = str(case.get('Identyfikator', ''))[:30]
            status = str(case.get('Status', ''))
            st.text(f"❗ {nick} ({email}) - {status}")
        st.markdown("```")
    
    # Informacja o automatycznym odświeżaniu
    st.markdown("---")
    st.caption("📡 Dane odświeżają się automatycznie co 60 sekund")
    
else:
    st.error("❌ Nie można załadować danych z Google Sheets")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Spróbuj ponownie"):
            st.cache_data.clear()
            st.rerun()

# Footer
st.markdown("---")
st.caption("ReflexLab™ Monitor v4.0 by Insight Shot")
