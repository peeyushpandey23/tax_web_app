from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import os

from app.config import settings
from app.database import db_manager
from app.models import HealthCheck, ErrorResponse
from app.routes.upload import router as upload_router
from app.routes.tax_calculation import router as tax_calculation_router
from app.routes.ai_advisor import router as ai_advisor_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Tax Advisor Application...")
    try:
        # Test database connection
        db_status = await db_manager.test_connection()
        if db_status:
            # Create tables if they don't exist
            await db_manager.create_tables()
            logger.info("Database tables created/verified successfully")
        else:
            logger.error("Database connection failed")
    except Exception as e:
        logger.error(f"Startup error: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Tax Advisor Application...")
    try:
        await db_manager.close_pool()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered tax advisor application for Indian salaried professionals",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Health check endpoint
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    try:
        db_status = await db_manager.test_connection()
        return HealthCheck(
            status="healthy" if db_status else "unhealthy",
            timestamp=datetime.utcnow(),
            database="connected" if db_status else "disconnected",
            version=settings.APP_VERSION
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            database="error",
            version=settings.APP_VERSION
        )

# Landing page route
@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page route"""
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering landing page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return templates.TemplateResponse(
        "error.html", 
        {
            "request": request, 
            "error_code": 404,
            "error_message": "Page not found"
        },
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handle 500 errors"""
    return templates.TemplateResponse(
        "error.html", 
        {
            "request": request, 
            "error_code": 500,
            "error_message": "Internal server error"
        },
        status_code=500
    )

# Include API routes
app.include_router(upload_router)
app.include_router(tax_calculation_router)
app.include_router(ai_advisor_router)

# Root endpoint
@app.get("/api/")
async def root():
    """Root API endpoint"""
    return {
        "message": "Tax Advisor Application API",
        "version": settings.APP_VERSION,
        "status": "running"
    }

# Upload page route
@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Upload page route"""
    try:
        return templates.TemplateResponse("upload.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering upload page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Review form page route
@app.get("/review-form", response_class=HTMLResponse)
async def review_form_page(request: Request):
    """Review form page route"""
    try:
        return templates.TemplateResponse("review_form.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering review form page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Tax results page route
@app.get("/tax-results", response_class=HTMLResponse)
async def tax_results_page(request: Request):
    """Tax results page route"""
    try:
        return templates.TemplateResponse("tax_results.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering tax results page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# AI Advisor page route (Phase 4 - Coming Soon)
@app.get("/ai-advisor", response_class=HTMLResponse)
async def ai_advisor_page(request: Request):
    """AI Advisor page route - Phase 4 feature"""
    try:
        return templates.TemplateResponse("ai_advisor_coming_soon.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering AI advisor page: {e}")
        # Fallback to a simple HTML response
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Advisor - Coming Soon</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .container { max-width: 600px; margin: 0 auto; }
                .coming-soon { color: #007bff; font-size: 2em; margin-bottom: 20px; }
                .description { color: #666; font-size: 1.1em; line-height: 1.6; }
                .back-button { margin-top: 30px; }
                .btn { background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }
                .btn:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="coming-soon">🤖 AI Advisor</h1>
                <h2>Coming Soon!</h2>
                <div class="description">
                    <p>The AI Advisor feature is currently under development as part of Phase 4.</p>
                    <p>This feature will provide personalized tax-saving recommendations and financial advice based on your data.</p>
                    <p>For now, you can view your tax calculation results and regime comparison.</p>
                </div>
                <div class="back-button">
                    <a href="/tax-results" class="btn">Back to Tax Results</a>
                </div>
            </div>
        </body>
        </html>
        """, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
