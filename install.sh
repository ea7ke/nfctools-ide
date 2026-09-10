#!/usr/bin/env bash
# Instala dependencias del sistema y de Python para MCT-IDE en Debian/Kali.
set -e

echo "[*] Instalando paquetes del sistema (apt)..."
sudo apt update
sudo apt install -y \
    python3 python3-pip python3-pyqt5 \
    libnfc-bin libnfc-dev \
    mfoc mfcuk \
    pcscd pcsc-tools

echo "[*] Habilitando pcscd (algunos lectores lo necesitan)..."
sudo systemctl enable --now pcscd || true

echo "[*] Comprobando binarios necesarios..."
for bin in nfc-list nfc-mfclassic mfoc mfcuk; do
    if ! command -v "$bin" >/dev/null 2>&1; then
        echo "  [!] $bin no encontrado en PATH. Puede que tu distro use otro nombre de paquete."
    else
        echo "  [OK] $bin"
    fi
done

echo "[*] Listo. Ejecuta con: python3 main.py"
