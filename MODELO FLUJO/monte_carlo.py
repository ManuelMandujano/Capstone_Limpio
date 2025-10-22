# monte_carlo.py
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from datetime import datetime

# Este codigo basicamente utiliza el mismo modelo que modelito2.py, pero adaptado para correr simulaciones de Monte Carlo
# en donde la idea es correr N simulaciones, cada una con un escenario aleatorio de años seleccionados sin reemplazo para
# simular diferentes condiciones hidrológicas y asi ver incertidumbre en resultados.

class MonteCarloEmbalse:
    
    def __init__(self, num_simulaciones=100, duracion_anos=30):
        self.num_simulaciones = num_simulaciones
        self.duracion_anos = duracion_anos
        
        self.anos_disponibles = [
            '1989/1990', '1990/1991', '1991/1992', '1992/1993', '1993/1994',
            '1994/1995', '1995/1996', '1996/1997', '1997/1998', '1998/1999',
            '1999/2000', '2000/2001', '2001/2002', '2002/2003', '2003/2004',
            '2004/2005', '2005/2006', '2006/2007', '2007/2008', '2008/2009',
            '2009/2010', '2010/2011', '2011/2012', '2012/2013', '2013/2014',
            '2014/2015', '2015/2016', '2016/2017', '2017/2018', '2018/2019'
        ]
        
        self.resultados_simulaciones = []
        self._cargar_datos_base()
        
    def _cargar_datos_base(self):
        data_file = "data/caudales.xlsx"
        xls = pd.ExcelFile(data_file)
        
        nuble = pd.read_excel(xls, sheet_name='Hoja1', skiprows=4, nrows=31)
        hoya1 = pd.read_excel(xls, sheet_name='Hoja1', skiprows=39, nrows=31)
        hoya2 = pd.read_excel(xls, sheet_name='Hoja1', skiprows=75, nrows=31)
        hoya3 = pd.read_excel(xls, sheet_name='Hoja1', skiprows=110, nrows=31)
        
        excel_columnas = ['MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC','ENE','FEB','MAR','ABR']
        orden_meses_modelo = [1,2,3,4,5,6,7,8,9,10,11,12]
        
        self.Q_nuble_base = {}
        self.Q_hoya1_base = {}
        self.Q_hoya2_base = {}
        self.Q_hoya3_base = {}
        self.Q_afl_base = {}

        for idx, fila in nuble.iterrows():
            ano_str = str(fila.get('AÑO',''))
            if (pd.notna(fila.get('AÑO')) and '/' in ano_str
                and not any(w in ano_str.upper() for w in ['PROMEDIO','TOTAL','MAX','MIN'])):
                try:
                    ano = int(ano_str.split('/')[0])
                    for col, mm in zip(excel_columnas, orden_meses_modelo):
                        n1 = nuble.loc[idx, col]
                        h1 = hoya1.loc[idx, col]
                        h2 = hoya2.loc[idx, col]
                        h3 = hoya3.loc[idx, col]
                        if pd.notna(n1):
                            self.Q_nuble_base[ano, mm] = float(n1)
                            self.Q_afl_base[ano, mm] = float(n1)
                        if pd.notna(h1): self.Q_hoya1_base[ano, mm] = float(h1)
                        if pd.notna(h2): self.Q_hoya2_base[ano, mm] = float(h2)
                        if pd.notna(h3): self.Q_hoya3_base[ano, mm] = float(h3)
                except Exception:
                    pass
    

    def generar_escenario(self):
        anos_disponibles = self.anos_disponibles.copy()
        escenario = []
        for _ in range(min(self.duracion_anos, len(anos_disponibles))):
            ano_seleccionado = np.random.choice(anos_disponibles)
            escenario.append(ano_seleccionado)
            anos_disponibles.remove(ano_seleccionado)
        return escenario
    

    def ejecutar_simulacion(self, num_sim, anos_escenario):
        print(f"\n{'='*60}")
        print(f"Ejecutando Simulacion #{num_sim + 1}/{self.num_simulaciones}")
        print(f"Primeros 5 años: {anos_escenario[:5]}")
        print(f"{'='*60}")
        try:
            resultado = self._resolver_modelo_montecarlo(anos_escenario)
            if resultado is not None:
                resultado['num_simulacion'] = num_sim + 1
                resultado['escenario_anos'] = ','.join(anos_escenario)
                print(f"Simulacion #{num_sim + 1} completada - Deficit: {resultado['deficit_total']:.2f} Hm³")
                return resultado
            else:
                print(f"Simulación #{num_sim + 1} fallo")
                return None
                
        except Exception as e:
            print(f"Error en simulacion #{num_sim + 1}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _resolver_modelo_montecarlo(self, anos_escenario):
        model = gp.Model("MC_Embalse")
        model.setParam('OutputFlag', 1)
        
        # Parametros
        C_VRFI = 175
        C_TIPO_A = 260
        C_TIPO_B = 105
        V_C_H = 3.9
        RESERVA_MIN_VRFI = 1.5  
        
        segundos_por_mes = {
            1: 31*24*3600, 2: 30*24*3600, 3: 31*24*3600, 4: 31*24*3600,
            5: 30*24*3600, 6: 31*24*3600, 7: 30*24*3600, 8: 31*24*3600,
            9: 31*24*3600, 10: 28*24*3600, 11: 31*24*3600, 12: 30*24*3600
        }
        
        num_A = 21221
        num_B = 7100
        DA_a_m = {1:9503,2:6516,3:3452,4:776,5:0,6:0,7:0,8:0,9:0,10:2444,11:6516,12:9580}
        DB_a_b = {1:3361,2:2305,3:1221,4:274,5:0,6:0,7:0,8:0,9:0,10:864,11:2305,12:3388}
        m_civil = {1:5,2:6,3:7,4:8,5:9,6:10,7:11,8:12,9:1,10:2,11:3,12:4}
        
        derechos = [52.00,52.00,52.00,52.00,57.70,76.22,69.22,52.00,52.00,52.00,52.00,52.00]
        qeco = [10.00,10.35,14.48,15.23,15.23,15.23,15.23,15.23,12.80,15.20,16.40,17.60]
        
        meses = list(range(1, 13))
        
        # Variables
        V_VRFI = model.addVars(anos_escenario, meses, name="V_VRFI", lb=0, ub=C_VRFI)
        V_A = model.addVars(anos_escenario, meses, name="V_A", lb=0, ub=C_TIPO_A)
        V_B = model.addVars(anos_escenario, meses, name="V_B", lb=0, ub=C_TIPO_B)
        
        IN_VRFI = model.addVars(anos_escenario, meses, name="IN_VRFI", lb=0)
        IN_A = model.addVars(anos_escenario, meses, name="IN_A", lb=0)
        IN_B = model.addVars(anos_escenario, meses, name="IN_B", lb=0)
        REBALSE_TOTAL = model.addVars(anos_escenario, meses, name="REBALSE_TOTAL", lb=0)
        
        Q_CONSUMO_HUMANO = model.addVars(anos_escenario, meses, name="Q_CONSUMO_HUMANO", lb=0)
        Q_A = model.addVars(anos_escenario, meses, name="Q_A", lb=0)
        Q_B = model.addVars(anos_escenario, meses, name="Q_B", lb=0)
        Q_A_apoyo = model.addVars(anos_escenario, meses, name="Q_A_apoyo", lb=0)
        Q_B_apoyo = model.addVars(anos_escenario, meses, name="Q_B_apoyo", lb=0)
        
        d_A = model.addVars(anos_escenario, meses, name="d_A", lb=0)
        d_B = model.addVars(anos_escenario, meses, name="d_B", lb=0)
        Q_turb = model.addVars(anos_escenario, meses, name="Q_turb", lb=0)
        
        # Variables auxiliares
        Rem = model.addVars(anos_escenario, meses, name="Rem", lb=0)
        ESPACIO_VRFI = model.addVars(anos_escenario, meses, name="ESPACIO_VRFI", lb=0)
        ESPACIO_A = model.addVars(anos_escenario, meses, name="ESPACIO_A", lb=0)
        ESPACIO_B = model.addVars(anos_escenario, meses, name="ESPACIO_B", lb=0)
        LLENADO_VRFI = model.addVars(anos_escenario, meses, name="LLENADO_VRFI", lb=0)
        REMANENTE_POST_VRFI = model.addVars(anos_escenario, meses, name="REMANENTE_POST_VRFI", lb=0)
        CUOTA_A = model.addVars(anos_escenario, meses, name="CUOTA_A", lb=0)
        CUOTA_B = model.addVars(anos_escenario, meses, name="CUOTA_B", lb=0)
        
        FALTANTE_A = model.addVars(anos_escenario, meses, name="FALTANTE_A", lb=0)
        FALTANTE_B = model.addVars(anos_escenario, meses, name="FALTANTE_B", lb=0)
        
        DISPONIBLE_A = model.addVars(anos_escenario, meses, name="DISPONIBLE_A")
        DEMANDA_A_50 = model.addVars(anos_escenario, meses, name="DEMANDA_A_50", lb=0)
        REQ_A_PROPIO = model.addVars(anos_escenario, meses, name="REQ_A_PROPIO", lb=0)
        
        DISPONIBLE_B = model.addVars(anos_escenario, meses, name="DISPONIBLE_B")
        DEMANDA_B_50 = model.addVars(anos_escenario, meses, name="DEMANDA_B_50", lb=0)
        REQ_B_PROPIO = model.addVars(anos_escenario, meses, name="REQ_B_PROPIO", lb=0)
        
        tA = model.addVars(anos_escenario, meses, name="tA")
        tB = model.addVars(anos_escenario, meses, name="tB")
        CERO_CONSTANTE = model.addVar(lb=0, ub=0, name="CERO_CONSTANTE")
        
        VRFI_avail = model.addVars(anos_escenario, meses, name="VRFI_avail")
        FALTANTE_TOTAL = model.addVars(anos_escenario, meses, name="FALTANTE_TOTAL", lb=0)
        APOYO_TOTAL = model.addVars(anos_escenario, meses, name="APOYO_TOTAL", lb=0)
        
        # Variables para el SSR con backlog
        SSR_ACUMULADO = model.addVars(anos_escenario, meses, name="SSR_ACUMULADO", lb=0)
        SSR_EXIGIDO = model.addVars(anos_escenario, meses, name="SSR_EXIGIDO", lb=0)
        SSR_CAPACIDAD_VARIABLE = model.addVars(anos_escenario, meses, name="SSR_CAPACIDAD_VARIABLE", lb=0)
        VRFI_DISPONIBLE_LIBRE = model.addVars(anos_escenario, meses, name="VRFI_DISPONIBLE_LIBRE", lb=0)
        
        # Variables para el reparto 71/29 
        PROPORCION_A = model.addVars(anos_escenario, meses, name="PROPORCION_A")
        PROPORCION_B = model.addVars(anos_escenario, meses, name="PROPORCION_B")
        ASIGNACION_A_BASE = model.addVars(anos_escenario, meses, name="ASIGNACION_A_BASE", lb=0)
        ASIGNACION_B_BASE = model.addVars(anos_escenario, meses, name="ASIGNACION_B_BASE", lb=0)
        EXCEDENTE_A = model.addVars(anos_escenario, meses, name="EXCEDENTE_A", lb=0)
        EXCEDENTE_B = model.addVars(anos_escenario, meses, name="EXCEDENTE_B", lb=0)
        BRECHA_A = model.addVars(anos_escenario, meses, name="BRECHA_A", lb=0)
        BRECHA_B = model.addVars(anos_escenario, meses, name="BRECHA_B", lb=0)
        EXTRA_HACIA_A = model.addVars(anos_escenario, meses, name="EXTRA_HACIA_A", lb=0)
        EXTRA_HACIA_B = model.addVars(anos_escenario, meses, name="EXTRA_HACIA_B", lb=0)

        # QPD efectivo
        QPD_eff = {}
        for año in anos_escenario:
            y = int(año.split('/')[0])
            for mes in meses:
                H = (self.Q_hoya1_base.get((y,mes),0) + 
                     self.Q_hoya2_base.get((y,mes),0) + 
                     self.Q_hoya3_base.get((y,mes),0))
                qpd_nom = max(derechos[mes-1], qeco[mes-1], max(0, 95.7 - H))
                QPD_eff[año, mes] = min(qpd_nom, self.Q_nuble_base.get((y,mes),0))
        
        ssr_mes = V_C_H / 12.0

        # Restricciones
        primer_ano = anos_escenario[0]
        model.addConstr(V_VRFI[primer_ano, 1] == 0, name="init_VRFI")
        model.addConstr(V_A[primer_ano, 1] == 0, name="init_VA")
        model.addConstr(V_B[primer_ano, 1] == 0, name="init_VB")
        
        for idx_ano, año in enumerate(anos_escenario):
            y = int(año.split('/')[0])
            
            for i, mes in enumerate(meses):
                seg = segundos_por_mes[mes]
                Qin_s = self.Q_afl_base.get((y,mes), 0)
                Qin = Qin_s * seg / 1_000_000.0
                UPREF = QPD_eff[año, mes] * seg / 1_000_000.0
                
                key = m_civil[mes]
                demA = (DA_a_m[key] * num_A) / 1_000_000.0
                demB = (DB_a_b[key] * num_B) / 1_000_000.0
                
                # Stocks previos menos los consecutivos entre años
                if i == 0:  
                    if idx_ano == 0:  
                        V_R_prev = 0
                        V_A_prev = 0
                        V_B_prev = 0
                    else:  
                        año_anterior = anos_escenario[idx_ano - 1]
                        V_R_prev = V_VRFI[año_anterior, 12]
                        V_A_prev = V_A[año_anterior, 12]
                        V_B_prev = V_B[año_anterior, 12]
                else:  
                    V_R_prev = V_VRFI[año, mes-1]
                    V_A_prev = V_A[año, mes-1]
                    V_B_prev = V_B[año, mes-1]
                
                if i == 0:
                    if idx_ano == 0:
                        backlog_prev = 0
                    else:
                        año_anterior = anos_escenario[idx_ano - 1]
                        backlog_prev = SSR_ACUMULADO[año_anterior, 12]
                else: 
                    backlog_prev = SSR_ACUMULADO[año, mes-1]

                # Deuda ssr del mes
                model.addConstr(SSR_EXIGIDO[año, mes] == ssr_mes + backlog_prev)
                model.addConstr(SSR_CAPACIDAD_VARIABLE[año, mes] == V_R_prev + IN_VRFI[año, mes])

                # Prioridad ssr
                model.addGenConstrMin(
                    Q_CONSUMO_HUMANO[año, mes],
                    [SSR_EXIGIDO[año, mes], SSR_CAPACIDAD_VARIABLE[año, mes]]
                )

                # Actualizar con ssr
                model.addConstr(SSR_ACUMULADO[año, mes] == SSR_EXIGIDO[año, mes] - Q_CONSUMO_HUMANO[año, mes])
                
                # Remanente y llenado
                model.addConstr(Rem[año,mes] == Qin - UPREF)
                model.addConstr(ESPACIO_VRFI[año,mes] == C_VRFI - V_R_prev)
                model.addConstr(ESPACIO_A[año,mes] == C_TIPO_A - V_A_prev)
                model.addConstr(ESPACIO_B[año,mes] == C_TIPO_B - V_B_prev)
                
                model.addGenConstrMin(LLENADO_VRFI[año,mes], [Rem[año,mes], ESPACIO_VRFI[año,mes]])
                model.addConstr(REMANENTE_POST_VRFI[año,mes] == Rem[año,mes] - LLENADO_VRFI[año,mes])
                model.addConstr(CUOTA_A[año,mes] == 0.71 * REMANENTE_POST_VRFI[año,mes])
                model.addConstr(CUOTA_B[año,mes] == 0.29 * REMANENTE_POST_VRFI[año,mes])
                model.addGenConstrMin(IN_A[año,mes], [CUOTA_A[año,mes], ESPACIO_A[año,mes]])
                model.addGenConstrMin(IN_B[año,mes], [CUOTA_B[año,mes], ESPACIO_B[año,mes]])
                
                model.addConstr(IN_VRFI[año,mes] == LLENADO_VRFI[año,mes])
                model.addConstr(REBALSE_TOTAL[año,mes] == Rem[año,mes] - IN_VRFI[año,mes] - IN_A[año,mes] - IN_B[año,mes])
                
                # Disponibilidad VRFI despues del ssr
                temp_free = model.addVar(lb=-GRB.INFINITY, name=f"temp_free_{año}_{mes}")
                model.addConstr(temp_free == V_R_prev + IN_VRFI[año, mes] - Q_CONSUMO_HUMANO[año, mes] - RESERVA_MIN_VRFI)
                model.addGenConstrMax(VRFI_DISPONIBLE_LIBRE[año, mes], [temp_free, CERO_CONSTANTE])
                
                # Balances
                model.addConstr(V_VRFI[año,mes] == V_R_prev + IN_VRFI[año,mes] - Q_CONSUMO_HUMANO[año,mes] - Q_A_apoyo[año,mes] - Q_B_apoyo[año,mes])
                model.addConstr(V_A[año,mes] == V_A_prev + IN_A[año,mes] - Q_A[año,mes])
                model.addConstr(V_B[año,mes] == V_B_prev + IN_B[año,mes] - Q_B[año,mes])
                
                # Disponibilidades
                model.addConstr(Q_A[año,mes] <= V_A_prev + IN_A[año,mes])
                model.addConstr(Q_B[año,mes] <= V_B_prev + IN_B[año,mes])
                
                # Propio primero
                model.addConstr(DISPONIBLE_A[año,mes] == V_A_prev + IN_A[año,mes])
                model.addConstr(DEMANDA_A_50[año,mes] == 0.5*demA)
                model.addGenConstrMin(REQ_A_PROPIO[año,mes], [DISPONIBLE_A[año,mes], DEMANDA_A_50[año,mes]])
                model.addConstr(Q_A[año,mes] >= REQ_A_PROPIO[año,mes])
                
                model.addConstr(DISPONIBLE_B[año,mes] == V_B_prev + IN_B[año,mes])
                model.addConstr(DEMANDA_B_50[año,mes] == 0.5*demB)
                model.addGenConstrMin(REQ_B_PROPIO[año,mes], [DISPONIBLE_B[año,mes], DEMANDA_B_50[año,mes]])
                model.addConstr(Q_B[año,mes] >= REQ_B_PROPIO[año,mes])
                
                # Apoyo VRFI
                model.addConstr(tA[año,mes] == 0.5*demA - Q_A[año,mes])
                model.addConstr(tB[año,mes] == 0.5*demB - Q_B[año,mes])
                model.addGenConstrMax(FALTANTE_A[año,mes], [tA[año,mes], CERO_CONSTANTE])
                model.addGenConstrMax(FALTANTE_B[año,mes], [tB[año,mes], CERO_CONSTANTE])

                # Reparto 71/29 capacidad
                model.addConstr(FALTANTE_TOTAL[año,mes] == FALTANTE_A[año,mes] + FALTANTE_B[año,mes])
                model.addGenConstrMin(APOYO_TOTAL[año,mes], [VRFI_DISPONIBLE_LIBRE[año, mes], FALTANTE_TOTAL[año,mes]])

                # Reparto proporcional base 71/29
                model.addConstr(PROPORCION_A[año, mes] == 0.71 * APOYO_TOTAL[año, mes])
                model.addConstr(PROPORCION_B[año, mes] == 0.29 * APOYO_TOTAL[año, mes])

                # Asignacion base sin exceder la necesidad
                model.addGenConstrMin(ASIGNACION_A_BASE[año, mes], [PROPORCION_A[año, mes], FALTANTE_A[año, mes]])
                model.addGenConstrMin(ASIGNACION_B_BASE[año, mes], [PROPORCION_B[año, mes], FALTANTE_B[año, mes]])

                # Calcular excedentes y brechas
                model.addConstr(EXCEDENTE_A[año, mes] == PROPORCION_A[año, mes] - ASIGNACION_A_BASE[año, mes])
                model.addConstr(EXCEDENTE_B[año, mes] == PROPORCION_B[año, mes] - ASIGNACION_B_BASE[año, mes])
                model.addConstr(BRECHA_A[año, mes] == FALTANTE_A[año, mes] - ASIGNACION_A_BASE[año, mes])
                model.addConstr(BRECHA_B[año, mes] == FALTANTE_B[año, mes] - ASIGNACION_B_BASE[año, mes])

                # Reasignar excedentes
                model.addGenConstrMin(EXTRA_HACIA_B[año, mes], [EXCEDENTE_A[año, mes], BRECHA_B[año, mes]])
                model.addGenConstrMin(EXTRA_HACIA_A[año, mes], [EXCEDENTE_B[año, mes], BRECHA_A[año, mes]])

                # Asignacion final con reasignación
                model.addConstr(Q_A_apoyo[año, mes] == ASIGNACION_A_BASE[año, mes] + EXTRA_HACIA_A[año, mes])
                model.addConstr(Q_B_apoyo[año, mes] == ASIGNACION_B_BASE[año, mes] + EXTRA_HACIA_B[año, mes])

                # Deficits
                model.addConstr(d_A[año,mes] == demA - (Q_A[año,mes] + Q_A_apoyo[año,mes]))
                model.addConstr(d_B[año,mes] == demB - (Q_B[año,mes] + Q_B_apoyo[año,mes]))
                
                model.addConstr(Q_A[año,mes] + Q_A_apoyo[año,mes] <= demA + 1e-9)
                model.addConstr(Q_B[año,mes] + Q_B_apoyo[año,mes] <= demB + 1e-9)
                
                # Turbinado
                model.addConstr(Q_turb[año,mes] == Q_A[año,mes] + Q_A_apoyo[año,mes] + Q_B[año,mes] + Q_B_apoyo[año,mes] + REBALSE_TOTAL[año,mes])
            
        # Objetivo
        total_def = gp.quicksum(d_A[año,mes] + d_B[año,mes] for año in anos_escenario for mes in meses)
        pen_vrfi = gp.quicksum(Q_A_apoyo[año,mes] + Q_B_apoyo[año,mes] for año in anos_escenario for mes in meses)
        inc_prop = gp.quicksum(Q_A[año,mes] + Q_B[año,mes] for año in anos_escenario for mes in meses)
        
        model.setObjective(total_def + 1e-3*pen_vrfi - 1e-3*inc_prop, GRB.MINIMIZE)
        

        model.optimize()
        
        if model.status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
            return None
        
        tiempo_ejecucion = model.Runtime
        gap = model.MIPGap if hasattr(model, 'MIPGap') else 0.0
        
        # Metricas
        deficit_total = model.objVal
        deficit_A = sum(d_A[año, mes].X for año in anos_escenario for mes in meses)
        deficit_B = sum(d_B[año, mes].X for año in anos_escenario for mes in meses)
        vol_turbinado = sum(Q_turb[año, mes].X for año in anos_escenario for mes in meses)
        apoyo_vrfi_A = sum(Q_A_apoyo[año, mes].X for año in anos_escenario for mes in meses)
        apoyo_vrfi_B = sum(Q_B_apoyo[año, mes].X for año in anos_escenario for mes in meses)
        rebalse_total = sum(REBALSE_TOTAL[año, mes].X for año in anos_escenario for mes in meses)
        
        caudal_disponible_total = 0
        
        demanda_total_A = 0
        demanda_total_B = 0
        servicio_total_A = 0
        servicio_total_B = 0
        
        for año in anos_escenario:
            y = int(año.split('/')[0])
            for mes in meses:
                seg = segundos_por_mes[mes]
                Qin_s = self.Q_afl_base.get((y,mes), 0)
                Qin = Qin_s * seg / 1_000_000.0
                UPREF = QPD_eff[año, mes] * seg / 1_000_000.0
                caudal_disponible_total += (Qin - UPREF)
                
                key = m_civil[mes]
                demA = (DA_a_m[key] * num_A) / 1_000_000.0
                demB = (DB_a_b[key] * num_B) / 1_000_000.0
                
                demanda_total_A += demA
                demanda_total_B += demB
                
                servA = Q_A[año, mes].X + Q_A_apoyo[año, mes].X
                servB = Q_B[año, mes].X + Q_B_apoyo[año, mes].X
                
                servicio_total_A += servA
                servicio_total_B += servB
        
        satisfaccion_A = (servicio_total_A / demanda_total_A * 100) if demanda_total_A > 0 else 100
        satisfaccion_B = (servicio_total_B / demanda_total_B * 100) if demanda_total_B > 0 else 100
        satisfaccion_total = ((servicio_total_A + servicio_total_B) / 
                             (demanda_total_A + demanda_total_B) * 100) \
                             if (demanda_total_A + demanda_total_B) > 0 else 100
        
        ultimo_ano = anos_escenario[-1]
        vol_final_VRFI = V_VRFI[ultimo_ano, 12].X
        vol_final_A = V_A[ultimo_ano, 12].X
        vol_final_B = V_B[ultimo_ano, 12].X
        vol_final_total = vol_final_VRFI + vol_final_A + vol_final_B
        
        return {
            'deficit_total': deficit_total,
            'deficit_tipo_A': deficit_A,
            'deficit_tipo_B': deficit_B,
            'volumen_turbinado_total': vol_turbinado,
            'apoyo_vrfi_a': apoyo_vrfi_A,
            'apoyo_vrfi_b': apoyo_vrfi_B,
            'rebalse_total': rebalse_total,
            'gap': gap,
            'tiempo_ejecucion_seg': tiempo_ejecucion,
            'vol_final_VRFI': vol_final_VRFI,
            'vol_final_A': vol_final_A,
            'vol_final_B': vol_final_B,
            'vol_final_total': vol_final_total,
            'caudal_disponible_total': caudal_disponible_total,
            'demanda_total_A': demanda_total_A,
            'demanda_total_B': demanda_total_B,
            'servicio_total_A': servicio_total_A,
            'servicio_total_B': servicio_total_B,
            'satisfaccion_A_%': satisfaccion_A,
            'satisfaccion_B_%': satisfaccion_B,
            'satisfaccion_total_%': satisfaccion_total
        }
    
    def ejecutar_monte_carlo(self):
        print(f"\n{'#'*60}")
        print(f"INICIANDO SIMULACIÓN DE MONTE CARLO")
        print(f"Numero de simulaciones: {self.num_simulaciones}")
        print(f"Duración por simulacion: {self.duracion_anos} años")
        print(f"{'#'*60}\n")
        
        for i in range(self.num_simulaciones):
            escenario = self.generar_escenario()
            resultado = self.ejecutar_simulacion(i, escenario)
            
            if resultado is not None:
                self.resultados_simulaciones.append(resultado)
        
        print(f"\n{'#'*60}")
        print(f"MONTE CARLO COMPLETADO")
        print(f"Simulaciones exitosas: {len(self.resultados_simulaciones)}/{self.num_simulaciones}")
        print(f"{'#'*60}\n")
    
    def exportar_resultados(self, archivo_salida=None):
        if not self.resultados_simulaciones:
            print(" No hay resultados para exportar")
            return
        
        if archivo_salida is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_salida = f"monte_carlo_resultados_{timestamp}.xlsx"
        
        df_resultados = pd.DataFrame(self.resultados_simulaciones)
        
        columnas_numericas = df_resultados.select_dtypes(include=[np.number]).columns
        df_estadisticas = df_resultados[columnas_numericas].describe()
        
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        df_percentiles = df_resultados[columnas_numericas].quantile([p/100 for p in percentiles])
        df_percentiles.index = [f'percentil_{p}' for p in percentiles]
        
        idx_mejor = df_resultados['deficit_total'].idxmin()
        idx_peor = df_resultados['deficit_total'].idxmax()
        
        df_mejor_escenario = df_resultados.loc[[idx_mejor]].copy()
        df_mejor_escenario.insert(0, 'tipo', 'MEJOR ESCENARIO')
        
        df_peor_escenario = df_resultados.loc[[idx_peor]].copy()
        df_peor_escenario.insert(0, 'tipo', 'PEOR ESCENARIO')
        
        with pd.ExcelWriter(archivo_salida, engine='openpyxl') as writer:
            df_resultados.to_excel(writer, sheet_name='Resultados_Completos', index=False)
            df_estadisticas.to_excel(writer, sheet_name='Estadisticas')
            df_percentiles.to_excel(writer, sheet_name='Percentiles')
            
            df_escenarios = pd.concat([df_mejor_escenario, df_peor_escenario], ignore_index=True)
            df_escenarios.to_excel(writer, sheet_name='Escenarios_Extremos', index=False)
            
            resumen = {
                'Métrica': [
                    'Número de Simulaciones',
                    'Duración (años)',
                    'Caudal Disponible Promedio (Hm³)',
                    'Caudal Disponible Mínimo (Hm³)',
                    'Caudal Disponible Máximo (Hm³)',
                    'Déficit Total Promedio (Hm³)',
                    'Déficit Total Mínimo (Hm³)',
                    'Déficit Total Máximo (Hm³)',
                    'Desviación Estándar Déficit (Hm³)',
                    'Satisfacción Promedio Total (%)',
                    'Satisfacción Promedio A (%)',
                    'Satisfacción Promedio B (%)',
                    'Satisfacción Mínima Total (%)',
                    'Satisfacción Máxima Total (%)',
                    'Volumen Turbinado Promedio (Hm³)',
                    'Rebalse Promedio (Hm³)',
                    'Tiempo Ejecución Promedio (seg)',
                    'Tiempo Ejecución Total (seg)',
                    'Gap Promedio (%)',
                    'Vol Final Total Promedio (Hm³)',
                    'Vol Final VRFI Promedio (Hm³)',
                    'Vol Final A Promedio (Hm³)',
                    'Vol Final B Promedio (Hm³)'
                ],
                'Valor': [
                    len(self.resultados_simulaciones),
                    self.duracion_anos,
                    df_resultados['caudal_disponible_total'].mean(),
                    df_resultados['caudal_disponible_total'].min(),
                    df_resultados['caudal_disponible_total'].max(),
                    df_resultados['deficit_total'].mean(),
                    df_resultados['deficit_total'].min(),
                    df_resultados['deficit_total'].max(),
                    df_resultados['deficit_total'].std(),
                    df_resultados['satisfaccion_total_%'].mean(),
                    df_resultados['satisfaccion_A_%'].mean(),
                    df_resultados['satisfaccion_B_%'].mean(),
                    df_resultados['satisfaccion_total_%'].min(),
                    df_resultados['satisfaccion_total_%'].max(),
                    df_resultados['volumen_turbinado_total'].mean(),
                    df_resultados['rebalse_total'].mean(),
                    df_resultados['tiempo_ejecucion_seg'].mean(),
                    df_resultados['tiempo_ejecucion_seg'].sum(),
                    df_resultados['gap'].mean() * 100,
                    df_resultados['vol_final_total'].mean(),
                    df_resultados['vol_final_VRFI'].mean(),
                    df_resultados['vol_final_A'].mean(),
                    df_resultados['vol_final_B'].mean()
                ]
            }
            df_resumen = pd.DataFrame(resumen)
            df_resumen.to_excel(writer, sheet_name='Resumen_Ejecutivo', index=False)
        
        print(f" Resultados exportados a: {archivo_salida}")
        print(f"\n RESUMEN:")
        print(f"    Caudal disponible promedio: {df_resultados['caudal_disponible_total'].mean():.2f} Hm³")
        print(f"    Déficit promedio: {df_resultados['deficit_total'].mean():.2f} Hm³")
        print(f"    Déficit mínimo: {df_resultados['deficit_total'].min():.2f} Hm³")
        print(f"    Déficit máximo: {df_resultados['deficit_total'].max():.2f} Hm³")
        print(f"    Satisfacción promedio: {df_resultados['satisfaccion_total_%'].mean():.2f}%")
        print(f"    Satisfacción mínima: {df_resultados['satisfaccion_total_%'].min():.2f}%")
        print(f"    Satisfacción máxima: {df_resultados['satisfaccion_total_%'].max():.2f}%")
        print(f"    Tiempo total ejecución: {df_resultados['tiempo_ejecucion_seg'].sum():.1f} seg")
        print(f"    Tiempo promedio por simulación: {df_resultados['tiempo_ejecucion_seg'].mean():.2f} seg")
        print(f"    Gap promedio: {df_resultados['gap'].mean()*100:.4f}%")
        print(f"    Vol final total promedio: {df_resultados['vol_final_total'].mean():.2f} Hm³")
        
        return archivo_salida


def main():
    # Estos se pueden cambiar en base a lo que se necesite
    NUM_SIMULACIONES = 10
    DURACION_ANOS = 30
    
    mc = MonteCarloEmbalse(
        num_simulaciones=NUM_SIMULACIONES,
        duracion_anos=DURACION_ANOS
    )
    
    mc.ejecutar_monte_carlo()
    mc.exportar_resultados()


if __name__ == "__main__":
    # Usamos semilla x mientras para reproducibilidad
    np.random.seed(42)
    main()