# 3D G-code Map Feature Post Processing (MFPP)

Add [isolines (contour lines/elevation lines)](https://en.wikipedia.org/wiki/Contour_line) and colored [elevation ranges](https://desktop.arcgis.com/en/arcmap/latest/map/styles-and-symbols/working-with-color-ramps.htm) to [3D printable map models](https://ansonliu.com/maps/).

This app adds additional features to the model by post processing sliced [3D printer G-code](https://marlinfw.org/meta/gcode/).

![map feature gcode post processing screenshot](/assets/gui_screenshot.png)

Only one isoline interval and colored elevation range is exposed at the moment but the implementation could support more. If you find this tool helpful, please leave feedback and consider supporting my development and 3D modeling through my [Printables](https://www.printables.com/@ansonl) "club membership" or [Paypal](https://paypal.me/0x80).

## Current G-code flavors supported

- Marlin 2 (PrusaSlicer/Bambu Studio)

Your slicer **must generate g-code with [Relative Extrusion](https://www.ideamaker.io/dictionaryDetail.html?name=Relative%20Extrusion&category_name=Printer%20Settings)**. PrusaSlicer and Bambu Studio default to relative extrusion. Cura defaults to absolute extrusion and relative extrusion must be enabled.

If you would like support for your printer or slicer G-code flavor to be added, please open an issue and if you are able to test the G-code on your printer.

## Getting Started

Set up your slicer and printer for MFPP by following the steps on every page below:

- [Slicer Setup](slicer-setup.md)

- [Configuration](configuration-setup.md)

- [Minimal Toolchange G-code](minimal-toolchange-gcode.md)

After following all the above set up pages, download the [latest release of MFPP](https://github.com/ansonl/topo-map-post-processing/releases) and run `gui.exe`.

If a release of MFPP has not been built for your OS, you can [download](https://github.com/ansonl/topo-map-post-processing/archive/refs/heads/master.zip) this repo, navigate to it in the command line and run `python gui.py`.

## Notes

🚧 **Issue:** Color change may not happen on layers where a feature/line type spans a layer boundary. the console log will show 0 features found on that layer. The lookahead distance can be increased to find the next feature. File a bug report with your G-code file so the proper lookahead distance can be determined.

🚧 **Issue:** Support and Bridge features are not explicitly prioritized to pprint first. TBD to prioritize them.

✅ **Issue:** Mixed OS line endings in the same file will lead to G-code errors. MFPP tries to auto detect the line ending used with first line ending found.

**Solution:** Select the correct line ending of your G-code instead of auto detect. Either convert the entire G-code file with Unix line endings to Windows line endings before post processing or generate the G-code on Windows. [Python on Windows does not handle Unix line endings correctly.](https://stackoverflow.com/questions/15934950/python-file-tell-giving-strange-numbers)

## Bug Reports

Open an issue on Github. Please note the OS, Slicer, printer, and provide the 3D model, MFPP configuration JSON, before/after G-code, and console log.

## License and Disclaimer

GNU AFFERO GENERAL PUBLIC LICENSE v3.0

Copyright © 2023 Anson Liu

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
