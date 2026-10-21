# Tempratur

A small Windows desktop app that shows the machine's internal temperatures in a dark, custom-drawn Tkinter window.

- GPU temperature from `nvidia-smi`
- CPU temperature from the Windows ACPI thermal zone
- CPU load and memory, with a two-minute history chart

## Run

```powershell
python Tempratur.pyw
```

Python 3.10 or newer with Tkinter. `psutil` provides the load and memory cards; without it the temperature cards still work. `nvidia-smi` comes with the NVIDIA driver.

Windows only exposes the ACPI thermal sensor to elevated processes, so the CPU card starts locked. Click it, or press "Enable CPU sensor", to restart the app with admin rights.

## Check

```powershell
python Tempratur.pyw --selftest
```

## Notes

`Tempratur.lnk` is not tracked. It is a local shortcut that points at this machine's `pythonw.exe`.
