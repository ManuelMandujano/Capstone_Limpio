# run_sensibilidad_csv.py
import pandas as pd

# === Usa tu clase ya definida ===
# from tu_modulo import EmbalseNuevaPunilla
from modelito2 import EmbalseNuevaPunilla  # ajusta el import a tu estructura

FULL_ANOS_30 = [
    '1989/1990','1990/1991','1991/1992','1992/1993','1993/1994',
    '1994/1995','1995/1996','1996/1997','1997/1998','1998/1999',
    '1999/2000','2000/2001','2001/2002','2002/2003','2003/2004',
    '2004/2005','2005/2006','2006/2007','2007/2008','2008/2009',
    '2009/2010','2010/2011','2011/2012','2012/2013','2013/2014',
    '2014/2015','2015/2016','2016/2017','2017/2018','2018/2019'
]

def split_blocks(seq, block_len: int):
    assert len(seq) % block_len == 0, "30 años debe ser múltiplo del bloque solicitado."
    return [seq[i:i+block_len] for i in range(0, len(seq), block_len)]

# Escenarios de volúmenes iniciales (VRFI, A, B)
ESCENARIOS_VOL = [
    (0.0,   0.0,   0.0),     # 0%
    (43.8,  65.0,  26.3),    # 25%
    (87.5,  130.0, 52.5),    # 50%
    (131.3, 195.0, 78.8),    # 75%
    (175.0, 260.0, 105.0),   # 100%
    # Si quieres 10% agrega: (17.5, 26.0, 10.5),
]

# Conjuntos de FEs a probar
FE_GRID = [0.50, 0.60, 0.70, 0.80, 0.90, 1.00]

def compute_interval_kpis(emb, anos_intervalo):
    """
    Calcula los KPIs por intervalo:
    - Qturb_total, Rebalse_total, Qdis_prom, Satisf_prom
    - Déficit del MODELO (sum d_A + d_B)
    - Déficit por FE adicional
    - Déficit total = modelo + FE
    - Stocks al fin del intervalo (VRFI, A, B, TOTAL)
    """
    assert set(anos_intervalo) == set(emb.anos), "El Embalse debe estar resuelto con este sub-rango."

    N_Y = len(anos_intervalo)
    TOT_PM = N_Y * 12

    Qturb_total = 0.0
    Rebalse_total = 0.0
    Qdis_total = 0.0

    Serv_total = 0.0
    Dem_eff_total = 0.0

    Def_modelo_total = 0.0
    Def_FE_total = 0.0

    for mes in emb.meses:
        key_civil = emb.hidrologico_a_civil[mes]
        # Demanda BASE (sin FE) — en Hm3/mes
        DemA_base = (emb.demanda_A_mensual[key_civil] * emb.num_acciones_A) / 1_000_000.0
        DemB_base = (emb.demanda_B_mensual[key_civil] * emb.num_acciones_B) / 1_000_000.0
        # Demanda efectiva para % satisfacción
        DemA_eff = DemA_base * emb.FEA
        DemB_eff = DemB_base * emb.FEB

        for ano in anos_intervalo:
            Qturb_total += emb.Q_turb[ano, mes].X
            Rebalse_total += emb.REBALSE_TOTAL[ano, mes].X
            Qdis_total += emb.Q_dis[ano, mes].X

            # Servicio entregado (propio + apoyo)
            ServA = emb.Q_A[ano, mes].X + emb.Q_A_apoyo[ano, mes].X
            ServB = emb.Q_B[ano, mes].X + emb.Q_B_apoyo[ano, mes].X
            Serv_total += (ServA + ServB)
            Dem_eff_total += (DemA_eff + DemB_eff)

            # Déficit del modelo
            dA = emb.d_A[ano, mes].X
            dB = emb.d_B[ano, mes].X
            Def_modelo_total += (dA + dB)

            # Déficit adicional por FE
            dA_FE = (1.0 - emb.FEA) * DemA_base
            dB_FE = (1.0 - emb.FEB) * DemB_base
            Def_FE_total += (dA_FE + dB_FE)

    Qdis_prom_mensual = Qdis_total / TOT_PM
    Satisf_prom = (100.0 * Serv_total / Dem_eff_total) if Dem_eff_total > 0 else 100.0

    # Stocks al fin del intervalo (fin del último mes = abr = 12)
    ultimo_ano = anos_intervalo[-1]
    VRFI_fin = emb.V_VRFI[ultimo_ano, 12].X
    A_fin    = emb.V_A[ultimo_ano, 12].X
    B_fin    = emb.V_B[ultimo_ano, 12].X
    TOTAL_fin = VRFI_fin + A_fin + B_fin

    return dict(
        Qturb_total_Hm3=Qturb_total,
        Rebalse_total_Hm3=Rebalse_total,
        Qdis_prom_Hm3_mes=Qdis_prom_mensual,
        Satisf_prom_pct=Satisf_prom,
        Def_modelo_Hm3=Def_modelo_total,
        Def_FE_Hm3=Def_FE_total,
        Def_total_Hm3=Def_modelo_total + Def_FE_total,
        VRFI_fin_Hm3=VRFI_fin,
        A_fin_Hm3=A_fin,
        B_fin_Hm3=B_fin,
        TOTAL_fin_Hm3=TOTAL_fin
    )

def run_suite_to_csv(period_years, fe_values, escenarios_vol, out_csv):
    """
    Corre toda la malla de sensibilidad para un tamaño de intervalo (5/10/15)
    y guarda un CSV con una fila por intervalo.
    """
    blocks = split_blocks(FULL_ANOS_30, period_years)
    rows = []

    for F in fe_values:
        FEA = F
        FEB = F
        for (v0, a0, b0) in escenarios_vol:
            for k, anos_k in enumerate(blocks, start=1):
                emb = EmbalseNuevaPunilla()
                emb.anos = anos_k[:]     # IMPORTANT: limitar el modelo al bloque
                emb.FEA = FEA
                emb.FEB = FEB
                emb.VRFI_init = v0
                emb.VA_init   = a0
                emb.VB_init   = b0

                sol = emb.solve()

                status_ok = sol is not None and sol.get('status') in (GRB.OPTIMAL, GRB.SUBOPTIMAL)  # 2, 9

                if not status_ok:
                    rows.append(dict(
                        period_years=period_years, iter=k,
                        interval_start=anos_k[0], interval_end=anos_k[-1],
                        FEA=FEA, FEB=FEB, VRFI0=v0, A0=a0, B0=b0,
                        Qturb_total_Hm3=None, Rebalse_total_Hm3=None, Qdis_prom_Hm3_mes=None,
                        Satisf_prom_pct=None, Def_modelo_Hm3=None, Def_FE_Hm3=None, Def_total_Hm3=None,
                        VRFI_fin_Hm3=None, A_fin_Hm3=None, B_fin_Hm3=None, TOTAL_fin_Hm3=None
                    ))
                    continue

                kpis = compute_interval_kpis(emb, anos_k)
                rows.append(dict(
                    period_years=period_years, iter=k,
                    interval_start=anos_k[0], interval_end=anos_k[-1],
                    FEA=FEA, FEB=FEB, VRFI0=v0, A0=a0, B0=b0,
                    **kpis
                ))

                # (Opcional) También puedes escribir el bloque de texto resumen:
                # resumen_txt = emb._texto_resumen_intervalo(
                #     f"Iteración {k} — FEA=FEB={F:.2f} — Inits (VRFI,A,B)=({v0},{a0},{b0})",
                #     anos_k
                # )
                # with open(f"resumen_{period_years}y_iter{k}_FE{F:.2f}_init{v0}-{a0}-{b0}.txt", "w", encoding="utf-8") as fh:
                #     fh.write(resumen_txt)

    df = pd.DataFrame(rows)
    # Orden lógico
    df = df.sort_values(
        ["period_years","FEA","FEB","VRFI0","A0","B0","iter","interval_start"],
        na_position="last"
    )
    df.to_csv(out_csv, index=False)
    print(f"[OK] CSV guardado: {out_csv} ({len(df)} filas)")
    return df

if __name__ == "__main__":
    from gurobipy import GRB
    # Tres CSV (uno por tanda 5y/10y/15y)
    run_suite_to_csv(5,  FE_GRID, ESCENARIOS_VOL, "resultados_5y.csv")
    run_suite_to_csv(10, FE_GRID, ESCENARIOS_VOL, "resultados_10y.csv")
    run_suite_to_csv(15, FE_GRID, ESCENARIOS_VOL, "resultados_15y.csv")
