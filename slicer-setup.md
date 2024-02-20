# Slicer Setup for MFPP

## G-code coordinate positioning mode

All printing G-code must use [Relative Positioning for Extrusion](https://www.ideamaker.io/dictionaryDetail.html?name=Relative%20Extrusion&category_name=Printer%20Settings).

Printhead XYZE absolution positioning can be set with `G91` and only the Extruder (E) can be set to relative positioning with `M83`. If too little/too much filament is extruded, your extrusion positioning may be set to absolute in the slicer.

## Set Printer G-code

Add markers in your slicer software G-code for the end of new layer change and start and end of toolchange.

Save the printer profile with a new name and select the new printer profile for your prints.

![mfpp slicer setup](assets/bambustudio-printer-settings.jpg)

### PrusaSlicer / BambuStudio steps

1. Printer > Settings > **Custom G-code / Machine G-code**

2. Add `; MFPP LAYER CHANGE END` on a new line at the end of **After layer change G-code / Layer change G-code**.

3. Add `; MFPP TOOLCHANGE START`  on a new line at the beginning of **Tool change G-code / Change filament G-code**.

4. Add `; MFPP TOOLCHANGE END`  on a new line at the end of **Tool change G-code / Change filament G-code**.

5. The resulting settings text fields should have an order like below

#### After layer change G-code

```gcode
; Existing layer change G-code stays HERE

; MFPP LAYER CHANGE END
```

#### Tool change G-code

```gcode
; MFPP TOOLCHANGE START

; Existing toolchange G-code stays HERE

; MFPP TOOLCHANGE END
```