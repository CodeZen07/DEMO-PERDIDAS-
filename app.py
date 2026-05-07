import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN E IDENTIDAD VISUAL
st.set_page_config(page_title="PuntoRojo v3.5 | EDEESTE", layout="wide", page_icon="🔴")

# Colores institucionales y de interfaz
AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"
GRIS_FONDO = "#f0f2f6"
GRIS_OSCURO = "#1e1e1e"

# CSS para mejorar la estética de las tarjetas y contenedores
st.markdown(f"""
    <style>
    .main {{ background-color: {GRIS_FONDO}; }}
    .stMetric {{
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    [data-testid="stSidebar"] {{
        background-color: white;
    }}
    .stButton>button {{
        width: 100%;
        border-radius: 5px;
        background-color: {AZUL_EDEESTE};
        color: white;
    }}
    </style>
""", unsafe_allow_html=True)

# 2. LÓGICA DE CARGA (Sin cambios en tu estructura funcional)
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

# 3. INTERFAZ DE USUARIO
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Red_dot.svg/1200px-Red_dot.svg.png", width=50)
    st.title("Configuración")
    st.markdown("---")
    archivo = st.file_uploader("📂 Cargar Datos Maestro", type=["xlsx"], help="Suba el archivo de Balance de Totalizadores generado por el sistema.")
    st.markdown("---")
    st.info("Desarrollado para la gestión eficiente de pérdidas en EDEESTE.")

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_balance(archivo)
    
    # Limpieza y cálculos (Mantenemos tu lógica intacta)
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else 'PERDIDA_PCT'
    col_kwh = 'PÉRDIDA' if 'PÉRDIDA' in df_bal.columns else 'PERDIDA'
    col_oficina = 'OFICINA' if 'OFICINA' in df_bal.columns else None
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal[col_kwh] = pd.to_numeric(df_bal[col_kwh], errors='coerce').fillna(0)
    max_kwh = df_bal[col_kwh].max() if df_bal[col_kwh].max() > 0 else 1
    df_bal['IPI'] = ((df_bal[col_kwh] / max_kwh) * 70 + (df_bal[col_pct] / 100) * 30).clip(0, 100)

    # Filtros dinámicos en sidebar
    opciones_oficina = ["TODAS"]
    if col_oficina:
        opciones_oficina += sorted(df_bal[col_oficina].dropna().unique().tolist())
    seleccion_oficina = st.sidebar.selectbox("📍 Filtrar por Oficina:", opciones_oficina)
    
    df_filtrado = df_bal if seleccion_oficina == "TODAS" else df_bal[df_bal[col_oficina] == seleccion_oficina]

    # --- ENCABEZADO DE DASHBOARD ---
    st.markdown(f"# 🔴 PuntoRojo v3.5 | <small>{seleccion_oficina}</small>", unsafe_allow_html=True)
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Pérdida Total", f"{df_filtrado[col_kwh].sum():,.0f} kWh", delta_color="inverse")
    kpi2.metric("% Pérdida Prom.", f"{df_filtrado[col_pct].mean():.2f}%")
    kpi3.metric("Puntos Críticos", len(df_filtrado[df_filtrado[col_pct] > 15]))
    top_id = df_filtrado.sort_values(by='IPI', ascending=False)['TOTALIZADOR'].iloc[0] if not df_filtrado.empty else "N/A"
    kpi4.metric("Máxima Prioridad", top_id)

    # --- SECCIÓN DE PRIORIZACIÓN (DISEÑO MEJORADO) ---
    st.markdown("### 🚀 Próximas Inspecciones Sugeridas")
    top_prioridad = df_filtrado.sort_values(by='IPI', ascending=False).head(5)
    cols_p = st.columns(5)
    for i, (idx, row) in enumerate(top_prioridad.iterrows()):
        with cols_p[i]:
            st.markdown(f"""
            <div style="padding:15px; border-radius:12px; border-left: 6px solid {AZUL_EDEESTE}; background-color: white; box-shadow: 2px 2px 8px rgba(0,0,0,0.05);">
                <small style="color: {AZUL_EDEESTE}; font-weight: bold;">Prioridad: {row['IPI']:.1f}/100</small><br>
                <strong style="color: {GRIS_OSCURO}; font-size: 1.1em;">ID: {row['TOTALIZADOR']}</strong><br>
                <span style="color: #d32f2f; font-size: 1.2em; font-weight: 800;">{row[col_kwh]:,.0f} kWh</span>
            </div>
            """, unsafe_allow_html=True)

    # --- GRÁFICOS ---
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        df_top10 = df_filtrado.sort_values(by=col_kwh, ascending=False).head(10)
        fig_top = px.bar(df_top10, x='TOTALIZADOR', y=col_kwh, color='IPI',
                         text_auto='.2s', color_continuous_scale='Reds',
                         title="Ranking de Impacto por Totalizador")
        fig_top.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_top, use_container_width=True)
    with c2:
        df_circ = df_filtrado.groupby('CIRCUITO')[[col_kwh]].sum().reset_index()
        fig_pie = px.pie(df_circ, values=col_kwh, names='CIRCUITO', hole=0.4, title="Pérdida por Circuito")
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- AUDITORÍA ---
    st.markdown("### 🔍 Auditoría de Suministros")
    totalizador_sel = st.selectbox("Seleccione un Totalizador para análisis profundo:", [""] + df_filtrado['TOTALIZADOR'].unique().tolist())

    if totalizador_sel:
        nics_vinculados = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]['NIC'].astype(str).tolist()
        if df_bdg is not None:
            detalle_clientes = df_bdg[df_bdg['NIC'].astype(str).isin(nics_vinculados)].copy()
            detalle_clientes['PROMEDIO_CONSUMO'] = pd.to_numeric(detalle_clientes['PROMEDIO_CONSUMO'], errors='coerce').fillna(0)
            detalle_clientes['BALANCE'] = pd.to_numeric(detalle_clientes['BALANCE'], errors='coerce').fillna(0)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Clientes", len(detalle_clientes))
            m2.metric("Deuda en Punto", f"RD$ {detalle_clientes['BALANCE'].sum():,.0f}")
            m3.metric("Consumo Promedio", f"{detalle_clientes['PROMEDIO_CONSUMO'].sum():,.0f} kWh")
            
            st.dataframe(detalle_clientes, use_container_width=True)
        else:
            st.warning("Cargue la hoja BDG para ver detalle de clientes.")

else:
    # PANTALLA DE BIENVENIDA AMISTOSA
    col_welcome, _ = st.columns([2, 1])
    with col_welcome:
        st.markdown(f"""
        # 👋 Bienvenido a PuntoRojo
        ### Sistema Inteligente de Control de Pérdidas Energéticas
        
        Esta herramienta permite analizar los balances de energía de **EDEESTE** para identificar:
        * 🎯 **Focos de fraude** y anomalías técnicas.
        * 🚀 **Priorización de brigadas** basada en volumen e impacto.
        * 📊 **Auditoría de suministros** cruzada con la base de datos comercial.
        
        **Para comenzar, suba el archivo de Balance en la barra lateral izquierda.**
        """)
        st.image("https://www.edeeste.com.do/wp-content/uploads/2021/04/Logo-Edeeste-01.png", width=250)
