import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Atlas - Control de Productividad", layout="wide")

# --- ESTILO CSS (CORREGIDO PARA EVITAR TYPEERROR) ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    .stMetric { 
        background-color: #f8f9fa; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #003399; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    h1, h2, h3 { color: #003399; font-family: 'Arial'; }
    .stButton>button {
        background-color: #003399;
        color: white;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_config=True)

# --- CABECERA ---
st.title("⚡ Dashboard de Productividad y KPI - EDEESTE")
st.markdown("### Centro de Mando Operativo | Ing. Juan Carlos Tejeda")

# --- CARGA DE DATOS MAESTROS (Categorías) ---
@st.cache_data
def load_master_data():
    try:
        # Intenta cargar el archivo de categorías que creaste en GitHub
        return pd.read_csv("tipos_os.csv")
    except:
        # Respaldo en caso de que el archivo no se encuentre
        return pd.DataFrame(columns=['Tipo de OS', 'Calcificacion en KPI', 'Familia'])

df_maestro = load_master_data()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Gestión de Datos")
    file_op = st.file_uploader("Subir Reporte de Gestión (Excel)", type=["xlsx", "xls"])
    
    if file_op:
        st.success("✅ Datos Operativos Cargados")
    
    st.divider()
    st.write("🔧 **Sistema Atlas**")
    st.write("Estrategia de Pérdidas Energéticas")

# --- LÓGICA DE PROCESAMIENTO ---
if file_op:
    # 1. Lectura
    df_raw = pd.read_excel(file_op)
    
    # 2. DEPURECIÓN Y CATEGORIZACIÓN (JOIN CON MAESTRO)
    if 'Tipo de OS' in df_raw.columns:
        df_final = df_raw.merge(df_maestro, on='Tipo de OS', how='left')
        df_final['Calcificacion en KPI'] = df_final['Calcificacion en KPI'].fillna('Pendiente Clasificar')
        df_final['Familia'] = df_final['Familia'].fillna('Otros')
    else:
        st.error("❌ El archivo no contiene la columna 'Tipo de OS'. Revisa el formato.")
        st.stop()

    # 3. FILTROS POR SUPERVISOR
    if 'Supervisor' in df_final.columns:
        sups = sorted(df_final['Supervisor'].dropna().unique().tolist())
        sel_sups = st.sidebar.multiselect("Seleccionar Supervisores", options=sups, default=sups)
        df_plot = df_final[df_final['Supervisor'].isin(sel_sups)]
    else:
        st.warning("⚠️ No se encontró la columna 'Supervisor'.")
        df_plot = df_final

    # 4. MÉTRICAS CLAVE (KPIs)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total de Órdenes", len(df_plot))
    with m2:
        norm = len(df_plot[df_plot['Calcificacion en KPI'] == 'Normalizacion'])
        st.metric("Normalizaciones", norm)
    with m3:
        insp = len(df_plot[df_plot['Calcificacion en KPI'] == 'Inspeccion'])
        st.metric("Inspecciones", insp)
    with m4:
        efect = (norm / len(df_plot) * 100) if len(df_plot) > 0 else 0
        st.metric("Efectividad %", f"{efect:.1f}%")

    # 5. GRÁFICOS INTERACTIVOS
    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📊 Gestión por Supervisor")
        df_chart = df_plot.groupby(['Supervisor', 'Calcificacion en KPI']).size().reset_index(name='Cant')
        fig_prod = px.bar(df_chart, x='Supervisor', y='Cant', color='Calcificacion en KPI',
                          barmode='group',
                          color_discrete_map={'Normalizacion': '#003399', 'Inspeccion': '#FFD700'},
                          template="plotly_white")
        st.plotly_chart(fig_prod, use_container_width=True)

    with c2:
        st.subheader("🥧 Distribución por Familias")
        fig_pie = px.pie(df_plot, names='Familia', 
                         color_discrete_sequence=['#003399', '#FFD700', '#A9A9A9', '#5DADE2'])
        st.plotly_chart(fig_pie, use_container_width=True)

    # 6. SUGERENCIAS DE PRODUCTIVIDAD
    st.divider()
    st.subheader("💡 Sugerencias de Atlas")
    if len(df_plot) > 0 and 'Supervisor' in df_plot.columns:
        top_sup = df_plot.groupby('Supervisor').size().idxmax()
        st.info(f"El supervisor **{top_sup}** lidera el volumen de gestión. Se recomienda analizar sus métodos de despacho para replicarlos en otras unidades.")

    # 7. EXPORTAR DATOS
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_plot.to_excel(writer, index=False, sheet_name='Reporte_Atlas')
    
    st.download_button(
        label="📥 Descargar Reporte Depurado",
        data=buffer.getvalue(),
        file_name="Productividad_EDEESTE_Atlas.xlsx",
        mime="application/vnd.ms-excel"
    )

else:
    st.warning("⚠️ Esperando carga de archivo Excel para procesar...")
    st.info("Sube el reporte en el panel izquierdo para ver la productividad de los supervisores y brigadas.")
