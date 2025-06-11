#!/usr/bin/env python3
"""
FlyBlog Monitor - Dashboard v2
- Naprawiony problem z "None"
- Lista uczestników na pełnej stronie (bez ramki)
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
        
        # Wczytaj dane - POPRAWKA: skiprows=1 pomija pierwszy wiersz z info
        df = pd.read_csv(url, header=2)
        
        # Wyczyść nazwy kolumn
        df.columns = df.columns.str.strip()
        
        # Debug - pokaż jakie kolumny znalazł
        print(f"Znalezione kolumny: {list(df.columns)}")
        
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

# Tytuł
st.title("🔍 FlyBlog Monitor Dashboard")
st.markdown("---")

# Wczytaj dane
df = load_data_from_sheets()

if df is not None and not df.empty:
    # Pobierz informacje z pierwszego wiersza oryginalnego pliku
    try:
        url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID}/export?format=csv"
        df_header = pd.read_csv(url, nrows=1, header=None)
        last_check = df_header.iloc[0, 0] if not df_header.empty else "Nieznany"
        st.subheader(f"⏰ {last_check}")
    except:
        st.subheader("⏰ Dane z Google Sheets")
    
    # Przygotuj dane
    df['Priority'] = df.apply(get_priority_emoji, axis=1)
    
    # Konwertuj kolumny numeryczne
    numeric_columns = ['Zadania', 'Moderator', 'Bez odp.']
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
        critical = len(df[df['Priority'].isin(['🔴🔴🔴', '🔴🔴'])])
        st.metric("🔴 Krytyczne przypadki", critical)
    
    with col3:
        # Policz wymagające uwagi
        warning = len(df[df['Priority'] == '🟡'])
        st.metric("🟡 Wymagają uwagi", warning)
    
    with col4:
        ok = len(df[df['Priority'] == '🟢'])
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
    posts_min = st.sidebar.slider("Postów bez odpowiedzi minimum", 0, 50, 0)
    
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
    
    # Nagłówek sekcji
    st.subheader(f"📊 Uczestnicy ({len(filtered_df)} z {total})")
    
    # NOWE: Link do projektu na górze
    if len(last_check) > 20 and "Projekt:" in last_check:
        try:
            project_id = re.search(r'Projekt:\s*(\d+)', last_check).group(1)
            st.markdown(f"🔗 [Otwórz projekt {project_id} na FlyBlog](https://forum.flyblog.pl/{project_id}/)")
        except:
            pass
    
    st.markdown("---")
    
    # ZMIANA: Zamiast st.dataframe używamy iteracji po uczestnikach
    # To pozwala na dodanie przycisków i lepsze formatowanie
    
    for idx, row in filtered_df.iterrows():
        # Kontener dla każdego uczestnika
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([0.5, 2, 3, 1, 1])
            
            with col1:
                st.write(row['Priority'])
            
            with col2:
                # Nick z możliwością skopiowania
                nick = row.get('Nick', 'Brak')
                if nick and nick != '-':
                    st.markdown(f"**{nick}**")
                    if st.button("📋", key=f"copy_{idx}", help=f"Kopiuj nick: {nick}"):
                        # Streamlit nie ma wbudowanego kopiowania, ale możemy pokazać
                        st.code(nick, language=None)
                else:
                    st.write("_Brak nicku_")
                
                # Email/Identyfikator w mniejszym foncie
                email = row.get('Identyfikator', '')
                if email and email != '-':
                    st.caption(email)
            
            with col3:
                # Status i szczegóły
                st.write(row.get('Status', ''))
                
                # Dodatkowe info
                details = []
                if 'Ostatni post' in row:
                    details.append(f"Ostatni post: {row['Ostatni post']}")
                if 'Milczenie' in row:
                    details.append(f"Milczy: {row['Milczenie']}")
                if 'Bez odp.' in row and row['Bez odp.'] > 0:
                    details.append(f"Bez odp.: {row['Bez odp.']}")
                
                if details:
                    st.caption(" | ".join(details))
            
            with col4:
                # Zadania
                zadania = row.get('Zadania', 0)
                moderator = row.get('Moderator', 0)
                st.write(f"📝 {zadania}/{moderator}")
            
            with col5:
                # Miejsce na przyszłe akcje
                if row['Priority'] in ['🔴🔴🔴', '🔴🔴']:
                    st.write("❗ PILNE")
            
            # Separator między uczestnikami
            st.divider()
    
    # Sekcja krytycznych przypadków
    critical_df = filtered_df[filtered_df['Priority'].isin(['🔴🔴🔴', '🔴🔴'])]
    if not critical_df.empty:
        st.markdown("---")
        st.subheader("🚨 Krytyczne przypadki wymagające natychmiastowej uwagi:")
        
        for _, case in critical_df.head(5).iterrows():
            with st.expander(f"{case['Priority']} {case.get('Nick', 'Brak nicku')} - {case.get('Status', 'Brak statusu')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Email:** {case.get('Identyfikator', 'Brak')}")
                    st.write(f"**Ostatni post:** {case.get('Ostatni post', 'Nieznany')}")
                    st.write(f"**Zadań:** {case.get('Zadania', 0)}")
                with col2:
                    st.write(f"**Milczy:** {case.get('Milczenie', 'Nieznane')}")
                    st.write(f"**Bez odpowiedzi:** {case.get('Bez odp.', 0)}")
                    if case.get('Imię'):
                        st.write(f"**Imię:** {case.get('Imię', '')}")
    
    # Automatyczne odświeżanie
    st.markdown("---")
    if st.button("🔄 Odśwież dane"):
        st.cache_data.clear()
        st.rerun()
    
    # Info
    st.caption("Dashboard odświeża dane z Google Sheets co 60 sekund")
    st.caption(f"[📊 Otwórz arkusz Google Sheets](https://docs.google.com/spreadsheets/d/{GOOGLE_SHEETS_ID})")
    
else:
    st.error("❌ Nie można załadować danych z Google Sheets")
    st.info("""
    **Możliwe przyczyny:**
    1. Arkusz nie jest publiczny
    2. Nieprawidłowe ID arkusza
    3. Problem z połączeniem
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        FlyBlog Monitor v2.0 | Dashboard by Streamlit<br>
        <small>Dane z Google Sheets aktualizowane przez monitor lokalny</small>
    </div>
    """,
    unsafe_allow_html=True
)
