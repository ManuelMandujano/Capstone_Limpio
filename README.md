````markdown
# Estructura del Proyecto

El proyecto se organiza de la siguiente manera:

```
Capstone_Limpio/
├── README.md                          # Documentación principal
└── MODELO FLUJO/                      # Carpeta principal del proyecto
    ├── caso_base.py                   # Modelo del caso base
    ├── main_modelito2.py              # Script principal (MILP)
    ├── monte_carlo.py                 # Simulaciones Monte Carlo
    ├── config/
    │   └── config.yaml                # Parámetros de configuración
    ├── data/                          # Datos de entrada
    │   └── caudales.xlsx              # Datos de caudales (flujos)
    ├── model/
    │   └── modelito2.py               # Módulos auxiliares del modelo
    ├── resultados_caso_base.xlsx      # Resultados exportados (caso base)
    ├── resultados_embalse.xlsx        # Resultados exportados (embalse)
    ├── reporte_caso_base.txt          # Reportes en texto
    └── reporte_embalse.txt            # Reportes en texto
```

### Descripción de carpetas

- **`config/`** — Parámetros y configuración del modelo
  - `config.yaml` — Archivo con parámetros globales (constantes, rutas, etc.)

- **`data/`** — Datos de entrada
  - `caudales.xlsx` — Series históricas de caudales/flujos utilizadas por el modelo

- **`model/`** — Módulos reutilizables del modelo
  - `modelito2.py` — Funciones y clases auxiliares del modelo de optimización


# Instrucciones de ejecución

> **Requisitos previos**
> - Tener una licencia activa de **Gurobi** instalada y configurada. y Tener **pandas** y **numpy** 

## Ejecución de los modelos

- **Caso Base:**  
  ```bash
  python caso_base.py
- **Modelo MIlP:**  
  ```bash
   python main_modelito2.py

- **Simulación Monte Carlo:**  
  ```bash
   python monte_carlo.py
  