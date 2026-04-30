import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- CONFIGURACIÓN BÁSICA ---
st.set_page_config(page_title="Atlas - EDEESTE", layout="wide")

# --- ESTILO SIN LLAVES (PARA EVITAR TYPEERROR EN PYTHON 3.14) ---
# Usamos variables directas para no confundir al intérprete
st.markdown("# ⚡ Sistema Atlas - EDEESTE")
st.markdown("### Centro de Mando Operativo | Ing. Juan Carlos Tejeda")

# --- CARGA DE CATEGORÍAS ---
@st.cache_data
def cargar_maestro():
    try:
        return pd.read_csv("tipos_os.csv")
    except:
        return pd.DataFrame(columns=['Tipo de OS', 'Calcificacion en KPI', 'Familia'])

df_maestro = cargar_maestro()

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    archivo = st.file_uploader("Subir Excel de Gestión", type=["xlsx", "xls"])
    st.divider()
    st.write("Configuración institucional activa: **Azul y Amarillo**")

# --- LÓGICA DE DATOS ---
if archivo:
    df_raw = pd.read_excel(archivo)
    
    # Unir con categorías del archivo tipos_os.csv
    if 'Tipo de OS' in df_raw.columns:
        df_final = df_raw.merge(df_maestro, on='Tipo de OS', how='left')
        df_final['Calcificacion en KPI'] = df_final['Calcificacion en KPI'].fillna('Pendiente')
        df_final['Familia'] = df_final['Familia'].fillna('Otros')
    else:
        st.error("Error: La columna 'Tipo de OS' no existe en el Excel.")
        st.stop()

    # Filtros por Supervisor
    if 'Supervisor' in df_final.columns:
        lista_sups = sorted(df_final['Supervisor'].dropna().unique().tolist())
        sel_sups = st.sidebar.multiselect("Supervisores", options=lista_sups, default=lista_sups)
        df_plot = df_final[df_final['Supervisor'].isin(sel_sups)]
    else:
        df_plot = df_final

    # --- MÉTRICAS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Total OS", len(df_plot))
    norm = len(df_plot[df_plot['Calcificacion en KPI'] == 'Normalizacion'])
    c2.metric("Normalizaciones", norm)
    c3.metric("Efectividad %", f"{(norm/len(df_plot)*100 if len(df_plot)>0 else 0):.1f}%")

    # --- GRÁFICOS ---
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.write("#### Productividad por Supervisor")
        # Colores institucionales: Azul (#003399) y Amarillo (#FFD700)[cite: 1]
        fig_bar = px.bar(
            df_plot.groupby(['Supervisor', 'Calcificacion en KPI']).size().reset_index(name='Cant'),
            x='Supervisor', y='Cant', color='Calcificacion en KPI',
            barmode='group',
            color_discrete_map={'Normalizacion': '#003399', 'Inspeccion': '#FFD700'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_der:
        st.write("#### Familias de Órdenes")
        fig_pie = px.pie(df_plot, names='Familia', hole=0.4,
                         color_discrete_sequence=['#003399', '#FFD700', '#A9A9A9'])
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- DESCARGA ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_plot.to_excel(writer, index=False)
    
    st.download_button("📥 Descargar Reporte Depurado", data=buffer.getvalue(), 
                       file_name="Productividad_Atlas.xlsx")

else:
    st.warning("👈 Sube un archivo Excel para activar el dashboard.")
