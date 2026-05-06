import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN PROFESIONAL
st.set_page_config(page_title="PuntoRojo v3.0 | Distrito Nacional", layout="wide", page_icon="🔴")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES DE PROCESAMIENTO DE DATOS
def procesar_datos(archivo):
    xls = pd.ExcelFile(archivo)
    
    # Carga de Balance Central (Pérdidas por Totalizador)
    df_balance = pd.read_excel(xls, sheet_name="Balance Central")
    df_balance.columns = [str(c).strip().upper() for c in df_balance.columns]
    
    # Carga de BDG (Información de Suministros)
    sheet_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    df_bdg = pd.read_excel(xls, sheet_name=sheet_bdg) if sheet_bdg else None
    if df_bdg is not None:
        df_bdg.columns = [str(c).strip().upper() for c in df_bdg.columns]
    
    # Carga de Relación (Vínculo Totalizador - Suministro)
    df_relacion = pd.read_excel(xls, sheet_name="Relación")
    df_relacion.columns = [str(c).strip().upper() for c in df_relacion.columns]
    
    return df_balance, df_bdg, df_relacion

# 3. INTERFAZ Y LÓGICA PRINCIPAL
st.title("🔴 Gestión Estratégica de Pérdidas - PuntoRojo v3.0")
st.sidebar.header("Configuración de Operaciones")

uploaded_file = st.sidebar.file_uploader("Cargar Balance de Totalizadores (.xlsx)", type="xlsx")

if uploaded_file:
    df_bal, df_bdg, df_rel = procesar_datos(uploaded_file)
    
    # --- FILTRO DISTRITO NACIONAL / SANTO DOMINGO ---
    # Se asume que existe una columna 'REGIÓN' o 'OFICINA'
    if 'REGIÓN' in df_bal.columns:
        df_bal = df_bal[df_bal['REGIÓN'].str.contains("DN|DISTRITO|OCCIDENTAL", case=False, na=False)]

    # --- MÉTRICAS DE PRIORIDAD ---
    # Ordenar por mayor porcentaje de pérdida
    df_prioridad = df_bal.sort_values(by='%PÉRDIDA', ascending=False).head(10)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("⚠️ Top 10 Prioridades de Intervención")
        st.table(df_prioridad[['TOTALIZADOR', 'CIRCUITO', '%PÉRDIDA', 'COMPRA']])

    with col2:
        st.subheader("📊 Distribución de Pérdidas por Circuito")
        fig_pie = px.pie(df_bal, values='PÉRDIDA', names='CIRCUITO', 
                         title='Localización de Pérdida de Energía',
                         color_discrete_sequence=px.colors.sequential.Reds_r)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- MAPA DE CALOR OPERATIVO ---
    st.subheader("📍 Mapa de Localización: Distrito Nacional y SDE")
    # Coordenadas base Santo Domingo
    m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    
    # Aquí se iteraría sobre df_bal si tuviera lat/lon
    # Por ahora marcamos la zona de influencia
    folium.Circle([18.4861, -69.9312], radius=5000, color="red", fill=True, opacity=0.2).add_to(m)
    st_folium(m, width=1300, height=400)

    # --- FILTRO DINÁMICO DE SUMINISTROS ---
    st.divider()
    st.subheader("🔍 Buscador de Suministros por Totalizador")
    
    lista_totalizadores = df_bal['TOTALIZADOR'].unique().tolist()
    totalizador_sel = st.selectbox("Seleccione un Totalizador para ver sus suministros asociados:", lista_totalizadores)

    if totalizador_sel:
        # Cruce de información: Relación + BDG
        suministros_asociados = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
        
        if df_bdg is not None:
            # Cruce con BDG por NIC para traer Balance y Estado
            suministros_final = pd.merge(suministros_asociados, 
                                         df_bdg[['NIC', 'ESTADO', 'BALANCE', 'CORTABLE']], 
                                         on='NIC', how='left')
            st.write(f"Suministros bajo el Totalizador: **{totalizador_sel}**")
            st.dataframe(suministros_final, use_container_width=True)
        else:
            st.dataframe(suministros_asociados, use_container_width=True)

else:
    st.info("Esperando carga de archivos para generar el análisis de prioridades.")
