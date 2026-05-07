import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN INSTITUCIONAL EDEESTE
st.set_page_config(page_title="PuntoRojo v3.0 | Gestión EDEESTE", layout="wide", page_icon="🔴")

AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"

st.markdown(f"""
    <style>
    .main {{ background-color: #f4f7f9; }}
    h1, h2, h3 {{ color: {AZUL_EDEESTE}; font-family: 'Segoe UI', sans-serif; }}
    .stMetric {{ background-color: white; border-radius: 10px; border-left: 5px solid {AMARILLO_EDEESTE}; }}
    </style>
    """, unsafe_allow_html=True)

# 2. PROCESAMIENTO DE DATOS
@st.cache_data
def cargar_datos_completos(archivo):
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

# 3. CUERPO DE LA APP
st.title("🔴 PuntoRojo v3.0 — Control de Pérdidas por Circuito")
archivo = st.sidebar.file_uploader("Cargar Archivo Excel EDEESTE", type=["xlsx"])

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_completos(archivo)
    
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else df_bal.columns[0]
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal['PÉRDIDA'] = pd.to_numeric(df_bal['PÉRDIDA'], errors='coerce').fillna(0)

    # --- NUEVA SECCIÓN: MATRIZ DE DEPENDENCIAS (CIRCUITO -> TOTALIZADORES) ---
    st.subheader("⛓️ Jerarquía de Red: Circuitos y sus Totalizadores")
    
    # Agrupamos para ver qué circuitos tienen más totalizadores y más pérdidas
    if 'CIRCUITO' in df_bal.columns:
        df_circuito_resumen = df_bal.groupby('CIRCUITO').agg({
            'TOTALIZADOR': 'count',
            'PÉRDIDA': 'sum',
            col_pct: 'mean'
        }).rename(columns={'TOTALIZADOR': 'CANT. TOTALIZADORES', col_pct: 'PÉRDIDA PROM. (%)'}).reset_index()
        
        # Ordenar por el que tiene más pérdida acumulada
        df_circuito_resumen = df_circuito_resumen.sort_values(by='PÉRDIDA', ascending=False)
        
        st.dataframe(df_circuito_resumen.style.format({
            'PÉRDIDA': '{:,.2f} kWh',
            'PÉRDIDA PROM. (%)': '{:.2f}%'
        }), use_container_width=True)
    
    st.divider()

    # --- TOP 10 VISUAL ---
    df_top10 = df_bal.sort_values(by=col_pct, ascending=False).head(10)
    
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.subheader("📊 Top 10 Totalizadores Críticos")
        fig_bar = px.bar(df_top10, x='TOTALIZADOR', y=col_pct, 
                         color_discrete_sequence=[AZUL_EDEESTE], text_auto='.1f')
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with c2:
        st.subheader("🎯 Participación por Circuito")
        fig_pie = px.pie(df_top10, values='PÉRDIDA', names='CIRCUITO', hole=0.4,
                         color_discrete_sequence=[AZUL_EDEESTE, AMARILLO_EDEESTE, "#1a3b6e", "#ffcd3a"])
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- MAPA OPERATIVO ---
    st.subheader("📍 Mapa de Focos Rojos")
    m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    for i, row in df_top10.iterrows():
        folium.CircleMarker(
            location=[18.485 + (i*0.003), -69.931 + (i*0.002)],
            radius=12, color=AZUL_EDEESTE, fill=True, fill_color='red', fill_opacity=0.8,
            popup=f"Totalizador: {row['TOTALIZADOR']}<br>Circuito: {row.get('CIRCUITO', 'N/D')}"
        ).add_to(m)
    st_folium(m, width=1300, height=450)

    # --- BUSCADOR FINAL ---
    st.divider()
    st.subheader("🔍 Auditoría de Suministros por Red")
    totalizador_sel = st.selectbox("Seleccione un Totalizador para ver su detalle:", [""] + df_bal['TOTALIZADOR'].unique().tolist())

    if totalizador_sel != "":
        nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
        if df_bdg is not None:
            detalle = pd.merge(nics, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
            st.write(f"### Análisis de Suministros para {totalizador_sel}")
            st.metric("Deuda Total en este Punto", f"RD$ {detalle['BALANCE'].sum():,.2f}")
            st.dataframe(detalle, use_container_width=True)

else:
    st.info("👋 Atlas listo. Cargue el archivo Excel para visualizar la relación Circuito-Totalizador.")
