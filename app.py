import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="PuntoRojo v3.3 | EDEESTE", layout="wide", page_icon="🔴")

AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"

# 2. CARGA DE DATOS (Mantiene tu estructura original pero con limpieza)
@st.cache_data
def cargar_datos_balance(archivo):
    xls = pd.ExcelFile(archivo)
    
    # Balance Central: El motor de los indicadores
    df_bal = pd.read_excel(xls, sheet_name="Balance Central")
    df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
    
    # Relación: Para el detalle de suministros
    df_rel = pd.read_excel(xls, sheet_name="Relación")
    df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
    
    return df_bal, df_rel

# 3. INTERFAZ Y FILTROS
st.title("🔴 PuntoRojo v3.3 — Control de Pérdidas")
archivo = st.sidebar.file_uploader("Cargar Archivo Excel", type=["xlsx"])

if archivo:
    df_bal, df_rel = cargar_datos_balance(archivo)
    
    # Limpieza de nombres de columnas para asegurar compatibilidad
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else 'PERDIDA_PCT'
    col_kwh = 'PÉRDIDA' if 'PÉRDIDA' in df_bal.columns else 'PERDIDA'
    col_oficina = 'OFICINA' if 'OFICINA' in df_bal.columns else None
    
    # Convertir a numérico lo necesario
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal[col_kwh] = pd.to_numeric(df_bal[col_kwh], errors='coerce').fillna(0)

    # --- BARRA LATERAL: FILTROS DINÁMICOS ---
    st.sidebar.header("🔍 Filtros de Segmentación")
    
    opciones_oficina = ["TODAS"]
    if col_oficina:
        opciones_oficina += sorted(df_bal[col_oficina].dropna().unique().tolist())
    
    seleccion_oficina = st.sidebar.selectbox("Seleccione Oficina/Zona:", opciones_oficina)
    
    # Aplicar Filtro de Oficina
    if seleccion_oficina != "TODAS":
        df_filtrado = df_bal[df_bal[col_oficina] == seleccion_oficina]
        titulo_seccion = f"Análisis: {seleccion_oficina}"
    else:
        df_filtrado = df_bal
        titulo_seccion = "Análisis General (Global EDEESTE)"

    # --- BLOQUE 1: RESUMEN DE PÉRDIDAS ---
    st.subheader(titulo_seccion)
    kpi1, kpi2, kpi3 = st.columns(3)
    
    with kpi1:
        st.metric("Pérdida Acumulada", f"{df_filtrado[col_kwh].sum():,.2f} kWh")
    with kpi2:
        st.metric("% Pérdida Promedio", f"{df_filtrado[col_pct].mean():.2f}%")
    with kpi3:
        st.metric("Puntos Críticos", len(df_filtrado[df_filtrado[col_pct] > 15]))

    # --- BLOQUE 2: TOP 10 DINÁMICO ---
    st.divider()
    st.subheader(f"📊 Top 10 Totalizadores con mayor pérdida en {seleccion_oficina}")
    
    # Ordenamos por pérdida absoluta (kWh) para ver el impacto financiero real
    df_top10 = df_filtrado.sort_values(by=col_kwh, ascending=False).head(10)
    
    fig_top = px.bar(
        df_top10, 
        x='TOTALIZADOR', 
        y=col_kwh, 
        color=col_pct,
        text_auto='.2s',
        labels={col_kwh: 'kWh Perdidos', col_pct: '% Pérdida'},
        color_continuous_scale='Reds',
        title="Impacto por Totalizador (Color = Gravedad en %)"
    )
    st.plotly_chart(fig_top, use_container_width=True)

    # --- BLOQUE 3: DETALLE POR CIRCUITO ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("### 📉 Distribución por Circuito")
        df_circ = df_filtrado.groupby('CIRCUITO')[[col_kwh]].sum().reset_index()
        fig_pie = px.pie(df_circ, values=col_kwh, names='CIRCUITO', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with c2:
        st.write("### 📋 Tabla de Datos")
        st.dataframe(
            df_filtrado[['TOTALIZADOR', 'CIRCUITO', col_kwh, col_pct, 'REPORTADO ESTADO' if 'REPORTADO ESTADO' in df_filtrado.columns else 'ESTADO ACTUAL']].style.format({col_kwh: '{:,.2f}', col_pct: '{:.2f}%'}),
            use_container_width=True
        )

else:
    st.info("👋 Bienvenida/o. Por favor carga el archivo de Balance de Totalizadores para comenzar el análisis por zona.")
