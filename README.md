# MCT-IDE

Interfaz gráfica ("IDE") en Debian/Kali para las herramientas de MIFARE
Classic: `nfc-list`, `mfoc`, `mfcuk` y `nfc-mfclassic` (libnfc). No
reimplementa ningún ataque: es un frontend que construye las líneas de
comandos por ti, muestra el progreso en vivo y organiza los resultados.

## Funcionalidad

- **Lector**: detecta el lector NFC y la tarjeta presente (UID, ATQA, SAK,
  tipo estimado 1K/4K).
- **Leer / Volcar**: lanza `mfoc` (nested/dictionary), `mfcuk` (darkside) o
  `nfc-mfclassic` (lectura directa con claves ya conocidas) eligiendo las
  opciones desde formularios en vez de recordar flags. Guarda el volcado
  `.mfd` resultante.
- **Claves**: carga uno o varios diccionarios de claves, añade claves
  sueltas a mano, fusiona sin duplicados y guarda un diccionario combinado
  listo para `-k`/`-f`.
- **Tarjetas**: base de datos local (SQLite) que organiza cada tarjeta por
  UID, con nombre, tipo, ruta del volcado, ruta de claves y notas. Permite
  ver el volcado en un visor hexadecimal por bloques/sectores.
- **Editor de UID**: para tarjetas "magic" (clones Gen1a / CUID). Ofrece:
  1. Un test **no destructivo** que reescribe el bloque 0 con el mismo UID
     que ya tiene la tarjeta, para detectar si acepta reescritura.
  2. Un botón de **forzar intento** que se salta esa comprobación, para
     quien ya sabe que su tarjeta es "magic".

  ⚠️ Una MIFARE Classic **original** tiene el UID grabado de fábrica y
  **no se puede cambiar**; esto solo funciona con clones fabricados para
  permitirlo.

## Instalación (Debian / Kali)

```bash
git clone <este-repo> mct-ide
cd mct-ide
chmod +x install.sh
./install.sh
python3 main.py
```

`install.sh` instala: `python3-pyqt5`, `libnfc-bin`, `libnfc-dev`, `mfoc`,
`mfcuk`, `pcscd`, `pcsc-tools`, y habilita el servicio `pcscd` (necesario
para algunos lectores PC/SC).

Si tu distro no trae `mfoc`/`mfcuk` empaquetados, compílalos desde sus
repositorios oficiales (`nfc-tools/mfcuk`, `nethemba/mfoc` o los forks
mantenidos en GitHub) y asegúrate de que queden en el `PATH`.

## Estructura del proyecto

```
mct-ide/
├── main.py                  # ventana principal, une las pestañas
├── backend/                 # lógica pura: construir comandos, parsear
│   ├── reader.py            #   salida de nfc-list
│   ├── mfoc_wrapper.py      #   comando/parseo de mfoc
│   ├── mfcuk_wrapper.py     #   comando/parseo de mfcuk
│   ├── nfc_mfclassic_wrapper.py
│   ├── uidwriter.py         #   edición de bloque 0 / BCC
│   ├── dumpio.py            #   cargar/guardar .mfd, listar bloques
│   ├── keys.py              #   diccionarios de claves
│   └── carddb.py            #   base de datos SQLite por UID
├── gui/                     # widgets PyQt5, una pestaña por fichero
├── install.sh
└── requirements.txt
```

El backend está separado de la GUI a propósito: cada wrapper solo
construye argv (listas de strings) y parsea texto, sin tocar Qt, así que
se puede testear sin hardware ni entorno gráfico (ver los tests que se
ejecutaron durante el desarrollo).

## Notas de seguridad / uso responsable

Estas herramientas explotan debilidades conocidas del cifrado propietario
Crypto-1 de MIFARE Classic. Úsalas solo sobre tarjetas propias o con
autorización explícita del propietario/organización. El proyecto no añade
ninguna capacidad nueva de ataque: solo hace más cómodo usar las mismas
herramientas que ya están en Kali Linux.

## Estado / próximos pasos sugeridos

- El parseo de progreso de `mfoc` (`backend/mfoc_wrapper.py`) usa una
  expresión regular sobre su salida por stdout; si tu versión de `mfoc`
  formatea las líneas de forma distinta, puede que no capture las claves
  en vivo (el volcado final se sigue guardando igual, esto solo afecta a
  la vista de progreso). Ajusta `_KEY_LINE_RE` si hace falta.
- La detección de tarjeta "magic" es heurística (basada en si
  `nfc-mfclassic` acepta o rechaza la reescritura del bloque 0), no un
  detector de comandos de puerta trasera Gen1a por APDU raw. Si quieres
  algo más fino, se podría añadir un módulo que hable con
  `libnfc`/`pcsc` directamente en vez de pasar por `nfc-mfclassic`.
- Falta empaquetado `.deb`/`.desktop` para instalación.
