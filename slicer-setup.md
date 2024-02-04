# Slicer Setup for MFPP

## Set Printer G-code

Add markers in your slicer software G-code for the end of new layer change and start and end of toolchange.

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