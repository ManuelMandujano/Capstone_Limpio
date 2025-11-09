# kpi_vs_inicial_con_FE.py
# -*- coding: utf-8 -*-
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# ====== Entradas ======
INPUT_FILES = ["resultados_5y.csv", "resultados_10y.csv", "resultados_15y.csv"]

# KPIs a graficar: (columna_csv, etiqueta)
KPIS = [
    ("Def_total_Hm3", "Déficit total [Hm³]"),
    ("Rebalse_total_Hm3", "Rebalse total [Hm³]"),
    ("Satisf_prom_pct", "Satisfacción promedio [%]"),
    ("TOTAL_fin_Hm3", "Agua almacenada final [Hm³]"),
    ("Qturb_total_Hm3", "Volumen turbinado [Hm³]"),
    ("Qdis_prom_Hm3_mes", "Caudal disponible prom. [Hm³/mes]"),
]

# Escenarios de volúmenes iniciales esperados (VRFI,A,B) -> etiqueta
ESCENARIOS_VOL = [
    ((0.0,   0.0,   0.0),   "Init 0%"),
    ((43.8,  65.0,  26.3),  "Init 25%"),
    ((87.5,  130.0, 52.5),  "Init 50%"),
    ((131.3, 195.0, 78.8),  "Init 75%"),
    ((175.0, 260.0, 105.0), "Init 100%"),
]
TOL = 1e-3

def etiqueta_init(vrfi, a, b):
    for (vr, va, vb), lab in ESCENARIOS_VOL:
        if abs(vrfi - vr) < TOL and abs(a - va) < TOL and abs(b - vb) < TOL:
            return lab
    return f"Init ({vrfi:.1f},{a:.1f},{b:.1f})"

def ordenar_init_labels(labels):
    orden = {lab: i for i, (_, lab) in enumerate(ESCENARIOS_VOL)}
    return sorted(labels, key=lambda x: orden.get(x, 999))

def cargar():
    frames = []
    for f in INPUT_FILES:
        p = Path(f)
        if not p.exists():
            print(f"[WARN] No encontré {f}, lo salto.")
            continue
        df = pd.read_csv(p)
        # periodo si no viniera
        if "period_years" not in df.columns:
            if "5y" in p.stem:  df["period_years"] = 5
            if "10y" in p.stem: df["period_years"] = 10
            if "15y" in p.stem: df["period_years"] = 15
        # FE efectivo
        df["FE"] = pd.to_numeric(df.get("FEA", df.get("FEB")), errors="coerce")
        # etiqueta init
        df["init_label"] = df.apply(lambda r: etiqueta_init(r["VRFI0"], r["A0"], r["B0"]), axis=1)
        # asegurar numéricos
        for col, _ in KPIS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        frames.append(df)
    if not frames:
        raise RuntimeError("No se cargó ningún CSV.")
    return pd.concat(frames, ignore_index=True)

def plot_periodo(df_periodo: pd.DataFrame, period: int, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    pdf = PdfPages(outdir / f"plots_kpi_vs_init_con_FE_{period}y.pdf")

    # FE únicos (ordenados)
    fes = sorted(df_periodo["FE"].dropna().unique())

    for col, label in KPIS:
        # Promediar por (FE, init_label) sobre las iteraciones
        g = (df_periodo
             .groupby(["FE", "init_label"], as_index=False)[col]
             .mean())

        # Orden de init en X
        init_order = ordenar_init_labels(g["init_label"].unique().tolist())

        # Pivot para guardar CSV de referencia
        piv = g.pivot_table(index="init_label", columns="FE", values=col)
        piv = piv.reindex(index=init_order)
        piv.to_csv(outdir / f"pivot_{col}_{period}y.csv")

        # === Figura ===
        fig = plt.figure(figsize=(10,6))
        for fe in fes:
            data_fe = g[g["FE"].round(3) == round(fe,3)].set_index("init_label").reindex(init_order)
            plt.plot(init_order, data_fe[col].values, marker="o", label=f"FE={fe:.2f}")
        plt.title(f"{label} — X: volúmenes iniciales — {period} años")
        plt.xlabel("Volumen inicial (escenario)")
        plt.ylabel(label)
        plt.xticks(rotation=20)
        plt.grid(True, linestyle="--", alpha=0.35)
        plt.legend(title="FE")
        plt.tight_layout()
        # guardar PNG y al PDF
        png_path = outdir / f"{col}_{period}y.png"
        plt.savefig(png_path, dpi=160)
        pdf.savefig(fig)
        plt.close(fig)

    pdf.close()

def main():
    df = cargar()
    root = Path("salidas_kpi_vs_init_con_FE")
    for period in sorted(df["period_years"].unique()):
        plot_periodo(df[df["period_years"] == period].copy(), period, root / f"{period}y")
    print("Listo. Revisa la carpeta 'salidas_kpi_vs_init_con_FE/' (PDF + PNG + pivots por KPI).")

if __name__ == "__main__":
    main()
