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

        # = DEMANDAS (m³/mes por acción)  esto  es segun doc de regla operación, después las pasamos a  Hm³
        self.num_acciones_A  = 21221
        self.num_acciones_B  = 7100
        self.demanda_A_mensual = {1:9503,2:6516,3:3452,4:776,5:0,6:0,7:0,8:0,9:0,10:2444,11:6516,12:9580}
        self.demanda_B_mensual  = {1:3361,2:2305,3:1221,4:274,5:0,6:0,7:0,8:0,9:0,10: 864,11:2305,12:3388}

        # orden de  de meses hidrologicos (1..12=MAY..ABR)  mes normal (ene=1,...,dic=12)
        self.hidrologico_a_civil  = {1:5,2:6,3:7,4:8,5:9,6:10,7:11,8:12,9:1,10:2,11:3,12:4}

        #factores de entrega(supuesto, son 1 hasta ahora)
        self.FEA = 1.0
        self.FEB = 1.0

        # VOLUMEN CONSUMO HUMANO en Hm³/año
        self.V_C_H = 3.9
        
        #es el acumulado del servicio de riego hace que se acumule si no se puede entregar agua para consumo humano
        self.acumular_ssr = True  

        #  reserva VRFI minima del vrfi para meses de sequía en consumo humano
        self.RESERVA_MIN_VRFI  = 2.275

        # volumenes iniciales (si es que no hay año previo)
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

        # Diagnóstico de disponibles y “gap a 50%”
        self.DISPONIBLE_A = m.addVars(self.anos, self.meses, name="DISPONIBLE_A")
        self.DISPONIBLE_B = m.addVars(self.anos, self.meses, name="DISPONIBLE_B")
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

        # SSR, servicio sobre riego, 
        self.SSR_EXIGIDO            = m.addVars(self.anos, self.meses, name="SSR_EXIGIDO", lb=0.0)
        self.SSR_ACUMULADO          = m.addVars(self.anos, self.meses, name="SSR_ACUMULADO", lb=0.0)
        self.SSR_CAPACIDAD_VARIABLE = m.addVars(self.anos, self.meses, name="SSR_CAPACIDAD_VARIABLE", lb=0.0)

    # Datos
    def cargar_data(self, file_path):
        # sacamos la info de cada columna tal como sale el el excel del profe, 
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

        # acá se cargan  desde las tablas del  Excel
        (self.caudal_afluente,
        self.Q_nuble,
        self.Q_hoya1,
        self.Q_hoya2,
        self.Q_hoya3) = self.cargar_data(data_file)

        # Caudal QPD efectivo en m³/s según derechos/ecológico y límite por Nuble en  de orden MAY–ABR
        derechos_MAY_ABR = [52.00, 52.00, 52.00, 52.00, 57.70, 76.22, 69.22, 52.00, 52.00, 52.00, 52.00, 52.00]
        qeco_MAY_ABR     = [10.00, 10.35, 14.48, 15.23, 15.23, 15.23, 15.23, 15.23, 12.80, 15.20, 16.40, 17.60]

        self.QPD_eff = {}
        for ano in self.anos:
            y = int(ano.split('/')[0])
            for mes in self.meses:
                # H es sumatoria de aportes de hoyas que reducen el QPD nominal 95.7 - H
                H = (self.Q_hoya1.get((y, mes), 0.0)
                    + self.Q_hoya2.get((y, mes), 0.0)
                    + self.Q_hoya3.get((y, mes), 0.0))
                # qpd_nom = máximo entre derecho, ecológico y (95.7 - H) truncado en 0
                qpd_nom = max(derechos_MAY_ABR[mes-1], qeco_MAY_ABR[mes-1], max(0.0, 95.7 - H))
                # QPD efectivo limitado por el propio Nuble
                self.QPD_eff[ano, mes] = min(qpd_nom, self.Q_nuble.get((y, mes), 0.0))

        # SSR mensual (Hm³/mes) es el  volumen anual de consumo humano/12 
        ssr_mes = self.V_C_H / 12.0

        for a_idx, ano in enumerate(self.anos):
            y = int(ano.split('/')[0])
            for i, mes in enumerate(self.meses):
                seg   = self.segundos_por_mes[mes]
                Qin_s = self.caudal_afluente.get((y, mes), 0.0)               
                Qin   = Qin_s * seg / 1_000_000.0                             # lo pasamos Hm³/mes 
                UPREF = self.QPD_eff[ano, mes] * seg / 1_000_000.0            

                key_civil = self.hidrologico_a_civil[mes]
                demA = (self.demanda_A_mensual[key_civil] * self.num_acciones_A * self.FEA) / 1_000_000.0  # pasamos demanda A a Hm³/mes
                demB = (self.demanda_B_mensual[key_civil] * self.num_acciones_B * self.FEB) / 1_000_000.0  # pasamos demanda B a Hm³/mes

                # lo que se realiza aca son es realionar los volúmenes al cierre del periodo anterior (si es el primer mes del año,  se toman  los del año previo o los iniciales)
                if i == 0:
                    if a_idx > 0:
                        ano_prev = self.anos[a_idx - 1]
                        V_R_prev = self.V_VRFI[ano_prev, 12]   # VRFI cuando termina, es decir el abril del año anterior
                        V_A_prev = self.V_A[ano_prev, 12]      # lo mismo para A 
                        V_B_prev = self.V_B[ano_prev, 12]      # lo mismo para b
                    else:
                        V_R_prev = self.model.addVar(lb=self.VRFI_init, ub=self.VRFI_init, name="VRFI_prev_init") 
                        V_A_prev = self.model.addVar(lb=self.VA_init,   ub=self.VA_init,   name="VA_prev_init")    
                        V_B_prev = self.model.addVar(lb=self.VB_init,   ub=self.VB_init,   name="VB_prev_init")   
                else:
                    V_R_prev = self.V_VRFI[ano, mes-1]  
                    V_A_prev = self.V_A[ano,  mes-1]   
                    V_B_prev = self.V_B[ano,  mes-1]   

                
                #  REMANENTE después de QPD 
                m.addConstr(self.REMANENTE_BRUTO[ano, mes] == Qin - UPREF,
                            name=f"REMANENTE_BRUTO_{ano}_{mes}")  # Remanente bruto = Afluencia - QPD
                m.addGenConstrMax(self.Rem[ano, mes],
                                [self.REMANENTE_BRUTO[ano, mes], self.CERO_CONSTANTE],
                                name=f"REMANENTE_clip0_{ano}_{mes}")  # Rem = max(Remanente_bruto, 0) para que no sea negativo

                #  espacios de vol disponibles antes de llenar (capacidad - stock previo) 
                m.addConstr(self.ESPACIO_VRFI[ano, mes] == self.C_VRFI - V_R_prev,
                            name=f"ESPACIO_VRFI_{ano}_{mes}")  
                m.addConstr(self.ESPACIO_A[ano, mes] == self.C_TIPO_A - V_A_prev,
                            name=f"ESPACIO_A_{ano}_{mes}")    
                m.addConstr(self.ESPACIO_B[ano, mes] == self.C_TIPO_B -
                             V_B_prev,
                            name=f"ESPACIO_B_{ano}_{mes}")     
                # Acá se controla el llenado de cada división del embalse en función del agua disponible y su espacio libre.
                # Primero se calcula el remanente bruto (la afluencia menos el caudal previo) y se asegura que no sea negativo usando addGenConstrMax.
                # Luego, para cada uno, se determina cuánto espacio tiene disponible restando su capacidad total menos el volumen almacenado previamente.
                # Finalmente, usAmos restricciones de tipo min para definir el llenado efectivo, de modo que cada división del embalse sólo pueda recibir el menor valor entre su proporción de agua asignada y el espacio libre que tiene.
                
                m.addGenConstrMin(self.LLENADO_VRFI[ano, mes],
                                [self.Rem[ano, mes], self.ESPACIO_VRFI[ano, mes]],
                                name=f"LLENADO_VRFI_min_{ano}_{mes}") 
                m.addConstr(self.REMANENTE_POST_VRFI[ano, mes] == self.Rem[ano, mes] - self.LLENADO_VRFI[ano, mes],
                            name=f"REMANENTE_POST_VRFI_{ano}_{mes}") 
                m.addConstr(self.CUOTA_A[ano, mes] == 0.71 * self.REMANENTE_POST_VRFI[ano, mes],
                            name=f"CUOTA_A_{ano}_{mes}")  
                m.addConstr(self.CUOTA_B[ano, mes] == 0.29 * self.REMANENTE_POST_VRFI[ano, mes],
                            name=f"CUOTA_B_{ano}_{mes}")  
                m.addGenConstrMin(self.LLENADO_A[ano, mes],
                                [self.CUOTA_A[ano, mes], self.ESPACIO_A[ano, mes]],
                                name=f"LLENADO_A_min_{ano}_{mes}")  
                m.addGenConstrMin(self.LLENADO_B[ano, mes],
                                [self.CUOTA_B[ano, mes], self.ESPACIO_B[ano, mes]],
                                name=f"LLENADO_B_min_{ano}_{mes}")  

                
                m.addConstr(self.IN_VRFI[ano, mes] == self.LLENADO_VRFI[ano, mes],
                            name=f"IN_VRFI_{ano}_{mes}")  
                m.addConstr(self.IN_A[ano, mes]    == self.LLENADO_A[ano, mes],
                            name=f"IN_A_{ano}_{mes}")    
                m.addConstr(self.IN_B[ano, mes]    == self.LLENADO_B[ano, mes],
                            name=f"IN_B_{ano}_{mes}")   

                # Calculamos el rebalse total . Además, definimos la  variable de diagnóstico para representar el caudal disponible post-QPD, q nos ayuda para revisar la consistencia del modelo.
                m.addConstr(self.REBALSE_TOTAL[ano, mes] ==
                            self.Rem[ano, mes] - self.IN_VRFI[ano, mes] - self.IN_A[ano, mes] - self.IN_B[ano, mes],
                            name=f"REBALSE_TOTAL_{ano}_{mes}")

    
                m.addConstr(self.Q_dis[ano, mes] == Qin - UPREF, name=f"Q_DISPONIBLE_{ano}_{mes}")

                # SSR mensual con prioridad dura 
                # En cada mes se calcula la exigencia de SSR, que corresponde al consumo humano, priorizándolo por sobre el riego. Si el volumen disponible (V_R_prev + IN_VRFI)
                # no alcanza para cubrir la cuota mensual más el acumulado acumulado del año previo,
                # se paga lo mínimo entre lo exigido y la capacidad disponible, acumulando el déficit
                # como SSR_ACUMULADO. Luego se calcula la disponibilidad efectiva del VRFI para apoyar  a los embalses A y B, asegurando su reserva mínima.
                if i == 0:
                    
                    if self.acumular_ssr and a_idx > 0:
                        ano_prev = self.anos[a_idx - 1]
                        acumulado_prev = self.SSR_ACUMULADO[ano_prev, 12]
                    else:
                        acumulado_prev = self.model.addVar(lb=0.0, ub=0.0, name=f"SSR_ACUMULADO_prev0_{ano}")  
                else:
                    acumulado_prev = self.SSR_ACUMULADO[ano, mes - 1]

                m.addConstr(self.SSR_EXIGIDO[ano, mes] == ssr_mes + acumulado_prev,
                            name=f"SSR_EXIGIDO_{ano}_{mes}")  

                m.addConstr(self.SSR_CAPACIDAD_VARIABLE[ano, mes] == V_R_prev + self.IN_VRFI[ano, mes],
                            name=f"SSR_CAP_VAR_{ano}_{mes}")  

                m.addGenConstrMin(self.Q_CONSUMO_HUMANO[ano, mes],
                                [self.SSR_EXIGIDO[ano, mes], self.SSR_CAPACIDAD_VARIABLE[ano, mes]],
                                name=f"SSR_PAGO_MIN_{ano}_{mes}")  

                m.addConstr(self.SSR_ACUMULADO[ano, mes] == self.SSR_EXIGIDO[ano, mes] - self.Q_CONSUMO_HUMANO[ano, mes],
                            name=f"SSR_ACUMULADO_{ano}_{mes}") 
                
                #  VRFI disponible para apoyar A/B, protegiendo su reserva mínima
                # DISPONIBILIDAD_PRELIM_VRFI = V_R_prev + IN_VRFI - Q_CONSUMO_HUMANO - RESERVA_MIN_VRFI
                DISPONIBILIDAD_PRELIM_VRFI = m.addVar(lb=-GRB.INFINITY, name=f"DISPONIBILIDAD_PRELIM_VRFI_{ano}_{mes}")
                m.addConstr(DISPONIBILIDAD_PRELIM_VRFI ==
                            V_R_prev + self.IN_VRFI[ano, mes] - self.Q_CONSUMO_HUMANO[ano, mes] - self.RESERVA_MIN_VRFI,
                            name=f"DISPONIBILIDAD_PRELIM_VRFI_{ano}_{mes}")  
                m.addGenConstrMax(self.VRFI_DISPONIBLE_LIBRE[ano, mes],
                                [DISPONIBILIDAD_PRELIM_VRFI, self.CERO_CONSTANTE],
                                name=f"VRFI_DISP_LIBRE_MAX_{ano}_{mes}")  
                
                # Límite físico de extracción propia A/B en el mes,  no sacar más que stock disponible)
                m.addConstr(self.Q_A[ano, mes] <= V_A_prev + self.IN_A[ano, mes], name=f"DISP_A_{ano}_{mes}")  
                m.addConstr(self.Q_B[ano, mes] <= V_B_prev + self.IN_B[ano, mes], name=f"DISP_B_{ano}_{mes}") 

                # Variables de diagnóstico para ver disponibilidad propia de A y B
                m.addConstr(self.DISPONIBLE_A[ano, mes] == V_A_prev + self.IN_A[ano, mes],
                            name=f"DISPONIBLE_A_def_{ano}_{mes}")  
                m.addConstr(self.DISPONIBLE_B[ano, mes] == V_B_prev + self.IN_B[ano, mes],
                            name=f"DISPONIBLE_B_def_{ano}_{mes}")  

                # No sobre servir respecto de la demanda propia
                m.addConstr(self.Q_A[ano, mes] <= demA, name=f"A_le_Dem_{ano}_{mes}")  
                m.addConstr(self.Q_B[ano, mes] <= demB, name=f"B_le_Dem_{ano}_{mes}") 


                # --- PROPIO SIEMPRE PRIMERO: Q_A = min(disponible propio A, DemA); Q_B = min(disponible propio B, DemB)

                # “Constantes” de demanda como variables fijadas (evita IIS al usar MIN)
                DEM_A_CONST = m.addVar(lb=demA, ub=demA, name=f"DEM_A_CONST_{ano}_{mes}")
                DEM_B_CONST = m.addVar(lb=demB, ub=demB, name=f"DEM_B_CONST_{ano}_{mes}")

                # Auxiliares para el mínimo
                MIN_A_PROPIO = m.addVar(lb=0.0, name=f"MIN_A_PROPIO_{ano}_{mes}")
                MIN_B_PROPIO = m.addVar(lb=0.0, name=f"MIN_B_PROPIO_{ano}_{mes}")

                # Q_A = min(DISPONIBLE_A, DemA)
                m.addGenConstrMin(MIN_A_PROPIO, [self.DISPONIBLE_A[ano, mes], DEM_A_CONST],
                                name=f"MIN_A_PROPIO_min_{ano}_{mes}")
                m.addConstr(self.Q_A[ano, mes] == MIN_A_PROPIO, name=f"A_usa_todo_propio_{ano}_{mes}")

                # Q_B = min(DISPONIBLE_B, DemB)
                m.addGenConstrMin(MIN_B_PROPIO, [self.DISPONIBLE_B[ano, mes], DEM_B_CONST],
                                name=f"MIN_B_PROPIO_min_{ano}_{mes}")
                m.addConstr(self.Q_B[ano, mes] == MIN_B_PROPIO, name=f"B_usa_todo_propio_{ano}_{mes}")

                # === FALTANTE SOLO HASTA 50% (dispara y limita VRFI)
                m.addConstr(self.T_A[ano, mes] == 0.5 * demA - self.Q_A[ano, mes], name=f"T_A_gap50_{ano}_{mes}")
                m.addConstr(self.T_B[ano, mes] == 0.5 * demB - self.Q_B[ano, mes], name=f"T_B_gap50_{ano}_{mes}")

                m.addGenConstrMax(self.FALTANTE_A[ano, mes], [self.T_A[ano, mes], self.CERO_CONSTANTE],
                                name=f"FALT_A_pos_gap50_{ano}_{mes}")
                m.addGenConstrMax(self.FALTANTE_B[ano, mes], [self.T_B[ano, mes], self.CERO_CONSTANTE],
                                name=f"FALT_B_pos_gap50_{ano}_{mes}")

 
                
                # Apoyo VRFI total limitado por disponibilidad y necesidad total. se gestiona el apoyo del VRFI hacia l A y B. Primero, se calcula la necesidad total sumando los faltantes individuales de A y B, y luego se define el apoyo total disponible como el mínimo entre el volumen libre del VRFI y esta necesidad total.
                
                m.addConstr(self.FALTANTE_TOTAL[ano, mes] == self.FALTANTE_A[ano, mes] + self.FALTANTE_B[ano, mes],
                            name=f"FALT_TOTAL_{ano}_{mes}") 
                m.addGenConstrMin(self.APOYO_TOTAL[ano, mes],
                                [self.VRFI_DISPONIBLE_LIBRE[ano, mes], self.FALTANTE_TOTAL[ano, mes]],
                                name=f"APOYO_TOTAL_min_{ano}_{mes}")  

                # reparto 71/29 del apoyo VRFI , con reasignación de excedentes
                m.addConstr(self.PROPORCION_A[ano, mes] == 0.71 * self.APOYO_TOTAL[ano, mes],
                            name=f"PROP_A_{ano}_{mes}")  
                m.addConstr(self.PROPORCION_B[ano, mes] == 0.29 * self.APOYO_TOTAL[ano, mes],
                            name=f"PROP_B_{ano}_{mes}")  

                # Asignación base limitada por la necesidad individual
                m.addGenConstrMin(self.ASIGNACION_A_BASE[ano, mes],
                                [self.FALTANTE_A[ano, mes], self.PROPORCION_A[ano, mes]],
                                name=f"ASIG_A_BASE_min_{ano}_{mes}")  
                m.addGenConstrMin(self.ASIGNACION_B_BASE[ano, mes],
                                [self.FALTANTE_B[ano, mes], self.PROPORCION_B[ano, mes]],
                                name=f"ASIG_B_BASE_min_{ano}_{mes}") 

                # excedentes de la proporción que no se usaron por falta de necesidad
                m.addConstr(self.EXCEDENTE_A[ano, mes] == self.PROPORCION_A[ano, mes] - self.ASIGNACION_A_BASE[ano, mes],
                            name=f"EXC_A_{ano}_{mes}")  
                m.addConstr(self.EXCEDENTE_B[ano, mes] == self.PROPORCION_B[ano, mes] - self.ASIGNACION_B_BASE[ano, mes],
                            name=f"EXC_B_{ano}_{mes}")  
                m.addConstr(self.BRECHA_A[ano, mes] == self.FALTANTE_A[ano, mes] - self.ASIGNACION_A_BASE[ano, mes],
                            name=f"BRECHA_A_{ano}_{mes}")  
                m.addConstr(self.BRECHA_B[ano, mes] == self.FALTANTE_B[ano, mes] - self.ASIGNACION_B_BASE[ano, mes],
                            name=f"BRECHA_B_{ano}_{mes}") 

                # Reasignación cruzada, el excedente de A puede cubrir brecha de B y viceversa
                m.addGenConstrMin(self.EXTRA_HACIA_B[ano, mes],
                                [self.EXCEDENTE_A[ano, mes], self.BRECHA_B[ano, mes]],
                                name=f"EXTRA_B_min_{ano}_{mes}")  
                m.addGenConstrMin(self.EXTRA_HACIA_A[ano, mes],
                                [self.EXCEDENTE_B[ano, mes], self.BRECHA_A[ano, mes]],
                                name=f"EXTRA_A_min_{ano}_{mes}") 
                
                # Apoyos finales a A y B incluyendo reasignaciones
                m.addConstr(self.Q_A_apoyo[ano, mes] == self.ASIGNACION_A_BASE[ano, mes] + self.EXTRA_HACIA_A[ano, mes],
                            name=f"Q_A_APOYO_{ano}_{mes}")  
                m.addConstr(self.Q_B_apoyo[ano, mes] == self.ASIGNACION_B_BASE[ano, mes] + self.EXTRA_HACIA_B[ano, mes],
                            name=f"Q_B_APOYO_{ano}_{mes}")

                # no usar más VRFI para apoyo que lo disponible 
                m.addConstr(self.Q_A_apoyo[ano, mes] + self.Q_B_apoyo[ano, mes] <= self.VRFI_DISPONIBLE_LIBRE[ano, mes],
                            name=f"APOYO_SUMA_LE_VRFI_{ano}_{mes}")

                # Estas son balacnces de masa y volumen para cada división del embalse osea 
                # volumen inicial + entradas - salidas = volumen final basicamente.
                m.addConstr(self.V_VRFI[ano, mes] ==
                            V_R_prev + self.IN_VRFI[ano, mes]
                            - self.Q_CONSUMO_HUMANO[ano, mes]
                            - self.Q_A_apoyo[ano, mes] - self.Q_B_apoyo[ano, mes],
                            name=f"BAL_VRFI_{ano}_{mes}")  
                m.addConstr(self.V_A[ano, mes] == V_A_prev + self.IN_A[ano, mes] - self.Q_A[ano, mes],
                            name=f"BAL_VA_{ano}_{mes}")    
                m.addConstr(self.V_B[ano, mes] == V_B_prev + self.IN_B[ano, mes] - self.Q_B[ano, mes],
                            name=f"BAL_VB_{ano}_{mes}")    

                # Estas son para imponer limites fisicos de capacidad maxima para cada parte del embalse osea que nunca tenga mas del maximo y que si llega tenga que distribuir agua
                m.addConstr(self.V_VRFI[ano, mes] <= self.C_VRFI,   name=f"CAP_VRFI_{ano}_{mes}")  
                m.addConstr(self.V_A[ano, mes]    <= self.C_TIPO_A, name=f"CAP_VA_{ano}_{mes}")    
                m.addConstr(self.V_B[ano, mes]    <= self.C_TIPO_B, name=f"CAP_VB_{ano}_{mes}")    

                # Aca se revisan los deficits para cada parte del embalse y que se cumpla siempre que el deficit = Dem - (Propio + Apoyo)
                m.addConstr(self.d_A[ano, mes] == demA - (self.Q_A[ano, mes] + self.Q_A_apoyo[ano, mes]),
                            name=f"DEF_A_{ano}_{mes}")  
                
                m.addConstr(self.d_B[ano, mes] == demB - (self.Q_B[ano, mes] + self.Q_B_apoyo[ano, mes]),
                            name=f"DEF_B_{ano}_{mes}")  

                # No sobre servir
                m.addConstr(self.Q_A[ano, mes] + self.Q_A_apoyo[ano, mes] <= demA ,
                            name=f"NOSOBRE_A_{ano}_{mes}") 
                m.addConstr(self.Q_B[ano, mes] + self.Q_B_apoyo[ano, mes] <= demB ,
                            name=f"NOSOBRE_B_{ano}_{mes}")  

                #  Turbinado no incluye ssr pero sí incluye rebalses
                m.addConstr(self.Q_turb[ano, mes] ==
                            (self.Q_A[ano, mes] + self.Q_A_apoyo[ano, mes]
                            + self.Q_B[ano, mes] + self.Q_B_apoyo[ano, mes]
                            + self.REBALSE_TOTAL[ano, mes]),
                            name=f"TURB_{ano}_{mes}")  



    #  función objetivo
    def funcion_objetivo(self):
        # Parte variable (déficit interno vs demanda con FE)
        total_def_vars = gp.quicksum(self.d_A[a,m] + self.d_B[a,m] for a in self.anos for m in self.meses)

        # Término CONSTANTE: suma de extras por FE en todos los meses (demanda base, sin FE)
        extra_const = 0.0
        for ano in self.anos:
            for mes in self.meses:
                key = self.hidrologico_a_civil[mes]
                DemA_base = (self.demanda_A_mensual[key] * self.num_acciones_A) / 1_000_000.0
                DemB_base = (self.demanda_B_mensual[key] * self.num_acciones_B) / 1_000_000.0
                extra_const += (1.0 - self.FEA) * DemA_base + (1.0 - self.FEB) * DemB_base

        # Minimiza "déficit interno + extra por FE" (la extra es constante → no afecta la política óptima)
        self.model.setObjective(total_def_vars + extra_const, GRB.MINIMIZE)


        
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
                    'LLENADO_A': self.LLENADO_A[ano, mes].X, 'LLENADO_B': self.LLENADO_B[ano, mes].X
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


    def exportar_a_txt(self, filename=None):
        import os

        def barra20(pct):
            n = int(round(min(max(pct, 0), 100) / 5.0))
            return "█" * n + "·" * (20 - n)

        # === Carpetas destino ===
        BASE_DIR = "reportes_embalse"
        HIST_DIR = os.path.join(BASE_DIR, "historicos")
        os.makedirs(HIST_DIR, exist_ok=True)

        # ===== Nombre de archivo único por intervalo/FE si no se entrega uno =====
        if filename is None:
            ini = self.anos[0].replace('/', '-')
            fin = self.anos[-1].replace('/', '-')
            auto = f"reporte_embalse_{ini}__{fin}_FEA{self.FEA:.2f}_FEB{self.FEB:.2f}.txt"
            filename = os.path.join(HIST_DIR, auto)   # ⇐ históricos a /historicos
        else:
            looks_historic = filename.startswith("reporte_embalse_") and "__" in filename
            target_dir = HIST_DIR if looks_historic else BASE_DIR
            os.makedirs(target_dir, exist_ok=True)
            if not os.path.isabs(filename):
                filename = os.path.join(target_dir, filename)

        mes_tag = {1:'may', 2:'jun', 3:'jul', 4:'ago', 5:'sep', 6:'oct',
                7:'nov', 8:'dic', 9:'ene', 10:'feb', 11:'mar', 12:'abr'}

        lineas = []

        N_Y  = len(self.anos)
        N_M  = 12
        TOT_PM = N_Y * N_M

        Qturb_total = 0.0
        rebalse_total = 0.0
        qdis_total  = 0.0
        serv_total  = 0.0
        dem_total   = 0.0

        # Déficit del modelo (∑ d_A + d_B), déficit por FE, y total reportado
        deficit_modelo_total = 0.0
        deficit_por_FE_total = 0.0
        deficit_total_periodo = 0.0  # = modelo + FE

        rebalse_prom_mes = {m: 0.0 for m in self.meses}
        qdis_prom_mes    = {m: 0.0 for m in self.meses}
        satisf_por_mes   = {}

        # Promedios mensuales (modelo / FE / total)
        deficit_prom_mes_modelo = {m: 0.0 for m in self.meses}
        deficit_prom_mes_FE     = {m: 0.0 for m in self.meses}
        deficit_prom_mes_total  = {m: 0.0 for m in self.meses}

        # Volúmenes almacenados al fin de cada mes (promedio)
        Vfin_VRFI_prom_mes = {m: 0.0 for m in self.meses}
        Vfin_A_prom_mes    = {m: 0.0 for m in self.meses}
        Vfin_B_prom_mes    = {m: 0.0 for m in self.meses}
        Vfin_TOTAL_prom_mes= {m: 0.0 for m in self.meses}

        for mes in self.meses:
            serv_sum = 0.0
            dem_sum  = 0.0
            key_civil = self.hidrologico_a_civil[mes]

            # Demanda BASE (sin FE)
            DemA_base_mes = (self.demanda_A_mensual[key_civil] * self.num_acciones_A) / 1_000_000.0
            DemB_base_mes = (self.demanda_B_mensual[key_civil] * self.num_acciones_B) / 1_000_000.0

            # Demanda efectiva (con FE)
            DemA_eff_mes = DemA_base_mes * self.FEA
            DemB_eff_mes = DemB_base_mes * self.FEB

            for ano in self.anos:
                Qturb_total   += self.Q_turb[ano, mes].X
                rebalse_total += self.REBALSE_TOTAL[ano, mes].X
                qdis_total    += self.Q_dis[ano, mes].X

                servA = self.Q_A[ano, mes].X + self.Q_A_apoyo[ano, mes].X
                servB = self.Q_B[ano, mes].X + self.Q_B_apoyo[ano, mes].X
                serv_sum += (servA + servB)  # ← corregido aquí

                dem_sum  += (DemA_eff_mes + DemB_eff_mes)
                rebalse_prom_mes[mes] += self.REBALSE_TOTAL[ano, mes].X
                qdis_prom_mes[mes]    += self.Q_dis[ano, mes].X

                # Déficit del modelo
                dA = self.d_A[ano, mes].X
                dB = self.d_B[ano, mes].X
                deficit_modelo_total += (dA + dB)
                deficit_prom_mes_modelo[mes] += (dA + dB)

                # Déficit adicional por FE
                dA_FE = (1.0 - self.FEA) * DemA_base_mes
                dB_FE = (1.0 - self.FEB) * DemB_base_mes
                deficit_por_FE_total += (dA_FE + dB_FE)
                deficit_prom_mes_FE[mes] += (dA_FE + dB_FE)

                # Stocks fin de mes
                Vfin_VRFI_prom_mes[mes] += self.V_VRFI[ano, mes].X
                Vfin_A_prom_mes[mes]    += self.V_A[ano, mes].X
                Vfin_B_prom_mes[mes]    += self.V_B[ano, mes].X

            # Promedios sobre N_Y años
            rebalse_prom_mes[mes] /= N_Y
            qdis_prom_mes[mes]    /= N_Y
            satisf_por_mes[mes]    = (100.0 * serv_sum / dem_sum) if dem_sum > 0 else 100.0

            deficit_prom_mes_modelo[mes] /= N_Y
            deficit_prom_mes_FE[mes]     /= N_Y
            deficit_prom_mes_total[mes]   = deficit_prom_mes_modelo[mes] + deficit_prom_mes_FE[mes]

            Vfin_VRFI_prom_mes[mes] /= N_Y
            Vfin_A_prom_mes[mes]    /= N_Y
            Vfin_B_prom_mes[mes]    /= N_Y
            Vfin_TOTAL_prom_mes[mes] = Vfin_VRFI_prom_mes[mes] + Vfin_A_prom_mes[mes] + Vfin_B_prom_mes[mes]

            serv_total += serv_sum
            dem_total  += dem_sum

        # Totales
        qdis_prom_mensual = qdis_total / TOT_PM
        satisf_global     = (100.0 * serv_total / dem_total) if dem_total > 0 else 100.0

        ultimo_ano = self.anos[-1]
        V_R_fin = self.V_VRFI[ultimo_ano, 12].X
        V_A_fin = self.V_A[ultimo_ano, 12].X
        V_B_fin = self.V_B[ultimo_ano, 12].X
        V_total_fin = V_R_fin + V_A_fin + V_B_fin

        deficit_total_periodo = deficit_modelo_total + deficit_por_FE_total

        # ===== Encabezado resumen =====
        lineas.append("="*78)
        lineas.append(f"RESUMEN DEL INTERVALO — {self.anos[0]} → {self.anos[-1]}")
        lineas.append("="*78)
        lineas.append(f"FEA={self.FEA:.3f} | FEB={self.FEB:.3f}")
        lineas.append(f"Volumen turbinado TOTAL (intervalo): {Qturb_total:,.1f} Hm³")
        lineas.append(f"Rebalse TOTAL (intervalo): {rebalse_total:,.1f} Hm³")
        lineas.append(f"Déficit del MODELO (∑d_A+d_B): {deficit_modelo_total:,.1f} Hm³")
        lineas.append(f"Déficit por FE agregado: {deficit_por_FE_total:,.1f} Hm³")
        lineas.append(f"Déficit TOTAL reportado: {deficit_total_periodo:,.1f} Hm³")
        lineas.append(f"Caudal disponible PROMEDIO mensual: {qdis_prom_mensual:,.2f} Hm³/mes")
        lineas.append(f"Satisfacción ponderada PROMEDIO: {satisf_global:6.2f}%")
        lineas.append("")

        # ===== Promedios mensuales =====
        lineas.append("Promedios mensuales sobre el intervalo:")
        lineas.append("Mes   Rebalse prom [Hm³/mes]   Q_dis prom [Hm³/mes]   %Satisfaccion (ponderada)")
        lineas.append("-"*70)
        for mes in self.meses:
            lineas.append(f"{mes_tag[mes]:<4}  {rebalse_prom_mes[mes]:10.2f}                {qdis_prom_mes[mes]:10.2f}                {satisf_por_mes[mes]:6.2f}%")
        lineas.append("")

        # ===== Guardar reporte =====
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas))

        print("[RESUMEN]",
            f"{self.anos[0]}→{self.anos[-1]}",
            f"FEA={self.FEA:.2f} FEB={self.FEB:.2f} |",
            f"d_modelo={deficit_modelo_total:.2f} Hm3 | d_FE={deficit_por_FE_total:.2f} Hm3 |",
            f"d_total={deficit_total_periodo:.2f} Hm3 | Qturb={Qturb_total:.2f} Hm3 |",
            f"Rebalse={rebalse_total:.2f} Hm3 | Qdis_prom={qdis_prom_mensual:.2f} Hm3/mes |",
            f"Satisf_prom={satisf_global:.2f}%")

        print(f"Reporte TXT escrito en {filename}")
        return filename



        
        # === NUEVO: bloque de texto sólo con el resumen de un intervalo ya resuelto ===
    def _texto_resumen_intervalo(self, titulo_iter, anos_intervalo):
        """
        Devuelve un string con el bloque de texto compacto del intervalo:
        cabecera, KPIs del intervalo, tablas de promedios mensuales
        incluyendo el déficit por FE, y 'agua almacenada al final del intervalo'.
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
        deficit_modelo_total = 0.0    # ∑ d_A + d_B (lo que minimiza la FO)
        deficit_por_FE_total = 0.0    # ∑ [(1−FEA)*DemA_base + (1−FEB)*DemB_base] por mes y año
        serv_total = 0.0
        dem_total  = 0.0  # demanda efectiva (con FE) para % satisfacción

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
                Qturb_total   += self.Q_turb[ano, mes].X
                rebalse_val    = self.REBALSE_TOTAL[ano, mes].X
                qdis_val       = self.Q_dis[ano, mes].X
                rebalse_total += rebalse_val
                qdis_total    += qdis_val

                # Déficit del modelo
                dA = self.d_A[ano, mes].X
                dB = self.d_B[ano, mes].X
                deficit_modelo_total += (dA + dB)
                d_modelo_prom_mes[mes] += (dA + dB)

                # Déficit por FE (se suma por cada año del intervalo)
                deficit_por_FE_total += d_FE_mes
                d_FE_prom_mes[mes]   += d_FE_mes

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
        satisf_global_intervalo     = (100.0 * serv_total / dem_total) if dem_total > 0 else 100.0

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
        lineas.append("Mes   Rebalse prom [Hm³/mes]   Q_dis prom [Hm³/mes]   %Satisfaccion (ponderada)")
        lineas.append("-"*70)
        for mes in self.meses:
            lineas.append(
                f"{mes_tag[mes]:<4}  "
                f"{rebalse_prom_mes[mes]:10.2f}                "
                f"{qdis_prom_mes[mes]:10.2f}                "
                f"{satisf_por_mes[mes]:6.2f}%"
            )
        lineas.append("")

        # Tabla 2 — déficit (modelo/FE/total) y stocks fin de mes (promedios)
        lineas.append("Promedios mensuales — Déficit (modelo / FE / total) y Volumen almacenado al fin de mes")
        lineas.append("Mes   d_modelo [Hm³/mes]   d_FE [Hm³/mes]   d_total [Hm³/mes]   VRFI fin prom   A fin prom   B fin prom   TOTAL fin prom [Hm³]")
        lineas.append("-"*110)
        for mes in self.meses:
            total_fin = vrfi_fin_prom[mes] + a_fin_prom[mes] + b_fin_prom[mes]
            lineas.append(
                f"{mes_tag[mes]:<4}  "
                f"{d_modelo_prom_mes[mes]:9.2f}           "
                f"{d_FE_prom_mes[mes]:9.2f}      "
                f"{d_total_prom_mes[mes]:9.2f}        "
                f"{vrfi_fin_prom[mes]:12.2f}   "
                f"{a_fin_prom[mes]:10.2f}   "
                f"{b_fin_prom[mes]:10.2f}   "
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
        lineas.append(f"  VRFI: {V_R_fin:.1f} Hm³   A: {V_A_fin:.1f} Hm³   B: {V_B_fin:.1f} Hm³   TOTAL: {total_fin:.1f} Hm³")
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
                # Dump detallado del IIS para ver nombres
                self.model.write("modelo_IIS.ilp")   # versión IIS (muy útil)
                self.model.write("modelo_IIS.lp")    # legible a ojo

                # También imprime en consola los elementos marcados en el IIS
                print("=== IIS: restricciones lineales ===")
                for c in self.model.getConstrs():
                    if c.IISConstr:
                        print(c.ConstrName)

                print("=== IIS: variables con bounds en conflicto ===")
                for v in self.model.getVars():
                    if v.IISLB:
                        print(f"LB en conflicto: {v.VarName}, LB={v.LB}")
                    if v.IISUB:
                        print(f"UB en conflicto: {v.VarName}, UB={v.UB}")

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
            
# === NUEVO: utilidades para dividir en bloques e imprimir resúmenes compactos ===

FULL_ANOS_30 = ['1989/1990','1990/1991','1991/1992','1992/1993','1993/1994',
                '1994/1995','1995/1996','1996/1997','1997/1998','1998/1999',
                '1999/2000','2000/2001','2001/2002','2002/2003','2003/2004',
                '2004/2005','2005/2006','2006/2007','2007/2008','2008/2009',
                '2009/2010','2010/2011','2011/2012','2012/2013','2013/2014',
                '2014/2015','2015/2016','2016/2017','2017/2018','2018/2019']

def _split_in_equal_blocks(seq, block_len):
    assert len(seq) % block_len == 0, "30 años debe ser múltiplo del bloque solicitado."
    return [seq[i:i+block_len] for i in range(0, len(seq), block_len)]

def run_sensitivity_brief_fixed_inits(
    period_years: int,
    FEA: float = 1.0,
    FEB: float = 1.0,
    VRFI_init: float = 0.0,
    VA_init: float = 0.0,
    VB_init: float = 0.0,
    basename: str = None
):
    """
    Corre intervalos de 'period_years' y genera UN archivo con SOLO el resumen
    (la sección que pegaste de ejemplo) concatenando cada intervalo.
    Usa siempre los mismos FEA/FEB y volúmenes iniciales en cada iteración
    (se resetean en cada bloque).
    """
    assert period_years in (5, 10, 15), "Solo periodos de 5, 10 o 15 años."
    blocks = _split_in_equal_blocks(FULL_ANOS_30, period_years)

    if basename is None:
        basename = f"resumen_{period_years}y_FEA{FEA:.2f}_FEB{FEB:.2f}_V{VRFI_init:.1f}-{VA_init:.1f}-{VB_init:.1f}.txt"

    out_lines = []
    out_lines.append("="*78)
    out_lines.append(f"RESÚMENES COMPACTOS — INTERVALOS DE {period_years} AÑOS")
    out_lines.append("="*78)
    out_lines.append(f"Factores fijos: FEA={FEA:.3f} | FEB={FEB:.3f}")
    out_lines.append(f"Volúmenes iniciales fijos: VRFI={VRFI_init:.2f} Hm³ | A={VA_init:.2f} Hm³ | B={VB_init:.2f} Hm³")
    out_lines.append("")

    for k, anos_k in enumerate(blocks, start=1):
        # Instancia limpia por intervalo
        emb = EmbalseNuevaPunilla()
        emb.anos = anos_k[:]    # limitar al subrango
        emb.FEA  = FEA
        emb.FEB  = FEB
        emb.VRFI_init = VRFI_init
        emb.VA_init   = VA_init
        emb.VB_init   = VB_init

        # Resolver
        sol = emb.solve()
        if sol is None or sol.get('status', None) not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
            out_lines.append(f"[Iteración {k}] **No se obtuvo solución óptima/subóptima en {anos_k[0]}→{anos_k[-1]}**")
            out_lines.append("")
            continue

        titulo = f"ITERACIÓN {k} — Intervalo {anos_k[0]} → {anos_k[-1]}"
        out_lines.append(emb._texto_resumen_intervalo(titulo, anos_k))
        out_lines.append("")

    with open(basename, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines))

    print(f"Archivo de resúmenes escrito en: {basename}")
    return basename

def run_sensitivity_brief_suite(
    FEA: float = 1.0,
    FEB: float = 1.0,
    VRFI_init: float = 0.0,
    VA_init: float = 0.0,
    VB_init: float = 0.0
):
    """
    Ejecuta y genera tres archivos:
      - 6 intervalos de 5 años  -> resumen_5y_*.txt
      - 3 intervalos de 10 años -> resumen_10y_*.txt
      - 2 intervalos de 15 años -> resumen_15y_*.txt
    """
    f5  = run_sensitivity_brief_fixed_inits(5,  FEA, FEB, VRFI_init, VA_init, VB_init)
    f10 = run_sensitivity_brief_fixed_inits(10, FEA, FEB, VRFI_init, VA_init, VB_init)
    f15 = run_sensitivity_brief_fixed_inits(15, FEA, FEB, VRFI_init, VA_init, VB_init)
    return {"5y": f5, "10y": f10, "15y": f15}


if __name__ == "__main__":
    # Ajusta FEA/FEB o volúmenes iniciales si quieres
    run_sensitivity_brief_suite(
        FEA=0.9, FEB=0.9,
        VRFI_init=0.0, VA_init=0.0, VB_init=0.0
    )

    # Si quieres solo una familia (por ejemplo, 6 de 5 años):
    # run_sensitivity_brief_fixed_inits(5, FEA=1.0, FEB=1.0, VRFI_init=0.0, VA_init=0.0, VB_init=0.0)
