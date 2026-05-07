import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN INSTITUCIONAL EDEESTE
st.set_page_config(page_title="PuntoRojo v3.0 | EDEESTE BI", layout="wide", page_icon="🔴")

# Colores Oficiales
AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"

st.markdown(f"""
    <style>
    .main {{ background-color: #f4f7f9; }}
    [data-testid="stMetricValue"] {{ font-size: 28px; color: {AZUL_EDEESTE}; }}
    h1, h2, h3 {{ color: {AZUL_EDEESTE}; }}
    .stButton>button {{ background-color: {AZUL_EDEESTE}; color: white; }}
    </style>
    """, unsafe_allow_html=True)

# 2. PROCESAMIENTO DE DATOS
@st.cache_data
def cargar_datos_edeeste(archivo):
    xls = pd.ExcelFile(archivo)
    df_bal = pd.read_excel(xls, sheet_name="Balance Central")
    df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
    
    df_rel = pd.read_excel(xls, sheet_name="Relación")
    df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
    
    nombre_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    df_bdg = pd.read_excel(xls, sheet_name=nombre_bdg) if nombre_bdg else None
    if df_bdg is not None:
        df_bdg.columns = [str(c).strip().upper() for c in df_bdg.columns]
        df_bdg['NIC'] = df_bdg['NIC'].astype(str)
        df_bdg['BALANCE'] = pd.to_numeric(df_bdg['BALANCE'], errors='coerce').fillna(0)
    
    return df_bal, df_rel, df_bdg

# 3. CUERPO DE LA APLICACIÓN
st.title("🔴 PuntoRojo v3.0 — Gestión de Pérdidas EDEESTE")
st.sidebar.markdown(f"<h2 style='color:{AZUL_EDEESTE}'>Panel de Control</h2>", unsafe_allow_html=True)

archivo = st.sidebar.file_uploader("Cargar Balance Operativo (.xlsx)", type=["xlsx"])

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_edeeste(archivo)
    
    # Limpieza de columna de pérdida
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else df_bal.columns[0]
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    
    # TOP 10 SIEMPRE VISIBLE
    df_top10 = df_bal.sort_values(by=col_pct, ascending=False).head(10)

    # --- MÉTRICAS GENERALES ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Pérdida Promedio Top 10", f"{df_top10[col_pct].mean():.1f}%")
    m2.metric("Totalizadores Analizados", len(df_bal))
    m3.metric("Circuito Mayor Pérdida", df_top10['CIRCUITO'].iloc[0] if 'CIRCUITO' in df_top10.columns else "N/D")

    st.divider()

    # --- GRÁFICOS INTERACTIVOS ---
    col_izq, col_der = st.columns([1.5, 1])

    with col_izq:
        st.subheader("📊 Ranking Top 10 Totalizadores Críticos")
        fig_bar = px.bar(
            df_top10, 
            x='TOTALIZADOR', 
            y=col_pct,
            color_discrete_sequence=[AZUL_EDEESTE],
            text_auto='.1f',
            title="Totalizadores con Mayor Porcentaje de Pérdida"
        )
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', font_color=AZUL_EDEESTE)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_der:
        st.subheader("🎯 Concentración de Pérdidas")
        # Gráfico de pastel con colores institucionales
        fig_pie = px.pie(
            df_top10, 
            values=col_pct, 
            names='TOTALIZADOR', 
            hole=0.4,
            color_discrete_sequence=[AZUL_EDEESTE, AMARILLO_EDEESTE, "#5c7893", "#ffda6a"]
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- MAPA DE LOCALIZACIÓN ---
    st.subheader("📍 Ubicación Estratégica de Puntos Críticos")
    m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    
    for i, row in df_top10.iterrows():
        # Alternar colores institucionales en el mapa
        color_mapa = 'blue' if i % 2 == 0 else 'orange'
        folium.CircleMarker(
            location=[18.485 + (i*0.003), -69.931 + (i*0.002)],
            radius=12,
            color=AZUL_EDEESTE,
            fill=True,
            fill_color=AMARILLO_EDEESTE,
            fill_opacity=0.8,
            popup=f"<b>{row['TOTALIZADOR']}</b><br>Pérdida: {row[col_pct]}%"
        ).add_to(m)
    st_folium(m, width=1300, height=450)

    # --- BUSCADOR DE SUMINISTROS (CRUCE BDG) ---
    st.divider()
    st.subheader("🔍 Auditoría Detallada de Suministros")
    totalizador_sel = st.selectbox("Seleccione un Totalizador para ver su red:", [""] + df_bal['TOTALIZADOR'].unique().tolist())

    if totalizador_sel != "":
        # Cruce Relación + BDG
        nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
        if df_bdg is not None:
            detalle = pd.merge(nics, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
            
            # KPI de Deuda
            st.metric("Deuda Acumulada en este Totalizador", f"RD$ {detalle['BALANCE'].sum():,.2f}")
            
            # Tabla sin el estilo que causaba el error (usando dataframe simple pero limpio)
            st.dataframe(detalle, use_container_width=True)
        else:
            st.dataframe(nics, use_container_width=True)

else:
    st.info("👋 Atlas a su servicio. Cargue el archivo para iniciar la auditoría institucional.")
