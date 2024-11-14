; MFM MINIMAL XL TOOLCHANGE START
M220 B
M220 S100
; CP TOOLCHANGE UNLOAD
M900 K0
G1 F12538
G1 X169.000 F2400
G4 S0
G1 E-20 F2100
; Filament-specific end gcode
; Change Tool -> ToolXX
G1 F21000
P0 S1 L2 D0
; 0
M109 S215 TXX
TXX S1 L0 D0

M900 K0.05 ; Filament gcode



M142 S36 ; set heatbreak target temp
M109 S215 T1 ; set temperature and wait for it to be reached

G1 F24000
G1 E20 F1500
G4 S0
; CP TOOLCHANGE WIPE
M220 R
G1 F24000
G4 S0
G92 E0
; MFM MINIMAL TOOLCHANGE END
