import random
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ─────────────────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PuntoRojo v3.0 – Gestión Gerencial",
    page_icon="🔴",
    layout="wide",
)

# ─────────────────────────────────────────────────────────
# FUNCIONES DE CARGA Y PROCESAMIENTO
# ─────────────────────────────────────────────────────────

def leer_balance_ct(xls):
    """Detecta la fila con 'ITEM' en Balance CT y extrae metadata."""
    raw = pd.read_excel(xls, sheet_name="Balance CT", header=None, dtype=str)
    meta = {}
    header_row = None

    for i, row in raw.iterrows():
        vals = row.fillna("").astype(str).tolist()
        for j, v in enumerate(vals):
            v_up = v.strip().upper()
            if "TOTALIZADOR:" in v_up and "TOTALIZADOR" not in meta:
                meta["TOTALIZADOR"] = vals[j + 2] if j + 2 < len(vals) else ""
            if "SECTOR:" in v_up and "SECTOR" not in meta:
                meta["SECTOR"] = vals[j + 2] if j + 2 < len(vals) else ""
            if "CIRCUITO" in v_up and "CIRCUITO" not in meta:
                meta["CIRCUITO"] = vals[j + 1] if j + 1 < len(vals) else ""

        if "ITEM" in [v.strip().upper() for v in vals]:
            header_row = i
            break

    if header_row is None: return meta, None

    df = pd.read_excel(xls, sheet_name="Balance CT", header=header_row)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Limpieza de filas vacías basada en ITEM
    df = df[pd.to_numeric(df["ITEM"], errors="coerce").notna()]
    return meta, df.reset_index(drop=True)

def leer_bdg(xls):
    """Carga la Base de Datos General (BDG)."""
    sheet = next((s for s in xls.sheet_names if "bdg" in s.lower()), None)
    if not sheet: return None
    df = pd.read_excel(xls, sheet_name=sheet)
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def cruzar_informacion(df_clientes, df_bdg):
    """Cruce Gerencial: Une datos de la BDG al Balance CT por el NIC."""
    if df_clientes is not None and df_bdg is not None:
        # Asegurar que NIC sea string para el cruce
        df_clientes["NIC"] = df_clientes["NIC"].astype(str)
        df_bdg["NIC"] = df_bdg["NIC"].astype(str)
        
        # Seleccionamos columnas clave de la BDG para el gerente
        columnas_interes = ["NIC", "ESTADO", "BALANCE", "CORTABLE", "TARIFA"]
        df_interes = df_bdg[[c for c in columnas_interes if c in df_bdg.columns]]
        
        return pd.merge(df_clientes, df_interes, on="NIC", how="left")
    return df_clientes

# ─────────────────────────────────────────────────────────
# LÓGICA DE SEMÁFORO
# ─────────────────────────────────────────────────────────

def semaforo_color(pct):
    pct = abs(float(pct))
    if pct > 30: return "red"
    elif pct >= 15: return "orange"
    else: return "green"

# ─────────────────────────────────────────────────────────
# INTERFAZ DE USUARIO (UI)
# ─────────────────────────────────────────────────────────

st.title("🔴 PuntoRojo v3.0 — Panel de Control Gerencial")
st.markdown("### Gestión de Pérdidas Eléctricas - Distrito Nacional")

archivo = st.file_uploader("Subir Balance de Totalizadores (.xlsx)", type=["xlsx"])

if archivo:
    xls = pd.ExcelFile(archivo)
    
    # Carga de datos
    with st.spinner("Realizando cruce de información..."):
        meta_ct, df_ct = leer_balance_ct(xls)
        df_bdg = leer_bdg(xls)
        
        # Ejecutar el cruce automático
        df_final = cruzar_informacion(df_ct, df_bdg)

    # TABS PARA ORGANIZACIÓN GERENCIAL
    tab_resumen, tab_detalles, tab_mapa = st.tabs(["📊 Resumen Ejecutivo", "📋 Detalle de Clientes", "🗺️ Mapa Operativo"])

    with tab_resumen:
        col1, col2, col3 = st.columns(3)
        col1.metric("Totalizador", meta_ct.get("TOTALIZADOR", "N/D"))
        col2.metric("Sector", meta_ct.get("SECTOR", "N/D"))
        col3.metric("Clientes en CT", len(df_final) if df_final is not None else 0)
        
        st.divider()
        st.info("Utilice las pestañas superiores para profundizar en el análisis de pérdidas.")

    with tab_detalles:
        st.subheader("Análisis de Suministros (Cruce BDG)")
        if df_final is not None:
            # Filtro de búsqueda
            busqueda = st.text_input("🔍 Buscar por NIC o Nombre")
            if busqueda:
                mask = df_final.apply(lambda r: r.astype(str).str.contains(busqueda, case=False)).any(axis=1)
                df_final = df_final[mask]
            
            st.dataframe(df_final, use_container_width=True)
        else:
            st.error("No se pudo procesar la información de clientes.")

    with tab_mapa:
        st.subheader("Localización de Pérdidas")
        # Aquí iría la lógica de folium ya definida en tu base anterior
        st.caption("Mapa configurado para visualización por circuito.")
        
else:
    st.warning("Por favor, suba un archivo para activar el tablero.")

# ─────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.write("**Estatus de Sistema:** Operativo")
st.sidebar.write("**Nivel:** Gerencial")
