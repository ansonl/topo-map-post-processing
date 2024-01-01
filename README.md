# 3D Map Feature Gcode Post Processing

Add [isolines (contour lines/elevation lines)](https://en.wikipedia.org/wiki/Contour_line) and colored [elevation ranges](https://desktop.arcgis.com/en/arcmap/latest/map/styles-and-symbols/working-with-color-ramps.htm) to [3D printable map models](https://ansonliu.com/maps/).

This app adds additional features to the model by post processing sliced [3D printer G-code](https://marlinfw.org/meta/gcode/).

Only one isoline interval and colored elevation range is supported but the implementation can support more. If you find this tool helpful, please leave feedback and consider supporting my development and 3D modeling through my [Printables](https://www.printables.com/@ansonl) "club membership" or [Paypal](https://paypal.me/0x80).

## Current G-code flavors supported

- Marlin 2 (sliced from Bambu Studio) for Bambu printers

If you would like support for your printer G-code flavor to be added, please open an issue and your printer can be used for testing.

## Feature Options

The options file is formatted as a JSON dictionary with the following keys. Options values are provided for each [3D printable map model](https://ansonliu.com/maps/) on the [specifications page](https://ansonliu.com/maps/specifications/).

Filament/color positions are 0-based. The first position is represented by 0. The recommended filament order is:

| Physical Position → | 1 | 2 | 3 | 4 |
| -------- | ------- | ------- | ------- | ------ |
| 0-based index in options | 0 | 1 | 2 | 3 |
| **Purpose** | Primary (base) | Secondary (hydro) | *Isoline* | *Elevation Color Change* |

### Required Options

| Key | Value | Cardinality | Description |
| -------- | ------- | ------- | ------- |
| `modelToRealWorldDefaultUnits` | *(model-units:real-world-units)* | 1 | Model units to Real World units scale. **Model Gcode units usually default to millimeters.** Use one of the two below computed values. |
| `modelToRealWorldDefaultUnits` (millimeters:meters)  | 1000 | 1 | Use this if you specify real world units in meters. |
| `modelToRealWorldDefaultUnits` (millimeters:feet)  | 304.8 | 1 | Use this if you specify real world units in feet. |
| `modelOneToNVerticalScale` | *(model:real-world)* | 1 | Model to Real World scale *(E.g. 1:500000 = 0.1mm:50m)* |
| `modelSeaLevelBaseThickness` | | 1 | The model thickness at sea level (0 m) |

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

## Known Issues

**Issue:** When this script is run on Windows, it can only correctly process G-code generated on a Windows computer. [Python on Windows does not handle Unix line endings correctly.](https://stackoverflow.com/questions/15934950/python-file-tell-giving-strange-numbers)

**Solution:** Either convert a G-code file with Unix line endings to Windows line endings before post processing or generate the G-code on Windows.
