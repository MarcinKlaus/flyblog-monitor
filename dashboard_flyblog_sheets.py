#!/usr/bin/env python3
"""
FlyBlog Monitor - Dashboard WWW czytający z Google Sheets
Wersja dla Streamlit Cloud - nie wymaga lokalnych plików
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
    initial_sidebar_state="expanded"
)

# ID arkusza Google Sheets
GOOGLE_SHEETS_ID = "1uW4Hy9O4R5if0pe9TIkjGO7i-gZBIBklbOHhqdS0GJg"

# Funkcja do wczytywania danych z Google Sheets
@st.cache_data(ttl=60)  # Cache na 60 sekund
def load_data_from_sheets():
    """Wczytuje dane z publicznego arkusza Google Sheets"""
    try:
        # Buduj URL do CSV
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv"
        
        # Wczytaj dane
        df = pd.read_csv(url, header=2)  # Nagłówki są w 3 wierszu (index 2)
        
        # Wyczyść nazwy kolumn
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
        # Usuń 'h' i konwertuj na int
        return int(str(silence_str).replace('h', ''))
    except:
        return 0

# Funkcja do określania priorytetu
def get_priority_emoji(row):
    """Zwraca emoji priorytetu na podstawie danych"""
    try:
        silence_hours = parse_silence_hours(row.get('Milczenie (h)', 'Nigdy'))
        posts_since = int(row.get('Od moderatora', 0))
        
        if silence_hours >= 72:
            return "🔴🔴🔴"
        elif posts_since >= 10:
            return "🔴🔴"
        elif silence_hours >= 48:
            return "🔴"
        elif posts_since >= 5:
            return "🟡"
        elif silence_hours >= 24:
            return "🟠"
        else:
            return "🟢"
    except:
        return "⚪"

# Tytuł
st.title("🔍 FlyBlog Monitor Dashboard")
st.markdown("---")

# Wczytaj dane
df = load_data_from_sheets()

if df is not None and not df.empty:
    # Pobierz czas ostatniego sprawdzenia z pierwszego wiersza
    try:
        # Odczytaj pierwszy wiersz który zawiera info o ostatnim sprawdzeniu
        with st.spinner('Ładowanie danych...'):
            url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv"
            df_header = pd.read_csv(url, nrows=1, header=None)
            last_check = df_header.iloc[0, 0] if not df_header.empty else "Nieznany"
            st.subheader(f"⏰ {last_check}")
    except:
        st.subheader("⏰ Dane z Google Sheets")
    
    # Przygotuj dane
    df['Priority'] = df.apply(get_priority_emoji, axis=1)
    
    # Konwertuj kolumny numeryczne
    numeric_columns = ['Respondent', 'Moderator', 'Od moderatora']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Statystyki w kolumnach
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = len(df)
        st.metric("👥 Wszyscy uczestnicy", total)
    
    with col2:
        # Policz krytyczne przypadki
        critical = 0
        for _, row in df.iterrows():
            silence = parse_silence_hours(row.get('Milczenie (h)', 'Nigdy'))
            posts = int(row.get('Od moderatora', 0))
            if silence >= 72 or posts >= 10:
                critical += 1
        st.metric("🔴 Krytyczne przypadki", critical)
    
    with col3:
        # Policz wymagające uwagi
        warning = 0
        for _, row in df.iterrows():
            silence = parse_silence_hours(row.get('Milczenie (h)', 'Nigdy'))
            posts = int(row.get('Od moderatora', 0))
            if (24 <= silence < 72) or (5 <= posts < 10):
                warning += 1
        st.metric("🟡 Wymagają uwagi", warning)
    
    with col4:
        ok = len(df[df['Priority'] == "🟢"])
        st.metric("🟢 Wszystko OK", ok)
    
    st.markdown("---")
    
    # Filtry w sidebarze
    st.sidebar.header("🔧 Filtry")
    
    # Filtr statusu
    all_priorities = df['Priority'].unique().tolist()
    status_filter = st.sidebar.multiselect(
        "Status",
        options=all_priorities,
        default=all_priorities
    )
    
    # Filtr milczenia
    silence_min = st.sidebar.slider("Milczy minimum (h)", 0, 168, 0)
    
    # Filtr postów od moderatora
    posts_min = st.sidebar.slider("Postów od moderatora minimum", 0, 50, 0)
    
    # Zastosuj filtry
    filtered_df = df[df['Priority'].isin(status_filter)].copy()
    
    # Filtruj po milczeniu
    if 'Milczenie (h)' in filtered_df.columns:
        filtered_df['silence_hours_num'] = filtered_df['Milczenie (h)'].apply(parse_silence_hours)
        filtered_df = filtered_df[filtered_df['silence_hours_num'] >= silence_min]
        filtered_df = filtered_df.drop('silence_hours_num', axis=1)
    
    # Filtruj po postach
    if 'Od moderatora' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Od moderatora'] >= posts_min]
    
    # Sortuj według ważności
    if 'Od moderatora' in filtered_df.columns and 'Milczenie (h)' in filtered_df.columns:
        filtered_df['silence_for_sort'] = filtered_df['Milczenie (h)'].apply(parse_silence_hours)
        filtered_df = filtered_df.sort_values(
            by=['Od moderatora', 'silence_for_sort'], 
            ascending=[False, False]
        ).drop('silence_for_sort', axis=1)
    
    # Tabela z danymi
    st.subheader(f"📊 Uczestnicy ({len(filtered_df)} z {total})")
    
    # Kolejność kolumn
    column_order = ['Priority', 'Nick', 'Email', 'Ostatni post', 'Milczenie (h)', 
                   'Respondent', 'Moderator', 'Od moderatora', 'Status']
    
    # Sprawdź które kolumny istnieją
    existing_columns = [col for col in column_order if col in filtered_df.columns]
    
    # Wyświetl tabelę
    if not filtered_df.empty:
        st.dataframe(
            filtered_df[existing_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Priority": st.column_config.TextColumn("🎯", width="small"),
                "Nick": st.column_config.TextColumn("Nick", width="small"),
                "Email": st.column_config.TextColumn("Email", width="medium"),
                "Ostatni post": st.column_config.TextColumn("Ostatni post", width="small"),
                "Milczenie (h)": st.column_config.TextColumn("Milczy", width="small"),
                "Respondent": st.column_config.NumberColumn("R", width="small"),
                "Moderator": st.column_config.NumberColumn("M", width="small"),
                "Od moderatora": st.column_config.NumberColumn("Od mod.", width="small"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
            }
        )
        
        # Sekcja krytycznych przypadków
        critical_df = filtered_df[filtered_df['Priority'].isin(["🔴🔴🔴", "🔴🔴"])]
        if not critical_df.empty:
            st.markdown("---")
            st.subheader("🚨 Krytyczne przypadki wymagające natychmiastowej uwagi:")
            
            for _, case in critical_df.head(5).iterrows():
                with st.expander(f"{case['Priority']} {case.get('Nick', 'Brak nicku')} - {case.get('Email', 'Brak emaila')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Postów od moderatora:** {case.get('Od moderatora', 0)}")
                        st.write(f"**Ostatni post:** {case.get('Ostatni post', 'Nieznany')}")
                    with col2:
                        st.write(f"**Milczy:** {case.get('Milczenie (h)', 'Nieznane')}")
                        st.write(f"**Status:** {case.get('Status', 'Nieznany')}")
    else:
        st.info("Brak uczestników spełniających kryteria filtrów")
    
    # Automatyczne odświeżanie
    st.markdown("---")
    if st.button("🔄 Odśwież dane"):
        st.cache_data.clear()
        st.rerun()
    
    # Info o automatycznym odświeżaniu
    st.caption("Dashboard odświeża dane z Google Sheets co 60 sekund")
    
    # Link do arkusza
    st.caption(f"[📊 Otwórz arkusz Google Sheets](https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID})")
    
else:
    st.error("❌ Nie można załadować danych z Google Sheets")
    st.info("""
    **Możliwe przyczyny:**
    1. Arkusz nie jest publiczny (udostępnij go z prawami 'Każdy z linkiem może wyświetlać')
    2. Nieprawidłowe ID arkusza
    3. Problem z połączeniem
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        FlyBlog Monitor v1.6 | Dashboard by Streamlit<br>
        <small>Dane z Google Sheets aktualizowane przez monitor lokalny</small>
    </div>
    """,
    unsafe_allow_html=True
)