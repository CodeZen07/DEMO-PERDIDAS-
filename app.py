import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN (Mantenemos tu base)
st.set_page_config(page_title="PuntoRojo v3.0 | Distrito Nacional", layout="wide", page_icon="🔴")

# 2. PROCESAMIENTO (Tu lógica original protegida)
@st.cache_data
def cargar_datos_seguro(archivo):
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

# 3. INTERFAZ
st.title("🔴 PuntoRojo v3.0 — Dashboard Operativo")
uploaded_file = st.sidebar.file_uploader("Subir Balance (.xlsx)", type=["xlsx"])

if uploaded_file:
    df_bal, df_rel, df_bdg = cargar_datos_seguro(uploaded_file)
    
    # Aseguramos columnas numéricas para evitar el KeyError
    col_perdida = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else df_bal.columns[0]
    df_bal[col_perdida] = pd.to_numeric(df_bal[col_perdida], errors='coerce').fillna(0)

    # --- NUEVOS GRÁFICOS DE BARRAS (Sin romper la base) ---
    st.subheader("📊 Análisis de Intervención")
    col_bar1, col_bar2 = st.columns(2)

    with col_bar1:
        # Gráfico de barras de los 10 peores (Más visual)
        top_10 = df_bal.sort_values(by=col_perdida, ascending=False).head(10)
        fig_bar = px.bar(top_10, x='TOTALIZADOR', y=col_perdida, 
                         title="Top 10 Totalizadores Críticos",
                         color=col_perdida, color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_bar2:
        # Gráfico de pastel original (Lo mantenemos como pediste)
        if 'PÉRDIDA' in df_bal.columns:
            fig_pie = px.pie(df_bal, values='PÉRDIDA', names='CIRCUITO', hole=0.4, title="Distribución por Circuito")
            st.plotly_chart(fig_pie, use_container_width=True)

    # --- SEMÁFORO DE OBSERVACIONES ---
    st.subheader("📑 Hoja de Ruta y Observaciones")
    
    def semaforo(pct):
        if pct > 30: return "🔴 CRÍTICO: Intervención Inmediata"
        if pct > 15: return "🟡 ALTA: Revisión Programada"
        return "🟢 NORMAL: Monitoreo"

    df_bal['OBSERVACIÓN'] = df_bal[col_perdida].apply(semaforo)
    st.dataframe(df_bal[['TOTALIZADOR', col_perdida, 'OBSERVACIÓN']].sort_values(by=col_perdida, ascending=False), use_container_width=True)

    # --- MAPA (Puntos por totalizador) ---
    st.subheader("📍 Mapa de Calor Operativo")
    m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    
    # Marcamos puntos para los 10 críticos
    for i, row in top_10.iterrows():
        folium.Marker(
            location=[18.48 + (i*0.002), -69.93 + (i*0.002)], # Distribución visual si no hay coord.
            popup=f"{row['TOTALIZADOR']}: {row[col_perdida]}%",
            icon=folium.Icon(color='red')
        ).add_to(m)
    st_folium(m, width=1300, height=400)

    # --- BUSCADOR Y CRUCE (Tu trabajo intacto) ---
    st.divider()
    st.subheader("🔍 Buscador de Suministros")
    total_sel = st.selectbox("Seleccione Totalizador:", df_bal['TOTALIZADOR'].unique())
    
    if total_sel:
        nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(total_sel)]
        if df_bdg is not None:
            detalle = pd.merge(nics, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
            st.dataframe(detalle, use_container_width=True)

else:
    st.info("Cargue el archivo para iniciar.")
