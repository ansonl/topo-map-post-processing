# 3D Map Feature Gcode Post Processing

Add [isolines (contour lines/elevation lines)](https://en.wikipedia.org/wiki/Contour_line) and colored [elevation ranges](https://desktop.arcgis.com/en/arcmap/latest/map/styles-and-symbols/working-with-color-ramps.htm) to [3D printable map models](https://ansonliu.com/maps/).

This app adds additional features to the model by post processing sliced [3D printer G-code](https://marlinfw.org/meta/gcode/).

![map feature gcode post processing screenshot](/assets/screenshot.png)

Only one isoline interval and colored elevation range is exposed at the moment but the implementation could support more. If you find this tool helpful, please leave feedback and consider supporting my development and 3D modeling through my [Printables](https://www.printables.com/@ansonl) "club membership" or [Paypal](https://paypal.me/0x80).

## Current G-code flavors supported

- Marlin 2 (PrusaSlicer/Bambu Studio)

If you would like support for your printer G-code flavor to be added, please open an issue and if you are able to test the G-code on your printer.

## Slicer Setup

### Set Printer G-code

Add markers in your slicer software G-code for the end of new layer change and start and end of toolchange.

#### PrusaSlicer / BambuStudio steps

1. Printer > Settings > **Custom G-code / Machine G-code**

2. Add `; MFPP LAYER CHANGE END` on a new line at the end of **After layer change G-code / Layer change G-code**.

3. Add `; MFPP TOOLCHANGE START`  on a new line at the beginning of **Tool change G-code / Change filament G-code**.

4. Add `; MFPP TOOLCHANGE END`  on a new line at the end of **Tool change G-code / Change filament G-code**.

5. The resulting settings text fields should have an order like below

##### After layer change G-code

```gcode
; Existing layer change G-code stays HERE

; MFPP LAYER CHANGE END
```

##### Tool change G-code

```gcode
; MFPP TOOLCHANGE START

; Existing toolchange G-code stays HERE

; MFPP TOOLCHANGE END
```

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

## Toolchange G-code File

You must supply a file containing a minimal toolchange G-code sequence for your printer.

1. The location for next extruder index (the tool/filament/color being switched to) must be replaced with `XX` in this text file. All instances of `XX` are replaced with the next extruder index. *E.g. When switching to extruder 1, `TXX` will become `T1`*

2. It is recommended to convert moves that change depending on the current print progress from absolute to relative.

This toolchange is used when a toolchange is needed but the existing Prime Tower and toolchange G-code cannot be used.

Premade minimal toolchange files are located in the `minimal_toolchanges` directory. Every 3D printer is different and you should manually verify that the provided G-code is compatible with your printer. 

If you would like to contribute your toolchange G-Code, please make a pull request.

## Known Issues

**Issue:** When this script is run on Windows, it can only correctly process G-code generated on a Windows computer. [Python on Windows does not handle Unix line endings correctly.](https://stackoverflow.com/questions/15934950/python-file-tell-giving-strange-numbers)

**Solution:** Either convert a G-code file with Unix line endings to Windows line endings before post processing or generate the G-code on Windows.

## License and Disclaimer

GNU AFFERO GENERAL PUBLIC LICENSE v3.0

Copyright © 2023 Anson Liu

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
