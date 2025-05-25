# TicketSplitter API

Aplicación para dividir los gastos de un ticket o factura entre varias personas.

## Funcionalidades

- Carga de imagen del ticket.
- Procesamiento OCR para extraer texto usando Gemini AI.
- Identificación de artículos y precios.
- Asignación de artículos a participantes.
- Cálculo de la parte de cada participante.
- **NUEVA UI moderna** con Astro + shadcn/ui + Tailwind CSS.

## Stack Tecnológico

- Backend: Python, FastAPI
- Frontend: **Astro, React, shadcn/ui, Tailwind CSS**
- OCR: Google Gemini AI

## ¡IMPORTANTE! Requisito: API Key de Gemini

Esta aplicación **REQUIERE** una API key de Google Gemini configurada como variable de entorno.

1. **Obtener API Key**: Ve a https://makersuite.google.com/app/apikey y crea una nueva API key.
2. **Configurar Variable de Entorno**:
   - **Temporal (solo para la sesión actual)**:
     ```powershell
     $env:GEMINI_API_KEY="tu-api-key-aquí"
     ```
   - **Permanente**: 
     - Panel de Control → Sistema → Configuración avanzada → Variables de entorno
     - Añadir nueva variable de usuario: `GEMINI_API_KEY` con tu API key

## Instalación y Ejecución

### Backend (FastAPI)

1. **Configurar el entorno virtual**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # En Windows
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar la API key de Gemini** (ver sección anterior).

4. **Ejecutar el backend**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend (Astro + shadcn/ui)

1. **Navegar al directorio del frontend**:
   ```bash
   cd frontend-new
   ```

2. **Instalar dependencias**:
   ```bash
   npm install
   ```

3. **Ejecutar el frontend**:
   ```bash
   npm run dev
   ```

## Acceso a la Aplicación

- **Frontend moderno**: http://localhost:4321 (Astro)
- **Frontend clásico**: http://localhost:8080 (si usas `python -m http.server 8080` desde `frontend/`)
- **Backend API**: http://localhost:8000
- **Documentación API**: http://localhost:8000/docs

## Características de la Nueva UI

✨ **Interfaz moderna y responsive** con shadcn/ui
🎨 **Diseño elegante** con gradientes y animaciones
📱 **Totalmente responsive** para móviles y tablets
🔄 **Indicador de progreso** visual por pasos
⚡ **Componentes reutilizables** y bien estructurados
🌙 **Soporte para modo oscuro**
🎯 **UX mejorada** con mejor feedback visual

## Estructura del Proyecto

```
TicketSplitter/
├── app/                    # Backend FastAPI
├── frontend/              # Frontend clásico (HTML/JS)
├── frontend-new/          # Frontend moderno (Astro + shadcn/ui)
│   ├── src/
│   │   ├── components/    # Componentes React
│   │   ├── layouts/       # Layouts de Astro
│   │   ├── pages/         # Páginas de Astro
│   │   └── styles/        # Estilos globales
├── tests/                 # Tests
└── requirements.txt       # Dependencias Python
```

## Desarrollo

Para desarrollo, ejecuta ambos servidores:
1. Backend en puerto 8000
2. Frontend en puerto 4321 (Astro) o 8080 (clásico)

La nueva UI en Astro ofrece una experiencia mucho más moderna y profesional.

