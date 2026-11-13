# Extractor de Metadatos

Herramienta técnica local para la inspección, extracción y catalogación de metadatos internos, estructurales y del sistema de archivos en documentos heterogéneos. Opera de forma 100% no destructiva y sin conexión a internet.

---

## Características Principales

* **Soporte Multiformato**:
  * **Hojas de cálculo**: Excel moderno (`.xlsx`) y binario/XML heredado (`.xls`).
  * **Documentos de texto**: Word moderno (`.docx`), Word heredado (`.doc`) y texto plano (`.txt`).
  * **Documentos digitales**: Archivos Adobe PDF (`.pdf`).
  * **Imágenes**: más de 170 formatos en 9 grupos — ráster, alta eficiencia, vectoriales, RAW de cámara, capas de edición, escaneo, científicos, texturas y nativos por sistema operativo.
* **Inspección Profunda y Estructural**:
  * Propiedades de autoría (creador, autor, última modificación, empresa).
  * Cronología (fechas de creación, guardado, modificación y acceso).
  * Estructura interna (conteo de páginas, tablas, hojas visibles y ocultas, flujos OLE).
  * Huella digital SHA-256 de cada archivo, para verificar integridad y detectar duplicados; copiable en texto plano con un clic.
  * Análisis de texto plano (conteo de líneas, palabras, caracteres y juego de caracteres / *encoding*).
* **Procesamiento Seguro y Privado**:
  * No modifica ni altera los documentos originales bajo ninguna circunstancia.
  * Funciona enteramente en la máquina local (`127.0.0.1`), sin salida a internet ni telemetría.
  * Los archivos temporales se purgan automáticamente tras ser analizados.
* **Doble Interfaz de Operación**:
  * **CLI (Consola)**: Ideal para automatizaciones, procesamiento por lotes y tuberías (*pipelines*).
  * **Web Local**: Interfaz gráfica moderna, responsiva, con arrastrar y soltar (*drag & drop*), búsqueda en vivo y visor de metadatos.

---

## Estructura del Proyecto

```
metadatos/
├── src/extractor/          # Paquete Python (código de la aplicación)
│   ├── __init__.py         #   API pública y versión
│   ├── __main__.py         #   permite `python -m extractor`
│   ├── config.py           #   identidad, versión y límites
│   ├── engine.py           #   motor de extracción (documentos)
│   ├── imagenes.py         #   motor de imágenes (3 niveles)
│   ├── cli.py              #   interfaz de consola
│   ├── web.py              #   servidor local e interfaz HTML
│   └── app.py              #   entrada unificada del ejecutable
├── tests/                  # Pruebas unitarias (unittest)
├── scripts/                # Compilación e instaladores
│   ├── build.py            #   orquestador Windows/macOS
│   ├── build.ps1|build.sh  #   envoltorios por plataforma
│   ├── entry.py            #   punto de entrada para PyInstaller
│   └── instalar.*|DESINSTALAR.*
├── assets/                 # icono.ico y icono.icns
├── pyproject.toml          # metadatos del paquete y dependencias
├── requirements.txt        # dependencias (fuente única)
├── README.md · AGENTS.md
└── .vscode/                # lanzadores y tareas del editor
```

* [`src/extractor/engine.py`](src/extractor/engine.py): Motor central de extracción y contrato de datos.
* [`src/extractor/imagenes.py`](src/extractor/imagenes.py): Módulo exclusivo de metadatos de imagen.
* [`src/extractor/cli.py`](src/extractor/cli.py): Interfaz de línea de comandos.
* [`src/extractor/web.py`](src/extractor/web.py): Servidor HTTP local con interfaz HTML5/CSS3 integrada.
* [`src/extractor/app.py`](src/extractor/app.py): Punto de entrada del ejecutable.
* [`tests/`](tests): Pruebas del contrato, del hash y de los tres niveles de imagen.
* [`scripts/build.py`](scripts/build.py): Orquestador de compilación para Windows y macOS.
* [`pyproject.toml`](pyproject.toml): Empaquetado estándar; `requirements.txt` sigue siendo la fuente de dependencias.

---

## Instalación

1. Clona o descarga la carpeta del proyecto en tu equipo.
2. Abre una terminal (PowerShell, CMD o Bash) en la raíz del proyecto e instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Opcional, para tener los comandos `extractor-metadatos` y `extractor-web` en el PATH:

```powershell
python -m pip install -e .
```

El módulo de imágenes requiere **Pillow ≥ 10.4** (incluido en `requirements.txt`). Sin él, el resto del sistema sigue funcionando y las imágenes se identifican por firma.

> **Nota para Windows**: Si el comando `python` no está en tu ruta global, puedes invocar el ejecutable directamente:
> ```powershell
> & "$env:LOCALAPPDATA\Microsoft\WindowsApps\python3.11.exe" -m pip install -r requirements.txt
> ```

---

## Modo 1: Uso por Línea de Comandos (CLI)

El paquete [`src/extractor/cli.py`](src/extractor/cli.py) permite analizar archivos individuales o árboles de directorios completos.

Con el paquete instalado (`pip install -e .`) el comando es `extractor-metadatos`; sin instalarlo, usa `python -m extractor` con `PYTHONPATH` apuntando a `src`:

```powershell
$env:PYTHONPATH = "src"
```

### Ejemplos comunes:

* **Analizar un único archivo**:
  ```powershell
  extractor-metadatos "C:\Documentos\informe.docx"
  ```

* **Analizar una carpeta completa y sus subcarpetas (recursivo)**:
  ```powershell
  extractor-metadatos "C:\Documentos" --recursive
  ```

* **Exportar resultados a un archivo CSV**:
  ```powershell
  extractor-metadatos "C:\Documentos" --format csv --output metadatos.csv
  ```

* **Exportar resultados a un archivo JSON**:
  ```powershell
  extractor-metadatos "C:\Documentos" --format json --output metadatos.json
  ```

### Parámetros admitidos:
* `paths`: Uno o más archivos o directorios a procesar.
* `-r, --recursive`: Habilita la exploración recursiva de carpetas.
* `-f, --format`: Define el formato de salida (`json` o `csv`; por defecto `json`).
* `-o, --output`: Ruta del archivo donde se guardará el resultado (si se omite, se imprime en consola).
* `--version`: Muestra la versión del paquete.

---

## Modo 2: Interfaz Web Local

Para utilizar la aplicación visual interactiva en el navegador:

```powershell
extractor-web            # o bien:  python -m extractor
```

El sistema abrirá automáticamente el navegador en `http://127.0.0.1:8766`.

### Funcionalidades de la interfaz web:
* **Arrastrar y soltar**: Soporte para soltar archivos múltiples o seleccionar carpetas completas.
* **Métricas en tiempo real**: Contadores de archivos procesados, correctos, con error y tamaño acumulado.
* **Filtro y búsqueda instantánea**: Búsqueda en tiempo real sobre cualquier metadato o nombre de archivo.
* **Visor de metadatos**: Visualización de etiquetas resumen (*Título, Autor, Páginas, etc.*) y acordeón para consultar y copiar el JSON completo.
* **Huella verificable**: El SHA-256 se muestra bajo cada archivo y se puede copiar en texto plano con el botón «Copiar» o seleccionándolo con un clic (la selección toma los 64 caracteres completos).
* **Exportación ágil**: Botones dedicados para descargar los resultados en formato JSON o CSV.
* **Botón de limpieza**: Reinicia la lista de trabajo en memoria sin necesidad de recargar la página.

### Opciones del servidor web:
* Cambiar de puerto: `extractor-web --port 8780`
* Ejecutar sin abrir el navegador: `extractor-web --no-browser`
* Para detener el servidor: Presiona `Ctrl + C` en la terminal.

---

## Metadatos de Imágenes

El módulo [`imagenes.py`](imagenes.py) reconoce **175 extensiones** agrupadas en 9 categorías y declara siempre hasta dónde llegó, en el campo `extraction`.

| Grupo | Ejemplos |
| :--- | :--- |
| **Ráster** | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tif` `.tiff` `.webp` `.ico` |
| **Alta eficiencia** | `.heic` `.avif` `.jxl` `.jp2` `.jxr` `.qoi` `.bpg` `.flif` |
| **Vectoriales** | `.svg` `.eps` `.ps` `.ai` `.cdr` `.wmf` `.emf` `.odg` `.dxf` `.dwg` |
| **RAW de cámara** | `.dng` `.cr2` `.cr3` `.nef` `.arw` `.raf` `.orf` `.rw2` `.pef` `.x3f` `.gpr` |
| **Capas de edición** | `.psd` `.psb` `.xcf` `.kra` `.ora` `.pdn` `.clip` `.procreate` `.afphoto` |
| **Escaneo** | `.djvu` `.jb2` `.pcx` `.dcx` `.mdi` `.pcd` |
| **Científico / cine / GIS** | `.exr` `.hdr` `.dpx` `.cin` `.dcm` `.nii` `.fits` `.ecw` `.sid` |
| **Texturas** | `.dds` `.tga` `.ktx` `.ktx2` `.pvr` `.astc` `.vtf` |
| **Sistema y retro** | `.icns` `.cur` `.ani` `.xbm` `.xpm` `.xwd` `.sgi` `.iff` `.koa` `.pi1` `.fli` |

### Tres niveles de profundidad

| Nivel | Qué obtiene | Formatos |
| :--- | :--- | :--- |
| `completa` | Dimensiones, modo, bits, fotogramas, DPI, perfil ICC, EXIF (cámara, fechas, GPS), transparencia y compresión | Todo lo que abre Pillow |
| `parcial` | Dimensiones y estructura del contenedor leídas con lectores propios | HEIF/AVIF/JPEG XL, RAW TIFF, SVG/SVGZ, DICOM, NIfTI, FITS, KTX, DDS, PVR, ILBM, XCF, KRA/ORA, EPS/AI, DXF/DWG, retro |
| `solo_firma` | Identificación del formato por bytes mágicos | Formatos sin lector disponible |

Cada registro indica `detected_by` (**firma**, **extensión+estructura** o **extensión**) y, si algo falló, `warnings` con el motivo. El sistema **no declara soporte que no tiene**.

Las fechas se exponen de forma explícita: `filesystem.accessed`, `filesystem.created` y `filesystem.modified`; en imágenes, `exif.modify_date`, `exif.datetime_original` y `exif.datetime_digitized`; y, cuando el archivo incluye un paquete XMP, `xmp.modify_date`, `xmp.create_date`, `xmp.metadata_date` y `xmp.creator_tool`. Los PDF añaden el bloque `xmp` con título, autoría, fechas y palabras clave cuando está presente.

> **Privacidad**: las coordenadas GPS del EXIF se extraen porque forman parte del análisis, pero nunca salen de la máquina. En DICOM no se expone ningún identificador de paciente: solo se informa `patient_identity_present`.

## Distribución: Windows y macOS

El equipo de destino **no necesita Python instalado**. Se obtienen siempre dos modos: **portable** (ejecutar sin instalar) e **instalado** (con acceso directo o en Launchpad).

> **Importante**: PyInstaller **no compila de forma cruzada**. El `.exe` se genera en Windows y el `.app` en macOS. `build.py` detecta la plataforma y empaqueta la que corresponda; ambos usan el mismo código fuente.

### Compilar

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1     # Windows
```
```sh
./scripts/build.sh                                               # macOS
```

Ambos son envoltorios de `scripts/build.py`, el orquestador único (también ejecutable directamente: `python scripts/build.py`):

| Artefacto | Windows | macOS |
| :--- | :--- | :--- |
| Ejecutable | `dist\ExtractorMetadatos\ExtractorMetadatos.exe` | `dist\Extractor de Metadatos.app` |
| Carpeta con todo | `dist\ExtractorMetadatos\` | dentro del `.app` (`Contents/Resources/app`) |
| Paquete para copiar | `ExtractorMetadatos-portable-windows.zip` | `ExtractorMetadatos-portable-macos.zip` |
| Instalador adicional | — | `ExtractorMetadatos-darwin.dmg` (si hay `hdiutil`) |

Para un único archivo: añade `--onefile` (`-OneFile` en PowerShell). Para revisar el entorno sin compilar: `--check`.

### Instalar

| | Windows | macOS |
| :--- | :--- | :--- |
| Instalador | `scripts\INSTALAR.bat` | `scripts\INSTALAR.command` (doble clic) |
| Destino | `%LOCALAPPDATA%\DIVIAC\ExtractorMetadatos` | `~/Applications/Extractor de Metadatos.app` |
| Accesos | Menú Inicio y escritorio | Launchpad, Finder y Spotlight |
| Desinstalar | `scripts\DESINSTALAR.bat` | `scripts\DESINSTALAR.command` |
| Permisos | Ninguno (por usuario) | Ninguno (por usuario) |

### Uso del ejecutable

| Invocación | Comportamiento |
| :--- | :--- |
| Doble clic o sin argumentos | Interfaz web en `127.0.0.1:8766` y navegador |
| `web --port 9000` | Interfaz en otro puerto |
| `--no-browser` | Interfaz sin abrir el navegador |
| `"C:\Documentos" -r -f csv -o salida.csv` | CLI por lotes, igual que `MetaDatos.py` |

En macOS el binario interno también acepta esos argumentos:

```sh
"/Applications/Extractor de Metadatos.app/Contents/Resources/app/ExtractorMetadatos" ~/Documentos -r
```

### Notas de despliegue

* Windows: binario de **64 bits**, Windows 10/11.
* macOS: **11 o superior**, Intel y Apple Silicon (el binario es nativo de la arquitectura donde se compila; para distribuir a ambas hay que compilar dos veces o usar un binario universal2).
* Sigue siendo 100 % local: no abre conexiones salientes.
* **Antivirus (Windows)**: falso positivo habitual de PyInstaller; excluye la carpeta o firma el binario.
* **Gatekeeper (macOS)**: un `.app` sin firmar descargado de internet queda en cuarentena. `INSTALAR.command` la retira automáticamente; si lo arrastras a mano, ejecuta `xattr -dr com.apple.quarantine "Extractor de Metadatos.app"`.
* Los scripts `.command` y `.sh` deben conservar el permiso de ejecución: `chmod +x INSTALAR.command` si el ZIP se copió desde Windows.

---

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

24 pruebas que cubren el contrato de datos, el SHA-256, la inspección no destructiva, el descubrimiento de archivos, las columnas del CSV, los tres niveles de extracción de imágenes, las fechas EXIF/XMP y las defensas del servidor local (CSP, Host/Origin y límites de carga). No requieren instalar el paquete (los módulos de prueba añaden `src` al `PYTHONPATH`).

---

## Esquema del Objeto de Metadatos

Cada elemento analizado produce un objeto con el siguiente estándar:

```json
{
  "file": "balance_2026.xlsx",
  "format": "xlsx",
  "filesystem": {
    "name": "balance_2026.xlsx",
    "extension": ".xlsx",
    "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "size_bytes": 45210,
    "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "accessed": "2026-11-02T09:00:00-05:00",
    "created": "2026-11-01T09:12:00-05:00",
    "modified": "2026-11-02T07:45:00-05:00"
  },
  "document": {
    "title": "Balance Financiero Anual",
    "creator": "Área de Contabilidad",
    "sheet_count": 4,
    "hidden_sheet_count": 0,
    "created": "2026-11-01T14:12:00Z"
  },
  "error": null
}
```

---

## Códigos de Salida del Sistema

* `0`: Proceso finalizado exitosamente sin incidencias.
* `1`: Uno o más archivos no pudieron procesarse o generaron advertencias de lectura.
* `2`: Error crítico en los parámetros de entrada o fallo de escritura en disco.

---

<sub>**DIVIAC - PeBe & DeepSeek**</sub>
