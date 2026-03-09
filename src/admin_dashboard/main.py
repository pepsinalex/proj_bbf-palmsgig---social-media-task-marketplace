"""Admin Dashboard FastAPI Application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Admin Dashboard Service",
    description="Admin Dashboard API for task management system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Admin Dashboard Service is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "admin-dashboard"}

@app.get("/admin/dashboard")
async def get_dashboard():
    return {
        "dashboard": "admin",
        "stats": {
            "total_users": 0,
            "total_tasks": 0,
            "active_sessions": 0
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)