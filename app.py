import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="PuntoRojo v5.0 | EDEESTE", layout="wide", page_icon="🔴")

AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"
GRIS_TEXTO = "#31333F" # Color oscuro para legibilidad

# Estilos para asegurar que el texto de los KPIs se vea (Dark Mode en texto)
st.markdown(f"""
    <style>
    [data-testid="stMetricValue"] {{ color: {AZUL_EDEESTE} !important; font-weight: bold; }}
    [data-testid="stMetricLabel"] {{ color: {GRIS_TEXTO} !important; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 24px; }}
    </style>
""", unsafe_allow_html=True)

# 2. CARGA Y PROCESAMIENTO
@st.cache_data
def cargar_datos_balance(archivo):
    xls = pd.ExcelFile(archivo)
    df_bal = pd.read_excel(xls, sheet_name="Balance Central")
    df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
    df_rel = pd.read_excel(xls, sheet_name="Relación")
    df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
    nombre_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    df_bdg = pd.read_excel(xls, sheet_name=nombre_bdg) if nombre_bdg else None
    return df_bal, df_rel, df_bdg

def generar_reporte_excel(df_top, df_circ):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_top.to_excel(writer, sheet_name='Top 10 Totalizadores', index=False)
        df_circ.to_excel(writer, sheet_name='Impacto por Circuito', index=False)
        
        # Hoja de Recomendaciones Estratégicas
        estrategia = pd.DataFrame({
            'Pilar': ['Normativa ISO 50001', 'Inspección Técnica', 'Gestión Social', 'Tecnología'],
            'Recomendación': [
                'Implementar sistemas de gestión de energía para mejora continua en medición.',
                'Priorizar totalizadores en Cuadrante 1 (Alta pérdida/Alto %). Revisar precintos y borneras.',
                'En zonas de alto impacto social, aplicar programas de regularización antes del corte.',
                'Desplegar medición inteligente (AMI) en los 10 puntos críticos detectados hoy.'
            ]
        })
        estrategia.to_excel(writer, sheet_name='Estrategia_ISO_Latam', index=False)
    return output.getvalue()

# 3. LÓGICA PRINCIPAL
archivo = st.sidebar.file_uploader("📂 Cargar Datos", type=["xlsx"])

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_balance(archivo)
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else 'PERDIDA_PCT'
    col_kwh = 'PÉRDIDA' if 'PÉRDIDA' in df_bal.columns else 'PERDIDA'
    col_oficina = 'OFICINA' if 'OFICINA' in df_bal.columns else 'OFICINA'
    
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal[col_kwh] = pd.to_numeric(df_bal[col_kwh], errors='coerce').fillna(0)
    
    # IPI y Filtros
    max_val = abs(df_bal[col_kwh]).max() if abs(df_bal[col_kwh]).max() > 0 else 1
    df_bal['IPI'] = ((abs(df_bal[col_kwh]) / max_val) * 70 + (abs(df_bal[col_pct]) / 100) * 30).clip(0, 100)
    
    opciones = ["TODAS"] + sorted(df_bal[col_oficina].dropna().unique().tolist()) if col_oficina in df_bal.columns else ["TODAS"]
    sel_oficina = st.sidebar.selectbox("Seleccione Oficina:", opciones)
    df_f = df_bal if sel_oficina == "TODAS" else df_bal[df_bal[col_oficina] == sel_oficina]

    tab1, tab2 = st.tabs(["📊 Dashboard Operativo", "🎯 Matriz de Decisión & Reporte"])

    with tab1:
        st.markdown(f"### 🔴 Estado de Red: {sel_oficina}")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Pérdida Total", f"{df_f[col_kwh].sum():,.0f} kWh")
        k2.metric("% Pérdida Promedio", f"{df_f[col_pct].mean():.2f}%")
        k3.metric("Puntos Críticos (>15%)", len(df_f[abs(df_f[col_pct]) > 15]))
        
        top_unit = df_f.sort_values(by='IPI', ascending=False)['TOTALIZADOR'].iloc[0] if not df_f.empty else "N/A"
        k4.metric("Máxima Prioridad", top_unit)

        # Ranking Visual
        df_top10 = df_f.sort_values(by=col_kwh, ascending=True).head(10) # Ascending True por ser negativos
        fig_bar = px.bar(df_top10, x='TOTALIZADOR', y=col_kwh, color='IPI', title="Top 10 Fugas de Energía", color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        st.subheader("📍 Matriz de Intervención Drástica")
        
        # Identificar zonas de acción inmediata
        mean_kwh = df_f[col_kwh].mean()
        fig_scatter = px.scatter(df_f, x=col_pct, y=col_kwh, size='IPI', color='IPI',
                                 hover_name='TOTALIZADOR', title="Matriz Volumen vs Intensidad",
                                 color_continuous_scale='Reds', labels={col_pct: '% Pérdida', col_kwh: 'kWh Perdidos'})
        
        fig_scatter.add_hline(y=mean_kwh, line_dash="dot", annotation_text="Pérdida Media", line_color="black")
        fig_scatter.add_vline(x=-15, line_dash="dot", annotation_text="Límite 15%", line_color="red")
        
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        st.info("💡 **Acción Drástica:** Los puntos en el cuadrante inferior izquierdo (Alta pérdida negativa y Alto %) son donde el impacto de una inspección será inmediato en los estados financieros.")

        # BOTÓN DE DESCARGA
        st.divider()
        st.subheader("📁 Generación de Reporte Ejecutivo")
        df_top_export = df_f.sort_values(by=col_kwh, ascending=True).head(10)
        df_circ_export = df_f.groupby('CIRCUITO')[col_kwh].sum().sort_values().reset_index()
        
        excel_data = generar_reporte_excel(df_top_export, df_circ_export)
        st.download_button(
            label="📥 Descargar Reporte de Intervención (ISO/Latam)",
            data=excel_data,
            file_name=f"Reporte_PuntoRojo_{sel_oficina}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👋 Cargue el archivo para activar el análisis de impacto.")
