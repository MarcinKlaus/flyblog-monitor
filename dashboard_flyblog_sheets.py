#!/usr/bin/env python3
"""
FlyBlog Monitor - Dashboard v3.2 - dostosowany do nowych kolumn
- Używa nowych nazw kolumn: IleWpisów, KiedyOstatni, IleMilczy, BezOdpMod, Podsumowanie
- Dwie kolumny uczestników
- "by Insight Shot" w tytule
- Link zamiast "PEŁNY"
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import re

# Konfiguracja strony
st.set_page_config(
    page_title="ReflexLab Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ID arkusza Google Sheets
GOOGLE_SHEETS_ID = "1uW4Hy9O4R5if0pe9TIkjGO7i-gZBIBklbOHhqdS0GJg"

# CSS dla Manrope i lepszego wyglądu
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@200..800&display=swap');
    
    * {
        font-family: 'Manrope', sans-serif !important;
    }
    
    .stApp {
        max-width: 100%;
        font-family: 'Manrope', sans-serif !important;
    }
    
    .block-container {
        padding-top: 2rem;
    }
    
    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 5px;
    }
    
    /* Ukryj przewijanie w tabelach */
    [data-testid="stDataFrame"] > div {
        max-height: none !important;
    }
    
    /* Manrope dla wszystkich elementów */
    .stMarkdown, .stText, h1, h2, h3, p, span, div {
        font-family: 'Manrope', sans-serif !important;
    }
</style>
""", unsafe_allow_html=True)

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
        # Sprawdzamy obie możliwe nazwy kolumn
        if 'Podsumowanie' in row:
            status = str(row.get('Podsumowanie', '')).upper()
        else:
            status = str(row.get('Status', '')).upper()
        
        if 'NIE ZALOGOWAŁ' in status or 'NIGDY NIE PISAŁ' in status or 'TRAGEDIA' in status:
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
    .block-container {
        padding-top: 2rem;
    }
    div[data-testid="stHorizontalBlock"] > div {
        padding: 0 5px;
    }
</style>
""", unsafe_allow_html=True)

# Tytuł z "by Insight Shot" i przycisk odświeżania w prawym górnym rogu
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("🔍 ReflexLab by Insight Shot")
with col_refresh:
    if st.button("🔄 Odśwież dane"):
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
        
        # Nagłówek z linkiem zamiast "PEŁNY"
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
    
    # Konwertuj kolumny numeryczne - UŻYWAMY NOWYCH NAZW
    numeric_columns = ['IleWpisów', 'BezOdpMod']
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
    
    # UŻYWAMY NOWEJ NAZWY KOLUMNY
    if 'IleMilczy' in filtered_df.columns:
        filtered_df['silence_hours_num'] = filtered_df['IleMilczy'].apply(parse_silence_hours)
        filtered_df = filtered_df[filtered_df['silence_hours_num'] >= silence_min]
        filtered_df = filtered_df.drop('silence_hours_num', axis=1)
    
    # UŻYWAMY NOWEJ NAZWY KOLUMNY
    if 'BezOdpMod' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['BezOdpMod'] >= posts_min]
    
    # Sortuj według priorytetu
    priority_order = {'🔴🔴🔴': 0, '🔴🔴': 1, '🔴': 2, '🟡': 3, '🟢': 4, '⚪': 5}
    filtered_df['priority_order'] = filtered_df['Priority'].map(priority_order)
    filtered_df = filtered_df.sort_values('priority_order').drop('priority_order', axis=1)
    
    # Nagłówek listy
    st.subheader(f"📊 Uczestnicy ({len(filtered_df)} z {len(df)})")
    
    # TABELA UCZESTNIKÓW W DWÓCH KOLUMNACH
    st.subheader(f"📊 Uczestnicy ({len(filtered_df)} z {len(df)})")
    
    # Podziel dane na dwie części
    half = len(filtered_df) // 2
    left_df = filtered_df.iloc[:half]
    right_df = filtered_df.iloc[half:]
    
    # Przygotuj dane do tabel
    def prepare_table_data(df_part):
        table_data = []
        for _, row in df_part.iterrows():
            # Sprawdzamy które nazwy kolumn istnieją
            if 'IleWpisów' in row:
                ile_wpisow = row.get('IleWpisów', 0)
            else:
                ile_wpisow = row.get('Zadania', 0)
                
            if 'IleMilczy' in row:
                milczenie = str(row.get('IleMilczy', '?'))
            else:
                milczenie = str(row.get('Milczenie', '?'))
                
            if 'BezOdpMod' in row:
                bez_odp = row.get('BezOdpMod', 0)
            else:
                bez_odp = row.get('Bez odp.', 0)
                
            if 'KiedyOstatni' in row:
                ostatni = str(row.get('KiedyOstatni', '-'))
            else:
                ostatni = str(row.get('Ostatni post', '-'))
                
            if 'Podsumowanie' in row:
                status = str(row.get('Podsumowanie', '-'))
            else:
                status = str(row.get('Status', '-'))
            
            # Dodaj email
            email = str(row.get('Email', row.get('Identyfikator', '')))
            nick_with_email = f"{row.get('Nick', '')} ({email[:20]}...)" if len(email) > 20 else f"{row.get('Nick', '')} ({email})"
            
            table_data.append({
                'St': row['Priority'],
                'Uczestnik': nick_with_email,
                'W': ile_wpisow,
                'Ost': ostatni[:10],  # Skrócone
                'M': milczenie,
                'B': bez_odp,
                'Status': status[:30]  # Skrócone
            })
        return pd.DataFrame(table_data)
    
    # Dwie kolumny z tabelami
    col1, col2 = st.columns(2)
    
    # Konfiguracja kolumn dla obu tabel
    column_config = {
        "St": st.column_config.TextColumn(
            "📊",
            width="small",
            help="Status priorytetu"
        ),
        "Uczestnik": st.column_config.TextColumn(
            "Uczestnik (email)",
            width="large"
        ),
        "W": st.column_config.NumberColumn(
            "Wpisów",
            help="Liczba wpisów",
            format="%d",
            width="small"
        ),
        "Ost": st.column_config.TextColumn(
            "Ostatni",
            help="Data ostatniego wpisu",
            width="small"
        ),
        "M": st.column_config.TextColumn(
            "Milczy",
            help="Godziny milczenia",
            width="small"
        ),
        "B": st.column_config.NumberColumn(
            "Bez",
            help="Bez odpowiedzi moderatora",
            format="%d",
            width="small"
        ),
        "Status": st.column_config.TextColumn(
            "Podsumowanie",
            width="medium"
        )
    }
    
    with col1:
        if not left_df.empty:
            table_left = prepare_table_data(left_df)
            st.dataframe(
                table_left,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                height=min(len(table_left) * 35 + 50, 600)  # Dynamiczna wysokość
            )
    
    with col2:
        if not right_df.empty:
            table_right = prepare_table_data(right_df)
            st.dataframe(
                table_right,
                use_container_width=True,
                hide_index=True,
                column_config=column_config,
                height=min(len(table_right) * 35 + 50, 600)  # Dynamiczna wysokość
            )
    
    # Top 5 najpilniejszych
    critical_df = filtered_df[filtered_df['Priority'].isin(['🔴🔴🔴', '🔴🔴'])]
    if not critical_df.empty and len(critical_df) > 5:
        st.markdown("---")
        st.subheader(f"🚨 Top 5 najpilniejszych:")
        st.markdown("```")
        for _, case in critical_df.head(5).iterrows():
        else:
            status_text = ""
        
        table_data.append({
            'Nick': str(case.get('Nick', 'brak'))[:15],
            'Email': str(case.get('Email', case.get('Identyfikator', '')))[:30],
            'Status': status_text
        })
    
    if table_data:
        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Nick": "Uczestnik",
                "Email": "Email", 
                "Status": "Problem"
            }
        )
    
    # Tabelka szczegółowa (opcjonalnie)
    with st.expander("📋 Szczegółowa tabela"):
        # Wybierz tylko istotne kolumny z NOWYMI NAZWAMI
        display_columns = ['Nick', 'Email', 'IleWpisów', 'KiedyOstatni', 'IleMilczy', 'BezOdpMod', 'Podsumowanie']
        available_columns = [col for col in display_columns if col in filtered_df.columns]
        st.dataframe(
            filtered_df[available_columns],
            use_container_width=True,
            hide_index=True
        )
    
    # Przyciski na dole - USUNIĘTE BO JUŻ JEST NA GÓRZE
    st.markdown("---")
    st.caption("Dane odświeżają się automatycznie co 60 sekund")
    
else:
    st.error("❌ Nie można załadować danych z Google Sheets")

# Footer
st.markdown("---")
st.caption("ReflexLab v3.3 by Insight Shot")
