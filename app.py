import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN DE ALTO NIVEL
st.set_page_config(page_title="PuntoRojo v3.0 | Dashboard Gerencial", layout="wide", page_icon="🔴")

# CSS para un look moderno y limpio
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #1f2937; }
    .stSelectbox label { font-size: 18px; font-weight: bold; color: #d32f2f; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS (Tu base sólida)
@st.cache_data
def cargar_datos_gerenciales(archivo):
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

# 3. INTERFAZ Y FILTROS INTERACTIVOS
st.title("📊 PuntoRojo BI — Inteligencia de Pérdidas")
uploaded_file = st.sidebar.file_uploader("Cargar Archivo Operativo", type=["xlsx"])

if uploaded_file:
    df_bal, df_rel, df_bdg = cargar_datos_gerenciales(uploaded_file)
    
    # Identificar columna de pérdida
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else df_bal.columns[0]
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    
    # --- SELECTOR INTERACTIVO PARA ENFOQUE ---
    st.sidebar.divider()
    totalizador_focal = st.sidebar.selectbox("🎯 Enfoque Individual (Totalizador):", ["Ver Todos"] + df_bal['TOTALIZADOR'].unique().tolist())

    # Lógica de filtrado interactivo
    if totalizador_focal != "Ver Todos":
        df_view = df_bal[df_bal['TOTALIZADOR'] == totalizador_focal]
    else:
        df_view = df_bal.sort_values(by=col_pct, ascending=False).head(15)

    # --- INDICADORES DINÁMICOS ---
    c1, c2, c3 = st.columns(3)
    val_pct = df_view[col_pct].mean()
    c1.metric("Pérdida Actual", f"{val_pct:.1f}%")
    c2.metric("Totalizadores Analizados", len(df_view))
    c3.metric("Estatus", "⚠️ CRÍTICO" if val_pct > 30 else "✅ BAJO CONTROL")

    # --- GRÁFICOS PROFESIONALES ---
    col_g1, col_g2 = st.columns([1.5, 1])

    with col_g1:
        # Gráfico de barras con escala de colores profesional (Reds)
        fig_bar = px.bar(
            df_view, 
            x='TOTALIZADOR', 
            y=col_pct,
            color=col_pct,
            color_continuous_scale=['#2ecc71', '#f1c40f', '#e67e22', '#c0392b'], # Verde a Rojo oscuro
            range_color=[0, 60],
            title="Análisis de Severidad por Totalizador",
            text_auto='.1f'
        )
        fig_bar.update_layout(plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_g2:
        # Gráfico Radial/Gauge para el porciento de pérdida del seleccionado
        if totalizador_focal != "Ver Todos":
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = df_view[col_pct].iloc[0],
                title = {'text': "Nivel de Pérdida"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#c0392b"},
                    'steps': [
                        {'range': [0, 15], 'color': "#d4efdf"},
                        {'range': [15, 30], 'color': "#fcf3cf"},
                        {'range': [30, 100], 'color': "#f2d7d5"}
                    ]
                }
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            # Gráfico de pastel mejorado
            fig_pie = px.pie(df_bal.head(10), values=col_pct, names='TOTALIZADOR', hole=0.5, title="Top 10 Participación de Pérdida")
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- MAPA INTERACTIVO ---
    st.subheader("📍 Georreferencia de Redes Críticas")
    # Si el archivo tiene columnas de dirección o ubicación, aquí se procesarían. 
    # Por ahora, usamos la lógica de dispersión sobre el DN.
    m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    
    for i, row in df_view.iterrows():
        color_punto = 'red' if row[col_pct] > 30 else 'orange' if row[col_pct] > 15 else 'green'
        # Simulación de ubicación por calles (puedes sustituir por lat/lon reales de tu Excel si existen)
        folium.CircleMarker(
            location=[18.48 + (i*0.001), -69.93 + (i*0.001)],
            radius=10,
            color=color_punto,
            fill=True,
            fill_opacity=0.7,
            popup=f"Totalizador: {row['TOTALIZADOR']} | Perdida: {row[col_pct]}%"
        ).add_to(m)
    st_folium(m, width=1300, height=450)

    # --- DETALLE DE SUMINISTROS (Tu trabajo previo) ---
    st.divider()
    if totalizador_focal != "Ver Todos":
        st.subheader(f"🔍 Auditoría de Suministros: {totalizador_focal}")
        nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_focal)]
        if df_bdg is not None:
            detalle = pd.merge(nics, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
            st.dataframe(detalle.style.background_gradient(subset=['BALANCE'], cmap='Reds'), use_container_width=True)
    else:
        st.info("Seleccione un totalizador en el panel izquierdo para ver el detalle de suministros.")

else:
    st.info("👋 Atlas a su servicio. Cargue el archivo para iniciar el análisis.")
