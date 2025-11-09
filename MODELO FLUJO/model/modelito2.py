import gurobipy as gp
from gurobipy import GRB
import pandas as pd

class EmbalseNuevaPunilla:

    def __init__(self):
        self.model = gp.Model("Embalse_Nueva_Punilla")

        self.anos = ['1989/1990', '1990/1991', '1991/1992', '1992/1993', '1993/1994',
                     '1994/1995', '1995/1996', '1996/1997', '1997/1998', '1998/1999',
                     '1999/2000', '2000/2001', '2001/2002', '2002/2003', '2003/2004',
                     '2004/2005', '2005/2006', '2006/2007', '2007/2008', '2008/2009',
                     '2009/2010', '2010/2011', '2011/2012', '2012/2013', '2013/2014',
                     '2014/2015', '2015/2016', '2016/2017', '2017/2018', '2018/2019']
        self.meses = list(range(1, 13))  

        # CAPACIDADES (Hm³)
        self.C_VRFI   = 175
        self.C_TIPO_A = 260
        self.C_TIPO_B = 105

        # Segundos x mes
        self.segundos_por_mes = {
            1: 31*24*3600,  # MAY
            2: 30*24*3600,  # JUN
            3: 31*24*3600,  # JUL
            4: 31*24*3600,  # AGO
            5: 30*24*3600,  # SEP
            6: 31*24*3600,  # OCT
            7: 30*24*3600,  # NOV
            8: 31*24*3600,  # DIC
            9: 31*24*3600,  # ENE
            10: 28*24*3600, # FEB
            11: 31*24*3600, # MAR
            12: 30*24*3600  # ABR
        }

        self.caudal_afluente  = {}
        self.Q_nuble = {}
        self.Q_hoya1 = {}
        self.Q_hoya2 = {}
        self.Q_hoya3 = {}

        # DEMANDAS (m³/mes por acción) -> luego a Hm³
        self.num_acciones_A  = 21221
        self.num_acciones_B  = 7100
        self.demanda_A_mensual = {1:9503,2:6516,3:3452,4:776,5:0,6:0,7:0,8:0,9:0,10:2444,11:6516,12:9580}
        self.demanda_B_mensual  = {1:3361,2:2305,3:1221,4:274,5:0,6:0,7:0,8:0,9:0,10: 864,11:2305,12:3388}

        # orden de meses hidrológicos (1..12=MAY..ABR) -> civil (ene=1,...,dic=12)
        self.hidrologico_a_civil  = {1:5,2:6,3:7,4:8,5:9,6:10,7:11,8:12,9:1,10:2,11:3,12:4}

        # factores de entrega
        self.FEA = 1.0
        self.FEB = 1.0

        # Consumo humano anual (Hm³/año)
        self.V_C_H = 3.9
        
        # SSR acumulado interanual
        self.acumular_ssr = True  

        # reserva mínima VRFI (Hm³)
        self.RESERVA_MIN_VRFI  = 2.275

        # volúmenes iniciales
        self.VRFI_init = 0.0
        self.VA_init   = 0.0
        self.VB_init   = 0.0

    # Variables
    def variables(self):
        m = self.model
        # volúmenes (en Hm³)
        self.V_VRFI = m.addVars(self.anos, self.meses, name="V_VRFI", lb=0, ub=self.C_VRFI)
        self.V_A    = m.addVars(self.anos, self.meses, name="V_A", lb=0, ub=self.C_TIPO_A)
        self.V_B    = m.addVars(self.anos, self.meses, name="V_B", lb=0, ub=self.C_TIPO_B)

        # llenados y rebalse (Hm³/mes)
        self.IN_VRFI = m.addVars(self.anos, self.meses, name="IN_VRFI", lb=0)
        self.IN_A    = m.addVars(self.anos, self.meses, name="IN_A", lb=0)   
        self.IN_B    = m.addVars(self.anos, self.meses, name="IN_B", lb=0)
        self.REBALSE_TOTAL = m.addVars(self.anos, self.meses, name="REBALSE_TOTAL", lb=0)

        # entregas (Hm³/mes)
        self.Q_CONSUMO_HUMANO = m.addVars(self.anos, self.meses, name="Q_CONSUMO_HUMANO", lb=0)
        self.Q_A  = m.addVars(self.anos, self.meses, name="Q_A", lb=0)
        self.Q_B  = m.addVars(self.anos, self.meses, name="Q_B", lb=0)

        # apoyo VRFI
        self.Q_A_apoyo = m.addVars(self.anos, self.meses, name="Q_A_apoyo", lb=0)
        self.Q_B_apoyo = m.addVars(self.anos, self.meses, name="Q_B_apoyo", lb=0)

        # déficits
        self.d_A = m.addVars(self.anos, self.meses, name="d_A", lb=0)
        self.d_B = m.addVars(self.anos, self.meses, name="d_B", lb=0)

        # turbinado y reporte
        self.Q_turb = m.addVars(self.anos, self.meses, name="Q_turb", lb=0)
        self.Q_dis  = m.addVars(self.anos, self.meses, name="Q_dis", lb=-GRB.INFINITY)

        # auxiliares de llenado
        self.Rem   = m.addVars(self.anos, self.meses, name="Rem", lb=0)
        self.ESPACIO_VRFI = m.addVars(self.anos, self.meses, name="ESPACIO_VRFI", lb=0)
        self.LLENADO_VRFI = m.addVars(self.anos, self.meses, name="LLENADO_VRFI", lb=0)
        self.REMANENTE_POST_VRFI = m.addVars(self.anos, self.meses, name="REMANENTE_POST_VRFI", lb=0)
        self.ESPACIO_A = m.addVars(self.anos, self.meses, name="ESPACIO_A", lb=0)
        self.ESPACIO_B = m.addVars(self.anos, self.meses, name="ESPACIO_B", lb=0)
        self.CUOTA_A   = m.addVars(self.anos, self.meses, name="CUOTA_A", lb=0)
        self.CUOTA_B   = m.addVars(self.anos, self.meses, name="CUOTA_B", lb=0)
        self.LLENADO_A = m.addVars(self.anos, self.meses, name="LLENADO_A", lb=0)
        self.LLENADO_B = m.addVars(self.anos, self.meses, name="LLENADO_B", lb=0)

        # faltantes 
        self.FALTANTE_A = m.addVars(self.anos, self.meses, name="FALTANTE_A", lb=0)
        self.FALTANTE_B = m.addVars(self.anos, self.meses, name="FALTANTE_B", lb=0)

        # apoyo total y VRFI libre
        self.VRFI_DISPONIBLE_LIBRE = m.addVars(self.anos, self.meses, name="VRFI_DISPONIBLE_LIBRE", lb=0)
        self.FALTANTE_TOTAL = m.addVars(self.anos, self.meses, name="FALTANTE_TOTAL", lb=0)
        self.APOYO_TOTAL    = m.addVars(self.anos, self.meses, name="APOYO_TOTAL", lb=0)

        # remanente bruto y cero constante
        self.REMANENTE_BRUTO = m.addVars(self.anos, self.meses, name="REMANENTE_BRUTO", lb=-GRB.INFINITY)
        self.CERO_CONSTANTE  = m.addVar(lb=0.0, ub=0.0, name="CERO_CONSTANTE")

        # diagnósticos A y B
        self.DISPONIBLE_A = m.addVars(self.anos, self.meses, name="DISPONIBLE_A")
        self.DISPONIBLE_B = m.addVars(self.anos, self.meses, name="DISPONIBLE_B")

        # --- IMPORTANTE: T_A/T_B pueden ser negativas (gap a 50%) ---
        self.T_A = m.addVars(self.anos, self.meses, name="T_A", lb=-GRB.INFINITY)
        self.T_B = m.addVars(self.anos, self.meses, name="T_B", lb=-GRB.INFINITY)

        # reparto 71/29
        self.PROPORCION_A = m.addVars(self.anos, self.meses, name="PROPORCION_A")
        self.PROPORCION_B = m.addVars(self.anos, self.meses, name="PROPORCION_B")
        self.ASIGNACION_A_BASE = m.addVars(self.anos, self.meses, name="ASIGNACION_A_BASE", lb=0.0)
        self.ASIGNACION_B_BASE = m.addVars(self.anos, self.meses, name="ASIGNACION_B_BASE", lb=0.0)
        self.EXCEDENTE_A = m.addVars(self.anos, self.meses, name="EXCEDENTE_A", lb=0.0)
        self.EXCEDENTE_B = m.addVars(self.anos, self.meses, name="EXCEDENTE_B", lb=0.0)
        self.BRECHA_A    = m.addVars(self.anos, self.meses, name="BRECHA_A", lb=0.0)
        self.BRECHA_B    = m.addVars(self.anos, self.meses, name="BRECHA_B", lb=0.0)
        self.EXTRA_HACIA_A = m.addVars(self.anos, self.meses, name="EXTRA_HACIA_A", lb=0.0)
        self.EXTRA_HACIA_B = m.addVars(self.anos, self.meses, name="EXTRA_HACIA_B", lb=0.0)

        # SSR
        self.SSR_EXIGIDO            = m.addVars(self.anos, self.meses, name="SSR_EXIGIDO", lb=0.0)
        self.SSR_ACUMULADO          = m.addVars(self.anos, self.meses, name="SSR_ACUMULADO", lb=0.0)
        self.SSR_CAPACIDAD_VARIABLE = m.addVars(self.anos, self.meses, name="SSR_CAPACIDAD_VARIABLE", lb=0.0)

        # binaria de rebalse
        self.REBALSE_ON = m.addVars(self.anos, self.meses, vtype=GRB.BINARY, name="REBALSE_ON")

        # binarios de vacío y uso de reserva
        self.Z_A_VACIO = m.addVars(self.anos, self.meses, vtype=GRB.BINARY, name="Z_A_VACIO")
        self.Z_B_VACIO = m.addVars(self.anos, self.meses, vtype=GRB.BINARY, name="Z_B_VACIO")
        self.RESERVA_USO_A = m.addVars(self.anos, self.meses, lb=0.0, name="RESERVA_USO_A")
        self.RESERVA_USO_B = m.addVars(self.anos, self.meses, lb=0.0, name="RESERVA_USO_B")

        # capacidad total de apoyo (libre + reserva habilitada)
        self.VRFI_APOYO_CAP = m.addVars(self.anos, self.meses, lb=0.0, name="VRFI_APOYO_CAP")

    # Datos
    def cargar_data(self, file_path):
        xls = pd.ExcelFile(file_path)
        nuble = pd.read_excel(xls, sheet_name='Hoja1', skiprows=4,  nrows=31)
        hoya1 = pd.read_excel(xls, sheet_name='Hoja1', skiprows=39, nrows=31)
        hoya2 = pd.read_excel(xls, sheet_name='Hoja1', skiprows=75, nrows=31)
        hoya3 = pd.read_excel(xls, sheet_name='Hoja1', skiprows=110,nrows=31)
        
        excel_nombre_columnas   = ['MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC','ENE','FEB','MAR','ABR']
        meses = [1,2,3,4,5,6,7,8,9,10,11,12]

        Q_nuble, Q_hoya1, Q_hoya2, Q_hoya3, Q_afl = {},{},{},{},{}

        for idx, row in nuble.iterrows():
            año_en_str = str(row.get('AÑO',''))
            if (pd.notna(row.get('AÑO')) and '/' in año_en_str
                and not any(w in año_en_str.upper() for w in ['PROMEDIO','TOTAL','MAX','MIN'])):
                try:
                    año = int(año_en_str.split('/')[0])
                    for col, mm in zip(excel_nombre_columnas, meses):
                        n1 = nuble.loc[idx, col]; h1 = hoya1.loc[idx, col]
                        h2 = hoya2.loc[idx, col]; h3 = hoya3.loc[idx, col]
                        if pd.notna(n1): Q_nuble[año, mm] = float(n1); Q_afl[año, mm] = float(n1)
                        if pd.notna(h1): Q_hoya1[año, mm] = float(h1)
                        if pd.notna(h2): Q_hoya2[año, mm] = float(h2)
                        if pd.notna(h3): Q_hoya3[año, mm] = float(h3)
                except Exception:
                    pass
        return Q_afl, Q_nuble, Q_hoya1, Q_hoya2, Q_hoya3

    # Restricciones
    def restricciones(self):
        m = self.model
        data_file = "data/caudales.xlsx"

        # cargar datos
        (self.caudal_afluente,
         self.Q_nuble,
         self.Q_hoya1,
         self.Q_hoya2,
         self.Q_hoya3) = self.cargar_data(data_file)

        # QPD efectivo (m³/s) (orden MAY–ABR)
        derechos_MAY_ABR = [52.00, 52.00, 52.00, 52.00, 57.70, 76.22, 69.22, 52.00, 52.00, 52.00, 52.00, 52.00]
        qeco_MAY_ABR     = [10.00, 10.35, 14.48, 15.23, 15.23, 15.23, 15.23, 15.23, 12.80, 15.20, 16.40, 17.60]

        self.QPD_eff = {}
        for ano in self.anos:
            y = int(ano.split('/')[0])
            for mes in self.meses:
                H = (self.Q_hoya1.get((y, mes), 0.0)
                     + self.Q_hoya2.get((y, mes), 0.0)
                     + self.Q_hoya3.get((y, mes), 0.0))
                qpd_nom = max(derechos_MAY_ABR[mes-1], qeco_MAY_ABR[mes-1], max(0.0, 95.7 - H))
                self.QPD_eff[ano, mes] = min(qpd_nom, self.Q_nuble.get((y, mes), 0.0))

        # SSR mensual (Hm³/mes)
        ssr_mes = self.V_C_H / 12.0

        for a_idx, ano in enumerate(self.anos):
            y = int(ano.split('/')[0])
            for i, mes in enumerate(self.meses):
                seg   = self.segundos_por_mes[mes]
                Qin_s = self.caudal_afluente.get((y, mes), 0.0)               
                Qin   = Qin_s * seg / 1_000_000.0
                UPREF = self.QPD_eff[ano, mes] * seg / 1_000_000.0

                key_civil = self.hidrologico_a_civil[mes]
                demA = (self.demanda_A_mensual[key_civil] * self.num_acciones_A * self.FEA) / 1_000_000.0
                demB = (self.demanda_B_mensual[key_civil] * self.num_acciones_B * self.FEB) / 1_000_000.0

                # stocks previos
                if i == 0:
                    if a_idx > 0:
                        ano_prev = self.anos[a_idx - 1]
                        V_R_prev = self.V_VRFI[ano_prev, 12]
                        V_A_prev = self.V_A[ano_prev, 12]
                        V_B_prev = self.V_B[ano_prev, 12]
                    else:
                        V_R_prev = self.model.addVar(lb=self.VRFI_init, ub=self.VRFI_init, name="VRFI_prev_init")
                        V_A_prev = self.model.addVar(lb=self.VA_init,   ub=self.VA_init,   name="VA_prev_init")
                        V_B_prev = self.model.addVar(lb=self.VB_init,   ub=self.VB_init,   name="VB_prev_init")
                else:
                    V_R_prev = self.V_VRFI[ano, mes-1]
                    V_A_prev = self.V_A[ano,  mes-1]
                    V_B_prev = self.V_B[ano,  mes-1]

                # remanente y espacios
                m.addConstr(self.REMANENTE_BRUTO[ano, mes] == Qin - UPREF, name=f"REMANENTE_BRUTO_{ano}_{mes}")
                m.addGenConstrMax(self.Rem[ano, mes],
                                  [self.REMANENTE_BRUTO[ano, mes], self.CERO_CONSTANTE],
                                  name=f"REMANENTE_clip0_{ano}_{mes}")

                m.addConstr(self.ESPACIO_VRFI[ano, mes] == self.C_VRFI - V_R_prev, name=f"ESPACIO_VRFI_{ano}_{mes}")
                m.addConstr(self.ESPACIO_A[ano, mes] == self.C_TIPO_A - V_A_prev,  name=f"ESPACIO_A_{ano}_{mes}")
                m.addConstr(self.ESPACIO_B[ano, mes] == self.C_TIPO_B - V_B_prev,  name=f"ESPACIO_B_{ano}_{mes}")

                m.addGenConstrMin(self.LLENADO_VRFI[ano, mes],
                                  [self.Rem[ano, mes], self.ESPACIO_VRFI[ano, mes]],
                                  name=f"LLENADO_VRFI_min_{ano}_{mes}")
                m.addConstr(self.REMANENTE_POST_VRFI[ano, mes] == self.Rem[ano, mes] - self.LLENADO_VRFI[ano, mes],
                            name=f"REMANENTE_POST_VRFI_{ano}_{mes}")
                m.addConstr(self.CUOTA_A[ano, mes] == 0.71 * self.REMANENTE_POST_VRFI[ano, mes], name=f"CUOTA_A_{ano}_{mes}")
                m.addConstr(self.CUOTA_B[ano, mes] == 0.29 * self.REMANENTE_POST_VRFI[ano, mes], name=f"CUOTA_B_{ano}_{mes}")
                m.addGenConstrMin(self.LLENADO_A[ano, mes],
                                  [self.CUOTA_A[ano, mes], self.ESPACIO_A[ano, mes]],
                                  name=f"LLENADO_A_min_{ano}_{mes}")
                m.addGenConstrMin(self.LLENADO_B[ano, mes],
                                  [self.CUOTA_B[ano, mes], self.ESPACIO_B[ano, mes]],
                                  name=f"LLENADO_B_min_{ano}_{mes}")

                m.addConstr(self.IN_VRFI[ano, mes] == self.LLENADO_VRFI[ano, mes], name=f"IN_VRFI_{ano}_{mes}")
                m.addConstr(self.IN_A[ano, mes]    == self.LLENADO_A[ano, mes],   name=f"IN_A_{ano}_{mes}")
                m.addConstr(self.IN_B[ano, mes]    == self.LLENADO_B[ano, mes],   name=f"IN_B_{ano}_{mes}")

                # rebalse total
                m.addConstr(self.REBALSE_TOTAL[ano, mes] ==
                            self.Rem[ano, mes] - self.IN_VRFI[ano, mes] - self.IN_A[ano, mes] - self.IN_B[ano, mes],
                            name=f"REBALSE_TOTAL_{ano}_{mes}")

                # Indicadores de rebalse (sin EPS: usando 0.0)
                m.addGenConstrIndicator(self.REBALSE_ON[ano, mes], 1,
                                        self.REBALSE_TOTAL[ano, mes] >= 0.0,
                                        name=f"rebalse_on_lo_{ano}_{mes}")
                m.addGenConstrIndicator(self.REBALSE_ON[ano, mes], 0,
                                        self.REBALSE_TOTAL[ano, mes] <= 0.0,
                                        name=f"rebalse_on_hi_{ano}_{mes}")

                # caudal disponible reportado
                m.addConstr(self.Q_dis[ano, mes] == Qin - UPREF, name=f"Q_DISPONIBLE_{ano}_{mes}")

                # SSR (prioridad dura)
                if i == 0:
                    if self.acumular_ssr and a_idx > 0:
                        ano_prev = self.anos[a_idx - 1]
                        acumulado_prev = self.SSR_ACUMULADO[ano_prev, 12]
                    else:
                        acumulado_prev = self.model.addVar(lb=0.0, ub=0.0, name=f"SSR_ACUMULADO_prev0_{ano}")
                else:
                    acumulado_prev = self.SSR_ACUMULADO[ano, mes - 1]

                m.addConstr(self.SSR_EXIGIDO[ano, mes] == ssr_mes + acumulado_prev, name=f"SSR_EXIGIDO_{ano}_{mes}")
                m.addConstr(self.SSR_CAPACIDAD_VARIABLE[ano, mes] == V_R_prev + self.IN_VRFI[ano, mes],
                            name=f"SSR_CAP_VAR_{ano}_{mes}")
                m.addGenConstrMin(self.Q_CONSUMO_HUMANO[ano, mes],
                                  [self.SSR_EXIGIDO[ano, mes], self.SSR_CAPACIDAD_VARIABLE[ano, mes]],
                                  name=f"SSR_PAGO_MIN_{ano}_{mes}")
                m.addConstr(self.SSR_ACUMULADO[ano, mes] == self.SSR_EXIGIDO[ano, mes] - self.Q_CONSUMO_HUMANO[ano, mes],
                            name=f"SSR_ACUMULADO_{ano}_{mes}")

                # VRFI disponible libre (protegiendo reserva mínima)
                DISPON_PRE_VRFI = m.addVar(lb=-GRB.INFINITY, name=f"DISPONIBILIDAD_PRELIM_VRFI_{ano}_{mes}")
                m.addConstr(DISPON_PRE_VRFI ==
                            V_R_prev + self.IN_VRFI[ano, mes] - self.Q_CONSUMO_HUMANO[ano, mes] - self.RESERVA_MIN_VRFI,
                            name=f"DISPONIBILIDAD_PRELIM_VRFI_{ano}_{mes}")
                m.addGenConstrMax(self.VRFI_DISPONIBLE_LIBRE[ano, mes],
                                  [DISPON_PRE_VRFI, self.CERO_CONSTANTE],
                                  name=f"VRFI_DISP_LIBRE_MAX_{ano}_{mes}")

                # límites de extracción propia
                m.addConstr(self.Q_A[ano, mes] <= V_A_prev + self.IN_A[ano, mes], name=f"DISP_A_{ano}_{mes}")
                m.addConstr(self.Q_B[ano, mes] <= V_B_prev + self.IN_B[ano, mes], name=f"DISP_B_{ano}_{mes}")

                # diagnósticos de disponibilidad
                m.addConstr(self.DISPONIBLE_A[ano, mes] == V_A_prev + self.IN_A[ano, mes], name=f"DISPONIBLE_A_def_{ano}_{mes}")
                m.addConstr(self.DISPONIBLE_B[ano, mes] == V_B_prev + self.IN_B[ano, mes], name=f"DISPONIBLE_B_def_{ano}_{mes}")

                # No sobre servir respecto de la demanda propia
                m.addConstr(self.Q_A[ano, mes] <= demA, name=f"A_le_Dem_{ano}_{mes}")
                m.addConstr(self.Q_B[ano, mes] <= demB, name=f"B_le_Dem_{ano}_{mes}")

                # ------------------------------------------------------------------
                # >>> BLOQUE NUEVO: "propio primero" y faltantes al 50% <<<
                # ------------------------------------------------------------------

                # “Constantes” de demanda como variables fijadas (para usar en MIN)
                DEM_A_CONST = m.addVar(lb=demA, ub=demA, name=f"DEM_A_CONST_{ano}_{mes}")
                DEM_B_CONST = m.addVar(lb=demB, ub=demB, name=f"DEM_B_CONST_{ano}_{mes}")

                # Auxiliares MIN
                MIN_A_PROPIO = m.addVar(lb=0.0, name=f"MIN_A_PROPIO_{ano}_{mes}")
                MIN_B_PROPIO = m.addVar(lb=0.0, name=f"MIN_B_PROPIO_{ano}_{mes}")

                # Q_A / Q_B usan todo lo propio hasta la demanda
                m.addGenConstrMin(MIN_A_PROPIO, [self.DISPONIBLE_A[ano, mes], DEM_A_CONST],
                                  name=f"MIN_A_PROPIO_min_{ano}_{mes}")
                m.addConstr(self.Q_A[ano, mes] == MIN_A_PROPIO, name=f"A_usa_todo_propio_{ano}_{mes}")

                m.addGenConstrMin(MIN_B_PROPIO, [self.DISPONIBLE_B[ano, mes], DEM_B_CONST],
                                  name=f"MIN_B_PROPIO_min_{ano}_{mes}")
                m.addConstr(self.Q_B[ano, mes] == MIN_B_PROPIO, name=f"B_usa_todo_propio_{ano}_{mes}")

                # Faltante SOLO respecto del 50% de la demanda (para activar apoyo VRFI)
                m.addConstr(self.T_A[ano, mes] == 0.5 * demA - self.Q_A[ano, mes], name=f"T_A_gap50_{ano}_{mes}")
                m.addConstr(self.T_B[ano, mes] == 0.5 * demB - self.Q_B[ano, mes], name=f"T_B_gap50_{ano}_{mes}")

                m.addGenConstrMax(self.FALTANTE_A[ano, mes], [self.T_A[ano, mes], self.CERO_CONSTANTE],
                                  name=f"FALT_A_pos_gap50_{ano}_{mes}")
                m.addGenConstrMax(self.FALTANTE_B[ano, mes], [self.T_B[ano, mes], self.CERO_CONSTANTE],
                                  name=f"FALT_B_pos_gap50_{ano}_{mes}")

                # --- vacíos y uso de reserva fija (umbral 0.0) ---
                m.addGenConstrIndicator(self.Z_A_VACIO[ano, mes], 1,
                                        self.DISPONIBLE_A[ano, mes] <= 0.0,
                                        name=f"A_vacio_hi_{ano}_{mes}")
                m.addGenConstrIndicator(self.Z_A_VACIO[ano, mes], 0,
                                        self.DISPONIBLE_A[ano, mes] >= 0.0,
                                        name=f"A_vacio_lo_{ano}_{mes}")
                m.addGenConstrIndicator(self.Z_B_VACIO[ano, mes], 1,
                                        self.DISPONIBLE_B[ano, mes] <= 0.0,
                                        name=f"B_vacio_hi_{ano}_{mes}")
                m.addGenConstrIndicator(self.Z_B_VACIO[ano, mes], 0,
                                        self.DISPONIBLE_B[ano, mes] >= 0.0,
                                        name=f"B_vacio_lo_{ano}_{mes}")

                m.addConstr(self.RESERVA_USO_A[ano, mes] <= self.RESERVA_MIN_VRFI * self.Z_A_VACIO[ano, mes],
                            name=f"uso_res_A_guard_{ano}_{mes}")
                m.addConstr(self.RESERVA_USO_B[ano, mes] <= self.RESERVA_MIN_VRFI * self.Z_B_VACIO[ano, mes],
                            name=f"uso_res_B_guard_{ano}_{mes}")

                m.addConstr(self.RESERVA_USO_A[ano, mes] + self.RESERVA_USO_B[ano, mes] <= self.RESERVA_MIN_VRFI,
                            name=f"uso_res_total_cap_{ano}_{mes}")

                DISP_POST_SSR = m.addVar(lb=-GRB.INFINITY, name=f"DISP_POST_SSR_{ano}_{mes}")
                DISP_POST_SSR_POS = m.addVar(lb=0.0, name=f"DISP_POST_SSR_POS_{ano}_{mes}")
                m.addConstr(DISP_POST_SSR == V_R_prev + self.IN_VRFI[ano, mes] - self.Q_CONSUMO_HUMANO[ano, mes],
                            name=f"def_post_ssr_{ano}_{mes}")
                m.addGenConstrMax(DISP_POST_SSR_POS, [DISP_POST_SSR, self.CERO_CONSTANTE],
                                  name=f"clip_post_ssr_{ano}_{mes}")
                m.addConstr(self.RESERVA_USO_A[ano, mes] + self.RESERVA_USO_B[ano, mes] <= DISP_POST_SSR_POS,
                            name=f"uso_res_stock_check_{ano}_{mes}")

                # Capacidad total de apoyo: libre + reserva autorizada
                m.addConstr(self.VRFI_APOYO_CAP[ano, mes] ==
                            self.VRFI_DISPONIBLE_LIBRE[ano, mes] +
                            self.RESERVA_USO_A[ano, mes] + self.RESERVA_USO_B[ano, mes],
                            name=f"cap_apoyo_total_{ano}_{mes}")

                # APOYO_TOTAL = min(VRFI_APOYO_CAP, FALTANTE_TOTAL)
                m.addConstr(self.FALTANTE_TOTAL[ano, mes] == self.FALTANTE_A[ano, mes] + self.FALTANTE_B[ano, mes],
                            name=f"FALT_TOTAL_{ano}_{mes}")
                m.addGenConstrMin(self.APOYO_TOTAL[ano, mes],
                                  [self.VRFI_APOYO_CAP[ano, mes], self.FALTANTE_TOTAL[ano, mes]],
                                  name=f"APOYO_TOTAL_min_{ano}_{mes}")

                # reparto 71/29
                m.addConstr(self.PROPORCION_A[ano, mes] == 0.71 * self.APOYO_TOTAL[ano, mes], name=f"PROP_A_{ano}_{mes}")
                m.addConstr(self.PROPORCION_B[ano, mes] == 0.29 * self.APOYO_TOTAL[ano, mes], name=f"PROP_B_{ano}_{mes}")

                # Asignación base limitada por necesidad individual
                m.addGenConstrMin(self.ASIGNACION_A_BASE[ano, mes],
                                  [self.FALTANTE_A[ano, mes], self.PROPORCION_A[ano, mes]],
                                  name=f"ASIG_A_BASE_min_{ano}_{mes}")
                m.addGenConstrMin(self.ASIGNACION_B_BASE[ano, mes],
                                  [self.FALTANTE_B[ano, mes], self.PROPORCION_B[ano, mes]],
                                  name=f"ASIG_B_BASE_min_{ano}_{mes}")

                # excedentes y brechas
                m.addConstr(self.EXCEDENTE_A[ano, mes] == self.PROPORCION_A[ano, mes] - self.ASIGNACION_A_BASE[ano, mes],
                            name=f"EXC_A_{ano}_{mes}")
                m.addConstr(self.EXCEDENTE_B[ano, mes] == self.PROPORCION_B[ano, mes] - self.ASIGNACION_B_BASE[ano, mes],
                            name=f"EXC_B_{ano}_{mes}")
                m.addConstr(self.BRECHA_A[ano, mes] == self.FALTANTE_A[ano, mes] - self.ASIGNACION_A_BASE[ano, mes],
                            name=f"BRECHA_A_{ano}_{mes}")
                m.addConstr(self.BRECHA_B[ano, mes] == self.FALTANTE_B[ano, mes] - self.ASIGNACION_B_BASE[ano, mes],
                            name=f"BRECHA_B_{ano}_{mes}")

                # Reasignación cruzada
                m.addGenConstrMin(self.EXTRA_HACIA_B[ano, mes],
                                  [self.EXCEDENTE_A[ano, mes], self.BRECHA_B[ano, mes]],
                                  name=f"EXTRA_B_min_{ano}_{mes}")
                m.addGenConstrMin(self.EXTRA_HACIA_A[ano, mes],
                                  [self.EXCEDENTE_B[ano, mes], self.BRECHA_A[ano, mes]],
                                  name=f"EXTRA_A_min_{ano}_{mes}")

                # Apoyos finales a A/B
                m.addConstr(self.Q_A_apoyo[ano, mes] == self.ASIGNACION_A_BASE[ano, mes] + self.EXTRA_HACIA_A[ano, mes],
                            name=f"Q_A_APOYO_{ano}_{mes}")
                m.addConstr(self.Q_B_apoyo[ano, mes] == self.ASIGNACION_B_BASE[ano, mes] + self.EXTRA_HACIA_B[ano, mes],
                            name=f"Q_B_APOYO_{ano}_{mes}")

                # no usar más VRFI para apoyo que la capacidad total de apoyo (incluida reserva)
                m.addConstr(self.Q_A_apoyo[ano, mes] + self.Q_B_apoyo[ano, mes] <= self.VRFI_APOYO_CAP[ano, mes],
                            name=f"APOYO_SUMA_LE_VRFI_{ano}_{mes}")

                # balances
                m.addConstr(self.V_VRFI[ano, mes] ==
                            V_R_prev + self.IN_VRFI[ano, mes]
                            - self.Q_CONSUMO_HUMANO[ano, mes]
                            - self.Q_A_apoyo[ano, mes] - self.Q_B_apoyo[ano, mes],
                            name=f"BAL_VRFI_{ano}_{mes}")
                m.addConstr(self.V_A[ano, mes] == V_A_prev + self.IN_A[ano, mes] - self.Q_A[ano, mes],
                            name=f"BAL_VA_{ano}_{mes}")
                m.addConstr(self.V_B[ano, mes] == V_B_prev + self.IN_B[ano, mes] - self.Q_B[ano, mes],
                            name=f"BAL_VB_{ano}_{mes}")

                # capacidades máximas
                m.addConstr(self.V_VRFI[ano, mes] <= self.C_VRFI,   name=f"CAP_VRFI_{ano}_{mes}")
                m.addConstr(self.V_A[ano, mes]    <= self.C_TIPO_A, name=f"CAP_VA_{ano}_{mes}")
                m.addConstr(self.V_B[ano, mes]    <= self.C_TIPO_B, name=f"CAP_VB_{ano}_{mes}")

                # déficits
                m.addConstr(self.d_A[ano, mes] == demA - (self.Q_A[ano, mes] + self.Q_A_apoyo[ano, mes]),
                            name=f"DEF_A_{ano}_{mes}")
                m.addConstr(self.d_B[ano, mes] == demB - (self.Q_B[ano, mes] + self.Q_B_apoyo[ano, mes]),
                            name=f"DEF_B_{ano}_{mes}")

                # No sobre servir
                m.addConstr(self.Q_A[ano, mes] + self.Q_A_apoyo[ano, mes] <= demA, name=f"NOSOBRE_A_{ano}_{mes}")
                m.addConstr(self.Q_B[ano, mes] + self.Q_B_apoyo[ano, mes] <= demB, name=f"NOSOBRE_B_{ano}_{mes}")

                # Turbinado (sin SSR, con rebalses)
                m.addConstr(self.Q_turb[ano, mes] ==
                            (self.Q_A[ano, mes] + self.Q_A_apoyo[ano, mes]
                             + self.Q_B[ano, mes] + self.Q_B_apoyo[ano, mes]
                             + self.REBALSE_TOTAL[ano, mes]),
                            name=f"TURB_{ano}_{mes}")

    #  función objetivo
    def funcion_objetivo(self):
        total_def = gp.quicksum(self.d_A[a,m] + self.d_B[a,m] for a in self.anos for m in self.meses)
        self.model.setObjective(total_def, GRB.MINIMIZE)

    def exportar_a_excel(self, filename="resultados_embalse.xlsx"):
        data = []
        for ano in self.anos:
            y = int(ano.split('/')[0])
            for mes in self.meses:
                seg = self.segundos_por_mes[mes]
                Qin_m3s = self.caudal_afluente.get((y, mes), 0.0)
                Qin = Qin_m3s * seg / 1_000_000.0
                QPD_eff_Hm3 = self.QPD_eff[ano, mes] * seg / 1_000_000.0
                key = self.hidrologico_a_civil[mes]
                DemA = (self.demanda_A_mensual[key] * self.num_acciones_A * self.FEA) / 1_000_000.0
                DemB = (self.demanda_B_mensual[key] * self.num_acciones_B * self.FEB) / 1_000_000.0
                fila = {
                    'Ano': ano, 'Mes': mes,
                    'V_VRFI': self.V_VRFI[ano, mes].X, 'V_A': self.V_A[ano, mes].X, 'V_B': self.V_B[ano, mes].X,
                    'Q_dis': self.Q_dis[ano, mes].X, 'Q_CONSUMO_HUMANO': self.Q_CONSUMO_HUMANO[ano, mes].X,
                    'SSR_EXIGIDO': self.SSR_EXIGIDO[ano, mes].X, 'SSR_ACUMULADO': self.SSR_ACUMULADO[ano, mes].X,
                    'Q_A': self.Q_A[ano, mes].X, 'Q_B': self.Q_B[ano, mes].X, 'Q_turb': self.Q_turb[ano, mes].X,
                    'IN_VRFI': self.IN_VRFI[ano, mes].X, 'IN_A': self.IN_A[ano, mes].X, 'IN_B': self.IN_B[ano, mes].X,
                    'REBALSE_TOTAL': self.REBALSE_TOTAL[ano, mes].X,
                    'VRFI_DISPONIBLE_LIBRE': self.VRFI_DISPONIBLE_LIBRE[ano, mes].X,
                    'FALTANTE_A': self.FALTANTE_A[ano, mes].X, 'FALTANTE_B': self.FALTANTE_B[ano, mes].X, 'FALTANTE_TOTAL': self.FALTANTE_TOTAL[ano, mes].X,
                    'd_A': self.d_A[ano, mes].X, 'd_B': self.d_B[ano, mes].X,
                    'QPD_eff_Hm3': QPD_eff_Hm3,
                    'Demanda_A': DemA, 'Demanda_B': DemB,
                    'Q_afl_m3s': Qin_m3s, 'Q_afl_Hm3': Qin,
                    'Rem': self.Rem[ano, mes].X, 'LLENADO_VRFI': self.LLENADO_VRFI[ano, mes].X, 'REMANENTE_POST_VRFI': self.REMANENTE_POST_VRFI[ano, mes].X,
                    'CUOTA_A': self.CUOTA_A[ano, mes].X, 'CUOTA_B': self.CUOTA_B[ano, mes].X,
                    'LLENADO_A': self.LLENADO_A[ano, mes].X, 'LLENADO_B': self.LLENADO_B[ano, mes].X,
                    # diagnósticos extra
                    'REBALSE_ON': self.REBALSE_ON[ano, mes].X,
                    'VRFI_APOYO_CAP': self.VRFI_APOYO_CAP[ano, mes].X,
                }
                fila['Q_A_apoyo'] = self.Q_A_apoyo[ano, mes].X
                fila['Q_B_apoyo'] = self.Q_B_apoyo[ano, mes].X
                tot_dem = DemA + DemB
                servA = fila['Q_A'] + fila['Q_A_apoyo']
                servB = fila['Q_B'] + fila['Q_B_apoyo']
                fila['Deficit_Total'] = self.d_A[ano, mes].X + self.d_B[ano, mes].X
                fila['Satisfaccion_A'] = (servA / DemA * 100) if (DemA > 0) else 100
                fila['Satisfaccion_B'] = (servB / DemB * 100) if (DemB > 0) else 100
                fila['Satisfaccion_Total'] = ((servA + servB) / tot_dem * 100) if tot_dem > 0 else 100
                data.append(fila)

        df_principal = pd.DataFrame(data)

        resumen = []
        for ano in self.anos:
            d = df_principal[df_principal['Ano'] == ano]
            resumen.append({
                'Ano': ano,
                'Deficit_Total_Anual': d['Deficit_Total'].sum(),
                'Deficit_A_Anual': d['d_A'].sum(),
                'Deficit_B_Anual': d['d_B'].sum(),
                'Volumen_Turbinado_Anual': d['Q_turb'].sum(),
                'Demanda_Total_Anual': d['Demanda_A'].sum() + d['Demanda_B'].sum(),
                'Satisfaccion_Promedio': d['Satisfaccion_Total'].mean(),
                'Mes_Mayor_Deficit': (d.loc[d['Deficit_Total'].idxmax(), 'Mes'] if d['Deficit_Total'].max() > 0 else 'Ninguno')
            })
        df_resumen = pd.DataFrame(resumen)

        with pd.ExcelWriter(filename, engine='openpyxl') as w:
            df_principal.to_excel(w, sheet_name='Resultados_Detallados', index=False)
            df_resumen.to_excel(w, sheet_name='Resumen_Anual', index=False)

        print(f" Resultados exportados a {filename}")
        print(f"Deficit total: {df_principal['Deficit_Total'].sum():.2f} Hm³")
        print(f" Satisfaccion promedio: {df_principal['Satisfaccion_Total'].mean():.1f}%")

        return df_principal, df_resumen

    def exportar_a_txt(self, filename="reporte_embalse.txt"):
        def barra20(pct):
            n = int(round(min(max(pct, 0), 100) / 5.0))
            return "█" * n + "·" * (20 - n)

        mes_tag = {1:'may', 2:'jun', 3:'jul', 4:'ago', 5:'sep', 6:'oct',
                   7:'nov', 8:'dic', 9:'ene', 10:'feb', 11:'mar', 12:'abr'}

        lineas = []

        N_Y  = len(self.anos)
        N_M  = 12
        TOT_PM = N_Y * N_M

        Qturb_total_30y = 0.0
        rebalse_total_30y = 0.0
        qdis_total_30y  = 0.0
        serv_total_30y  = 0.0
        dem_total_30y   = 0.0

        rebalse_prom_mes = {m: 0.0 for m in self.meses}
        qdis_prom_mes    = {m: 0.0 for m in self.meses}
        satisf_por_mes   = {}

        for mes in self.meses:
            serv_sum = 0.0
            dem_sum  = 0.0
            key_civil = self.hidrologico_a_civil[mes]
            DemA_mes = (self.demanda_A_mensual[key_civil] * self.num_acciones_A * self.FEA) / 1_000_000.0
            DemB_mes = (self.demanda_B_mensual[key_civil] * self.num_acciones_B * self.FEB) / 1_000_000.0

            for ano in self.anos:
                Qturb_total_30y   += self.Q_turb[ano, mes].X
                rebalse_total_30y += self.REBALSE_TOTAL[ano, mes].X
                qdis_total_30y    += self.Q_dis[ano, mes].X
                servA = self.Q_A[ano, mes].X + self.Q_A_apoyo[ano, mes].X
                servB = self.Q_B[ano, mes].X + self.Q_B_apoyo[ano, mes].X
                serv_sum += (servA + servB)
                dem_sum  += (DemA_mes + DemB_mes)
                rebalse_prom_mes[mes] += self.REBALSE_TOTAL[ano, mes].X
                qdis_prom_mes[mes]    += self.Q_dis[ano, mes].X

            rebalse_prom_mes[mes] /= N_Y
            qdis_prom_mes[mes]    /= N_Y
            satisf_por_mes[mes]    = (100.0 * serv_sum / dem_sum) if dem_sum > 0 else 100.0
            serv_total_30y += serv_sum
            dem_total_30y  += dem_sum

        rebalse_prom_mensual_30y = rebalse_total_30y / TOT_PM
        qdis_prom_mensual_30y    = qdis_total_30y  / TOT_PM
        qdis_prom_total_30y      = qdis_total_30y  / TOT_PM
        satisf_global_30y        = (100.0 * serv_total_30y / dem_total_30y) if dem_total_30y > 0 else 100.0

        ultimo_ano = self.anos[-1]
        V_R_fin = self.V_VRFI[ultimo_ano, 12].X
        V_A_fin = self.V_A[ultimo_ano, 12].X
        V_B_fin = self.V_B[ultimo_ano, 12].X
        V_total_fin_30y = V_R_fin + V_A_fin + V_B_fin

        lineas.append("="*70)
        lineas.append("RESUMEN 30 ANOS — AGREGADOS")
        lineas.append("="*70)
        lineas.append(f"Volumen turbinado TOTAL (30 anos): {Qturb_total_30y:,.1f} Hm³")
        lineas.append(f"Rebalse TOTAL (30 anos): {rebalse_total_30y:,.1f} Hm³")
        lineas.append(f"Rebalse PROMEDIO mensual (30 anos): {rebalse_prom_mensual_30y:,.2f} Hm³/mes")
        lineas.append(f"Caudal disponible PROMEDIO mensual (30 anos): {qdis_prom_mensual_30y:,.2f} Hm³/mes")
        lineas.append(f"Caudal disponible PROMEDIO (30 anos): {qdis_prom_total_30y:,.2f} Hm³/mes")
        lineas.append(f"Satisfaccion ponderada PROMEDIO (30 anos): {satisf_global_30y:6.2f}%")
        lineas.append("")
        lineas.append("Promedios mensuales sobre 30 anos:")
        lineas.append("Mes   Rebalse prom [Hm³/mes]   Q_dis prom [Hm³/mes]   %Satisfaccion (ponderada)")
        lineas.append("-"*70)
        for mes in self.meses:
            lineas.append(f"{mes_tag[mes]:<4}  {rebalse_prom_mes[mes]:10.2f}                {qdis_prom_mes[mes]:10.2f}                {satisf_por_mes[mes]:6.2f}%")
        lineas.append("")
        lineas.append("Agua almacenada al final de los 30 anos (fin del ultimo periodo):")
        lineas.append(f"  VRFI: {V_R_fin:.1f} Hm³   A: {V_A_fin:.1f} Hm³   B: {V_B_fin:.1f} Hm³   TOTAL: {V_total_fin_30y:.1f} Hm³")
        lineas.append("")

        for ano in self.anos:
            y = int(ano.split('/')[0])
            lineas.append("="*37)
            lineas.append(f"REPORTE ANUAL: {ano}  (mes a mes)")
            lineas.append("="*37)
            lineas.append("Tabla 1 — Fisica del sistema (volumenes en Hm³; caudales en m³/s y Qin/QPD en Hm³/mes)")
            encabezado1 = ("Mes   Qin     Qin_m    QPD     QPD_m    IN_R     INA      INB      EB       "
                           "Motivo_EB        VRFI prev→fin         A prev→fin        B prev→fin        "
                           "VRFI %p→f     A %p→f      B %p→f      CHEQ    |  Stocks fin  ")
            lineas.append(encabezado1)
            lineas.append("-"*230)

            for i, mes in enumerate(self.meses):
                seg = self.segundos_por_mes[mes]
                Qin_m3s = self.caudal_afluente.get((y, mes), 0.0)
                Qin_Hm3 = Qin_m3s * seg / 1_000_000.0
                QPD_m3s = self.QPD_eff[ano, mes]
                QPD_Hm3 = QPD_m3s * seg / 1_000_000.0
                IN_R = self.IN_VRFI[ano, mes].X
                INA  = self.IN_A[ano, mes].X
                INB  = self.IN_B[ano, mes].X
                EB   = self.REBALSE_TOTAL[ano, mes].X

                if i == 0:
                    prev_ano = f"{y-1}/{y}"
                    V_R_prev = self.V_VRFI[prev_ano, 12].X if prev_ano in self.anos else self.VRFI_init
                    V_A_prev = self.V_A[prev_ano, 12].X    if prev_ano in self.anos else self.VA_init
                    V_B_prev = self.V_B[prev_ano, 12].X    if prev_ano in self.anos else self.VB_init
                else:
                    V_R_prev = self.V_VRFI[ano, mes-1].X
                    V_A_prev = self.V_A[ano, mes-1].X
                    V_B_prev = self.V_B[ano, mes-1].X

                V_R_fin_m = self.V_VRFI[ano, mes].X
                V_A_fin_m = self.V_A[ano, mes].X
                V_B_fin_m = self.V_B[ano, mes].X

                pct_R_prev = (V_R_prev / self.C_VRFI  * 100) if self.C_VRFI  > 0 else 0
                pct_R_fin  = (V_R_fin_m / self.C_VRFI * 100) if self.C_VRFI  > 0 else 0
                pct_A_prev = (V_A_prev / self.C_TIPO_A * 100) if self.C_TIPO_A > 0 else 0
                pct_A_fin  = (V_A_fin_m / self.C_TIPO_A * 100) if self.C_TIPO_A > 0 else 0
                pct_B_prev = (V_B_prev / self.C_TIPO_B * 100) if self.C_TIPO_B > 0 else 0
                pct_B_fin  = (V_B_fin_m / self.C_TIPO_B * 100) if self.C_TIPO_B > 0 else 0

                motivo  = "-"

                barR = barra20(pct_R_fin)
                barA = barra20(pct_A_fin)
                barB = barra20(pct_B_fin)

                fila1 = (f"{mes_tag[mes]:<4} "
                         f"{Qin_m3s:6.2f}  {Qin_Hm3:7.1f}  "
                         f"{QPD_m3s:6.2f}  {QPD_Hm3:7.1f}  "
                         f"{IN_R:7.1f}  {INA:7.1f}  {INB:7.1f}  {EB:7.1f}  "
                         f"{motivo:<24}  "
                         f"{V_R_prev:5.1f}→{V_R_fin_m:<5.1f}      "
                         f"{V_A_prev:5.1f}→{V_A_fin_m:<5.1f}    "
                         f"{V_B_prev:5.1f}→{V_B_fin_m:<5.1f}    "
                         f"{pct_R_prev:3.0f}→{pct_R_fin:<3.0f}%     "
                         f"{pct_A_prev:3.0f}→{pct_A_fin:<3.0f}%   "
                         f"{pct_B_prev:3.0f}→{pct_B_fin:<3.0f}%     "
                         f" |  VRFI[{V_R_fin_m:6.1f}] {barR}  "
                         f"A[{V_A_fin_m:6.1f}] {barA}  "
                         f"B[{V_B_fin_m:6.1f}] {barB}")
                lineas.append(fila1)

            lineas.append("")
            lineas.append("Tabla 2 — Servicio (Hm³/mes) + SSR (Hm³) + Qturb (Hm³)")
            encabezado2 = ("Mes   DemA*FE    ServA     dA      DemB*FE    ServB     dB      Q_SSR    "
                           "A_out    VRFI→A    B_out    VRFI→B   VRFI_avail  FALTANTE_TOTAL  APOYO_TOTAL   Qturb")
            lineas.append(encabezado2)
            lineas.append("-"*160)

            for i, mes in enumerate(self.meses):
                key = self.hidrologico_a_civil[mes]
                DemA = (self.demanda_A_mensual[key] * self.num_acciones_A * self.FEA) / 1_000_000.0
                DemB = (self.demanda_B_mensual[key] * self.num_acciones_B * self.FEB) / 1_000_000.0
                ServA = self.Q_A[ano, mes].X + self.Q_A_apoyo[ano, mes].X
                ServB = self.Q_B[ano, mes].X + self.Q_B_apoyo[ano, mes].X
                dA    = self.d_A[ano, mes].X
                dB    = self.d_B[ano, mes].X
                Q_SSR = self.Q_CONSUMO_HUMANO[ano, mes].X
                A_out = self.Q_A[ano, mes].X
                B_out = self.Q_B[ano, mes].X
                VA    = self.Q_A_apoyo[ano, mes].X
                VB    = self.Q_B_apoyo[ano, mes].X
                Qturb = self.Q_turb[ano, mes].X
                VRFIa = self.VRFI_DISPONIBLE_LIBRE[ano, mes].X
                needT = self.FALTANTE_TOTAL[ano, mes].X
                supT  = self.APOYO_TOTAL[ano, mes].X

                fila2 = (f"{mes_tag[mes]:<4} "
                         f"{DemA:8.1f}   {ServA:6.1f}   {dA:6.1f}   "
                         f"{DemB:8.1f}   {ServB:6.1f}   {dB:6.1f}   "
                         f"{Q_SSR:6.1f}   "
                         f"{A_out:6.1f}    {VA:6.1f}     {B_out:6.1f}    {VB:6.1f}   "
                         f"{VRFIa:8.1f}   {needT:7.1f}    {supT:9.1f}   "
                         f"{Qturb:6.1f}")
                lineas.append(fila2)

            lineas.append("")

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))
        print(f"Reporte TXT escrito en {filename}")
        return filename

        # === NUEVO: bloque de texto sólo con el resumen de un intervalo ya resuelto ===
    def _texto_resumen_intervalo(self, titulo_iter, anos_intervalo):
        """
        Devuelve un string con el bloque de texto compacto del intervalo:
        cabecera, KPIs del intervalo, tablas de promedios mensuales incluyendo
        el déficit por FE, y 'agua almacenada al final del intervalo'.
        Debe llamarse después de emb.solve() para que .X tenga valores.
        """
        assert set(anos_intervalo) == set(self.anos), \
            "Este Embalse debe haberse resuelto con exactamente este subrango de anos."

        mes_tag = {1:'may', 2:'jun', 3:'jul', 4:'ago', 5:'sep', 6:'oct',
                7:'nov', 8:'dic', 9:'ene', 10:'feb', 11:'mar', 12:'abr'}

        lineas = []
        lineas.append("="*78)
        lineas.append(titulo_iter)
        lineas.append("-"*78)
        lineas.append(f"FEA={self.FEA:.3f} | FEB={self.FEB:.3f}")
        lineas.append(f"VRFI0={self.VRFI_init:.2f} Hm³ | A0={self.VA_init:.2f} Hm³ | B0={self.VB_init:.2f} Hm³")
        lineas.append("="*78)

        # --- KPIs del intervalo ---
        N_Y = len(anos_intervalo)
        TOT_PM = N_Y * 12

        Qturb_total = 0.0
        rebalse_total = 0.0
        qdis_total = 0.0

        # Déficits
        deficit_modelo_total = 0.0  # ∑ d_A + d_B (lo que minimiza la FO)
        deficit_por_FE_total = 0.0  # ∑ [(1−FEA)*DemA_base + (1−FEB)*DemB_base] por mes y año

        serv_total = 0.0
        dem_total = 0.0  # demanda efectiva (con FE) para % satisfacción

        # Para tablas de promedios mensuales
        rebalse_prom_mes = {m: 0.0 for m in self.meses}
        qdis_prom_mes    = {m: 0.0 for m in self.meses}
        satisf_por_mes   = {}

        # Nuevas columnas: déficit promedio mensual desglosado
        d_modelo_prom_mes = {m: 0.0 for m in self.meses}
        d_FE_prom_mes     = {m: 0.0 for m in self.meses}
        d_total_prom_mes  = {m: 0.0 for m in self.meses}

        # Stocks fin de mes promedio
        vrfi_fin_prom = {m: 0.0 for m in self.meses}
        a_fin_prom    = {m: 0.0 for m in self.meses}
        b_fin_prom    = {m: 0.0 for m in self.meses}

        for mes in self.meses:
            serv_sum_mes = 0.0
            dem_sum_mes  = 0.0

            # Demanda BASE (sin FE) — para castigo FE
            key_civil = self.hidrologico_a_civil[mes]
            DemA_base_mes = (self.demanda_A_mensual[key_civil] * self.num_acciones_A) / 1_000_000.0
            DemB_base_mes = (self.demanda_B_mensual[key_civil] * self.num_acciones_B) / 1_000_000.0

            # Demanda efectiva (con FE) — para satisfacción
            DemA_eff_mes = DemA_base_mes * self.FEA
            DemB_eff_mes = DemB_base_mes * self.FEB

            # Déficit por FE de este mes (constante por año dentro de la tanda si FE es fijo)
            d_FE_mes = (1.0 - self.FEA) * DemA_base_mes + (1.0 - self.FEB) * DemB_base_mes

            for ano in anos_intervalo:
                # Agregados físicos
                Qturb_total += self.Q_turb[ano, mes].X
                rebalse_val  = self.REBALSE_TOTAL[ano, mes].X
                qdis_val     = self.Q_dis[ano, mes].X
                rebalse_total += rebalse_val
                qdis_total    += qdis_val

                # Déficit del modelo
                dA = self.d_A[ano, mes].X
                dB = self.d_B[ano, mes].X
                deficit_modelo_total += (dA + dB)
                d_modelo_prom_mes[mes] += (dA + dB)

                # Déficit por FE (se suma por cada año del intervalo)
                deficit_por_FE_total += d_FE_mes
                d_FE_prom_mes[mes] += d_FE_mes

                # Servicio y demanda efectiva (para % satisfacción)
                ServA = self.Q_A[ano, mes].X + self.Q_A_apoyo[ano, mes].X
                ServB = self.Q_B[ano, mes].X + self.Q_B_apoyo[ano, mes].X
                serv_sum_mes += (ServA + ServB)
                dem_sum_mes  += (DemA_eff_mes + DemB_eff_mes)

                # Promedios mensuales (acumular para luego dividir por N_Y)
                rebalse_prom_mes[mes] += rebalse_val
                qdis_prom_mes[mes]    += qdis_val
                vrfi_fin_prom[mes]    += self.V_VRFI[ano, mes].X
                a_fin_prom[mes]       += self.V_A[ano, mes].X
                b_fin_prom[mes]       += self.V_B[ano, mes].X

            # Promedios sobre N_Y años
            rebalse_prom_mes[mes] /= N_Y
            qdis_prom_mes[mes]    /= N_Y
            d_modelo_prom_mes[mes] /= N_Y
            d_FE_prom_mes[mes]     /= N_Y
            d_total_prom_mes[mes]   = d_modelo_prom_mes[mes] + d_FE_prom_mes[mes]
            vrfi_fin_prom[mes]     /= N_Y
            a_fin_prom[mes]        /= N_Y
            b_fin_prom[mes]        /= N_Y
            satisf_por_mes[mes]     = (100.0 * serv_sum_mes / dem_sum_mes) if dem_sum_mes > 0 else 100.0

            serv_total += serv_sum_mes
            dem_total  += dem_sum_mes

        qdis_prom_mensual_intervalo = qdis_total / TOT_PM
        satisf_global_intervalo = (100.0 * serv_total / dem_total) if dem_total > 0 else 100.0
        deficit_total_intervalo = deficit_modelo_total + deficit_por_FE_total

        # rango textual del intervalo
        rango_txt = f"{anos_intervalo[0]} \u2192 {anos_intervalo[-1]}"

        lineas.append("")
        lineas.append("="*70)
        lineas.append(f"RESUMEN DEL INTERVALO — {rango_txt}")
        lineas.append("="*70)
        lineas.append(f"Volumen turbinado TOTAL (intervalo): {Qturb_total:,.1f} Hm³")
        lineas.append(f"Rebalse TOTAL (intervalo): {rebalse_total:,.1f} Hm³")
        lineas.append(f"Déficit del MODELO (∑d_A+d_B): {deficit_modelo_total:,.1f} Hm³")
        lineas.append(f"Déficit por FE agregado: {deficit_por_FE_total:,.1f} Hm³")
        lineas.append(f"Déficit TOTAL (modelo + FE): {deficit_total_intervalo:,.1f} Hm³")
        lineas.append(f"Caudal disponible PROMEDIO mensual (intervalo): {qdis_prom_mensual_intervalo:,.2f} Hm³/mes")
        lineas.append(f"Satisfacción ponderada PROMEDIO (intervalo): {satisf_global_intervalo:6.2f}%")
        lineas.append("")

        # Tabla 1 — promedios mensuales
        lineas.append("Promedios mensuales sobre el intervalo:")
        lineas.append("Mes  Rebalse prom [Hm³/mes]  Q_dis prom [Hm³/mes]  %Satisfaccion (ponderada)")
        lineas.append("-"*70)
        for mes in self.meses:
            lineas.append(
                f"{mes_tag[mes]:<4} "
                f"{rebalse_prom_mes[mes]:10.2f} "
                f"{qdis_prom_mes[mes]:10.2f} "
                f"{satisf_por_mes[mes]:6.2f}%"
            )
        lineas.append("")

        # Tabla 2 — déficit (modelo/FE/total) y stocks fin de mes (promedios)
        lineas.append("Promedios mensuales — Déficit (modelo / FE / total) y Volumen almacenado al fin de mes")
        lineas.append("Mes  d_modelo [Hm³/mes]  d_FE [Hm³/mes]  d_total [Hm³/mes]  VRFI fin prom  A fin prom  B fin prom  TOTAL fin prom [Hm³]")
        lineas.append("-"*110)
        for mes in self.meses:
            total_fin = vrfi_fin_prom[mes] + a_fin_prom[mes] + b_fin_prom[mes]
            lineas.append(
                f"{mes_tag[mes]:<4} "
                f"{d_modelo_prom_mes[mes]:9.2f} "
                f"{d_FE_prom_mes[mes]:9.2f} "
                f"{d_total_prom_mes[mes]:9.2f} "
                f"{vrfi_fin_prom[mes]:12.2f} "
                f"{a_fin_prom[mes]:10.2f} "
                f"{b_fin_prom[mes]:10.2f} "
                f"{total_fin:16.2f}"
            )
        lineas.append("")

        # Agua almacenada al final del último mes del intervalo
        ultimo_ano = anos_intervalo[-1]
        V_R_fin = self.V_VRFI[ultimo_ano, 12].X
        V_A_fin = self.V_A[ultimo_ano, 12].X
        V_B_fin = self.V_B[ultimo_ano, 12].X
        total_fin = V_R_fin + V_A_fin + V_B_fin
        lineas.append(f"Agua almacenada al final del intervalo (fin del último periodo):")
        lineas.append(f"  VRFI: {V_R_fin:.1f} Hm³  A: {V_A_fin:.1f} Hm³  B: {V_B_fin:.1f} Hm³  TOTAL: {total_fin:.1f} Hm³")
        lineas.append("")

        return "\n".join(lineas)


    def solve(self):
        try:
            print("Iniciando optimización del Embalse Nueva Punilla...")
            data_file = "data/caudales.xlsx"
            self.caudal_afluente, self.Q_nuble, self.Q_hoya1, self.Q_hoya2, self.Q_hoya3 = self.cargar_data(data_file)
            self.variables()
            self.restricciones()
            self.funcion_objetivo()
            self.model.optimize()
            if self.model.status == GRB.INFEASIBLE:
                self.model.computeIIS()
                self.model.write("modelo.ilp")
                return None

            if self.model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
                return self.get_solution()
            print(f"Modelo no resuelto optimalmente. Status: {self.model.status}")
            return None
        except Exception as e:
            print(f"Error al resolver el modelo: {e}")
            return None

    def get_solution(self):
        sol = {'status': self.model.status, 'obj_val': self.model.objVal}
        df_det, df_res = self.exportar_a_excel()
        sol['df_detalle'] = df_det
        sol['df_resumen'] = df_res
        txt_file = self.exportar_a_txt()
        sol['txt_file'] = txt_file
        return sol


if __name__ == "__main__":
    # Definir los 30 años completos
    FULL_ANOS_30 = [
        '1989/1990','1990/1991','1991/1992','1992/1993','1993/1994',
        '1994/1995','1995/1996','1996/1997','1997/1998','1998/1999',
        '1999/2000','2000/2001','2001/2002','2002/2003','2003/2004',
        '2004/2005','2005/2006','2006/2007','2007/2008','2008/2009',
        '2009/2010','2010/2011','2011/2012','2012/2013','2013/2014',
        '2014/2015','2015/2016','2016/2017','2017/2018','2018/2019'
    ]

    emb = EmbalseNuevaPunilla()
    emb.anos = FULL_ANOS_30[:]
    emb.FEA = 1.0
    emb.FEB = 1.0
    emb.VRFI_init = 0.0
    emb.VA_init = 0.0
    emb.VB_init = 0.0

    sol = emb.solve()
    if sol is None:
        print("[ERROR] El modelo no se resolvió correctamente.")
    else:
        print("[OK] Solución obtenida.")
        resumen = emb._texto_resumen_intervalo("Caso general — 30 años completos", FULL_ANOS_30)
        with open("resumen_30y_FE1.txt", "w", encoding="utf-8") as f:
            f.write(resumen)
        print("[OK] Resumen guardado en resumen_30y_FE1.txt")
