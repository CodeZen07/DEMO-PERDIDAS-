import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN VISUAL GERENCIAL
st.set_page_config(page_title="PuntoRojo v3.0 | Distrito Nacional", layout="wide", page_icon="🔴")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; border-top: 4px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS CON CACHÉ PARA VELOCIDAD
@st.cache_data
def cargar_datos(archivo):
    xls = pd.ExcelFile(archivo)
    
    # Balance Central: Análisis de totalizadores
    df_bal = pd.read_excel(xls, sheet_name="Balance Central")
    df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
    
    # Relación: Mapeo Totalizador -> NIC
    df_rel = pd.read_excel(xls, sheet_name="Relación")
    df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
    
    # BDG: Información del cliente
    sheet_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    df_bdg = pd.read_excel(xls, sheet_name=sheet_bdg) if sheet_bdg else None
    if df_bdg is not None:
        df_bdg.columns = [str(c).strip().upper() for c in df_bdg.columns]
        df_bdg['NIC'] = df_bdg['NIC'].astype(str)
        
    return df_bal, df_rel, df_bdg

# 3. CUERPO DE LA APP
st.title("🔴 PuntoRojo v3.0 — Dashboard Operativo")
st.sidebar.header("Carga de Archivos")

archivo_subido = st.sidebar.file_uploader("Subir reporte de balances (.xlsx)", type="xlsx")

if archivo_subido:
    df_bal, df_rel, df_bdg = cargar_datos(archivo_subido)
    
    # Limpieza de valores de pérdida
    df_bal['%PÉRDIDA'] = pd.to_numeric(df_bal['%PÉRDIDA'], errors='coerce').fillna(0)
    df_bal['PÉRDIDA'] = pd.to_numeric(df_bal['PÉRDIDA'], errors='coerce').fillna(0)

    # --- FILA 1: PRIORIDADES Y GRÁFICO ---
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.subheader("⚠️ Top 10 Totalizadores a Intervenir")
        df_prioridad = df_bal.sort_values(by='%PÉRDIDA', ascending=False).head(10)
        st.dataframe(df_prioridad[['TOTALIZADOR', 'CIRCUITO', '%PÉRDIDA', 'COMPRA']], use_container_width=True)

    with col_der:
        st.subheader("📊 Distribución de Pérdidas por Circuito")
        fig = px.pie(df_bal, values='PÉRDIDA', names='CIRCUITO', hole=0.4,
                     color_discrete_sequence=px.colors.sequential.Reds_r)
        st.plotly_chart(fig, use_container_width=True)

    # --- FILA 2: MAPA DN ---
    st.subheader("📍 Mapa de Calor: Distrito Nacional")
    mapa = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    folium.Circle([18.4861, -69.9312], radius=4500, color="red", fill=True, opacity=0.3, popup="Zona Crítica DN").add_to(mapa)
    st_folium(mapa, width=1300, height=400)

    # --- FILA 3: BUSCADOR ASOCIADO ---
    st.divider()
    st.subheader("🔍 Consulta de Suministros por Totalizador")
    totalizador_sel = st.selectbox("Seleccione el Totalizador:", df_bal['TOTALIZADOR'].unique())

    if totalizador_sel:
        # Cruce Relación + BDG
        nics_en_red = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
        nics_en_red['NIC'] = nics_en_red['NIC'].astype(str)
        
        if df_bdg is not None:
            detalle = pd.merge(nics_en_red, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
            
            # Indicadores del totalizador
            m1, m2 = st.columns(2)
            m1.metric("Clientes en esta red", len(detalle))
            m2.metric("Deuda Acumulada", f"${detalle['BALANCE'].sum():,.2f}")
            
            st.dataframe(detalle, use_container_width=True)

else:
    st.info("Cargue el archivo Excel para iniciar el cruce de información gerencial.")
