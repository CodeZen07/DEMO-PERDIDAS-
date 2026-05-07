import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="PuntoRojo v3.4 | EDEESTE", layout="wide", page_icon="🔴")

AZUL_EDEESTE = "#00235d"
AMARILLO_EDEESTE = "#ffc20e"

# 2. CARGA DE DATOS MEJORADA (Incluye BDG)
@st.cache_data
def cargar_datos_balance(archivo):
    xls = pd.ExcelFile(archivo)
    
    # Balance Central
    df_bal = pd.read_excel(xls, sheet_name="Balance Central")
    df_bal.columns = [str(c).strip().upper() for c in df_bal.columns]
    
    # Relación
    df_rel = pd.read_excel(xls, sheet_name="Relación")
    df_rel.columns = [str(c).strip().upper() for c in df_rel.columns]
    
    # BDG (Búsqueda flexible por nombre de hoja)
    nombre_bdg = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    df_bdg = pd.read_excel(xls, sheet_name=nombre_bdg) if nombre_bdg else None
    if df_bdg is not None:
        df_bdg.columns = [str(c).strip().upper() for c in df_bdg.columns]
    
    return df_bal, df_rel, df_bdg

# 3. INTERFAZ Y FILTROS
st.title("🔴 PuntoRojo v3.4 — Control de Pérdidas")
archivo = st.sidebar.file_uploader("Cargar Archivo Excel", type=["xlsx"])

if archivo:
    df_bal, df_rel, df_bdg = cargar_datos_balance(archivo)
    
    # Identificación de columnas
    col_pct = '%PÉRDIDA' if '%PÉRDIDA' in df_bal.columns else 'PERDIDA_PCT'
    col_kwh = 'PÉRDIDA' if 'PÉRDIDA' in df_bal.columns else 'PERDIDA'
    col_oficina = 'OFICINA' if 'OFICINA' in df_bal.columns else None
    
    # Limpieza numérica inicial
    df_bal[col_pct] = pd.to_numeric(df_bal[col_pct], errors='coerce').fillna(0)
    df_bal[col_kwh] = pd.to_numeric(df_bal[col_kwh], errors='coerce').fillna(0)

    # --- MEJORA: ÍNDICE DE PRIORIZACIÓN DE INSPECCIÓN (IPI) ---
    max_kwh = df_bal[col_kwh].max() if df_bal[col_kwh].max() > 0 else 1
    df_bal['IPI'] = ((df_bal[col_kwh] / max_kwh) * 70 + (df_bal[col_pct] / 100) * 30).clip(0, 100)

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

    # --- BLOQUE 1: KPIs DE IMPACTO ---
    st.subheader(titulo_seccion)
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric("Pérdida Acumulada", f"{df_filtrado[col_kwh].sum():,.2f} kWh")
    with kpi2:
        st.metric("% Pérdida Promedio", f"{df_filtrado[col_pct].mean():.2f}%")
    with kpi3:
        st.metric("Puntos Críticos (>15%)", len(df_filtrado[df_filtrado[col_pct] > 15]))
    with kpi4:
        top_id = df_filtrado.sort_values(by='IPI', ascending=False)['TOTALIZADOR'].iloc[0] if not df_filtrado.empty else "N/A"
        st.metric("Máxima Prioridad", f"ID: {top_id}")

    # --- BLOQUE 2: PRIORIZACIÓN ESTRATÉGICA ---
    st.divider()
    st.subheader("🚀 Próximas Inspecciones Sugeridas (Basado en IPI)")
    top_prioridad = df_filtrado.sort_values(by='IPI', ascending=False).head(5)
    cols_p = st.columns(5)
    for i, (idx, row) in enumerate(top_prioridad.iterrows()):
        with cols_p[i]:
            st.markdown(f"""
            <div style="padding:10px; border-radius:10px; border-left: 5px solid #d32f2f; background-color:white;">
                <small>Prioridad: {row['IPI']:.1f}/100</small><br>
                <strong>ID: {row['TOTALIZADOR']}</strong><br>
                <span style="color:#d32f2f;">{row[col_kwh]:,.0f} kWh</span>
            </div>
            """, unsafe_allow_html=True)

    # --- BLOQUE 3: GRÁFICOS DINÁMICOS ---
    st.divider()
    c_graf1, c_graf2 = st.columns([2, 1])
    
    with c_graf1:
        st.subheader(f"📊 Top 10 Impacto en {seleccion_oficina}")
        df_top10 = df_filtrado.sort_values(by=col_kwh, ascending=False).head(10)
        fig_top = px.bar(df_top10, x='TOTALIZADOR', y=col_kwh, color='IPI',
                         text_auto='.2s', color_continuous_scale='Reds',
                         labels={col_kwh: 'kWh Perdidos', 'IPI': 'Score Prioridad'})
        st.plotly_chart(fig_top, use_container_width=True)

    with c_graf2:
        st.subheader("📉 Distribución por Circuito")
        df_circ = df_filtrado.groupby('CIRCUITO')[[col_kwh]].sum().reset_index()
        fig_pie = px.pie(df_circ, values=col_kwh, names='CIRCUITO', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- BLOQUE 4: AUDITORÍA DE SUMINISTROS (FILTRO POR TOTALIZADOR) ---
    st.divider()
    st.subheader("🔍 Auditoría Detallada: Totalizador ↔ Medidores y Contratos")
    
    totalizador_sel = st.selectbox("Seleccione un Totalizador para ver sus componentes asociados:", [""] + df_filtrado['TOTALIZADOR'].unique().tolist())

    if totalizador_sel:
        # 1. Obtener los NICs vinculados a través de la hoja 'Relación'
        nics_vinculados = df_rel[df_rel['TOTALIZADOR'].astype(str) == str(totalizador_sel)]['NIC'].astype(str).tolist()
        
        if df_bdg is not None:
            # 2. Filtrar BDG y aplicar limpieza para evitar el TypeError
            detalle_clientes = df_bdg[df_bdg['NIC'].astype(str).isin(nics_vinculados)].copy()
            
            # Limpieza de datos críticos para evitar errores de suma
            detalle_clientes['PROMEDIO_CONSUMO'] = pd.to_numeric(detalle_clientes['PROMEDIO_CONSUMO'], errors='coerce').fillna(0)
            detalle_clientes['BALANCE'] = pd.to_numeric(detalle_clientes['BALANCE'], errors='coerce').fillna(0)
            
            # Métricas del totalizador seleccionado
            inf1, inf2, inf3 = st.columns(3)
            inf1.metric("Medidores/Contratos", len(detalle_clientes))
            inf2.metric("Deuda Total en Punto", f"RD$ {detalle_clientes['BALANCE'].sum():,.2f}")
            inf3.metric("Consumo Prom. Clientes", f"{detalle_clientes['PROMEDIO_CONSUMO'].sum():,.0f} kWh")
            
            st.write(f"### Detalle de Suministros Asociados al ID {totalizador_sel}")
            # Columnas de interés (Medidores, NICs, Contratos)
            cols_interes = ['NIC', 'NIS_RAD', 'CONTADOR', 'NOMBRE', 'ESTADO', 'BALANCE', 'CORTABLE', 'PROMEDIO_CONSUMO', 'DIRECCION']
            cols_finales = [c for c in cols_interes if c in detalle_clientes.columns]
            
            st.dataframe(detalle_clientes[cols_finales], use_container_width=True)
        else:
            st.warning("⚠️ No se encontró la hoja de base de datos (BDG) para cruzar los contratos.")

    # --- BLOQUE 5: TABLA MAESTRA ---
    with st.expander("Ver Tabla General de Datos"):
        st.dataframe(
            df_filtrado[['TOTALIZADOR', 'CIRCUITO', col_kwh, col_pct, 'IPI']].style.format({col_kwh: '{:,.2f}', col_pct: '{:.2f}%', 'IPI': '{:.1f}'}),
            use_container_width=True
        )

else:
    st.info("👋 Por favor, cargue el archivo Excel de Balance de Totalizadores.")
