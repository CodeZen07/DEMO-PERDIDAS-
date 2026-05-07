import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="PuntoRojo v4.0 | EDEESTE", layout="wide", page_icon="🔴")

AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"
GRIS_OSCURO = "#1e1e1e"

# 2. CARGA DE DATOS
@st.cache_data
def cargar_datos_balance(archivo):
    xls = pd.ExcelFile(archivo)
    df_bal = pd.read_excel(xls, sheet_name="Balance Central")
    df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
    df_rel = pd.read_excel(xls, sheet_name="Relación")
    df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
    nombre_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    df_bdg = pd.read_excel(xls, sheet_name=nombre_bdg) if nombre_bdg else None
    if df_bdg is not None:
        df_bdg.columns = [str(c).strip().upper() for c in df_bdg.columns]
    return df_bal, df_rel, df_bdg

# 3. INTERFAZ
st.title("🔴 PuntoRojo v4.0 — Inteligencia Operativa")
archivo = st.sidebar.file_uploader("Cargar Archivo Excel", type=["xlsx"])

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_balance(archivo)
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else 'PERDIDA_PCT'
    col_kwh = 'PÉRDIDA' if 'PÉRDIDA' in df_bal.columns else 'PERDIDA'
    col_oficina = 'OFICINA' if 'OFICINA' in df_bal.columns else None
    
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal[col_kwh] = pd.to_numeric(df_bal[col_kwh], errors='coerce').fillna(0)

    # IPI (Índice de Priorización)
    max_kwh = df_bal[col_kwh].max() if df_bal[col_kwh].max() > 0 else 1
    df_bal['IPI'] = ((df_bal[col_kwh] / max_kwh) * 70 + (df_bal[col_pct] / 100) * 30).clip(0, 100)

    # Filtros
    opciones_oficina = ["TODAS"]
    if col_oficina: opciones_oficina += sorted(df_bal[col_oficina].dropna().unique().tolist())
    seleccion_oficina = st.sidebar.selectbox("Seleccione Oficina:", opciones_oficina)
    df_filtrado = df_bal if seleccion_oficina == "TODAS" else df_bal[df_bal[col_oficina] == seleccion_oficina]

    # --- BLOQUE PARETO 80/20 ---
    st.divider()
    st.subheader("🎯 Análisis de Impacto Pareto 80/20")
    
    # Preparar datos para Pareto
    df_pareto = df_filtrado.sort_values(by=col_kwh, ascending=False).reset_index()
    df_pareto['PERDIDA_ACUM'] = df_pareto[col_kwh].cumsum()
    total_perdida = df_pareto[col_kwh].sum()
    df_pareto['PCT_ACUM'] = (df_pareto['PERDIDA_ACUM'] / total_perdida) * 100
    
    # Identificar el punto 80%
    pocos_vitales = df_pareto[df_pareto['PCT_ACUM'] <= 80]
    
    cp1, cp2 = st.columns([2, 1])
    with cp1:
        fig_pareto = go.Figure()
        fig_pareto.add_trace(go.Bar(x=df_pareto['TOTALIZADOR'][:20], y=df_pareto[col_kwh][:20], name="kWh Perdidos", marker_color=AZUL_EDEESTE))
        fig_pareto.add_trace(go.Scatter(x=df_pareto['TOTALIZADOR'][:20], y=df_pareto['PCT_ACUM'][:20], name="% Acumulado", yaxis="y2", line=dict(color="#d32f2f", width=3)))
        
        fig_pareto.update_layout(
            title="Curva de Pareto: Top 20 Totalizadores Críticos",
            yaxis=dict(title="kWh Perdidos"),
            yaxis2=dict(title="% Acumulado", overlaying="y", side="right", range=[0, 105]),
            legend=dict(x=0.8, y=1.2)
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

    with cp2:
        st.info(f"""
        **Hallazgo Estratégico:**
        Interviniendo solo **{len(pocos_vitales)}** totalizadores de los {len(df_pareto)}, 
        podrás recuperar el **80%** de la energía perdida en {seleccion_oficina}.
        """)
        st.metric("Totalizadores 'Pocos Vitales'", len(pocos_vitales))
        st.metric("Energía Recuperable (80%)", f"{total_perdida * 0.8:,.0f} kWh")

    # --- BLOQUE MATRIZ DE DECISIÓN ---
    st.divider()
    st.subheader("📍 Matriz de Decisión: Volumen vs Intensidad")
    
    fig_scatter = px.scatter(
        df_filtrado, x=col_pct, y=col_kwh, size='IPI', color='IPI',
        hover_name='TOTALIZADOR', color_continuous_scale='Reds',
        labels={col_pct: '% de Pérdida', col_kwh: 'kWh Perdidos'},
        title="Cuadrantes de Acción (Burbuja según Score IPI)"
    )
    # Líneas de referencia (Promedios)
    fig_scatter.add_hline(y=df_filtrado[col_kwh].mean(), line_dash="dot", annotation_text="Pérdida Media")
    fig_scatter.add_vline(x=15, line_dash="dot", annotation_text="Límite Crítico (15%)")
    
    st.plotly_chart(fig_scatter, use_container_width=True)

    # --- BLOQUE AUDITORÍA (Mantenido igual por tu solicitud) ---
    st.divider()
    st.subheader("🔍 Auditoría Detallada")
    totalizador_sel = st.selectbox("Seleccione un Totalizador:", [""] + df_filtrado['TOTALIZADOR'].unique().tolist())

    if totalizador_sel:
        nics_vinculados = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]['NIC'].astype(str).tolist()
        if df_bdg is not None:
            detalle_clientes = df_bdg[df_bdg['NIC'].astype(str).isin(nics_vinculados)].copy()
            detalle_clientes['PROMEDIO_CONSUMO'] = pd.to_numeric(detalle_clientes['PROMEDIO_CONSUMO'], errors='coerce').fillna(0)
            detalle_clientes['BALANCE'] = pd.to_numeric(detalle_clientes['BALANCE'], errors='coerce').fillna(0)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Clientes", len(detalle_clientes))
            m2.metric("Deuda", f"RD$ {detalle_clientes['BALANCE'].sum():,.2f}")
            m3.metric("Consumo Prom.", f"{detalle_clientes['PROMEDIO_CONSUMO'].sum():,.0f} kWh")
            st.dataframe(detalle_clientes, use_container_width=True)

else:
    st.info("👋 Por favor, cargue el archivo Excel para iniciar el análisis estratégico.")
