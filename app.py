import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

# 1. CONFIGURACIÓN DE INTERFAZ PROFESIONAL
st.set_page_config(page_title="PuntoRojo v3.0 | Gestión de Pérdidas", layout="wide", page_icon="🔴")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-top: 4px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNCIÓN PARA PROCESAR EL ARCHIVO EXCEL Y CRUZAR DATOS
@st.cache_data
def procesar_excel_gerencial(file):
    try:
        xls = pd.ExcelFile(file)
        
        # Carga de Balance Central (Lista de Totalizadores)
        df_bal = pd.read_excel(xls, sheet_name="Balance Central")
        df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
        
        # Carga de Relación (Puente Totalizador -> NIC)
        df_rel = pd.read_excel(xls, sheet_name="Relación")
        df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
        
        # Carga de BDG (Datos del cliente)
        nombre_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
        df_bdg = pd.read_excel(xls, sheet_name=nombre_bdg) if nombre_bdg else None
        if df_bdg is not None:
            df_bdg.columns = [str(c).strip().upper() for c in df_bdg.columns]
            df_bdg['NIC'] = df_bdg['NIC'].astype(str)
            df_bdg['BALANCE'] = pd.to_numeric(df_bdg['BALANCE'], errors='coerce').fillna(0)
            
        return df_bal, df_rel, df_bdg
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None, None, None

# 3. INTERFAZ PRINCIPAL
st.title("🔴 PuntoRojo v3.0: Control de Pérdidas Distrito Nacional")
st.sidebar.header("Carga de Datos")

# --- FUNCIÓN DE SUBIDA DE ARCHIVO ---
archivo_excel = st.sidebar.file_uploader("Subir Balance de Totalizadores (.xlsx)", type=["xlsx"])

if archivo_excel:
    df_bal, df_rel, df_bdg = procesar_excel_gerencial(archivo_excel)
    
    if df_bal is not None:
        # Asegurar datos numéricos para el análisis
        df_bal['%PÉRDIDA'] = pd.to_numeric(df_bal['%PÉRDIDA'], errors='coerce').fillna(0)
        df_bal['PÉRDIDA'] = pd.to_numeric(df_bal['PÉRDIDA'], errors='coerce').fillna(0)

        # --- FILA 1: KPIs Y GRÁFICO DE PRIORIDADES ---
        col_tabla, col_grafico = st.columns([1, 1])
        
        with col_tabla:
            st.subheader("⚠️ Top 10 Prioridades de Intervención")
            df_prioridad = df_bal.sort_values(by='%PÉRDIDA', ascending=False).head(10)
            st.dataframe(df_prioridad[['TOTALIZADOR', 'CIRCUITO', '%PÉRDIDA', 'PÉRDIDA']], use_container_width=True)

        with col_grafico:
            st.subheader("📊 Distribución de Pérdidas por Circuito")
            fig = px.pie(df_bal, values='PÉRDIDA', names='CIRCUITO', hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Reds_r)
            st.plotly_chart(fig, use_container_width=True)

        # --- FILA 2: MAPA OPERATIVO ---
        st.subheader("📍 Localización Estratégica (DN y Santo Domingo Este)")
        # Coordenadas base para el mapa
        m = folium.Map(location=[18.4861, -69.9312], zoom_start=12, tiles="cartodbpositron")
        folium.Circle([18.4861, -69.9312], radius=4000, color="red", fill=True, popup="Foco de Pérdida DN").add_to(m)
        st_folium(m, width=1300, height=400)

        # --- FILA 3: BUSCADOR Y CRUCE AUTOMÁTICO ---
        st.divider()
        st.subheader("🔍 Buscador de Suministros por Totalizador")
        
        opciones_totalizador = df_bal['TOTALIZADOR'].unique()
        totalizador_sel = st.selectbox("Seleccione un Totalizador para ver los suministros asociados:", opciones_totalizador)

        if totalizador_sel:
            # Cruce en tiempo real: Relación -> BDG
            nics_asociados = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
            nics_asociados['NIC'] = nics_asociados['NIC'].astype(str)
            
            if df_bdg is not None:
                # Cruce de información gerencial (Deuda y Estado)
                detalle_final = pd.merge(nics_asociados, 
                                        df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], 
                                        on='NIC', how='left')
                
                # Resumen rápido del totalizador seleccionado
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Suministros", len(detalle_final))
                c2.metric("Deuda Acumulada en Red", f"${detalle_final['BALANCE'].sum():,.2f}")
                c3.metric("Intervención Sugerida", "Técnica/Corte" if detalle_final['BALANCE'].sum() > 50000 else "Inspección")
                
                st.dataframe(detalle_final, use_container_width=True)
            else:
                st.dataframe(nics_asociados, use_container_width=True)

else:
    st.info("👋 Bienvenido. Por favor, suba el archivo Excel en el panel de la izquierda para generar el análisis.")
