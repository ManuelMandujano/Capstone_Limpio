import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from datetime import datetime

class MonteCarloEmbalse:
    
    def __init__(self, num_simulaciones=100, duracion_anos=30, acumular_ssr=True, 
                 VRFI_init=0.0, VA_init=0.0, VB_init=0.0):
        self.num_simulaciones = num_simulaciones
        self.duracion_anos = duracion_anos
        self.acumular_ssr = acumular_ssr
        self.VRFI_init = VRFI_init
        self.VA_init = VA_init
        self.VB_init = VB_init
        
        self.anos_disponibles = [
            '1989/1990', '1990/1991', '1991/1992', '1992/1993', '1993/1994',
            '1994/1995', '1995/1996', '1996/1997', '1997/1998', '1998/1999',
            '1999/2000', '2000/2001', '2001/2002', '2002/2003', '2003/2004',
            '2004/2005', '2005/2006', '2006/2007', '2007/2008', '2008/2009',
            '2009/2010', '2010/2011', '2011/2012', '2012/2013', '2013/2014',
            '2014/2015', '2015/2016', '2016/2017', '2017/2018', '2018/2019'
        ]

        self.anos_humedos = ['1997/1998', '2002/2003', '1993/1994', '2006/2007', '1992/1993', '2001/2002', '2005/2006', '1991/1992']
        self.anos_secos = ['1998/1999', '2016/2017', '2010/2011', '1996/1997', '2007/2008', '2012/2013', '1990/1991', '1989/1990']
        self.anos_mixtos_extremos = ['1997/1998', '2002/2003', '1993/1994', '2006/2007', '1992/1993', '2001/2002', '2005/2006', '1991/1992',
                                     '1998/1999', '2016/2017', '2010/2011', '1996/1997', '2007/2008', '2012/2013', '1990/1991', '1989/1990']

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
        # anos_disponibles = self.anos_mixtos_extremos.copy()
        # anos_disponibles = self.anos_humedos.copy()
        # anos_disponibles = self.anos_secos.copy()

        # Para los mixtos extremos 
        # anos_disponibles = []
        
        # secos
        #num_secos = min(4, len(self.anos_secos))
        #anos_secos_seleccionados = np.random.choice(self.anos_secos, size=num_secos, replace=False)
        #anos_disponibles.extend(anos_secos_seleccionados)

        # humedos
        #num_humedos = min(4, len(self.anos_humedos))
        #anos_humedos_seleccionados = np.random.choice(self.anos_humedos, size=num_humedos, replace=False)
        #nos_disponibles.extend(anos_humedos_seleccionados)

        escenario = []
        anos_pool = anos_disponibles.copy()
        num_anos_escenario = min(self.duracion_anos, len(anos_pool))
        escenario = list(np.random.choice(anos_pool, size=num_anos_escenario, replace=False))
        
        # Distintos escenarios hechos a "mano" (igual aleatorio pero seleccionando el orden especifico de que va antes de que)
        
        # 5 secos y 3 random
        #escenario = ['1998/1999','2016/2017','2010/2011','1996/1997','2007/2008','2017/2018','2006/2007','1997/1998']
        # 5 secos luego recuperacion gradual
        #escenario = ['1996/1997','2010/2011','1989/1990','1990/1991','2016/2017','2005/2006','2001/2002','2017/2018']
        # 5 humedos y 3 secos
        #escenario = ['1997/1998','2002/2003','1993/1994','2006/2007','1992/1993','1996/1997','1989/1990','1990/1991']
        # Alternado seco - humedo
        #escenario = ['1998/1999','1997/1998','2016/2017','2002/2003','2010/2011','1993/1994','1996/1997','2006/2007']
        # Sequia de 3 años en el medio
        #escenario = ['2001/2002','1993/1994','2010/2011','1996/1997','1990/1991','1992/1993','2005/2006','1997/1998']




        return escenario
    
    def ejecutar_simulacion(self, num_sim, anos_escenario, FEA=1.0, FEB=1.0):
        print(f"\n{'='*60}")
        print(f"Ejecutando Simulacion #{num_sim + 1}/{self.num_simulaciones}")
        print(f"Primeros 5 años: {anos_escenario[:5]}")
        print(f"{'='*60}")
        try:
            resultado = self._resolver_modelo_montecarlo(anos_escenario, FEA=FEA, FEB=FEB)
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
    
    def _resolver_modelo_montecarlo(self, anos_escenario, FEA=1.0, FEB=1.0):
        model = gp.Model("MC_Embalse")
        model.setParam('OutputFlag', 1)
        
        C_VRFI = 175
        C_TIPO_A = 260
        C_TIPO_B = 105
        V_C_H = 3.9
        RESERVA_MIN_VRFI = 2.275
        
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
        
        tA = model.addVars(anos_escenario, meses, name="tA", lb=-GRB.INFINITY)
        tB = model.addVars(anos_escenario, meses, name="tB", lb=-GRB.INFINITY)
        CERO_CONSTANTE = model.addVar(lb=0, ub=0, name="CERO_CONSTANTE")
        
        REMANENTE_BRUTO = model.addVars(anos_escenario, meses, name="REMANENTE_BRUTO", lb=-GRB.INFINITY)
        LLENADO_A = model.addVars(anos_escenario, meses, name="LLENADO_A", lb=0)
        LLENADO_B = model.addVars(anos_escenario, meses, name="LLENADO_B", lb=0)
        
        FALTANTE_TOTAL = model.addVars(anos_escenario, meses, name="FALTANTE_TOTAL", lb=0)
        APOYO_TOTAL = model.addVars(anos_escenario, meses, name="APOYO_TOTAL", lb=0)
        
        SSR_ACUMULADO = model.addVars(anos_escenario, meses, name="SSR_ACUMULADO", lb=0)
        SSR_EXIGIDO = model.addVars(anos_escenario, meses, name="SSR_EXIGIDO", lb=0)
        SSR_CAPACIDAD_VARIABLE = model.addVars(anos_escenario, meses, name="SSR_CAPACIDAD_VARIABLE", lb=0)
        VRFI_DISPONIBLE_LIBRE = model.addVars(anos_escenario, meses, name="VRFI_DISPONIBLE_LIBRE", lb=0)
        
        PROPORCION_A = model.addVars(anos_escenario, meses, name="PROPORCION_A")
        PROPORCION_B = model.addVars(anos_escenario, meses, name="PROPORCION_B")
        ASIGNACION_A_BASE = model.addVars(anos_escenario, meses, name="ASIGNACION_A_BASE", lb=0)
        ASIGNACION_B_BASE = model.addVars(anos_escenario, meses, name="ASIGNACION_B_BASE", lb=0)
        EXCEDENTE_A = model.addVars(anos_escenario, meses, name="EXCEDENTE_A", lb=0.0)
        EXCEDENTE_B = model.addVars(anos_escenario, meses, name="EXCEDENTE_B", lb=0.0)
        BRECHA_A = model.addVars(anos_escenario, meses, name="BRECHA_A", lb=0.0)
        BRECHA_B = model.addVars(anos_escenario, meses, name="BRECHA_B", lb=0.0)
        EXTRA_HACIA_A = model.addVars(anos_escenario, meses, name="EXTRA_HACIA_A", lb=0.0)
        EXTRA_HACIA_B = model.addVars(anos_escenario, meses, name="EXTRA_HACIA_B", lb=0.0)
        
        REBALSE_ON = model.addVars(anos_escenario, meses, vtype=GRB.BINARY, name="REBALSE_ON")
        
        Z_A_VACIO = model.addVars(anos_escenario, meses, vtype=GRB.BINARY, name="Z_A_VACIO")
        Z_B_VACIO = model.addVars(anos_escenario, meses, vtype=GRB.BINARY, name="Z_B_VACIO")
        RESERVA_USO_A = model.addVars(anos_escenario, meses, lb=0.0, name="RESERVA_USO_A")
        RESERVA_USO_B = model.addVars(anos_escenario, meses, lb=0.0, name="RESERVA_USO_B")
        
        VRFI_APOYO_CAP = model.addVars(anos_escenario, meses, lb=0.0, name="VRFI_APOYO_CAP")

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
        
        for idx_ano, año in enumerate(anos_escenario):
            y = int(año.split('/')[0])
            
            for i, mes in enumerate(meses):
                seg = segundos_por_mes[mes]
                Qin_s = self.Q_afl_base.get((y,mes), 0)
                Qin = Qin_s * seg / 1_000_000.0
                UPREF = QPD_eff[año, mes] * seg / 1_000_000.0
                
                key = m_civil[mes]
                demA = (DA_a_m[key] * num_A * FEA) / 1_000_000.0
                demB = (DB_a_b[key] * num_B * FEB) / 1_000_000.0
                
                if i == 0:
                    if idx_ano > 0:
                        año_anterior = anos_escenario[idx_ano - 1]
                        V_R_prev = V_VRFI[año_anterior, 12]
                        V_A_prev = V_A[año_anterior, 12]
                        V_B_prev = V_B[año_anterior, 12]
                    else:
                        V_R_prev = model.addVar(lb=self.VRFI_init, ub=self.VRFI_init, name="VRFI_prev_init")
                        V_A_prev = model.addVar(lb=self.VA_init, ub=self.VA_init, name="VA_prev_init")
                        V_B_prev = model.addVar(lb=self.VB_init, ub=self.VB_init, name="VB_prev_init")
                else:
                    V_R_prev = V_VRFI[año, mes-1]
                    V_A_prev = V_A[año, mes-1]
                    V_B_prev = V_B[año, mes-1]
                
                if i == 0:
                    if self.acumular_ssr and idx_ano > 0:
                        año_anterior = anos_escenario[idx_ano - 1]
                        acumulado_prev = SSR_ACUMULADO[año_anterior, 12]
                    else:
                        acumulado_prev = model.addVar(lb=0.0, ub=0.0, name=f"SSR_ACUMULADO_prev0_{año}")
                else:
                    acumulado_prev = SSR_ACUMULADO[año, mes - 1]

                model.addConstr(SSR_EXIGIDO[año, mes] == ssr_mes + acumulado_prev)
                model.addConstr(SSR_CAPACIDAD_VARIABLE[año, mes] == V_R_prev + IN_VRFI[año, mes])
                model.addGenConstrMin(
                    Q_CONSUMO_HUMANO[año, mes],
                    [SSR_EXIGIDO[año, mes], SSR_CAPACIDAD_VARIABLE[año, mes]]
                )
                model.addConstr(SSR_ACUMULADO[año, mes] == SSR_EXIGIDO[año, mes] - Q_CONSUMO_HUMANO[año, mes])
                
                model.addConstr(REMANENTE_BRUTO[año, mes] == Qin - UPREF, name=f"REMANENTE_BRUTO_{año}_{mes}")
                model.addGenConstrMax(Rem[año, mes], [REMANENTE_BRUTO[año, mes], CERO_CONSTANTE], name=f"REMANENTE_clip0_{año}_{mes}")
                
                model.addConstr(ESPACIO_VRFI[año,mes] == C_VRFI - V_R_prev)
                model.addConstr(ESPACIO_A[año,mes] == C_TIPO_A - V_A_prev)
                model.addConstr(ESPACIO_B[año,mes] == C_TIPO_B - V_B_prev)
                
                model.addGenConstrMin(LLENADO_VRFI[año,mes], [Rem[año,mes], ESPACIO_VRFI[año,mes]])
                model.addConstr(REMANENTE_POST_VRFI[año,mes] == Rem[año,mes] - LLENADO_VRFI[año,mes])
                model.addConstr(CUOTA_A[año,mes] == 0.71 * REMANENTE_POST_VRFI[año,mes])
                model.addConstr(CUOTA_B[año,mes] == 0.29 * REMANENTE_POST_VRFI[año,mes])
                model.addGenConstrMin(LLENADO_A[año,mes], [CUOTA_A[año,mes], ESPACIO_A[año,mes]])
                model.addGenConstrMin(LLENADO_B[año,mes], [CUOTA_B[año,mes], ESPACIO_B[año,mes]])
                
                model.addConstr(IN_VRFI[año,mes] == LLENADO_VRFI[año,mes])
                model.addConstr(IN_A[año,mes] == LLENADO_A[año,mes])
                model.addConstr(IN_B[año,mes] == LLENADO_B[año,mes])
                
                model.addConstr(REBALSE_TOTAL[año,mes] == Rem[año,mes] - IN_VRFI[año,mes] - IN_A[año,mes] - IN_B[año,mes])
                
                model.addGenConstrIndicator(REBALSE_ON[año, mes], 1, REBALSE_TOTAL[año, mes] >= 0.0, name=f"rebalse_on_lo_{año}_{mes}")
                model.addGenConstrIndicator(REBALSE_ON[año, mes], 0, REBALSE_TOTAL[año, mes] <= 0.0, name=f"rebalse_on_hi_{año}_{mes}")
                
                DISPON_PRE_VRFI = model.addVar(lb=-GRB.INFINITY, name=f"DISPONIBILIDAD_PRELIM_VRFI_{año}_{mes}")
                model.addConstr(DISPON_PRE_VRFI == V_R_prev + IN_VRFI[año, mes] - Q_CONSUMO_HUMANO[año, mes] - RESERVA_MIN_VRFI, name=f"DISPONIBILIDAD_PRELIM_VRFI_{año}_{mes}")
                model.addGenConstrMax(VRFI_DISPONIBLE_LIBRE[año, mes], [DISPON_PRE_VRFI, CERO_CONSTANTE], name=f"VRFI_DISP_LIBRE_MAX_{año}_{mes}")
                
                model.addConstr(Q_A[año,mes] <= V_A_prev + IN_A[año,mes])
                model.addConstr(Q_B[año,mes] <= V_B_prev + IN_B[año,mes])
                
                model.addConstr(DISPONIBLE_A[año,mes] == V_A_prev + IN_A[año,mes])
                model.addConstr(DISPONIBLE_B[año,mes] == V_B_prev + IN_B[año,mes])
                
                model.addConstr(Q_A[año,mes] <= demA)
                model.addConstr(Q_B[año,mes] <= demB)
                
                DEM_A_CONST = model.addVar(lb=demA, ub=demA, name=f"DEM_A_CONST_{año}_{mes}")
                DEM_B_CONST = model.addVar(lb=demB, ub=demB, name=f"DEM_B_CONST_{año}_{mes}")
                
                MIN_A_PROPIO = model.addVar(lb=0.0, name=f"MIN_A_PROPIO_{año}_{mes}")
                MIN_B_PROPIO = model.addVar(lb=0.0, name=f"MIN_B_PROPIO_{año}_{mes}")
                
                model.addGenConstrMin(MIN_A_PROPIO, [DISPONIBLE_A[año, mes], DEM_A_CONST], name=f"MIN_A_PROPIO_min_{año}_{mes}")
                model.addConstr(Q_A[año, mes] == MIN_A_PROPIO, name=f"A_usa_todo_propio_{año}_{mes}")
                
                model.addGenConstrMin(MIN_B_PROPIO, [DISPONIBLE_B[año, mes], DEM_B_CONST], name=f"MIN_B_PROPIO_min_{año}_{mes}")
                model.addConstr(Q_B[año, mes] == MIN_B_PROPIO, name=f"B_usa_todo_propio_{año}_{mes}")
                
                model.addConstr(tA[año,mes] == 0.5*demA - Q_A[año,mes])
                model.addConstr(tB[año,mes] == 0.5*demB - Q_B[año,mes])
                model.addGenConstrMax(FALTANTE_A[año,mes], [tA[año,mes], CERO_CONSTANTE])
                model.addGenConstrMax(FALTANTE_B[año,mes], [tB[año,mes], CERO_CONSTANTE])
                
                model.addGenConstrIndicator(Z_A_VACIO[año, mes], 1, DISPONIBLE_A[año, mes] <= 0.0, name=f"A_vacio_hi_{año}_{mes}")
                model.addGenConstrIndicator(Z_A_VACIO[año, mes], 0, DISPONIBLE_A[año, mes] >= 0.0, name=f"A_vacio_lo_{año}_{mes}")
                model.addGenConstrIndicator(Z_B_VACIO[año, mes], 1, DISPONIBLE_B[año, mes] <= 0.0, name=f"B_vacio_hi_{año}_{mes}")
                model.addGenConstrIndicator(Z_B_VACIO[año, mes], 0, DISPONIBLE_B[año, mes] >= 0.0, name=f"B_vacio_lo_{año}_{mes}")
                
                model.addConstr(RESERVA_USO_A[año, mes] <= RESERVA_MIN_VRFI * Z_A_VACIO[año, mes], name=f"uso_res_A_guard_{año}_{mes}")
                model.addConstr(RESERVA_USO_B[año, mes] <= RESERVA_MIN_VRFI * Z_B_VACIO[año, mes], name=f"uso_res_B_guard_{año}_{mes}")
                
                model.addConstr(RESERVA_USO_A[año, mes] + RESERVA_USO_B[año, mes] <= RESERVA_MIN_VRFI, name=f"uso_res_total_cap_{año}_{mes}")
                
                DISP_POST_SSR = model.addVar(lb=-GRB.INFINITY, name=f"DISP_POST_SSR_{año}_{mes}")
                DISP_POST_SSR_POS = model.addVar(lb=0.0, name=f"DISP_POST_SSR_POS_{año}_{mes}")
                model.addConstr(DISP_POST_SSR == V_R_prev + IN_VRFI[año, mes] - Q_CONSUMO_HUMANO[año, mes], name=f"def_post_ssr_{año}_{mes}")
                model.addGenConstrMax(DISP_POST_SSR_POS, [DISP_POST_SSR, CERO_CONSTANTE], name=f"clip_post_ssr_{año}_{mes}")
                model.addConstr(RESERVA_USO_A[año, mes] + RESERVA_USO_B[año, mes] <= DISP_POST_SSR_POS, name=f"uso_res_stock_check_{año}_{mes}")
                
                model.addConstr(VRFI_APOYO_CAP[año, mes] == VRFI_DISPONIBLE_LIBRE[año, mes] + RESERVA_USO_A[año, mes] + RESERVA_USO_B[año, mes], name=f"cap_apoyo_total_{año}_{mes}")

                model.addConstr(FALTANTE_TOTAL[año,mes] == FALTANTE_A[año,mes] + FALTANTE_B[año,mes])
                model.addGenConstrMin(APOYO_TOTAL[año,mes], [VRFI_APOYO_CAP[año, mes], FALTANTE_TOTAL[año,mes]])

                model.addConstr(PROPORCION_A[año, mes] == 0.71 * APOYO_TOTAL[año, mes])
                model.addConstr(PROPORCION_B[año, mes] == 0.29 * APOYO_TOTAL[año, mes])

                model.addGenConstrMin(ASIGNACION_A_BASE[año, mes], [PROPORCION_A[año, mes], FALTANTE_A[año, mes]])
                model.addGenConstrMin(ASIGNACION_B_BASE[año, mes], [PROPORCION_B[año, mes], FALTANTE_B[año, mes]])

                model.addConstr(EXCEDENTE_A[año, mes] == PROPORCION_A[año, mes] - ASIGNACION_A_BASE[año, mes])
                model.addConstr(EXCEDENTE_B[año, mes] == PROPORCION_B[año, mes] - ASIGNACION_B_BASE[año, mes])
                model.addConstr(BRECHA_A[año, mes] == FALTANTE_A[año, mes] - ASIGNACION_A_BASE[año, mes])
                model.addConstr(BRECHA_B[año, mes] == FALTANTE_B[año, mes] - ASIGNACION_B_BASE[año, mes])

                model.addGenConstrMin(EXTRA_HACIA_B[año, mes], [EXCEDENTE_A[año, mes], BRECHA_B[año, mes]])
                model.addGenConstrMin(EXTRA_HACIA_A[año, mes], [EXCEDENTE_B[año, mes], BRECHA_A[año, mes]])

                model.addConstr(Q_A_apoyo[año, mes] == ASIGNACION_A_BASE[año, mes] + EXTRA_HACIA_A[año, mes])
                model.addConstr(Q_B_apoyo[año, mes] == ASIGNACION_B_BASE[año, mes] + EXTRA_HACIA_B[año, mes])
                
                model.addConstr(Q_A_apoyo[año, mes] + Q_B_apoyo[año, mes] <= VRFI_APOYO_CAP[año, mes], name=f"APOYO_SUMA_LE_VRFI_{año}_{mes}")
                
                model.addConstr(V_VRFI[año,mes] == V_R_prev + IN_VRFI[año,mes] - Q_CONSUMO_HUMANO[año,mes] - Q_A_apoyo[año,mes] - Q_B_apoyo[año,mes])
                model.addConstr(V_A[año,mes] == V_A_prev + IN_A[año,mes] - Q_A[año,mes])
                model.addConstr(V_B[año,mes] == V_B_prev + IN_B[año,mes] - Q_B[año,mes])
                
                model.addConstr(V_VRFI[año, mes] <= C_VRFI)
                model.addConstr(V_A[año, mes] <= C_TIPO_A)
                model.addConstr(V_B[año, mes] <= C_TIPO_B)

                model.addConstr(d_A[año,mes] == demA - (Q_A[año,mes] + Q_A_apoyo[año,mes]))
                model.addConstr(d_B[año,mes] == demB - (Q_B[año,mes] + Q_B_apoyo[año,mes]))
                
                model.addConstr(Q_A[año,mes] + Q_A_apoyo[año,mes] <= demA)
                model.addConstr(Q_B[año,mes] + Q_B_apoyo[año,mes] <= demB)
                
                model.addConstr(Q_turb[año,mes] == Q_A[año,mes] + Q_A_apoyo[año,mes] + Q_B[año,mes] + Q_B_apoyo[año,mes] + REBALSE_TOTAL[año,mes])
            
        extra_const = 0.0
        for año in anos_escenario:
            y = int(año.split('/')[0])
            for mes in meses:
                key = m_civil[mes]
                DemA_base = (DA_a_m[key] * num_A) / 1_000_000.0
                DemB_base = (DB_a_b[key] * num_B) / 1_000_000.0
                d_FE = (1.0 - FEA) * DemA_base + (1.0 - FEB) * DemB_base
                extra_const += d_FE
        
        total_def_vars = gp.quicksum(d_A[año,mes] + d_B[año,mes] for año in anos_escenario for mes in meses)
        model.setObjective(total_def_vars + extra_const, GRB.MINIMIZE)

        model.optimize()
        
        if model.status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
            return None
        
        tiempo_ejecucion = model.Runtime
        gap = model.MIPGap if hasattr(model, 'MIPGap') else 0.0
        
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
    
    def ejecutar_monte_carlo(self, FEA=1.0, FEB=1.0):
        print(f"\n{'#'*60}")
        print(f"INICIANDO SIMULACIÓN DE MONTE CARLO")
        print(f"Numero de simulaciones: {self.num_simulaciones}")
        print(f"Duración por simulacion: {self.duracion_anos} años")
        print(f"FEA: {FEA}, FEB: {FEB}")
        print(f"{'#'*60}\n")
        
        for i in range(self.num_simulaciones):
            escenario = self.generar_escenario()
            resultado = self.ejecutar_simulacion(i, escenario, FEA=FEA, FEB=FEB)
            
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
        
        import os
        output_dir = "resultados montecarlo"
        os.makedirs(output_dir, exist_ok=True)
        
        if archivo_salida is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archivo_salida = f"monte_carlo_resultados_{timestamp}.xlsx"
        
        archivo_salida = os.path.join(output_dir, archivo_salida)
        
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
    NUM_SIMULACIONES = 10
    DURACION_ANOS = 8
    FEA = 1.0
    FEB = 1.0
    
    mc = MonteCarloEmbalse(
        num_simulaciones=NUM_SIMULACIONES,
        duracion_anos=DURACION_ANOS,
        acumular_ssr=True,
        VRFI_init=0.0,
        VA_init=0.0,
        VB_init=0.0
    )
    
    mc.ejecutar_monte_carlo(FEA=FEA, FEB=FEB)
    mc.exportar_resultados()


if __name__ == "__main__":
    np.random.seed(42)
    main()