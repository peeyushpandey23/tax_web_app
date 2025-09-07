import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.database import db_manager
from app.models import UserFinancialsCreate, DraftResponse
from app.services.pdf_processor import pdf_processor
from app.services.salary_aggregator import salary_aggregator
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)

@router.post("/upload")
async def upload_documents(
    document_type: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Upload and process PDF documents (salary slips or Form 16)
    """
    try:
        # Validate file count
        if len(files) > 4:
            raise HTTPException(status_code=400, detail="Maximum 4 files allowed")
        
        # Validate file types and sizes
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF file")
            
            if file.size > settings.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"{file.filename} exceeds maximum file size")
        
        # Process uploaded files
        processed_files = []
        extracted_data_list = []
        
        for file in files:
            # Generate unique filename
            file_extension = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(settings.UPLOAD_FOLDER, unique_filename)
            
            try:
                # Save file temporarily
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    buffer.write(content)
                
                # Process PDF
                result = await pdf_processor.process_pdf(file_path, document_type)
                
                if result['success']:
                    processed_files.append({
                        'filename': file.filename,
                        'extracted_data': result['extracted_data'],
                        'document_type': result['document_type']
                    })
                    extracted_data_list.append(result['extracted_data'])
                else:
                    logger.error(f"Failed to process {file.filename}: {result.get('error', 'Unknown error')}")
                    raise HTTPException(status_code=400, detail=f"Failed to process {file.filename}")
                
            finally:
                # Clean up temporary file immediately
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        # Aggregate salary data
        if document_type in ['salary_slip_single', 'salary_slip_multiple']:
            final_data = await salary_aggregator.aggregate_salary_slips(extracted_data_list, 'salary_slip')
        else:
            final_data = await salary_aggregator.aggregate_salary_slips(extracted_data_list, 'form16')
        
        # Generate processing summary
        processing_summary = await salary_aggregator.get_processing_summary(extracted_data_list, final_data)
        
        # Create session ID
        session_id = str(uuid.uuid4())
        
        # Store in database as draft
        await save_financial_data_draft(session_id, final_data)
        
        logger.info(f"Successfully processed {len(files)} files for session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "extracted_data": final_data,
            "processing_summary": processing_summary,
            "message": f"Successfully processed {len(files)} document(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload processing failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during document processing")

@router.post("/submit-financials")
async def submit_financials(financial_data: UserFinancialsCreate):
    """
    Submit final financial data and mark as completed
    """
    try:
        # Generate session ID if not provided
        if not hasattr(financial_data, 'session_id') or not financial_data.session_id:
            session_id = str(uuid.uuid4())
        else:
            session_id = financial_data.session_id
        
        # Convert to database format
        db_data = {
            "session_id": session_id,
            "gross_salary": float(financial_data.gross_salary),
            "basic_salary": float(financial_data.basic_salary),
            "hra_received": float(financial_data.hra_received),
            "rent_paid": float(financial_data.rent_paid),
            "deduction_80c": float(financial_data.deduction_80c),
            "deduction_80d": float(financial_data.deduction_80d),
            "standard_deduction": float(financial_data.standard_deduction),
            "professional_tax": float(financial_data.professional_tax),
            "tds": float(financial_data.tds),
            "status": "completed",
            "is_draft": False,
            "draft_expires_at": None
        }
        
        # Insert or update in database using REST API
        try:
            # Try to update existing record
            await db_manager.adapter.update("UserFinancials", db_data, {"session_id": session_id})
        except:
            # If update fails, insert new record
            await db_manager.adapter.insert("UserFinancials", db_data)
        
        logger.info(f"Financial data submitted successfully for session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Financial data submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit financial data: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit financial data")

@router.post("/save-draft")
async def save_draft(financial_data: UserFinancialsCreate):
    """
    Save financial data as draft
    """
    try:
        # Generate session ID if not provided
        if not hasattr(financial_data, 'session_id') or not financial_data.session_id:
            session_id = str(uuid.uuid4())
        else:
            session_id = financial_data.session_id
        
        # Set draft expiration (7 days from now)
        draft_expires_at = datetime.utcnow() + timedelta(days=7)
        
        # Convert to database format
        db_data = {
            "session_id": session_id,
            "gross_salary": float(financial_data.gross_salary),
            "basic_salary": float(financial_data.basic_salary),
            "hra_received": float(financial_data.hra_received),
            "rent_paid": float(financial_data.rent_paid),
            "deduction_80c": float(financial_data.deduction_80c),
            "deduction_80d": float(financial_data.deduction_80d),
            "standard_deduction": float(financial_data.standard_deduction),
            "professional_tax": float(financial_data.professional_tax),
            "tds": float(financial_data.tds),
            "status": "draft",
            "is_draft": True,
            "draft_expires_at": draft_expires_at.isoformat()
        }
        
        # Insert or update in database using REST API
        try:
            # Try to update existing record
            await db_manager.adapter.update("UserFinancials", db_data, {"session_id": session_id})
        except:
            # If update fails, insert new record
            await db_manager.adapter.insert("UserFinancials", db_data)
        
        logger.info(f"Draft saved successfully for session {session_id}")
        
        return DraftResponse(
            draft_id=session_id,
            message="Draft saved successfully",
            expires_at=draft_expires_at
        )
        
    except Exception as e:
        logger.error(f"Failed to save draft: {e}")
        raise HTTPException(status_code=500, detail="Failed to save draft")

@router.get("/drafts")
async def get_drafts():
    """
    Get all available drafts
    """
    try:
        # Get drafts using REST API
        drafts = await db_manager.adapter.fetch_all("UserFinancials", {
            "is_draft": True,
            "status": "draft"
        })
        
        # Convert to response format
        draft_list = []
        for draft in drafts:
            draft_list.append({
                "draft_id": draft["session_id"],
                "financial_data": {
                    "gross_salary": draft["gross_salary"],
                    "basic_salary": draft["basic_salary"],
                    "hra_received": draft["hra_received"],
                    "rent_paid": draft["rent_paid"],
                    "deduction_80c": draft["deduction_80c"],
                    "deduction_80d": draft["deduction_80d"],
                    "standard_deduction": draft["standard_deduction"],
                    "professional_tax": draft["professional_tax"],
                    "tds": draft["tds"]
                },
                "created_at": draft["created_at"],
                "expires_at": draft["draft_expires_at"]
            })
        
        return draft_list
        
    except Exception as e:
        logger.error(f"Failed to retrieve drafts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve drafts")

@router.get("/draft/{draft_id}")
async def get_draft(draft_id: str):
    """
    Get specific draft by ID
    """
    try:
        # Get draft using REST API
        draft = await db_manager.adapter.fetch_one("UserFinancials", {"session_id": draft_id})
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found or expired")
        
        return {
            "draft_id": draft["session_id"],
            "financial_data": {
                "gross_salary": draft["gross_salary"],
                "basic_salary": draft["basic_salary"],
                "hra_received": draft["hra_received"],
                "rent_paid": draft["rent_paid"],
                "deduction_80c": draft["deduction_80c"],
                "deduction_80d": draft["deduction_80d"],
                "standard_deduction": draft["standard_deduction"],
                "professional_tax": draft["professional_tax"],
                "tds": draft["tds"]
            },
            "created_at": draft["created_at"],
            "expires_at": draft["draft_expires_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve draft {draft_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve draft")

async def save_financial_data_draft(session_id: str, financial_data: dict):
    """
    Helper function to save financial data as draft during upload
    """
    try:
        draft_expires_at = datetime.utcnow() + timedelta(days=7)
        
        db_data = {
            "session_id": session_id,
            "gross_salary": financial_data.get('gross_salary', 0),
            "basic_salary": financial_data.get('basic_salary', 0),
            "hra_received": financial_data.get('hra_received', 0),
            "rent_paid": financial_data.get('rent_paid', 0),
            "deduction_80c": financial_data.get('deduction_80c', 0),
            "deduction_80d": financial_data.get('deduction_80d', 0),
            "standard_deduction": financial_data.get('standard_deduction', 50000),
            "professional_tax": financial_data.get('professional_tax', 0),
            "tds": financial_data.get('tds', 0),
            "status": "draft",
            "is_draft": True,
            "draft_expires_at": draft_expires_at.isoformat()
        }
        
        await db_manager.adapter.insert("UserFinancials", db_data)
        logger.info(f"Financial data draft saved for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to save financial data draft: {e}")
        # Don't raise exception here as it's not critical for the upload process

