import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. CONFIGURACIÓN E IDENTIDAD VISUAL
st.set_page_config(page_title="PuntoRojo v4.5 | EDEESTE", layout="wide", page_icon="🔴")

AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"
GRIS_FONDO = "#f0f2f6"
GRIS_OSCURO = "#1e1e1e"

# Estilos CSS
st.markdown(f"""
    <style>
    .main {{ background-color: {GRIS_FONDO}; }}
    .stMetric {{
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    </style>
""", unsafe_allow_html=True)

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

# 3. SIDEBAR Y CARGA
with st.sidebar:
    st.title("Configuración")
    archivo = st.file_uploader("📂 Cargar Datos Maestro", type=["xlsx"])
    st.markdown("---")
    st.info("Desarrollado para EDEESTE")

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_balance(archivo)
    
    # Procesamiento Global de Datos
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else 'PERDIDA_PCT'
    col_kwh = 'PÉRDIDA' if 'PÉRDIDA' in df_bal.columns else 'PERDIDA'
    col_oficina = 'OFICINA' if 'OFICINA' in df_bal.columns else None
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal[col_kwh] = pd.to_numeric(df_bal[col_kwh], errors='coerce').fillna(0)
    max_kwh = df_bal[col_kwh].max() if df_bal[col_kwh].max() > 0 else 1
    df_bal['IPI'] = ((df_bal[col_kwh] / max_kwh) * 70 + (df_bal[col_pct] / 100) * 30).clip(0, 100)

    # Filtro de Oficina en Sidebar
    opciones_oficina = ["TODAS"]
    if col_oficina: opciones_oficina += sorted(df_bal[col_oficina].dropna().unique().tolist())
    seleccion_oficina = st.sidebar.selectbox("📍 Filtrar por Oficina:", opciones_oficina)
    df_filtrado = df_bal if seleccion_oficina == "TODAS" else df_bal[df_bal[col_oficina] == seleccion_oficina]

    # --- NAVEGACIÓN POR PESTAÑAS ---
    tab1, tab2 = st.tabs(["📊 Panel de Control General", "🎯 Análisis Estratégico (Pareto)"])

    # ---------------------------------------------------------
    # PESTAÑA 1: CÓDIGO ORIGINAL (Interfáz Amigable)
    # ---------------------------------------------------------
    with tab1:
        st.markdown(f"# 🔴 PuntoRojo v4.5 | <small>{seleccion_oficina}</small>", unsafe_allow_html=True)
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Pérdida Total", f"{df_filtrado[col_kwh].sum():,.0f} kWh")
        kpi2.metric("% Pérdida Prom.", f"{df_filtrado[col_pct].mean():.2f}%")
        kpi3.metric("Puntos Críticos", len(df_filtrado[df_filtrado[col_pct] > 15]))
        top_id = df_filtrado.sort_values(by='IPI', ascending=False)['TOTALIZADOR'].iloc[0] if not df_filtrado.empty else "N/A"
        kpi4.metric("Máxima Prioridad", top_id)

        st.markdown("### 🚀 Próximas Inspecciones Sugeridas")
        top_prioridad = df_filtrado.sort_values(by='IPI', ascending=False).head(5)
        cols_p = st.columns(5)
        for i, (idx, row) in enumerate(top_prioridad.iterrows()):
            with cols_p[i]:
                st.markdown(f"""
                <div style="padding:15px; border-radius:12px; border-left: 6px solid {AZUL_EDEESTE}; background-color: white; box-shadow: 2px 2px 8px rgba(0,0,0,0.05);">
                    <small style="color: {AZUL_EDEESTE}; font-weight: bold;">IPI: {row['IPI']:.1f}/100</small><br>
                    <strong style="color: {GRIS_OSCURO};">ID: {row['TOTALIZADOR']}</strong><br>
                    <span style="color: #d32f2f; font-weight: 800;">{row[col_kwh]:,.0f} kWh</span>
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        c1, c2 = st.columns([2, 1])
        with c1:
            df_top10 = df_filtrado.sort_values(by=col_kwh, ascending=False).head(10)
            fig_top = px.bar(df_top10, x='TOTALIZADOR', y=col_kwh, color='IPI', text_auto='.2s', color_continuous_scale='Reds', title="Ranking de Impacto")
            st.plotly_chart(fig_top, use_container_width=True)
        with c2:
            df_circ = df_filtrado.groupby('CIRCUITO')[[col_kwh]].sum().reset_index()
            fig_pie = px.pie(df_circ, values=col_kwh, names='CIRCUITO', hole=0.4, title="Pérdida por Circuito")
            st.plotly_chart(fig_pie, use_container_width=True)

    # ---------------------------------------------------------
    # PESTAÑA 2: CÓDIGO NUEVO (Pareto y Matriz)
    # ---------------------------------------------------------
    with tab2:
        st.header("🎯 Análisis de Impacto Estratégico")
        
        # Lógica Pareto
        df_pareto = df_filtrado.sort_values(by=col_kwh, ascending=False).reset_index()
        df_pareto['PERDIDA_ACUM'] = df_pareto[col_kwh].cumsum()
        total_p = df_pareto[col_kwh].sum()
        df_pareto['PCT_ACUM'] = (df_pareto['PERDIDA_ACUM'] / total_p) * 100 if total_p > 0 else 0
        pocos_vitales = df_pareto[df_pareto['PCT_ACUM'] <= 80]

        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            fig_p = go.Figure()
            fig_p.add_trace(go.Bar(x=df_pareto['TOTALIZADOR'][:25], y=df_pareto[col_kwh][:25], name="kWh", marker_color=AZUL_EDEESTE))
            fig_p.add_trace(go.Scatter(x=df_pareto['TOTALIZADOR'][:25], y=df_pareto['PCT_ACUM'][:25], name="% Acumulado", yaxis="y2", line=dict(color="#d32f2f", width=3)))
            fig_p.update_layout(title="Curva de Pareto 80/20", yaxis2=dict(overlaying="y", side="right", range=[0, 105]))
            st.plotly_chart(fig_p, use_container_width=True)
        
        with col_p2:
            st.metric("Totalizadores que hacen el 80%", len(pocos_vitales))
            st.warning(f"Concentrando esfuerzos en solo {len(pocos_vitales)} puntos, impactas el 80% del problema en esta zona.")

        st.divider()
        st.subheader("📍 Matriz de Decisión (Intensidad vs Volumen)")
        fig_scatter = px.scatter(df_filtrado, x=col_pct, y=col_kwh, size='IPI', color='IPI', hover_name='TOTALIZADOR', color_continuous_scale='Reds')
        fig_scatter.add_hline(y=df_filtrado[col_kwh].mean(), line_dash="dot", annotation_text="Pérdida Promedio")
        st.plotly_chart(fig_scatter, use_container_width=True)

    # --- SECCIÓN COMÚN: AUDITORÍA (Al final para que sirva a ambas pestañas) ---
    st.divider()
    st.subheader("🔍 Auditoría de Suministros (Detalle NICs)")
    totalizador_sel = st.selectbox("Seleccione ID para análisis profundo:", [""] + df_filtrado['TOTALIZADOR'].unique().tolist())
    if totalizador_sel:
        nics = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]['NIC'].astype(str).tolist()
        if df_bdg is not None:
            detalle = df_bdg[df_bdg['NIC'].astype(str).isin(nics)].copy()
            st.write(f"Suministros vinculados al ID: {totalizador_sel}")
            st.dataframe(detalle, use_container_width=True)
else:
    st.markdown("# 👋 Bienvenido a PuntoRojo\nSuba el archivo Excel en la barra lateral para comenzar.")
