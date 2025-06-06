#!/usr/bin/env python3
"""
FlyBlog Monitor - Dashboard WWW
Piękny dashboard do oglądania na stronie WWW
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
import time

# Konfiguracja strony
st.set_page_config(
    page_title="FlyBlog Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tytuł
st.title("🔍 FlyBlog Monitor Dashboard")
st.markdown("---")

# Funkcja do ładowania danych
@st.cache_data(ttl=60)  # Cache na 60 sekund
def load_data():
    try:
        with open('flyblog_activity_cache_v16.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except:
        return None

# Funkcja do obliczania godzin milczenia
def calculate_silence_hours(last_activity):
    if not last_activity or last_activity == 'Brak danych':
        return 999
    try:
        dt = datetime.fromisoformat(last_activity)
        diff = datetime.now() - dt
        return diff.total_seconds() / 3600
    except:
        return 999

# Funkcja do formatowania czasu
def format_time_ago(last_activity):
    if not last_activity or last_activity == 'Brak danych':
        return 'Nigdy'
    try:
        dt = datetime.fromisoformat(last_activity)
        diff = datetime.now() - dt
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h temu"
        elif hours > 0:
            return f"{hours}h {minutes}m temu"
        else:
            return f"{minutes}m temu"
    except:
        return 'Błąd'

# Ładuj dane
data = load_data()

if data:
    # Czas ostatniego sprawdzenia
    last_check = data.get('timestamp', 'Nieznany')
    st.subheader(f"⏰ Ostatnie sprawdzenie: {last_check}")
    
    # Przygotuj dane uczestników
    participants = []
    for email, info in data.get('last_check', {}).items():
        silence_hours = calculate_silence_hours(info.get('last_post_time'))
        
        # Określ status
        status_emoji = "🟢"
        if silence_hours >= 72:
            status_emoji = "🔴🔴🔴"
        elif info.get('posts_since_moderator', 0) >= 10:
            status_emoji = "🔴🔴"
        elif silence_hours >= 48:
            status_emoji = "🔴"
        elif info.get('posts_since_moderator', 0) >= 5:
            status_emoji = "🟡"
        elif silence_hours >= 24:
            status_emoji = "🟠"
        
        participants.append({
            'Status': status_emoji,
            'Email': email,
            'Posty respondenta': info.get('respondent_posts', 0),
            'Posty moderatora': info.get('moderator_posts', 0),
            'Od moderatora': info.get('posts_since_moderator', 0),
            'Ostatni post': format_time_ago(info.get('last_post_time')),
            'Milczy (h)': int(silence_hours) if silence_hours < 999 else 'Nigdy',
            'silence_hours_num': silence_hours  # Do sortowania
        })
    
    # Sortuj według priorytetu
    participants.sort(key=lambda x: (-x['Od moderatora'], -x['silence_hours_num']))
    
    # Statystyki w kolumnach
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = len(participants)
        st.metric("👥 Wszyscy uczestnicy", total)
    
    with col2:
        critical = sum(1 for p in participants if p['silence_hours_num'] >= 72 or p['Od moderatora'] >= 10)
        st.metric("🔴 Krytyczne przypadki", critical)
    
    with col3:
        warning = sum(1 for p in participants if 5 <= p['Od moderatora'] < 10 or 24 <= p['silence_hours_num'] < 72)
        st.metric("🟡 Wymagają uwagi", warning)
    
    with col4:
        ok = sum(1 for p in participants if p['Od moderatora'] == 0 and p['silence_hours_num'] < 24)
        st.metric("🟢 Wszystko OK", ok)
    
    st.markdown("---")
    
    # Filtry w sidebarze
    st.sidebar.header("🔧 Filtry")
    
    # Filtr statusu
    status_filter = st.sidebar.multiselect(
        "Status",
        options=["🔴🔴🔴", "🔴🔴", "🔴", "🟡", "🟠", "🟢"],
        default=["🔴🔴🔴", "🔴🔴", "🔴", "🟡", "🟠", "🟢"]
    )
    
    # Filtr milczenia
    silence_min = st.sidebar.slider("Milczy minimum (h)", 0, 168, 0)
    
    # Filtr postów od moderatora
    posts_min = st.sidebar.slider("Postów od moderatora minimum", 0, 50, 0)
    
    # Zastosuj filtry
    filtered_participants = [
        p for p in participants 
        if p['Status'] in status_filter
        and (p['silence_hours_num'] >= silence_min if p['silence_hours_num'] < 999 else False)
        and p['Od moderatora'] >= posts_min
    ]
    
    # Tabela z danymi
    st.subheader(f"📊 Uczestnicy ({len(filtered_participants)} z {total})")
    
    # Usuń kolumnę pomocniczą przed wyświetleniem
    for p in filtered_participants:
        del p['silence_hours_num']
    
    # Wyświetl tabelę
    if filtered_participants:
        df = pd.DataFrame(filtered_participants)
        
        # Stylizacja tabeli
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Email": st.column_config.TextColumn("Email", width="medium"),
                "Posty respondenta": st.column_config.NumberColumn("Respondent", width="small"),
                "Posty moderatora": st.column_config.NumberColumn("Moderator", width="small"),
                "Od moderatora": st.column_config.NumberColumn("Od mod.", width="small"),
                "Ostatni post": st.column_config.TextColumn("Ostatni post", width="medium"),
                "Milczy (h)": st.column_config.TextColumn("Milczy", width="small"),
            }
        )
        
        # Sekcja krytycznych przypadków
        critical_cases = [p for p in filtered_participants if p['Status'] in ["🔴🔴🔴", "🔴🔴"]]
        if critical_cases:
            st.markdown("---")
            st.subheader("🚨 Krytyczne przypadki wymagające natychmiastowej uwagi:")
            for case in critical_cases[:5]:  # Top 5
                with st.expander(f"{case['Status']} {case['Email']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Postów od moderatora:** {case['Od moderatora']}")
                        st.write(f"**Ostatni post:** {case['Ostatni post']}")
                    with col2:
                        st.write(f"**Milczy:** {case['Milczy (h)']} godzin")
                        st.write(f"**Wszystkich postów:** {case['Posty respondenta']}")
    else:
        st.info("Brak uczestników spełniających kryteria filtrów")
    
    # Automatyczne odświeżanie
    st.markdown("---")
    if st.button("🔄 Odśwież dane"):
        st.cache_data.clear()
        st.rerun()
    
    st.caption("Dashboard odświeża się automatycznie co 60 sekund")
    
else:
    st.error("❌ Nie można załadować danych. Sprawdź czy plik cache istnieje.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        FlyBlog Monitor v1.6 | Dashboard by Streamlit
    </div>
    """,
    unsafe_allow_html=True
)