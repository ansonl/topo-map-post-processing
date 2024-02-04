# MFPP Configuration

## Feature Options

The options file is formatted as a JSON dictionary with the following keys. Options values are provided for each [3D printable map model](https://ansonliu.com/maps/) on the [specifications page](https://ansonliu.com/maps/specifications/).

Filament/color positions are 0-based. The first position is represented by 0. The recommended filament order is:

| Physical Position (left to right) → | 1 | 2 | 3 | 4 |
| -------- | ------- | ------- | ------- | ------ |
| 0-based index in options | `0` | `1` | `2` | `3` |
| **Purpose** | Primary (base) | Secondary (hydro) | *Isoline* | *Elevation Color Change* |

### Required Options

| Key | Value | Cardinality | Description |
| -------- | ------- | ------- | ------- |
| `modelToRealWorldDefaultUnits` | *(model-units:real-world-units)* | 1 | Model units to Real World units scale. **Model Gcode units usually default to millimeters.** Use one of the two below computed values. |
| `modelToRealWorldDefaultUnits` (millimeters:meters)  | 1000 | 1 | Use `1000` if you specify real world units in meters. |
| `modelToRealWorldDefaultUnits` (millimeters:feet)  | 304.8 | 1 | Use `304.8` if you specify real world units in feet. |
| `modelOneToNVerticalScale` | *(real-world-scale:model-scale)* | 1 | Model to Real World scale *(E.g. 1:500000 = 0.1mm:50m)* |
| `modelSeaLevelBaseThickness` |  | 1 | The model height at sea level (0 m) in model units. This is used as zero elevation for the isoline and elevation color change. *(E.g. 1.8 = 1.8mm)*|

For

### Isoline Options

| Key | Value | Cardinality | Description |
| -------- | ------- | ------- | ------- |
| `realWorldIsolineElevationInterval` | | 1 | Isoline elevation interval in real world units. |
| `realWorldIsolineElevationStart` | | 1 | Isoline starting elevation in real world units. |
| `realWorldIsolineElevationEnd` | | 1 | Isoline ending elevation in real world units. |
| `modelIsolineHeight` | | 1 | Isoline display height in model units. |
| `isolineColorIndex` | | 1 | Isoline filament/color loaded position. Recommended index is 2 (third slot). |
| `realWorldElevationReplacementColorStart` | | 1 | Elevation based replacement color start elevation in real world units. |
| `realWorldElevationReplacementColorEnd` | | 1 | Elevation based replacement color end elevation in real world units. |
| `replacementColorIndex` | | 1 | Elevation based replacement color filament/color loaded position. Recommended index is 3 (fourth slot). |
| `replacementOriginalColorIndex` | | 1 | Elevation based replacement color **replaced** filament/color loaded position. Recommended index is 0 (first slot). |
| `isolineFeatures` | [string] | ≥0 | List of printing object feature types to color at isoline elevations.  |

### Elevation Change Options

| Key | Value | Cardinality | Description |
| -------- | ------- | ------- | ------- |
| `realWorldElevationReplacementColorStart` | | 1 | Elevation based replacement color start elevation in real world units. |
| `realWorldElevationReplacementColorEnd` | | 1 | Elevation based replacement color end elevation in real world units. |
| `replacementColorIndex` | | 1 | Elevation based replacement color filament/color loaded position. Recommended index is 3 (fourth slot). |
| `replacementOriginalColorIndex` | | 1 | Elevation based replacement color **replaced** filament/color loaded position. Recommended index is 0 (first slot). |

### Example Options file with Isoline and Elevation Change features

```json
{
  "modelToRealWorldDefaultUnits": 1000,
  "modelOneToNVerticalScale": 500000,
  "modelSeaLevelBaseThickness": 0.1,
  "realWorldIsolineElevationInterval": 500,
  "realWorldIsolineElevationStart": 200,
  "realWorldIsolineElevationEnd": 5000,
  "modelIsolineHeight": 0.5,
  "isolineColorIndex": 2,
  "realWorldElevationReplacementColorStart": 3650,
  "realWorldElevationReplacementColorEnd": 100000,
  "replacementColorIndex": 3,
  "replacementOriginalColorIndex": 0
}
```