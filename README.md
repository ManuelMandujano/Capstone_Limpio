
**Requisitos previos**
- Tener una licencia activa de **Gurobi** instalada y configurada.
- Tener **pandas** y **numpy**

## Ejecución de los modelos
- **Caso Base:**
```bash
python caso_base.py
````

* **Modelo MIlP:**

```bash
python main_modelito2.py
```

* **Simulación Monte Carlo:**

```bash
python monte_carlo.py
```

**Adicionales**
Se utilizó la extensión de VSCode Copilot. A continuación se describen sus aportes concretos para el proyecto:

* Nos entregó sugerencias de código y autocompletado ya que proporcionó autocompletado contextual para funciones, bucles y estructuras de control.
* Como también sugerencias para iterar sobre variables y construir restricciones.
* Corrección de errores sintácticos y tipográficos.
* Por último, también sirvió con sugerencias para extraer bloques repetidos a funciones auxiliares, reducir duplicación y mejorar la trazabilidad del flujo de datos.

El proyecto se organiza de la siguiente manera:

```
Capstone_Limpio/
├── README.md                          # Documentación principal
└── MODELO FLUJO/                      # Carpeta principal del proyecto
    ├── caso_base.py                   # Modelo del caso base
    ├── main_modelito2.py              # Script para correr Modelo principal 
    ├── monte_carlo.py                 # Simulaciones Monte Carlo
    ├── config/
    │   └── config.yaml                # Parámetros de configuración
    ├── data/                          # Datos de entrada
    │   └── caudales.xlsx              
    ├── model/
    │   └── modelito2.py               # nuestro Modelo completo
    ├── resultados_caso_base.xlsx      # Resultados generados al correr el Caso Base en xlsx
    ├── resultados_embalse.xlsx        # Resultados generados al correr el Modelo en xlsx
    ├── reporte_caso_base.txt          # Reportes en texto del Caso Base en xlsx
    └── reporte_embalse.txt            # Reportes en texto del  Modelo
```
