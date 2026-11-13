# AGENTS.md — Especificación Funcional y Guía para Agentes de IA

Este documento define la arquitectura técnica, las necesidades funcionales y los protocolos de operación que cualquier agente de inteligencia artificial o desarrollador automatizado debe respetar al inspeccionar, modificar o ampliar el sistema **Extractor de Metadatos**.

---

## 1. Propósito del Sistema

El sistema es una herramienta técnica local y no destructiva diseñada para inspeccionar, catalogar y extraer metadatos internos, estructurales y del sistema de archivos a partir de documentos heterogéneos (`.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.txt`) y de **archivos de imagen en más de 170 formatos** (ráster, vectoriales, RAW de cámara, capas de edición, escaneo, científicos, texturas y nativos de cada sistema operativo), garantizando confidencialidad absoluta mediante procesamiento 100% fuera de línea (*air-gapped* o local).

---

## 2. Necesidades Funcionales del Sistema (RF)

| Identificador | Requisito Funcional | Descripción Técnica |
| :--- | :--- | :--- |
| **RF-01** | **Inspección no destructiva** | El sistema debe operar en modo estrictamente de solo lectura (`read-only`), sin alterar sumas de verificación (*hashes*), fechas de acceso o contenidos del archivo original. El SHA-256 se calcula para verificarlas, nunca se reescribe. |
| **RF-02** | **Soporte multiformato amplio** | Análisis de formatos binarios heredados (OLE2 para `.doc` y `.xls`), formatos empaquetados basados en XML (OOXML para `.docx` y `.xlsx`), documentos vectoriales (`.pdf`), texto plano (`.txt`) y **archivos de imagen en 9 grupos taxonómicos** (ráster, alta eficiencia, vectorial, RAW, capas, escaneo, científico, texturas y sistema). |
| **RF-03** | **Extracción estructural profunda** | Más allá de fechas y autores, se deben computar métricas internas: número de páginas, número de hojas de cálculo, estado de visibilidad de pestañas, tablas OLE, conteo de palabras, codificación de caracteres y líneas; en imágenes, dimensiones, profundidad de bits, fotogramas, perfil ICC, EXIF y estructura del contenedor. |
| **RF-04** | **Privacidad y aislamiento estricto** | Todo el procesamiento se realiza en la máquina anfitriona (`localhost` / `127.0.0.1`). Ningún dato o archivo se transmitirá a redes externas o APIs de terceros. |
| **RF-05** | **Doble interfaz desacoplada** | 1. **Consola (CLI)**: Para scripts de automatización por lotes, tuberías (*pipelines*) e integración con herramientas del sistema operativo.<br>2. **Servidor Web Local**: Para usuarios finales que requieran interactividad visual, filtrado dinámico y exportación asistida. |
| **RF-06** | **Estandarización de salida** | Contrato de datos uniforme para todos los tipos de archivo en formato JSON y exportación tabular en CSV con metadatos anidados normalizados. |
| **RF-07** | **Aislamiento de errores** | La falla en el procesamiento de un archivo corrupto o protegido con contraseña no debe abortar la ejecución del lote completo; el error debe registrarse puntualmente en el objeto de salida. |

---

## 3. Arquitectura y Módulos

```
d:\PyInstitucional\metadatos\
│
├── src\extractor\      # Paquete Python de la aplicación
│   ├── __init__.py     #   API pública y versión
│   ├── __main__.py     #   permite `python -m extractor`
│   ├── config.py       #   identidad, versión y límites
│   ├── engine.py       #   motor de extracción de documentos
│   ├── imagenes.py     #   módulo de imágenes (3 niveles)
│   ├── cli.py          #   interfaz de línea de comandos
│   ├── web.py          #   servidor HTTP e interfaz HTML5/CSS3
│   └── app.py          #   entrada unificada del ejecutable
├── tests\              # Pruebas unitarias (unittest, sin dependencias extra)
├── scripts\            # Compilación e instaladores
│   ├── build.py        #   orquestador Windows/macOS
│   ├── build.ps1       #   envoltorio de Windows
│   ├── build.sh        #   envoltorio de macOS
│   ├── entry.py        #   punto de entrada para PyInstaller
│   ├── instalar.ps1    #   instalación en Windows (por usuario)
│   ├── INSTALAR.bat    #   instalador de doble clic para Windows
│   ├── DESINSTALAR.bat #   desinstalador de doble clic para Windows
│   ├── desinstalar.ps1 #   desinstalación limpia en Windows
│   ├── instalar.sh     #   instalación en macOS (~/Applications)
│   ├── INSTALAR.command    # instalador de doble clic para macOS
│   ├── DESINSTALAR.command # desinstalador de doble clic para macOS
│   └── desinstalar.sh  #   desinstalación limpia en macOS
├── assets\             # Iconos: icono.ico (Windows) e icono.icns (macOS)
├── pyproject.toml      # Empaquetado estándar (src layout) y entry points
├── requirements.txt    # Dependencias (fuente única para pip y pyproject)
├── README.md           # Manual de usuario, despliegue y guía operativa
├── AGENTS.md           # Este archivo: Especificación funcional y guía de agentes
└── .vscode\            # Lanzadores y tareas del editor
```

> **Integridad del motor**: `src/extractor/engine.py` es la única fuente válida del motor. Un `.pyc` dentro de `__pycache__` **no es importable** por sí solo, y el paquete se resuelve con `src` en `PYTHONPATH` o instalándolo con `pip install -e .`. No se debe parchear copiando bytecode a mano.

### 3.1. Motor Central (`src/extractor/engine.py`)
* **`SUPPORTED_EXTENSIONS`**: `set` de extensiones validadas (`.xlsx`, `.xls`, `.doc`, `.docx`, `.txt`, `.pdf`) y **única fuente de verdad** del soporte multiformato.
* **Analizadores especializados**:
  * **OOXML (`.xlsx`, `.docx`)**: Lectura mediante las APIs de alto nivel `openpyxl.load_workbook(read_only=True, data_only=True)` y `docx.Document`. No se parsean a mano los flujos `docProps/*.xml` ni `xl/workbook.xml`.
  * **OLE2 Binario (`.doc`)**: `olefile.OleFileIO` + `get_metadata()` (que internamente resuelve `\x05SummaryInformation` y `\x05DocumentSummaryInformation`) y `listdir()` para inventariar flujos compuestos.
  * **XLS heredado (`.xls`)**: Enrutado por firma de los primeros 256 bytes; si empieza por `<?xml` o `<Workbook` se procesa como SpreadsheetML con `defusedxml.ElementTree.iterparse`, en caso contrario como BIFF con `xlrd.open_workbook(on_demand=True)`.
  * **PDF (`.pdf`)**: Diccionario `/Info` mediante `pypdf.PdfReader`, más tamaño y orientación de página, páginas rotadas (`/Rotate`) y número de adjuntos. **No** se extraen metadatos XMP.
  * **Texto (`.txt`)**: Detección determinista de juego de caracteres con `charset-normalizer`, cómputo de caracteres, palabras, líneas, líneas no vacías y presencia de BOM.
* **Normalización (`json_value`)**: Fechas (`datetime`, `date`) a ISO 8601, `bytes` a hexadecimal y tipos específicos a `str`.
* **Integridad (`sha256_digest`)**: Huella SHA-256 de cada archivo, calculada en bloques de 1 MiB con `hashlib` para no cargar el contenido en memoria ni alterar el original.
* **Aislamiento de errores (`extract_file`)**: captura `OSError`, `ValueError` y `RuntimeError`; ante cualquier fallo devuelve `"document": {}` y `"error": "<TipoDeExcepción>: <mensaje>"`.

### 3.2. Módulo de Imágenes (`src/extractor/imagenes.py`)
* **Taxonomía (`IMAGE_GROUPS`)**: 9 grupos (ráster, moderno, vectorial, raw, capas, escaneo, cientifico, textura, sistema) que suman **175 extensiones**. `IMAGE_EXTENSIONS` es su unión y se agrega a `SUPPORTED_EXTENSIONS`.
* **Sufijos compuestos**: `.9.png` y `.nii.gz` se resuelven con `_effective_suffix` y `COMPOUND_SUFFIXES`, no con `Path.suffix`.
* **Detección por firma (`_sniff`)**: identifica el contenido real antes de mirar la extensión; devuelve también el origen (`firma`, `firma (gzip)`, `extensión+estructura`, `extensión`). Cubre ambigüedades como TGA (sin firma propia, validado por cabecera) frente a CUR.
* **Tres niveles de profundidad, declarados en `extraction`**:
  1. `completa` — Pillow abre el archivo: dimensiones, modo, bits, fotogramas, DPI, ICC, EXIF y GPS.
  2. `parcial` — lector estructural propio: SVG/SVGZ (`defusedxml`), ISOBMFF (HEIF/AVIF/JPEG XL/CR3), IFD TIFF (que cubre la mayoría de RAW), DICOM, NIfTI, FITS, KTX/KTX2, DDS, PVR, IFF/ILBM, XCF, ZIP (KRA/ORA/ODG/Sketch/Figma/Pixelmator), PostScript/EPS/AI, DXF/DWG, formatos retro de tamaño fijo.
  3. `solo_firma` — únicamente identificación; se registra en `warnings` el motivo.
* **Regla de honestidad**: nunca se declara soporte que no exista. Si un formato no se puede leer, `extraction` lo dice y el campo `warnings` explica por qué.
* **Privacidad de EXIF**: el GPS y los datos de cámara se extraen porque son objeto del análisis, pero **solo se muestran en local**; DICOM no expone identificadores de paciente, únicamente `patient_identity_present`.
* **Defensa ante bombas de descompresión**: `Image.MAX_IMAGE_PIXELS` acotado a 250 Mpx y lectura perezosa (no se llama a `load()`).

### 3.3. Servidor e Interfaz Web (`src/extractor/web.py`)
* **Arquitectura de servidor**: `ThreadingHTTPServer` ejecutándose en un hilo demonio local (`127.0.0.1`) con capacidad de selección de puerto dinámico.
* **Seguridad HTTP**: Cabeceras estrictas (`X-Content-Type-Options: nosniff`, `Content-Security-Policy` con `nonce` por respuesta, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` y `Cache-Control: no-store`). Se validan `Host`, `Origin` y `Sec-Fetch-Site` para rechazar peticiones de otros orígenes.
* **Límites de carga**: `MAX_FILE_SIZE` = 40 MB por archivo, `MAX_REQUEST_SIZE` = 40 MB + 256 KB para absorber las cabeceras del cuerpo multipart, `MAX_CONCURRENT_REQUESTS` = 4 y `REQUEST_TIMEOUT_SECONDS` = 30. La UI valida antes de enviar; el servidor revalida y responde `413`.
* **Extracción efímera**: Recepción multipart transmitida por bloques a un archivo temporal esponjado, almacenamiento transitorio en un directorio propio de la ejecución y destrucción asegurada mediante `try ... finally` y `atexit`.
* **Frontend reactivo**: Código HTML5/CSS3 autocontenido (sin frameworks externos ni descargas CDN), diseño fluido con CSS Grid/Flexbox, soporte para arrastrar y soltar (*drag & drop*), filtrado en memoria y descarga dinámica. Las extensiones admitidas y el límite de tamaño **se inyectan desde `extractor.engine.SUPPORTED_EXTENSIONS` y `extractor.config.MAX_FILE_SIZE`**, nunca se duplican como literales en el JavaScript. El SHA-256 de cada fila se copia en texto plano mediante `navigator.clipboard`, con respaldo a `document.execCommand` cuando la API moderna no está disponible.
* **Identidad y marca**: `APP_NAME`, `ORGANIZATION` y `AUTHORS` son las únicas constantes de identidad del producto; alimentan el `<title>`, el encabezado, el pie y el banner de consola. Un cambio de nombre se hace solo ahí, nunca repitiendo literales en el HTML.

### 3.4. Empaquetado y Despliegue (`app.py`, `scripts/build.py`)
* **Entrada única**: `src/extractor/app.py` abre la interfaz web cuando no recibe argumentos y delega en `cli.main()` cuando recibe rutas; `web --port` fuerza la interfaz. En macOS, un fallo al arrancar se reporta con un diálogo nativo (`osascript`), porque no hay consola visible.
* **Un solo orquestador**: `scripts/build.py` detecta la plataforma y produce el paquete correspondiente. `scripts/build.ps1` y `scripts/build.sh` son envoltorios de tres líneas; la lógica no se duplica.
* **Sin compilación cruzada**: PyInstaller no compila para otro sistema operativo. El `.exe` se genera en Windows y el `.app` en macOS, desde el mismo código fuente. Nunca se debe prometer un binario de otra plataforma sin compilarlo allí.
* **macOS**: el `.app` se construye a mano (no con `--windowed`) para conservar el binario ejecutable por consola. Estructura: `Contents/MacOS/<lanzador>`, `Contents/Resources/app/<carga>` y `Contents/Resources/icono.icns`, con `Info.plist` propio. Se genera además un `.dmg` si existe `hdiutil`.
* **Permisos POSIX**: `zip_tree` fija los modos (755 para lanzador, binario y scripts) según el contenido, no según el sistema de archivos, porque `chmod` no marca el bit de ejecución en Windows. Sin esto, el `.app` llega al Mac sin permiso de arranque.
* **Regla de dependencias**: toda biblioteca nueva debe declararse en `requirements.txt` **y** en `COLLECT_ALL`/`COLLECT_SUBMODULES` de `build.py`. Si falta en el segundo, el ejecutable falla en otra máquina aunque funcione en desarrollo.
* **Tamaño**: `openpyxl` arrastra `pandas → scipy → pyarrow`; están en `EXCLUDES`. Sin esas exclusiones el paquete pasa de 57 MB a 266 MB sin ganar ninguna función.
* **Instalación por usuario, sin privilegios**: `%LOCALAPPDATA%\DIVIAC\ExtractorMetadatos` en Windows y `~/Applications/Extractor de Metadatos.app` en macOS. El modo portable consiste en ejecutar el binario sin instalar nada.
* **Verificación obligatoria**: tras compilar hay que ejecutar el artefacto y comprobar `/health`, una extracción real y el modo CLI. Un build sin probar no se entrega; en macOS, además, comprobar que el `.app` abre con doble clic.

---

## 4. Contrato de Datos (Esquema de Salida JSON)

Todo análisis generado por el sistema debe cumplir con la siguiente estructura canónica:

```json
{
  "file": "nombre_archivo.docx",
  "format": "docx",
  "filesystem": {
    "name": "nombre_archivo.docx",
    "extension": ".docx",
    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "size_bytes": 1048576,
    "created": "2026-11-02T08:00:00-05:00",
    "modified": "2026-11-02T08:15:00-05:00"
  },
  "document": {
    "title": "Documento Institucional",
    "author": "Usuario",
    "creator": "Microsoft Office Word",
    "revision": "3",
    "created": "2026-10-30T10:00:00Z",
    "modified": "2026-11-02T13:15:00Z"
  },
  "error": null
}
```

*Si ocurre un error en la extracción del documento, `"document"` será `{}` y `"error"` contendrá `<TipoDeExcepción>: <mensaje>` (por ejemplo `RuntimeError: No se pudo leer el archivo DOCX: ...`).*

**Claves garantizadas**: `file`, `format`, `filesystem`, `document` y `error` existen siempre. `filesystem` contiene `name`, `extension`, `mime_type`, `size_bytes`, `sha256`, `accessed`, `created` y `modified`. `created` usa `st_birthtime` cuando el sistema lo expone; en Windows, `st_ctime` es la fecha de creación, mientras que en POSIX sin `st_birthtime` corresponde al cambio de inodo.

**Claves de `document` por formato** (las ausentes se omiten, nunca se emiten vacías):

**Imágenes** (comunes a los tres niveles): `format`, `format_detail`, `category`, `mime_type`, `detected_by`, `extraction`, `width`, `height`, `megapixels`.

| Nivel | Campos adicionales |
| :--- | :--- |
| `completa` (Pillow) | `mode`, `bit_depth`, `has_alpha`, `animated`, `frames`, `dpi`, `compression`, `progressive`, `interlaced`, `icc_profile{present,bytes,description}`, `exif{image_description,make,model,lens_make,lens_model,software,artist,copyright,datetime,modify_date,datetime_original,datetime_digitized,offset_time,offset_time_original,offset_time_digitized,subsec_time,subsec_time_original,subsec_time_digitized,orientation,exposure_time,exposure_program,exposure_bias,f_number,max_aperture,iso,metering_mode,light_source,flash,focal_length,focal_length_35mm,color_space,white_balance,scene_capture_type,user_comment,camera_owner,body_serial_number,image_unique_id,gps{latitude,longitude,altitude,altitude_ref,direction,direction_ref,status,map_datum,processing_method,date_stamp,time_stamp}}`, `xmp{title,creator,description,subject,keywords,rights,modify_date,create_date,metadata_date,creator_tool,datetime_original}`, `icon_sizes[]`, `loop`, `frame_duration_ms`, `nine_patch` |
| `parcial` (contenedor) | `brand`, `compatible_brands[]`, `codec` (ISOBMFF); `vector`, `svg_version`, `view_box`, `element_count`, `has_script`, `external_references`, `title` (SVG); `make`, `model`, `datetime`, `software`, `compression` (IFD TIFF/RAW); `modality`, `rows`, `columns`, `bits_allocated`, `patient_identity_present` (DICOM); `dimensions`, `datatype`, `voxel_size[]`, `slices` (NIfTI); `telescope`, `instrument`, `observation_date` (FITS); `format_fourcc`, `mip_levels` (texturas); `bitplanes`, `zip_entries`, `declared_mime`, `has_preview`, `layer_files`, `version`, `bounding_box[]`, `width_pt`, `height_pt` |

**Documentos**:

| Formato | Campos |
| :--- | :--- |
| `.xlsx` | `title`, `subject`, `creator`, `keywords`, `description`, `last_modified_by`, `created`, `modified`, `category`, `revision`, `identifier`, `language`, `sheet_count`, `hidden_sheet_count`, `sheets[]`, `defined_name_count` |
| `.docx` | `title`, `subject`, `author`, `keywords`, `comments`, `last_modified_by`, `created`, `modified`, `category`, `revision`, `identifier`, `language`, `paragraph_count`, `nonempty_paragraph_count`, `heading_count`, `table_count`, `table_characters`, `section_count`, `text_characters`, `section_layouts[]`, `headers_present`, `footers_present` |
| `.doc` | `title`, `subject`, `author`, `keywords`, `comments`, `template`, `last_modified_by`, `revision`, `created`, `modified`, `creating_application`, `pages`, `words`, `characters`, `compound_streams[]`, `compound_stream_count` |
| `.xls` (BIFF) | `sheet_count`, `hidden_sheet_count`, `sheets[]`, `date_mode` |
| `.xls` (SpreadsheetML) | `title`, `subject`, `author`, `keywords`, `description`, `last_modified_by`, `created`, `modified`, `revision`, `category`, `company`, `manager`, `sheet_count`, `hidden_sheet_count`, `sheets[]` |
| `.pdf` | `pages`, `encrypted`, `pdf_version`, `title`, `author`, `subject`, `creator`, `producer`, `created`, `modified`, `keywords`, `trapped`, `page_sizes{}`, `landscape_pages`, `rotated_pages`, `attachment_count`, `xmp{title,creator,description,subject,keywords,producer,rights,created,modified,metadata_date,creator_tool,document_id,instance_id}` |
| `.txt` | `encoding`, `characters`, `words`, `lines`, `nonempty_lines`, `has_bom` |

`sheets[]` usa la forma `{name, visibility, rows, columns}`; `section_layouts[]` usa `{width_inches, height_inches, orientation}`; `compound_streams[]` usa `{path, size_bytes}`. En `.xls` SpreadsheetML `rows` y `columns` conservan el valor textual del atributo o `null` si falta.

**Exportación CSV**: columnas fijas `file`, `format`, `size_bytes`, `sha256`, `created`, `modified`, `document_metadata` (JSON serializado del objeto `document`) y `error`. El CSV escrito a archivo usa BOM UTF-8; el emitido por consola no lo añade.

---

## 5. Directrices Operativas para Agentes de IA

Cuando un agente trabaje sobre esta base de código, debe acatar las siguientes reglas:

1. **Minimización y concisión**:
   * Mantener el código compacto y legible. Evitar código redundante (*boilerplate* innecesario).
   * Mantener comentarios y documentación concisos (máximo 1 línea por función o procedimiento).
2. **Idioma estricto**:
   * Toda la documentación, comentarios, cadenas visibles en la interfaz y mensajes de consola deben estar redactados en **castellano**.
3. **No regresión funcional**:
   * No eliminar soporte para ninguno de los 6 formatos admitidos.
   * Preservar los argumentos de línea de comandos de la CLI (`-r`, `-f`, `-o`, `--version`) y del servidor (`--port`, `--no-browser`).
4. **Seguridad y privacidad**:
   * Nunca incorporar llamadas de red salientes, servicios en la nube o analíticas.
   * Validar límites de tamaño (máximo 40 MB por archivo en web).
5. **Autovalidación**:
   * Tras cualquier edición en Python, compilar el archivo con `python -m py_compile <archivo.py>` para garantizar que no existan errores de sintaxis.
   * No se considera terminada una tarea sin ejecutar la CLI contra al menos un archivo de cada formato tocado.
6. **Fuente única de verdad**:
   * La lista de extensiones admitidas vive solo en `extractor.engine.SUPPORTED_EXTENSIONS`; el límite de tamaño, solo en `extractor.config.MAX_FILE_SIZE`. Cualquier otro literal equivalente (JavaScript, HTML, documentación) debe derivarse de esas constantes.
   * Los nombres de campo del contrato (§4) solo pueden definirse en los diccionarios de `src/extractor/engine.py` y en `csv_row`; el frontend los consume, no los reescribe.
7. **Estado de la interfaz**:
   * El estado de la sesión web reside en la estructura `records`; el DOM es una representación derivada y siempre reconstruible a partir de ella.
8. **Organización del código**:
   * El código de la aplicación vive exclusivamente en `src/extractor/`; no se admiten módulos sueltos en la raíz.
   * Las pruebas van en `tests/` y las herramientas de compilación e instalación en `scripts/`.
   * Toda funcionalidad nueva entra con su prueba en `tests/`; `python -m unittest discover -s tests` debe seguir en verde.

---

## 6. Códigos de Salida de la CLI

| Código | Significado |
| :--- | :--- |
| `0` | Proceso finalizado sin incidencias: todos los archivos se procesaron y ninguno produjo error. |
| `1` | Al menos un archivo presentó error de extracción, o hubo errores de descubrimiento de rutas. |
| `2` | Fallo crítico: no se pudo escribir el resultado en `-o` (deja el error en `stderr`). |

Los errores de extracción **no abortan** el lote (RF-07): se informan por `stderr`, se registran en el objeto de salida y el resto de archivos continúa procesándose.


