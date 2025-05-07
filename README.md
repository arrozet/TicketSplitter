# TicketSplitter API

Aplicación para dividir los gastos de un ticket o factura entre varias personas.

## Funcionalidades

- Carga de imagen del ticket.
- Procesamiento OCR para extraer texto.
- Identificación de artículos y precios.
- Asignación de artículos a participantes.
- Cálculo de la parte de cada participante.

## Stack Tecnológico

- Backend: Python, FastAPI
- Frontend: HTML, CSS (Bulma), JavaScript
- OCR: Tesseract

## ¡IMPORTANTE! Requisito: Tesseract OCR

Esta aplicación **REQUIERE** que Tesseract OCR esté instalado en el sistema donde se ejecuta el backend.

- **Instalación**: Sigue las instrucciones para tu sistema operativo (ver la documentación de Tesseract o guías online).
  - Windows: Descarga desde [UB Mannheim Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki). **Asegúrate de añadir Tesseract al PATH del sistema durante la instalación.**
  - Linux (Ubuntu/Debian): `sudo apt install tesseract-ocr tesseract-ocr-spa` (incluye español).
  - macOS (Homebrew): `brew install tesseract tesseract-lang`.
- **Idiomas**: Asegúrate de instalar los paquetes de idiomas necesarios (ej. español `spa`).
- **Verificación**: Después de instalar, abre una nueva terminal y ejecuta `tesseract --version`. Si el comando es reconocido, está correctamente instalado en el PATH.
- **Alternativa (Variable de Entorno)**: Si no puedes añadirlo al PATH, puedes definir la variable de entorno `TESSERACT_PATH` con la ruta completa al ejecutable `tesseract` (ej. `C:\Program Files\Tesseract-OCR\tesseract.exe`).

Si Tesseract no está correctamente instalado y accesible, la funcionalidad de subida de tickets fallará con un error 500.

## Próximos pasos
1. Configurar el entorno virtual.
2. Instalar dependencias de Python: `pip install -r requirements.txt`
3. **Verificar la instalación de Tesseract OCR (ver sección IMPORTANTE arriba).**
4. Ejecutar la aplicación backend: `uvicorn app.main:app --reload`
5. Servir el frontend (ver instrucciones previas, ej. `python -m http.server 8080` desde `frontend/`)
