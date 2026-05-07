import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURACIÓN EDEESTE
st.set_page_config(page_title="PuntoRojo v3.1 | Business Intelligence", layout="wide", page_icon="🔴")

AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"

# 2. PROCESAMIENTO (Base sólida)
@st.cache_data
def cargar_datos_final(archivo):
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
st.title("🔴 PuntoRojo v3.1 — Inteligencia de Pérdidas EDEESTE")
archivo = st.sidebar.file_uploader("Cargar Reporte Operativo (.xlsx)", type=["xlsx"])

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_final(archivo)
    
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else df_bal.columns[0]
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal['PÉRDIDA'] = pd.to_numeric(df_bal['PÉRDIDA'], errors='coerce').fillna(0)

    # --- SUSTITUCIÓN DEL MAPA: TREEMAP DE JERARQUÍA DE PÉRDIDAS ---
    st.subheader("📊 Mapa de Calor de Pérdidas (Jerarquía por Circuito)")
    st.info("Este gráfico sustituye al mapa: el tamaño del cuadro es el volumen de pérdida (kWh) y el color la severidad (%)")
    
    fig_tree = px.treemap(
        df_bal, 
        path=['CIRCUITO', 'TOTALIZADOR'], 
        values='PÉRDIDA',
        color=col_pct,
        color_continuous_scale=[AMARILLO_EDEESTE, '#e67e22', '#d32f2f', AZUL_EDEESTE],
        title="Distribución Crítica: Circuitos y Totalizadores"
    )
    fig_tree.update_layout(margin=dict(t=30, l=10, r=10, b=10))
    st.plotly_chart(fig_tree, use_container_width=True)

    # --- FILA DE ANÁLISIS TOP 10 ---
    st.divider()
    col_izq, col_der = st.columns(2)
    
    df_top10 = df_bal.sort_values(by=col_pct, ascending=False).head(10)

    with col_izq:
        st.subheader("🔝 Top 10 Totalizadores Críticos")
        fig_bar = px.bar(df_top10, x='TOTALIZADOR', y=col_pct, 
                         color_discrete_sequence=[AZUL_EDEESTE], text_auto='.1f')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_der:
        st.subheader("⚠️ Matriz de Prioridad de Intervención")
        # Tabla resumen con indicadores visuales simples
        df_prioridad = df_top10[['TOTALIZADOR', 'CIRCUITO', col_pct]].copy()
        df_prioridad['PRIORIDAD'] = df_prioridad[col_pct].apply(lambda x: "🚨 CRÍTICA" if x > 40 else "⚠️ ALTA")
        st.table(df_prioridad)

    # --- BUSCADOR Y CRUCE (Tu trabajo intacto) ---
    st.divider()
    st.subheader("🔍 Auditoría de Suministros por Red")
    totalizador_sel = st.selectbox("Seleccione un Totalizador para ver su detalle:", [""] + df_bal['TOTALIZADOR'].unique().tolist())

    if totalizador_sel != "":
        nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]
        if df_bdg is not None:
            detalle = pd.merge(nics, df_bdg[['NIC', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE']], on='NIC', how='left')
            st.metric("Deuda Total en este Punto", f"RD$ {detalle['BALANCE'].sum():,.2f}")
            st.dataframe(detalle, use_container_width=True)

else:
    st.info("👋 Atlas listo. Cargue el archivo Excel para iniciar el análisis sin errores de mapa.")
