import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Atlas Pro - EDEESTE", layout="wide", initial_sidebar_state="expanded")

# ---------------- ESTILO ----------------
st.markdown("""
<style>
.main {background-color: #f8f9fa;}
.block-container {padding-top: 1.5rem;}
.metric-card {
    background-color: white;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
st.title("⚡ Atlas Dashboard Pro")
st.caption("Centro de Inteligencia Operativa | EDEESTE")

# ---------------- CACHE ----------------
@st.cache_data
def cargar_maestro():
    try:
        return pd.read_csv("tipos_os.csv")
    except:
        return pd.DataFrame(columns=['Tipo de OS', 'Calcificacion en KPI', 'Familia'])

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Control Ejecutivo")
    archivo = st.file_uploader("📂 Subir archivo Excel", type=["xlsx", "xls"])
    st.markdown("---")
    tema = st.radio("🎨 Tema", ["Claro", "Oscuro"], horizontal=True)

# ---------------- DATA ----------------
df_maestro = cargar_maestro()

if archivo:
    df_raw = pd.read_excel(archivo)

    if 'Tipo de OS' not in df_raw.columns:
        st.error("❌ Falta la columna 'Tipo de OS'")
        st.stop()

    df = df_raw.merge(df_maestro, on='Tipo de OS', how='left')
    df['Calcificacion en KPI'] = df['Calcificacion en KPI'].fillna('Pendiente')
    df['Familia'] = df['Familia'].fillna('Otros')

    # ---------------- FILTROS ----------------
    with st.sidebar:
        if 'Supervisor' in df.columns:
            sup_sel = st.multiselect("Supervisor", sorted(df['Supervisor'].dropna().unique()), default=None)
        else:
            sup_sel = None

        if 'Familia' in df.columns:
            fam_sel = st.multiselect("Familia", sorted(df['Familia'].dropna().unique()), default=None)
        else:
            fam_sel = None

    df_filtered = df.copy()

    if sup_sel:
        df_filtered = df_filtered[df_filtered['Supervisor'].isin(sup_sel)]

    if fam_sel:
        df_filtered = df_filtered[df_filtered['Familia'].isin(fam_sel)]

    # ---------------- KPIs ----------------
    total = len(df_filtered)
    normal = len(df_filtered[df_filtered['Calcificacion en KPI'] == 'Normalizacion'])
    efectividad = (normal / total * 100) if total > 0 else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("📊 Total OS", total)
    c2.metric("✅ Normalizaciones", normal)
    c3.metric("🎯 Efectividad", f"{efectividad:.1f}%")
    c4.metric("📅 Fecha", datetime.now().strftime("%d %b %Y"))

    st.markdown("---")

    # ---------------- GRAFICOS ----------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Productividad por Supervisor")
        df_sup = df_filtered.groupby(['Supervisor', 'Calcificacion en KPI']).size().reset_index(name='Cantidad')

        fig1 = px.bar(df_sup,
                      x='Supervisor',
                      y='Cantidad',
                      color='Calcificacion en KPI',
                      barmode='group',
                      color_discrete_map={
                          'Normalizacion': '#003399',
                          'Inspeccion': '#FFD700',
                          'Pendiente': '#A9A9A9'
                      })

        fig1.update_layout(legend_title="Estado KPI", xaxis_title="", yaxis_title="Cantidad")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Distribución por Familia")
        fig2 = px.pie(df_filtered,
                      names='Familia',
                      hole=0.5,
                      color_discrete_sequence=px.colors.qualitative.Set2)

        fig2.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)

    # ---------------- HEATMAP ----------------
    st.subheader("Mapa de Calor Operativo")
    pivot = pd.pivot_table(df_filtered,
                           values='Tipo de OS',
                           index='Supervisor',
                           columns='Familia',
                           aggfunc='count',
                           fill_value=0)

    fig3 = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index
    ))

    st.plotly_chart(fig3, use_container_width=True)

    # ---------------- TABLA ----------------
    st.subheader("Vista Detallada")
    st.dataframe(df_filtered, use_container_width=True)

    # ---------------- EXPORT ----------------
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_filtered.to_excel(writer, index=False)

    st.download_button("📥 Descargar reporte", buffer.getvalue(), "reporte_atlas.xlsx")

else:
    st.info("👈 Sube un archivo para comenzar el análisis")
