# GeometryDumper

A CMSSW `EDAnalyzer` designed to extract the exact spatial coordinates (translations) and orientation matrices (rotations) of every CMS Tracker sensor directly from the `TrackerGeometry` C++ objects. 

This tool is primarily built to generate ideal, zero-state geometry CSV files.

## Prerequisites

- A working CMSSW environment (tested on Phase-2 `CMSSW_16_1_X` releases).
- Standard CMS software dependencies (`scram`, `cmsRun`).

## Installation

Compile the plugin with:

``` bash
cd $CMSSW_BASE/src
scram b -j $(nproc)
```

And you are good to go!

## Usage

The execution is handled by a dynamic Python configuration file (`dumpGeom_cfg.py`). It lets you specify the target geometry scenario directly from the command line, and it automatically looks up the correct Tracker version from the CMSSW detector version dictionary to name the output file.

1. Place `dumpGeom_cfg.py` in your working directory.

2. Run the configuration file via `cmsRun`, passing your desired geometry scenario as an argument:

    ```bash
    cmsRun dumpGeom_cfg.py geometry=D112
    ```

3. The script will successfully dump a CSV file into your current directory named automatically based on the geometry (e.g., `Run4D112_T37.csv`).

The generated CSV contains the following headers, designed to be easily ingested by pandas: `DetId,Subdetector,X,Y,Z,RotXX,RotXY,RotXZ,RotYX,RotYY,RotYZ,RotZX,RotZY,RotZZ`

* `DetId`: The unique identifier for each detector element.
* `Subdetector`: The subdetector type according to `GeometricDet::GDEnumType`.
* `X, Y, Z`: The global position coordinates of the detector element.
* `RotXX, RotXY, ..., RotZZ`: The components of the 3x3 rotation matrix representing the detector element's orientation in global coordinates, that is:

$$
\begin{bmatrix}
Rot_{XX} & Rot_{XY} & Rot_{XZ} \\
Rot_{YX} & Rot_{YY} & Rot_{YZ} \\
Rot_{ZX} & Rot_{ZY} & Rot_{ZZ}
\end{bmatrix}
=
\begin{bmatrix}
| & | & | \\
x_{\text{local}} & y_{\text{local}} & z_{\text{local}} \\
| & | & | \\
\end{bmatrix}$$