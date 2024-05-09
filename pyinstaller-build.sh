# Windows
pyinstaller --onefile src/gui.py --name MFM

# MacOS
# Create code signing identity first
# https://github.com/pyinstaller/pyinstaller/issues/6167#issuecomment-906307356
pyinstaller --onefile src/gui.py --codesign-identity ansonliu-imac-code-sign --name MFM