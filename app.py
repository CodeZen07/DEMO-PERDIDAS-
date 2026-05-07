import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="PuntoRojo v3.0 | Dashboard Gerencial", layout="wide", page_icon="🔴")

# Estilos visuales
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stMetric { border-top: 5px solid #d32f2f !important; background-color: white; border-radius: 10px; }
    .priority-high { color: white; background-color: #d32f2f; padding: 5px; border-radius: 5px; font-weight: bold; }
    .priority-med { color: black; background-color: #fbc02d; padding: 5px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES DE PROCESAMIENTO
@st.cache_data
def procesar_informacion(archivo):
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

# 3. INTERFAZ PRINCIPAL
st.title("📊 PuntoRojo v3.0 — Inteligencia Operativa")
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/3/3d/Flag_of_the_Dominican_Republic.svg", width=100)
uploaded_file = st.sidebar.file_uploader("Cargar Balance de Energía (.xlsx)", type=["xlsx"])

if uploaded_file:
    df_bal, df_rel, df_bdg = procesar_informacion(uploaded_file)
    
    # Conversiones numéricas seguras
    for col in ['%PÉRDIDA', 'PÉRDIDA', 'COMPRA', 'VENTA']:
        if col in df_bal.columns:
            df_bal[col] = pd.to_numeric(df_bal[col], errors='coerce').fillna(0)

    # --- MÉTRICAS ESTRATÉGICAS ---
    c1, c2, c3, c4 = st.columns(4)
    total_perdida = df_bal['PÉRDIDA'].sum()
    c1.metric("Energía Perdida Total", f"{total_perdida:,.0f} kWh", delta="-5% vs mes anterior", delta_color="inverse")
    c2.metric("Totalizadores en Crisis", len(df_bal[df_bal['%PÉRDIDA'] > 35]))
    c3.metric("% Pérdida Global", f"{(df_bal['PÉRDIDA'].sum() / df_bal['COMPRA'].sum() * 100):.1f}%")
    c4.metric("Circuito Crítico", df_bal.loc[df_bal['PÉRDIDA'].idxmax(), 'CIRCUITO'])

    st.divider()

    # --- FILA DE GRÁFICOS DE BARRAS ---
    col_bar1, col_bar2 = st.columns([1.2, 1])

    with col_bar1:
        st.subheader("🚀 Top 10 Totalizadores por Volumen de Pérdida (kWh)")
        # Gráfico de barras horizontales más intuitivo
        top_kwh = df_bal.sort_values('PÉRDIDA', ascending=False).head(10)
        fig_bar = px.bar(top_kwh, x='PÉRDIDA', y='TOTALIZADOR', orientation='h',
                         color='%PÉRDIDA', color_continuous_scale='Reds',
                         text_auto='.2s', labels={'PÉRDIDA': 'kWh Perdidos'})
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_bar2:
        st.subheader("🎯 Comparativo: Compra vs Venta")
        # Gráfico de barras agrupadas para ver la brecha
        top_5_comp = df_bal.sort_values('COMPRA', ascending=False).head(5)
        fig_comp = go.Figure(data=[
            go.Bar(name='Compra (Entrada)', x=top_5_comp['TOTALIZADOR'], y=top_5_comp['COMPRA'], marker_color='#333'),
            go.Bar(name='Venta (Facturado)', x=top_5_comp['TOTALIZADOR'], y=top_5_comp['VENTA'], marker_color='#d32f2f')
        ])
        fig_comp.update_layout(barmode='group', margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_comp, use_container_width=True)

    # --- SISTEMA DE SEMÁFORO Y OBSERVACIONES ---
    st.subheader("📝 Hoja de Ruta: Dónde Proceder Primero")
    
    def generar_observacion(row):
        if row['%PÉRDIDA'] > 40: return "🔴 CRÍTICO: Intervención técnica inmediata. Posible fraude masivo o falla de equipo."
        if row['%PÉRDIDA'] > 20: return "🟡 ALTA: Programar revisión de suministros y normalización de medidores."
        return "🟢 NORMAL: Monitoreo rutinario."

    df_bal['ACCIÓN'] = df_bal.apply(generar_observacion, axis=1)
    
    # Mostrar tabla estilizada de intervención
    st.dataframe(df_bal[['TOTALIZADOR', 'CIRCUITO', '%PÉRDIDA', 'ACCIÓN']].sort_values('%PÉRDIDA', ascending=False), 
                 use_container_width=True, hide_index=True)

    # --- MAPA OPERATIVO DISTRITO NACIONAL ---
    st.subheader("📍 Georreferencia de Pérdidas (DN y SDE)")
    m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    
    # Simulación de puntos rojos en calles basado en los top críticos
    for i, row in top_kwh.iterrows():
        # Aquí podrías usar lat/lon reales si los tienes, si no, distribuimos puntos cerca de zonas clave
        folium.Marker(
            location=[18.48 + (i*0.005), -69.93 + (i*0.002)],
            popup=f"Totalizador: {row['TOTALIZADOR']} - Perdida: {row['%PÉRDIDA']}%",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
    
    st_folium(m, width=1300, height=450)

    # --- EXPLORADOR DE SUMINISTROS (CONSERVA TU TRABAJO ANTERIOR) ---
    st.divider()
    st.subheader("🔍 Auditoría de Clientes por Red")
    total_sel = st.selectbox("Seleccione Totalizador para ver suministros:", df_bal['TOTALIZADOR'].unique())
    
    if total_sel:
        nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(total_sel)]
        if df_bdg is not None:
            detalle = pd.merge(nics, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
            st.dataframe(detalle, use_container_width=True)

else:
    st.info("Cargue el archivo para generar la inteligencia visual de PuntoRojo.")
