from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import receipts
# En el futuro, podríamos añadir más routers aquí, por ejemplo, para usuarios o grupos:
# from app.api.endpoints import users, groups

app = FastAPI(
    title="TicketSplitter API",
    description="API para dividir tickets y facturas.",
    version="0.1.0"
)

# Configuración de CORS (Cross-Origin Resource Sharing)
# Permite que el frontend (servido desde un origen diferente) interactúe con esta API.
# Para desarrollo, permitir todos los orígenes ("*") es común.
# Para producción, se debería restringir a los orígenes específicos del frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lista de orígenes permitidos (ej. ["http://localhost:8080", "https://tusitio.com"])
    allow_credentials=True, # Permitir cookies y cabeceras de autorización
    allow_methods=["*"],  # Métodos HTTP permitidos (GET, POST, PUT, etc.)
    allow_headers=["*"],  # Cabeceras HTTP permitidas
)

# Incluir routers de los diferentes módulos de la API
# Cada router agrupa endpoints relacionados (ej. todos los de /receipts)
app.include_router(receipts.router, prefix="/api/v1/receipts", tags=["Receipts"])
# Ejemplo para futuros routers:
# app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(groups.router, prefix="/api/v1/groups", tags=["Groups"])

@app.get("/health", tags=["Health"])
async def healthCheck():
    """Endpoint simple para verificar que la API está funcionando."""
    return {"status": "ok"} 