# Tempratur

A small Windows desktop app that shows the machine's internal temperatures in a dark, custom-drawn Tkinter window.

- GPU temperature from `nvidia-smi`
- CPU temperature from the Windows thermal zone
- CPU load and memory, with a two-minute history chart
- 45-second CPU and GPU stress tests from the footer buttons
- Tray icon, start with Windows, and a notification above 85°C

## Run

```powershell
pip install -r requirements.txt
python Tempratur.pyw
```

Python 3.10 or newer with Tkinter. `pystray` and `Pillow` provide the tray icon; without them the app runs as a normal window. `psutil` provides load and memory. `nvidia-smi` comes with the NVIDIA driver.

The CPU temperature comes from the Windows thermal-zone performance counter, which works without admin on most laptops. If a machine only exposes the ACPI WMI class, the CPU card starts locked and offers a one-click restart with admin rights.

Closing the window keeps the app in the notification area. Right-click the tray icon for "Start with Windows" and "Quit", or press Ctrl+Q in the window. Esc hides it.

## Test the sensors

Press **Test CPU** or Ctrl+T for a 45-second full-core CPU load, and **Test GPU** or Ctrl+G to drive the NVIDIA GPU through CUDA for 45 seconds. The CPU test stops early at 95°C, the GPU test at 90°C. If the CPU card is locked, enable the sensor first.

The GPU test uses the CUDA interface in the installed NVIDIA driver, so it needs no CUDA toolkit and no extra files. The button stays disabled when no NVIDIA GPU is detected. Both tests warm the other card a little through the shared heatsink.

## Build a single exe

```powershell
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name Tempratur --icon Tempratur.ico Tempratur.pyw
```

The result is `dist/Tempratur.exe`, with no Python install needed on the target machine.

## Check

```powershell
python Tempratur.pyw --selftest
```

## Notes

`Tempratur.lnk` is not tracked. It is a local shortcut for this machine.
