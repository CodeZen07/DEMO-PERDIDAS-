import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- CONFIGURACIÓN DE IDENTIDAD VISUAL EDEESTE ---
AZUL_EDEESTE = "#003399"
AMARILLO_EDEESTE = "#FFD700"
BLANCO = "#FFFFFF"

st.set_page_config(page_title="Atlas - Control de Productividad", layout="wide")

# Estilos CSS para el Dashboard
st.markdown(f"""
    <style>
    .stApp {{ background-color: {BLANCO}; }}
    .stMetric {{ 
        background-color: #f8f9fa; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid {AZUL_EDEESTE}; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }}
    h1, h2, h3 {{ color: {AZUL_EDEESTE}; font-family: 'Arial'; }}
    .stButton>button {{
        background-color: {AZUL_EDEESTE};
        color: white;
        border-radius: 8px;
        width: 100%;
    }}
    </style>
    """, unsafe_allow_config=True)

# --- TÍTULO Y LOGO ---
st.title("⚡ Dashboard de Productividad y KPI - EDEESTE")
st.markdown("### Centro de Mando Operativo")

# --- CARGA DE DATOS MAESTROS (Categorías) ---
@st.cache_data
def load_master_data():
    try:
        # Intentamos cargar el archivo de categorías que creaste en GitHub
        return pd.read_csv("tipos_os.csv")
    except:
        # Si no existe, creamos un pequeño dataframe de respaldo
        return pd.DataFrame(columns=['Tipo de OS', 'Calcificacion en KPI', 'Familia'])

df_maestro = load_master_data()

# --- BARRA LATERAL (Configuración y Carga) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    file_op = st.file_uploader("Subir Archivo de Gestión (Excel)", type=["xlsx", "xls"])
    
    if file_op:
        st.success("✅ Archivo operativo cargado")
    
    st.markdown("---")
    st.write("🔧 **Desarrollado por:** Ing. Juan Carlos Tejeda")
    st.write("🎯 **Objetivo:** Optimización de Pérdidas")

# --- LÓGICA PRINCIPAL ---
if file_op:
    # 1. Leer datos del Excel subido
    df_raw = pd.read_excel(file_op)
    
    # 2. DEPURACIÓN Y SEGMENTACIÓN AUTOMÁTICA
    # Cruzamos el archivo subido con el maestro de categorías (tipos_os.csv)
    if 'Tipo de OS' in df_raw.columns:
        df_final = df_raw.merge(df_maestro, on='Tipo de OS', how='left')
        # Llenar vacíos si la orden no estaba en el maestro
        df_final['Calcificacion en KPI'] = df_final['Calcificacion en KPI'].fillna('Pendiente Clasificar')
        df_final['Familia'] = df_final['Familia'].fillna('Otros')
    else:
        st.error("❌ Error: El archivo no tiene la columna 'Tipo de OS'. Por favor revisa el formato.")
        st.stop()

    # 3. FILTROS DINÁMICOS
    st.sidebar.subheader("🔍 Filtros de Análisis")
    
    # Filtro de Supervisores
    if 'Supervisor' in df_final.columns:
        sups = df_final['Supervisor'].unique().tolist()
        sel_sups = st.sidebar.multiselect("Filtrar por Supervisor", options=sups, default=sups)
        df_plot = df_final[df_final['Supervisor'].isin(sel_sups)]
    else:
        st.warning("No se encontró la columna 'Supervisor'.")
        df_plot = df_final

    # 4. DASHBOARD DE MÉTRICAS (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total de Órdenes", len(df_plot))
    with col2:
        norm = len(df_plot[df_plot['Calcificacion en KPI'] == 'Normalizacion'])
        st.metric("Normalizaciones", norm)
    with col3:
        insp = len(df_plot[df_plot['Calcificacion en KPI'] == 'Inspeccion'])
        st.metric("Inspecciones", insp)
    with col4:
        efectividad = (norm / len(df_plot) * 100) if len(df_plot) > 0 else 0
        st.metric("Efectividad %", f"{efectividad:.1f}%")

    # 5. VISUALIZACIONES INTERACTIVAS
    st.markdown("---")
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("📊 Productividad por Supervisor")
        # Agrupamos datos para el gráfico
        df_chart = df_plot.groupby(['Supervisor', 'Calcificacion en KPI']).size().reset_index(name='Cantidad')
        fig_prod = px.bar(df_chart, x='Supervisor', y='Cantidad', color='Calcificacion en KPI',
                          barmode='group',
                          color_discrete_map={'Normalizacion': AZUL_EDEESTE, 'Inspeccion': AMARILLO_EDEESTE},
                          template="plotly_white")
        st.plotly_chart(fig_prod, use_container_width=True)

    with row1_col2:
        st.subheader("🥧 Distribución por Familia de Orden")
        fig_pie = px.pie(df_plot, names='Familia', 
                         color_discrete_sequence=[AZUL_EDEESTE, AMARILLO_EDEESTE, "#5DADE2", "#F4D03F"])
        st.plotly_chart(fig_pie, use_container_width=True)

    # 6. SUGERENCIAS DE INTELIGENCIA OPERATIVA
    st.markdown("---")
    st.subheader("💡 Sugerencias de Optimización (Atlas)")
    
    if len(df_plot) > 0:
        top_supervisor = df_plot.groupby('Supervisor').size().idxmax()
        low_supervisor = df_plot.groupby('Supervisor').size().idxmin()
        
        st.info(f"""
        *   **Balance de Carga:** El supervisor **{top_supervisor}** tiene la mayor carga operativa. Considerar redistribuir órdenes hacia **{low_supervisor}** para optimizar tiempos.
        *   **Enfoque en Normalización:** Se recomienda priorizar las órdenes de la familia 'Medida' para aumentar el KPI de Normalización.
        """)

    # 7. EXPORTACIÓN DE RESULTADOS
    st.subheader("📥 Exportar Datos Depurados")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_plot.to_excel(writer, index=False, sheet_name='Reporte_Productividad')
    
    st.download_button(
        label="Descargar Reporte en Excel",
        data=buffer.getvalue(),
        file_name="Productividad_Depurada_EDEESTE.xlsx",
        mime="application/vnd.ms-excel"
    )

else:
    # Pantalla de bienvenida cuando no hay archivo
    st.warning("⚠️ Esperando carga de datos operativos...")
    st.image("https://edeeste.com.do/wp-content/uploads/2021/01/logo-edeeste.png", width=300)
    st.info("Para comenzar, sube el archivo Excel con las gestiones de las brigadas en el panel lateral.")
