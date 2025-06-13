# src/main.py
"""
OneClickDNS - Gestor de DNS
Este módulo implementa una aplicación gráfica para Windows que permite gestionar de forma sencilla los servidores DNS de los adaptadores de red del sistema. Incluye funciones para aplicar y restablecer configuraciones DNS, así como una interfaz gráfica basada en Tkinter y un icono de bandeja del sistema usando pystray.
Funciones principales:
- Elevación automática de privilegios de administrador.
- Obtención de adaptadores de red disponibles mediante 'netsh'.
- Aplicación y restablecimiento de DNS usando presets definidos externamente.
- Validación de presets DNS antes de aplicar cambios.
- Interfaz gráfica para seleccionar adaptador y proveedor DNS.
- Integración con la bandeja del sistema para minimizar la ventana principal.
Dependencias:
- pystray
- Pillow (PIL)
- tkinter
- dns_logic (módulo propio con lógica de DNS)
"""

import os
import sys
import ctypes
import subprocess
import pystray
from PIL import Image
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from dns_logic import dns_presets, aplicar_dns, quitar_dns, validar_preset

CREATE_NO_WINDOW = 0x08000000


# --- Elevación automática ---
def es_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if not es_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1
    )
    sys.exit()


# --- Obtener adaptadores ---
def obtener_adaptadores():
    try:
        resultado = subprocess.run(
            ["netsh", "interface", "show", "interface"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=False,
            check=True,
            creationflags=CREATE_NO_WINDOW,
        )
        adaptadores = []
        for linea in resultado.stdout.splitlines()[3:]:
            if "Conectado" in linea or "Connected" in linea:
                partes = linea.split()
                if len(partes) >= 4:
                    nombre = " ".join(partes[3:])
                    adaptadores.append(nombre)
        return adaptadores if adaptadores else ["Ethernet", "Wi-Fi"]
    except subprocess.CalledProcessError:
        messagebox.showerror("Error", "No se pudieron obtener adaptadores.")
        return []


# --- Acciones GUI ---
def aplicar_dns_gui():
    adaptador = adaptador_seleccionado.get()
    preset_nombre = dns_seleccionado.get()
    if not adaptador or not preset_nombre:
        messagebox.showerror("Error", "Seleccione adaptador y proveedor DNS")
        return

    preset = next((p for p in dns_presets if p["nombre"] == preset_nombre), None)
    if not preset:
        messagebox.showerror("Error", "Proveedor DNS no encontrado")
        return

    errores = validar_preset(preset)
    if errores:
        continuar = messagebox.askyesno(
            "Advertencia",
            f"Se encontraron problemas:\n\n{chr(10).join(errores)}\n\n¿Desea continuar?",
        )
        if not continuar:
            return

    aplicar_dns(adaptador, preset)
    messagebox.showinfo("Listo", f"DNS de '{preset_nombre}' aplicados correctamente.")


def quitar_dns_gui():
    adaptador = adaptador_seleccionado.get()
    if not adaptador:
        messagebox.showerror("Error", "Seleccione un adaptador de red.")
        return
    quitar_dns(adaptador)
    messagebox.showinfo("Listo", f"DNS restablecidos en {adaptador}.")


def refrescar_adaptadores():
    adaptadores = obtener_adaptadores()

    if not adaptadores:
        ventana.quit()
        return
    menu_adaptadores["menu"].delete(0, "end")
    for adaptador in adaptadores:
        menu_adaptadores["menu"].add_command(
            label=adaptador,
            command=lambda valor=adaptador: adaptador_seleccionado.set(valor),
        )
    adaptador_seleccionado.set(adaptadores[0])


# --- GUI ---
BASE_DIR = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).parent.parent
)
ICON_MAIN = BASE_DIR / "assets" / "icons" / "icon.ico"
ICON_TRAY = BASE_DIR / "assets" / "icons" / "tray_icon.ico"

ventana = tk.Tk()
ventana.title("OneClickDNS - Gestor de DNS")
try:
    ventana.iconbitmap(ICON_MAIN)
except Exception:
    pass
ventana.geometry("350x350")
ventana.resizable(False, False)


def crear_icono_tray():
    # Cargar imagen para el ícono (usando la ruta que ya definiste)
    image = Image.open(ICON_TRAY)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir OneClickDNS", abrir_app),
        pystray.MenuItem("Salir", salir_app),
    )

    return pystray.Icon("OneClickDNS", image, "OneClickDNS - Gestor de DNS", menu)


def abrir_app():
    ventana.deiconify()  # Muestra la ventana
    icono_tray.stop()  # Elimina el ícono de la bandeja


def salir_app():
    icono_tray.stop()  # Detiene el ícono
    ventana.destroy()  # Cierra la aplicación


def minimizar_a_tray():
    ventana.withdraw()  # Oculta la ventana
    global icono_tray
    icono_tray = crear_icono_tray()
    icono_tray.run()  # Muestra el ícono en la bandeja


adaptador_seleccionado = tk.StringVar()
tk.Label(ventana, text="Adaptador de red:").pack(pady=5)
menu_adaptadores = tk.OptionMenu(ventana, adaptador_seleccionado, "")
menu_adaptadores.config(width=50)
menu_adaptadores.pack(pady=5)
tk.Button(ventana, text="Refrescar adaptadores", command=refrescar_adaptadores).pack(
    pady=5
)

dns_seleccionado = tk.StringVar()
tk.Label(ventana, text="Proveedor de DNS:").pack(pady=5)
menu_dns = tk.OptionMenu(ventana, dns_seleccionado, *[p["nombre"] for p in dns_presets])
menu_dns.config(width=50)
menu_dns.pack(pady=5)

tk.Button(ventana, text="Aplicar DNS", command=aplicar_dns_gui).pack(pady=10)
tk.Button(ventana, text="Restablecer DNS (DHCP)", command=quitar_dns_gui).pack(pady=5)

refrescar_adaptadores()
ventana.protocol("WM_DELETE_WINDOW", minimizar_a_tray)
ventana.mainloop()
