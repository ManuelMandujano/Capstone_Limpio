# analisis_sensibilidad.py
# -*- coding: utf-8 -*-
from pathlib import Path
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# ==========================
# Config
# ==========================
INPUT_FILES = [
    "resultados_5y.csv",
    "resultados_10y.csv",
    "resultados_15y.csv",
]

# KPIs a analizar (columnas existentes en tus CSVs)
KPIS = [
    ("Def_total_Hm3", "Déficit total [Hm³]"),
    ("Rebalse_total_Hm3", "Rebalse total [Hm³]"),
    ("Satisf_prom_pct", "Satisfacción promedio [%]"),
    ("TOTAL_fin_Hm3", "Agua almacenada final [Hm³]"),
    ("Qturb_total_Hm3", "Volumen turbinado [Hm³]"),
    ("Qdis_prom_Hm3_mes", "Caudal disponible prom. [Hm³/mes]"),
]

# Escenarios de volúmenes iniciales (VRFI, A, B) -> etiqueta %
ESCENARIOS_VOL = [
    ((0.0, 0.0, 0.0), "Init 0%"),
    ((43.8, 65.0, 26.3), "Init 25%"),
    ((87.5, 130.0, 52.5), "Init 50%"),
    ((131.3, 195.0, 78.8), "Init 75%"),
    ((175.0, 260.0, 105.0), "Init 100%"),
]
TOL = 1e-3  # tolerancia para igualar flotantes

# ==========================
# Utilidades
# ==========================
def etiqueta_init(vrfi, a, b):
    for (vr, va, vb), lab in ESCENARIOS_VOL:
        if abs(vrfi - vr) < TOL and abs(a - va) < TOL and abs(b - vb) < TOL:
            return lab
    # si no calza exactamente, arma % relativo si deseas; aquí devolvemos valor numérico
    return f"Init ({vrfi:.1f},{a:.1f},{b:.1f})"

def asegurar_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def ordenar_init_labels(labels):
    orden = {lab: i for i, (_, lab) in enumerate(ESCENARIOS_VOL)}
    return sorted(labels, key=lambda x: orden.get(x, 999))

def figura_linea(x, y, title, xlabel, ylabel, out_png: Path):
    plt.figure(figsize=(10,5))
    plt.plot(x, y, marker="o")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

# ==========================
# Carga y preparación
# ==========================
def cargar_y_preparar():
    frames = []
    for f in INPUT_FILES:
        p = Path(f)
        if not p.exists():
            print(f"[WARN] No encontré {f}, lo salto.")
            continue
        df = pd.read_csv(p)
        # Normalizaciones mínimas:
        if "period_years" not in df.columns:
            # inferir desde el nombre del archivo
            if "5y" in p.stem:
                df["period_years"] = 5
            elif "10y" in p.stem:
                df["period_years"] = 10
            elif "15y" in p.stem:
                df["period_years"] = 15

        # FE efectivo (suponemos FEA == FEB)
        if "FEA" in df.columns:
            df["FE"] = df["FEA"]
        elif "FEB" in df.columns:
            df["FE"] = df["FEB"]
        else:
            raise ValueError("No encuentro columnas FEA/FEB en el CSV.")

        # Etiqueta de escenario inicial
        df["init_label"] = df.apply(lambda r: etiqueta_init(r["VRFI0"], r["A0"], r["B0"]), axis=1)

        frames.append(df)

    if not frames:
        raise RuntimeError("No se cargó ningún CSV. Revisa rutas/nombres de archivos.")
    full = pd.concat(frames, ignore_index=True)

    # Asegurar numéricos por si vienen como texto
    for col, _ in KPIS:
        full[col] = pd.to_numeric(full[col], errors="coerce")
    full["FE"] = pd.to_numeric(full["FE"], errors="coerce")

    return full

# ==========================
# Análisis y gráficos
# ==========================
def analizar_periodo(df_periodo: pd.DataFrame, period_years: int, out_root: Path):
    """Genera: resúmenes + gráficos para un periodo específico."""
    # carpetas de salida
    out_fe_fijo = out_root / f"{period_years}y" / "analisis_por_FE_fijo"
    out_vol_fijo = out_root / f"{period_years}y" / "analisis_por_VOL_fijo"
    asegurar_dir(out_fe_fijo)
    asegurar_dir(out_vol_fijo)

    # PDFs contenedores
    pdf_fe = PdfPages(out_fe_fijo / f"graficos_FEfijo_{period_years}y.pdf")
    pdf_vol = PdfPages(out_vol_fijo / f"graficos_VOLfijo_{period_years}y.pdf")

    # ============
    # 1) FE fijo: variar vol. inicial
    # ============
    res_tablas_fe = []
    for fe in sorted(df_periodo["FE"].unique()):
        df_fe = df_periodo[df_periodo["FE"].round(3) == round(fe,3)]
        # promedio por escenario inicial (sobre las 6/3/2 iteraciones)
        g = df_fe.groupby("init_label", as_index=False)[[k for k,_ in KPIS]].mean()
        g["FE"] = fe
        # ordenar por % inicial
        g = g.set_index("init_label").loc[ordenar_init_labels(g["init_label"].tolist())].reset_index()
        res_tablas_fe.append(g)

        # gráficos: un KPI por figura, X=init (%), Y=KPI
        x = g["init_label"]
        for col, lab in KPIS:
            fig = plt.figure(figsize=(10,5))
            plt.plot(x, g[col], marker="o")
            plt.title(f"{lab} — FE fijo = {fe:.2f} — Periodo {period_years} años")
            plt.xlabel("Volumen inicial (escenario)")
            plt.ylabel(lab)
            plt.xticks(rotation=20)
            plt.grid(True, linestyle="--", alpha=0.4)
            plt.tight_layout()
            pdf_fe.savefig(fig)
            plt.close(fig)

    if res_tablas_fe:
        resumen_fe = pd.concat(res_tablas_fe, ignore_index=True)
        resumen_fe.to_csv(out_fe_fijo / f"resumen_FEfijo_{period_years}y.csv", index=False)

    pdf_fe.close()

    # ============
    # 2) Volumen inicial fijo: variar FE
    # ============
    res_tablas_vol = []
    init_vals = ordenar_init_labels(df_periodo["init_label"].unique().tolist())
    for init_lab in init_vals:
        df_init = df_periodo[df_periodo["init_label"] == init_lab]
        if df_init.empty:
            continue
        g = df_init.groupby("FE", as_index=False)[[k for k,_ in KPIS]].mean().sort_values("FE")
        g["init_label"] = init_lab
        res_tablas_vol.append(g)

        # gráficos: un KPI por figura, X=FE, Y=KPI
        x = g["FE"]
        for col, lab in KPIS:
            fig = plt.figure(figsize=(10,5))
            plt.plot(x, g[col], marker="o")
            plt.title(f"{lab} — {init_lab} — Periodo {period_years} años")
            plt.xlabel("FEA = FEB")
            plt.ylabel(lab)
            plt.grid(True, linestyle="--", alpha=0.4)
            plt.tight_layout()
            pdf_vol.savefig(fig)
            plt.close(fig)

    if res_tablas_vol:
        resumen_vol = pd.concat(res_tablas_vol, ignore_index=True)
        resumen_vol.to_csv(out_vol_fijo / f"resumen_VOLfijo_{period_years}y.csv", index=False)

    pdf_vol.close()

def main():
    df = cargar_y_preparar()

    # carpeta raíz de salida
    out_root = Path("salidas_sensibilidad")
    asegurar_dir(out_root)

    # Procesar por período (5, 10, 15)
    for period in sorted(df["period_years"].unique()):
        dfp = df[df["period_years"] == period].copy()
        if dfp.empty:
            continue
        analizar_periodo(dfp, period, out_root)

    print("Listo. Revisa la carpeta 'salidas_sensibilidad/' para CSVs y PDFs.")

if __name__ == "__main__":
    main()
