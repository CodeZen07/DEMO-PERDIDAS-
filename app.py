import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN PROFESIONAL
st.set_page_config(page_title="PuntoRojo v3.0 | Distrito Nacional", layout="wide", page_icon="🔴")

# Estilos CSS para mejorar la apariencia gerencial
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
        border-top: 5px solid #ff4b4b; 
    }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIONES DE PROCESAMIENTO (Mantenemos tu lógica intacta)
@st.cache_data
def cargar_y_cruzar(archivo):
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

# 3. CUERPO DE LA APP
st.title("🔴 PuntoRojo v3.0: Control Estratégico de Pérdidas")
st.sidebar.header("📥 Entrada de Datos")
uploaded_file = st.sidebar.file_uploader("Subir Balance de Totalizadores (.xlsx)", type=["xlsx"])

if uploaded_file:
    df_bal, df_rel, df_bdg = cargar_y_cruzar(uploaded_file)
    
    # Cálculos rápidos
    df_bal['%PÉRDIDA'] = pd.to_numeric(df_bal['%PÉRDIDA'], errors='coerce').fillna(0)
    df_bal['PÉRDIDA'] = pd.to_numeric(df_bal['PÉRDIDA'], errors='coerce').fillna(0)
    
    # --- MEJORA: MÉTRICAS FLASH ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pérdida Promedio", f"{df_bal['%PÉRDIDA'].mean():.2f}%")
    m2.metric("Totalizadores Críticos", len(df_bal[df_bal['%PÉRDIDA'] > 30]))
    m3.metric("Energía Perdida Total", f"{df_bal['PÉRDIDA'].sum():,.0f} kWh")
    m4.metric("Circuito Más Crítico", df_bal.groupby('CIRCUITO')['PÉRDIDA'].sum().idxmax())

    # --- TABS PARA ORGANIZAR EL TRABAJO ---
    tab_prioridad, tab_mapa, tab_detalle = st.tabs(["🚀 Plan de Acción", "📍 Georreferencia", "🔍 Auditoría de Red"])

    with tab_prioridad:
        col_list, col_pie = st.columns([1, 1])
        with col_list:
            st.subheader("Top 10 Intervenciones Prioritarias")
            df_prioridad = df_bal.sort_values(by='%PÉRDIDA', ascending=False).head(10)
            st.table(df_prioridad[['TOTALIZADOR', 'CIRCUITO', '%PÉRDIDA']])
            
            # MEJORA: Botón de descarga de prioridades
            csv = df_prioridad.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Plan de Intervención", csv, "prioridades_punto_rojo.csv", "text/csv")

        with col_pie:
            st.subheader("Pérdidas por Circuito")
            fig = px.pie(df_bal, values='PÉRDIDA', names='CIRCUITO', hole=0.5, 
                         color_discrete_sequence=px.colors.sequential.Reds_r)
            st.plotly_chart(fig, use_container_width=True)

    with tab_mapa:
        st.subheader("Foco de Operaciones: Distrito Nacional")
        m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
        # Marcamos las subestaciones o áreas críticas
        folium.Circle([18.4861, -69.9312], radius=4000, color="red", fill=True, opacity=0.3).add_to(m)
        st_folium(m, width=1200, height=450)

    with tab_detalle:
        st.subheader("Explorador de Suministros por Totalizador")
        totalizador_sel = st.selectbox("Seleccione el Totalizador para auditar:", df_bal['TOTALIZADOR'].unique())
        
        if totalizador_sel:
            nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
            nics['NIC'] = nics['NIC'].astype(str)
            
            if df_bdg is not None:
                # Cruce de datos
                final = pd.merge(nics, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
                
                # MEJORA: Filtros dinámicos para el gerente
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filtro_estado = st.multiselect("Filtrar por Estado:", final['ESTADO'].unique(), default=final['ESTADO'].unique())
                with col_f2:
                    solo_cortables = st.checkbox("Ver solo suministros CORTABLES")
                
                # Aplicar filtros
                final = final[final['ESTADO'].isin(filtro_estado)]
                if solo_cortables:
                    final = final[final['CORTABLE'] == 'S'] # Ajustar según tu BDG (S/N o 1/0)
                
                st.dataframe(final, use_container_width=True)
            else:
                st.dataframe(nics, use_container_width=True)

else:
    st.info("👋 PuntoRojo v3.0 está listo. Cargue el archivo de Balance Central para iniciar el análisis.")
