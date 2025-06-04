# TicketSplitter API

A powerful and intuitive application designed to simplify the process of splitting bills and receipts among groups. Whether you're dining out with friends, sharing household expenses, or managing group purchases, TicketSplitter makes it effortless to divide costs fairly and accurately.

## Core Features

- **Smart Receipt Processing**:
  - Upload any receipt or bill image
  - Advanced OCR processing powered by Google's Gemini AI
  - Automatic extraction of items, quantities, and prices
  - Support for various receipt formats and layouts

- **Intelligent Item Management**:
  - Automatic item categorization
  - Smart price detection and validation
  - Support for multiple currencies
  - Handling of special cases like discounts and taxes

- **Flexible Group Management**:
  - Add/remove participants dynamically
  - Assign items to specific participants
  - Handle shared items and split costs
  - Support for different payment methods

- **Advanced Calculations**:
  - Real-time cost distribution
  - Support for different splitting methods (equal, custom, percentage-based)
  - Tax and tip calculations
  - Detailed breakdown of individual shares

- **Modern User Experience**:
  - **NEW modern UI** with Astro + shadcn/ui + Tailwind CSS
  - Responsive design for all devices
  - Dark mode support
  - Intuitive step-by-step process
  - Real-time updates and calculations

## Tech Stack

- **Backend**: 
  - Python 3.x
  - FastAPI for high-performance API endpoints
  - Pydantic for data validation
  - Async support for better performance

- **Frontend**: 
  - **Astro** for optimal performance
  - **React** for interactive components
  - **shadcn/ui** for beautiful UI components
  - **Tailwind CSS** for responsive styling

- **AI/ML**:
  - Google Gemini AI for advanced OCR processing
  - Intelligent text extraction and parsing
  - Natural language understanding for receipt analysis

## IMPORTANT! Requirement: Gemini API Key

This application **REQUIRES** a Google Gemini API key configured as an environment variable.

1.  **Get API Key**: Go to https://makersuite.google.com/app/apikey and create a new API key.
2.  **Set Environment Variable**:
    -   **Temporary (current session only)**:
        ```powershell
        $env:GEMINI_API_KEY="your-api-key-here"
        ```
    -   **Permanent**:
        -   Control Panel → System → Advanced system settings → Environment Variables
        -   Add a new user variable: `GEMINI_API_KEY` with your API key.

## Installation and Execution

### Backend (FastAPI)

1.  **Set up the virtual environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # On Windows
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up the Gemini API key** (see previous section).

4.  **Run the backend**:
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```

### Frontend (Astro + shadcn/ui)

1.  **Navigate to the frontend directory**:
    ```bash
    cd frontend-new
    ```

2.  **Install dependencies**:
    ```bash
    npm install
    ```

3.  **Run the frontend**:
    ```bash
    npm run dev
    ```

## Running Tests

### Python Tests (from the project root)
```bash
pytest --cov=app --cov-branch --cov-report=html tests/
```

### End-to-End (E2E) Tests (from the project root)
First, set the environment variable:
```powershell
$env:K6_BROWSER_HEADLESS="false" 
```
Then, run the k6 tests:
```bash
k6 run tests/test_e2e.js
```

## Accessing the Application

-   **Modern Frontend**: http://localhost:4321 (Astro)
-   **Classic Frontend**: http://localhost:8080 (if you use `python -m http.server 8080` from `frontend/`)
-   **Backend API**: http://localhost:8000
-   **API Documentation**: http://localhost:8000/docs

## New UI Features

✨ **Modern and responsive interface** with shadcn/ui
🎨 **Elegant design** with gradients and animations
📱 **Fully responsive** for mobile and tablets
🔄 **Visual progress indicator** by steps
⚡ **Reusable and well-structured components**
🌙 **Dark mode support**
🎯 **Improved UX** with better visual feedback

## Project Structure

```
TicketSplitter/
├── app/                    # Backend FastAPI
│   ├── api/               # API endpoints
│   │   └── endpoints/     # Route handlers
│   ├── models/           # Data models
│   └── services/         # Business logic
├── frontend-new/         # Modern Frontend (Astro + shadcn/ui)
│   ├── src/
│   │   ├── components/   # React Components
│   │   │   └── ui/      # shadcn/ui components
│   │   ├── layouts/     # Astro Layouts
│   │   ├── pages/       # Astro Pages
│   │   └── styles/      # Global Styles
│   └── public/          # Static assets
├── tests/               # Test suite
│   ├── api/            # API tests
│   ├── models/         # Model tests
│   └── services/       # Service tests
├── docs/               # Documentation
└── requirements.txt    # Python Dependencies
```

## Development

For development, run both servers:
1.  Backend on port 8000
2.  Frontend on port 4321 (Astro) or 8080 (classic)

The new UI in Astro offers a much more modern and professional experience.

