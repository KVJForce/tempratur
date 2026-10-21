# Tempratur

A small Windows desktop app that shows the machine's internal temperatures in a dark, custom-drawn Tkinter window.

- GPU temperature from `nvidia-smi`
- CPU temperature from the Windows ACPI thermal zone
- CPU load and memory, with a two-minute history chart
- Tray icon, start with Windows, and a notification above 85°C

## Run

```powershell
pip install -r requirements.txt
python Tempratur.pyw
```

Python 3.10 or newer with Tkinter. `pystray` and `Pillow` provide the tray icon; without them the app runs as a normal window. `psutil` provides load and memory. `nvidia-smi` comes with the NVIDIA driver.

Windows only exposes the ACPI thermal sensor to elevated processes, so the CPU card starts locked. Click it, or press "Enable CPU sensor", to restart with admin rights.

Closing the window keeps the app in the notification area. Right-click the tray icon for "Start with Windows" and "Quit", or press Ctrl+Q in the window. Esc hides it.

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
