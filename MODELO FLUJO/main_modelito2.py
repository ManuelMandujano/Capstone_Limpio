# main.py
from model.modelito2 import EmbalseNuevaPunilla

def main():
    embalse_model = EmbalseNuevaPunilla()
    solucion = embalse_model.solve()
    if solucion:
        print("✓ Modelo resuelto exitosamente")
        print(f"Valor objetivo (déficit total): {solucion['obj_val']:.2f} Hm³")
        print(f"Status del solver: {solucion['status']}")
        if solucion['obj_val'] == 0:
            print("✓ No hay déficit de riego")
        else:
            print(f" Existe un déficit total de {solucion['obj_val']:.2f} Hm³")
            
        df_resumen = solucion['df_resumen']
        print("\n RESUMEN ANUAL:")
        for _, row in df_resumen.iterrows():
            print(f"  {row['Año']}: Déficit {row['Deficit_Total_Anual']:.1f} Hm³ - Satisfacción {row['Satisfaccion_Promedio']:.1f}%")
            
    else:
        print(" Error al resolver el modelo")

if __name__ == "__main__":
    main()
