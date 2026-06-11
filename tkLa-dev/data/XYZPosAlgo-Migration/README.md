# XYZPosAlgo-Migration Data Validation

This directory contains the geometry validation data used during the `XYZPosAlgo` migration phase in `tkLayout`. It provides a direct comparison between the standalone tracker layout software output and the full CMSSW framework zero-state geometry dump.

## Directory Structure

```text
XYZPosAlgo-Migration/
├── CMSSW/
│   ├── Run4D112_T37.csv   # dumpGeom_cfg.py output for configuration D112 (T37)
│   ├── Run4D126_T40.csv   # dumpGeom_cfg.py output for configuration D126 (T40)
│   └── Run4D127_T41.csv   # dumpGeom_cfg.py output for configuration D127 (T41)
└── tkLa/
    ├── tkLa_T37.csv       # tkLayout output for configuration OT v8.0.6 IT v7.4.2 (T37)
    ├── tkLa_T40.csv       # tkLayout output for configuration OT v8.0.6 IT v7.4.4 (T40)
    └── tkLa_T41.csv       # tkLayout output for configuration OT v8.0.7 IT v7.4.4 (T41)
```

## Data Sources

* **`tkLa/`**: Contains the raw CSV outputs from **tkLayout** generated during the initial `DetId` building phase.
* **`CMSSW/`**: Contains the reference tracker geometry extracted via the `tkLa-dev/GeometryDumper` package using the `dumpGeom_cfg.py` configuration.

## File Schema & Columns Reference

Every CSV file in this directory adheres to a standardized coordinate mapping structure. Use these columns to cross-reference sensor positions and orientations between the two frameworks.

### Global Positions & Rotation Matrix

Each detector element (sensor module) is defined by its absolute global position vector and a 3x3 orientation matrix that maps local module coordinates to global CMS space:

$$\text{Global Position} = \begin{pmatrix} X \\ Y \\ Z \end{pmatrix}$$

$$\text{Orientation Matrix} = \begin{pmatrix} 
\text{RotXX} & \text{RotXY} & \text{RotXZ} \\ 
\text{RotYX} & \text{RotYY} & \text{RotYZ} \\ 
\text{RotZX} & \text{RotZY} & \text{RotZZ} 
\end{pmatrix}$$

### Column Descriptions

| Column Name | Data Type | Description |
| --- | --- | --- |
| **`DetId`** | `Integer` | The unique 32-bit identifier for each specific detector element. **Use this as the primary key to join `tkLa` and `CMSSW` files.** |
| **`Subdetector`** | `Integer` | The subdetector type classifications mapped according to the `GeometricDet::GDEnumType` convention (e.g., PixelBarrel, Phase2OTBarrel). |
| **`X`** | `Float` | Global X position coordinate of the detector element center (cm). |
| **`Y`** | `Float` | Global Y position coordinate of the detector element center (cm). |
| **`Z`** | `Float` | Global Z position coordinate of the detector element center (cm). |
| **`RotXX` ... `RotZZ**`** | `Float` | Components of the 3x3 global rotation matrix defining local-to-global transformation. |

## Quick Start Validation

To validate matching tracking scenarios (e.g., Scenario **T37**), read both datasets into a validation script and join them on the unique tracker identifier:

```python
import pandas as pd

# Load corresponding layouts
df_tkLa = pd.read_csv("tkLa/tkLa_T37.csv")
df_cmssw = pd.read_csv("CMSSW/Run4D112_T37.csv")

# Merge on unique DetId anchor
validation_df = pd.merge(df_tkLa, df_cmssw, on="DetId", suffixes=("_tkLa", "_cmssw"))

# Calculate delta residuals
validation_df["delta_X"] = validation_df["X_tkLa"] - validation_df["X_cmssw"]
print(validation_df[["DetId", "delta_X"]].head())
```