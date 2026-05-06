import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN DE PÁGINA (Debe ser lo primero)
st.set_page_config(page_title="PuntoRojo v3.0 | Distrito Nacional", layout="wide", page_icon="🔴")

# Estilo para KPIs gerenciales
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES DE PROCESAMIENTO
@st.cache_data
def cargar_todo(archivo):
    xls = pd.ExcelFile(archivo)
    
    # Lectura de pestañas clave
    df_bal = pd.read_excel(xls, sheet_name="Balance Central")
    df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
    
    df_rel = pd.read_excel(xls, sheet_name="Relación")
    df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
    
    # Buscar la BDG dinámicamente
    nombre_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    df_bdg = pd.read_excel(xls, sheet_name=nombre_bdg) if nombre_bdg else None
    if df_bdg is not None:
        df_bdg.columns = [str(c).strip().upper() for c in df_bdg.columns]
        df_bdg['NIC'] = df_bdg['NIC'].astype(str)
        df_bdg['BALANCE'] = pd.to_numeric(df_bdg['BALANCE'], errors='coerce').fillna(0)
    
    return df_bal, df_rel, df_bdg

# 3. INTERFAZ DE USUARIO - ESTO ES LO QUE "SALE" EN PANTALLA
st.title("🔴 PuntoRojo v3.0: Gestión Estratégica de Pérdidas")
st.markdown("---")

# --- BOTÓN DE SUBIDA (VISIBLE SIEMPRE EN LA BARRA LATERAL) ---
st.sidebar.header("Panel de Datos")
uploaded_file = st.sidebar.file_uploader("Subir Balance de Totalizadores (.xlsx)", type=["xlsx"])

# Lógica si el archivo existe
if uploaded_file:
    # Procesar datos
    df_bal, df_rel, df_bdg = cargar_todo(uploaded_file)
    
    # Limpieza básica para gráficos
    df_bal['%PÉRDIDA'] = pd.to_numeric(df_bal['%PÉRDIDA'], errors='coerce').fillna(0)
    df_bal['PÉRDIDA'] = pd.to_numeric(df_bal['PÉRDIDA'], errors='coerce').fillna(0)

    # SECCIÓN 1: PRIORIDADES Y PASTEL
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚠️ Top 10 Totalizadores Críticos")
        # Lista de prioridades para intervención inmediata
        df_prioridad = df_bal.sort_values(by='%PÉRDIDA', ascending=False).head(10)
        st.dataframe(df_prioridad[['TOTALIZADOR', 'CIRCUITO', '%PÉRDIDA', 'COMPRA']], use_container_width=True)

    with col2:
        st.subheader("📊 Pérdidas por Circuito")
        # Gráfico de pastel para ver la mayor pérdida localizada
        fig_pie = px.pie(df_bal, values='PÉRDIDA', names='CIRCUITO', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Reds_r)
        st.plotly_chart(fig_pie, use_container_width=True)

    # SECCIÓN 2: MAPA DISTRITO NACIONAL
    st.subheader("📍 Localización Operativa (DN y SDE)")
    m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
    folium.Circle([18.4861, -69.9312], radius=4000, color="red", fill=True, popup="DN Central").add_to(m)
    st_folium(m, width=1300, height=400)

    # SECCIÓN 3: FILTRO Y CRUCE AUTOMÁTICO
    st.divider()
    st.subheader("🔍 Buscador de Suministros por Totalizador")
    
    totalizador_sel = st.selectbox("Seleccione un Totalizador para ver sus NICs:", df_bal['TOTALIZADOR'].unique())

    if totalizador_sel:
        # Cruce Relación + BDG
        nics_en_totalizador = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
        nics_en_totalizador['NIC'] = nics_en_totalizador['NIC'].astype(str)
        
        if df_bdg is not None:
            # Traer Balance y Estado de la BDG al reporte del totalizador
            final = pd.merge(nics_en_totalizador, 
                             df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], 
                             on='NIC', how='left')
            
            # Indicadores Rápidos
            c1, c2, c3 = st.columns(3)
            c1.metric("Cant. Suministros", len(final))
            c2.metric("Deuda Total Red", f"${final['BALANCE'].sum():,.2f}")
            c3.metric("Acción Sugerida", "Operativo de Corte" if final['BALANCE'].sum() > 30000 else "Normal")
            
            st.dataframe(final, use_container_width=True)
        else:
            st.dataframe(nics_en_totalizador, use_container_width=True)

else:
    # Esto es lo que sale si NO se ha subido archivo
    st.warning("⚠️ El sistema está listo. Por favor, cargue el archivo Excel (.xlsx) en el menú lateral para iniciar.")
    st.image("https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1350&q=80", caption="Análisis de Redes Eléctricas")
