import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import PyPDF2

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

@router.post("/check-pdf-password")
async def check_pdf_password(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Check if a PDF file is password-protected
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Check if PDF is password-protected
            with open(temp_file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                is_encrypted = pdf_reader.is_encrypted
                
                logger.info(f"PDF password check for {file.filename}: encrypted={is_encrypted}")
                
                return {
                    "success": True,
                    "filename": file.filename,
                    "is_password_protected": is_encrypted,
                    "message": "Password-protected PDF detected" if is_encrypted else "PDF is not password-protected"
                }
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        logger.error(f"Error checking PDF password protection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check PDF: {str(e)}")

@router.post("/upload")
async def upload_documents(
    request: Request,
    document_type: str = Form(...),
    files: List[UploadFile] = File(...),
    pdf_password: Optional[str] = Form(None)
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
                result = await pdf_processor.process_pdf(file_path, document_type, pdf_password)
                
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
        
        # Extract user_id from headers
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            logger.warning("No user_id provided in headers, using session_id as fallback")
            user_id = session_id
        
        # Store in database as draft
        await save_financial_data_draft(session_id, final_data, user_id)
        
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
        logger.info(f"Received financial data submission: {financial_data.model_dump()}")
        
        # Generate session ID if not provided
        if not hasattr(financial_data, 'session_id') or not financial_data.session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session ID: {session_id}")
        else:
            session_id = str(financial_data.session_id)
            logger.info(f"Using existing session ID: {session_id}")
        
        # Convert to database format (Pydantic already validates these as Decimal)
        db_data = {
            "session_id": session_id,
            "financial_year": financial_data.financial_year,
            "age": financial_data.age,
            "gross_salary": float(financial_data.gross_salary),
            "basic_salary": float(financial_data.basic_salary),
            "hra_received": float(financial_data.hra_received),
            "rent_paid": float(financial_data.rent_paid),
            "lta_received": float(financial_data.lta_received),
            "other_exemptions": float(financial_data.other_exemptions),
            "deduction_80c": float(financial_data.deduction_80c),
            "deduction_80d": float(financial_data.deduction_80d),
            "deduction_80dd": float(financial_data.deduction_80dd),
            "deduction_80e": float(financial_data.deduction_80e),
            "deduction_80tta": float(financial_data.deduction_80tta),
            "home_loan_interest": float(financial_data.home_loan_interest),
            "other_deductions": float(financial_data.other_deductions) if financial_data.other_deductions is not None else 0,
            "other_income": float(financial_data.other_income) if financial_data.other_income is not None else 0,
            "standard_deduction": float(financial_data.standard_deduction),
            "professional_tax": float(financial_data.professional_tax),
            "tds": float(financial_data.tds),
            "status": "completed",
            "is_draft": False,
            "draft_expires_at": None
        }
        
        # Insert or update in database
        query = """
        INSERT INTO "UserFinancials" (
            session_id, financial_year, age, gross_salary, basic_salary, hra_received, rent_paid,
            lta_received, other_exemptions, deduction_80c, deduction_80d, deduction_80dd,
            deduction_80e, deduction_80tta, home_loan_interest, other_deductions, other_income,
            standard_deduction, professional_tax, tds, status, is_draft, draft_expires_at, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, NOW()
        )
        ON CONFLICT (session_id) DO UPDATE SET
            financial_year = EXCLUDED.financial_year,
            age = EXCLUDED.age,
            gross_salary = EXCLUDED.gross_salary,
            basic_salary = EXCLUDED.basic_salary,
            hra_received = EXCLUDED.hra_received,
            rent_paid = EXCLUDED.rent_paid,
            lta_received = EXCLUDED.lta_received,
            other_exemptions = EXCLUDED.other_exemptions,
            deduction_80c = EXCLUDED.deduction_80c,
            deduction_80d = EXCLUDED.deduction_80d,
            deduction_80dd = EXCLUDED.deduction_80dd,
            deduction_80e = EXCLUDED.deduction_80e,
            deduction_80tta = EXCLUDED.deduction_80tta,
            home_loan_interest = EXCLUDED.home_loan_interest,
            other_deductions = EXCLUDED.other_deductions,
            other_income = EXCLUDED.other_income,
            standard_deduction = EXCLUDED.standard_deduction,
            professional_tax = EXCLUDED.professional_tax,
            tds = EXCLUDED.tds,
            status = EXCLUDED.status,
            is_draft = EXCLUDED.is_draft,
            draft_expires_at = EXCLUDED.draft_expires_at
        """
        
        logger.info(f"Executing database query with data: {db_data}")
        await db_manager.execute_query(
            query,
            db_data["session_id"], db_data["financial_year"], db_data["age"],
            db_data["gross_salary"], db_data["basic_salary"], db_data["hra_received"], 
            db_data["rent_paid"], db_data["lta_received"], db_data["other_exemptions"],
            db_data["deduction_80c"], db_data["deduction_80d"], db_data["deduction_80dd"],
            db_data["deduction_80e"], db_data["deduction_80tta"], db_data["home_loan_interest"],
            db_data["other_deductions"], db_data["other_income"], db_data["standard_deduction"],
            db_data["professional_tax"], db_data["tds"], db_data["status"], 
            db_data["is_draft"], db_data["draft_expires_at"]
        )
        
        logger.info(f"Financial data submitted successfully for session {session_id}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Financial data submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit financial data: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to submit financial data: {str(e)}")

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
            "financial_year": financial_data.financial_year,
            "age": financial_data.age,
            "gross_salary": float(financial_data.gross_salary),
            "basic_salary": float(financial_data.basic_salary),
            "hra_received": float(financial_data.hra_received),
            "rent_paid": float(financial_data.rent_paid),
            "lta_received": float(financial_data.lta_received),
            "other_exemptions": float(financial_data.other_exemptions),
            "deduction_80c": float(financial_data.deduction_80c),
            "deduction_80d": float(financial_data.deduction_80d),
            "deduction_80dd": float(financial_data.deduction_80dd),
            "deduction_80e": float(financial_data.deduction_80e),
            "deduction_80tta": float(financial_data.deduction_80tta),
            "home_loan_interest": float(financial_data.home_loan_interest),
            "other_deductions": float(financial_data.other_deductions) if financial_data.other_deductions is not None else 0,
            "other_income": float(financial_data.other_income) if financial_data.other_income is not None else 0,
            "standard_deduction": float(financial_data.standard_deduction),
            "professional_tax": float(financial_data.professional_tax),
            "tds": float(financial_data.tds),
            "status": "draft",
            "is_draft": True,
            "draft_expires_at": draft_expires_at
        }
        
        # Insert or update in database
        query = """
        INSERT INTO "UserFinancials" (
            session_id, financial_year, age, gross_salary, basic_salary, hra_received, rent_paid,
            lta_received, other_exemptions, deduction_80c, deduction_80d, deduction_80dd,
            deduction_80e, deduction_80tta, home_loan_interest, other_deductions, other_income,
            standard_deduction, professional_tax, tds, status, is_draft, draft_expires_at, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, NOW()
        )
        ON CONFLICT (session_id) DO UPDATE SET
            financial_year = EXCLUDED.financial_year,
            age = EXCLUDED.age,
            gross_salary = EXCLUDED.gross_salary,
            basic_salary = EXCLUDED.basic_salary,
            hra_received = EXCLUDED.hra_received,
            rent_paid = EXCLUDED.rent_paid,
            lta_received = EXCLUDED.lta_received,
            other_exemptions = EXCLUDED.other_exemptions,
            deduction_80c = EXCLUDED.deduction_80c,
            deduction_80d = EXCLUDED.deduction_80d,
            deduction_80dd = EXCLUDED.deduction_80dd,
            deduction_80e = EXCLUDED.deduction_80e,
            deduction_80tta = EXCLUDED.deduction_80tta,
            home_loan_interest = EXCLUDED.home_loan_interest,
            other_deductions = EXCLUDED.other_deductions,
            other_income = EXCLUDED.other_income,
            standard_deduction = EXCLUDED.standard_deduction,
            professional_tax = EXCLUDED.professional_tax,
            tds = EXCLUDED.tds,
            status = EXCLUDED.status,
            is_draft = EXCLUDED.is_draft,
            draft_expires_at = EXCLUDED.draft_expires_at
        """
        
        await db_manager.execute_query(
            query,
            db_data["session_id"], db_data["financial_year"], db_data["age"],
            db_data["gross_salary"], db_data["basic_salary"], db_data["hra_received"], 
            db_data["rent_paid"], db_data["lta_received"], db_data["other_exemptions"],
            db_data["deduction_80c"], db_data["deduction_80d"], db_data["deduction_80dd"],
            db_data["deduction_80e"], db_data["deduction_80tta"], db_data["home_loan_interest"],
            db_data["other_deductions"], db_data["other_income"], db_data["standard_deduction"],
            db_data["professional_tax"], db_data["tds"], db_data["status"], 
            db_data["is_draft"], db_data["draft_expires_at"]
        )
        
        logger.info(f"Draft saved successfully for session {session_id}")
        
        return DraftResponse(
            draft_id=session_id,
            message="Draft saved successfully",
            expires_at=draft_expires_at
        )
        
    except Exception as e:
        logger.error(f"Failed to save draft: {e}")
        raise HTTPException(status_code=500, detail="Failed to save draft")

@router.get("/debug-drafts")
async def debug_drafts(request: Request):
    """Debug endpoint to see all drafts in database"""
    try:
        user_id = request.headers.get('X-User-ID')
        
        # Get all drafts regardless of user
        query = """
        SELECT session_id, user_id, gross_salary, created_at, is_draft, status
        FROM "UserFinancials"
        WHERE is_draft = TRUE
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        drafts = await db_manager.fetch_all(query)
        logger.info(f"Found {len(drafts)} total drafts in database")
        
        # Count drafts per user
        user_draft_counts = {}
        for draft in drafts:
            uid = draft.get('user_id', 'NULL')
            user_draft_counts[uid] = user_draft_counts.get(uid, 0) + 1
        
        return {
            "total_drafts": len(drafts),
            "drafts": drafts,
            "current_user_id": user_id,
            "drafts_per_user": user_draft_counts,
            "note": "After cleanup, each user should have max 1 draft"
        }
        
    except Exception as e:
        logger.error(f"Debug drafts failed: {e}")
        return {"error": str(e)}

@router.get("/test-drafts")
async def test_drafts(request: Request):
    """Test endpoint to debug draft issues"""
    user_id = request.headers.get('X-User-ID')
    logger.info(f"Test endpoint called - user_id from header: {user_id}")
    logger.info(f"All headers: {dict(request.headers)}")
    return {
        "user_id_from_header": user_id,
        "all_headers": dict(request.headers),
        "message": "Test endpoint working"
    }

@router.get("/drafts")
async def get_drafts(request: Request):
    """
    Get drafts for the current user and clean up old drafts if multiple exist
    """
    try:
        # Extract user_id from headers
        user_id = request.headers.get('X-User-ID')
        logger.info(f"Drafts endpoint called - user_id from header: {user_id}")
        logger.info(f"Drafts endpoint headers: {dict(request.headers)}")
        
        if not user_id:
            logger.warning("No user_id provided in headers for drafts request")
            return []
        
        # First, check how many drafts exist for this user
        count_query = """
        SELECT COUNT(*) as draft_count
        FROM "UserFinancials"
        WHERE is_draft = TRUE AND user_id = $1
        AND (draft_expires_at IS NULL OR draft_expires_at > NOW())
        """
        
        count_result = await db_manager.fetch_one(count_query, user_id)
        draft_count = count_result['draft_count'] if count_result else 0
        
        logger.info(f"Found {draft_count} drafts for user {user_id}")
        
        # If multiple drafts exist, clean up old ones (keep only the latest)
        if draft_count > 1:
            logger.info(f"Multiple drafts found ({draft_count}), cleaning up old ones...")
            cleanup_query = """
            WITH latest_draft AS (
                SELECT session_id
                FROM "UserFinancials"
                WHERE is_draft = TRUE AND user_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            )
            DELETE FROM "UserFinancials"
            WHERE is_draft = TRUE 
            AND user_id = $1 
            AND session_id NOT IN (SELECT session_id FROM latest_draft)
            """
            
            await db_manager.execute_query(cleanup_query, user_id)
            logger.info(f"Cleaned up old drafts for user {user_id}, kept only the latest one")
        
        # Now get the remaining draft(s) - should be 0 or 1
        query = """
        SELECT session_id, financial_year, age, gross_salary, basic_salary, hra_received, rent_paid,
               lta_received, other_exemptions, deduction_80c, deduction_80d, deduction_80dd,
               deduction_80e, deduction_80tta, home_loan_interest, other_deductions,
               other_income, standard_deduction, professional_tax, tds,
               created_at, draft_expires_at
        FROM "UserFinancials"
        WHERE is_draft = TRUE AND status = 'draft'
        AND (draft_expires_at IS NULL OR draft_expires_at > NOW())
        AND user_id = $1
        ORDER BY created_at DESC
        """
        
        drafts = await db_manager.fetch_all(query, user_id)
        logger.info(f"Returning {len(drafts)} draft(s) for user {user_id}")
        
        # Convert to response format
        draft_list = []
        for draft in drafts:
            draft_list.append({
                "draft_id": draft["session_id"],
                "financial_data": {
                    "financial_year": draft["financial_year"],
                    "age": draft["age"],
                    "gross_salary": draft["gross_salary"],
                    "basic_salary": draft["basic_salary"],
                    "hra_received": draft["hra_received"],
                    "rent_paid": draft["rent_paid"],
                    "lta_received": draft["lta_received"],
                    "other_exemptions": draft["other_exemptions"],
                    "deduction_80c": draft["deduction_80c"],
                    "deduction_80d": draft["deduction_80d"],
                    "deduction_80dd": draft["deduction_80dd"],
                    "deduction_80e": draft["deduction_80e"],
                    "deduction_80tta": draft["deduction_80tta"],
                    "home_loan_interest": draft["home_loan_interest"],
                    "other_deductions": draft["other_deductions"],
                    "other_income": draft["other_income"],
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
async def get_draft(draft_id: str, request: Request):
    """
    Get specific draft by ID (only if it belongs to the current user)
    """
    try:
        # Extract user_id from headers
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            logger.warning("No user_id provided in headers for draft request")
            raise HTTPException(status_code=401, detail="User identification required")
        
        query = """
        SELECT session_id, financial_year, age, gross_salary, basic_salary, hra_received, rent_paid,
               lta_received, other_exemptions, deduction_80c, deduction_80d, deduction_80dd,
               deduction_80e, deduction_80tta, home_loan_interest, other_deductions,
               other_income, standard_deduction, professional_tax, tds,
               created_at, draft_expires_at
        FROM "UserFinancials"
        WHERE session_id = $1 AND is_draft = TRUE AND status = 'draft'
        AND (draft_expires_at IS NULL OR draft_expires_at > NOW())
        AND user_id = $2
        """
        
        draft = await db_manager.fetch_one(query, draft_id, user_id)
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found or expired")
        
        return {
            "draft_id": draft["session_id"],
            "financial_data": {
                "financial_year": draft["financial_year"],
                "age": draft["age"],
                "gross_salary": draft["gross_salary"],
                "basic_salary": draft["basic_salary"],
                "hra_received": draft["hra_received"],
                "rent_paid": draft["rent_paid"],
                "lta_received": draft["lta_received"],
                "other_exemptions": draft["other_exemptions"],
                "deduction_80c": draft["deduction_80c"],
                "deduction_80d": draft["deduction_80d"],
                "deduction_80dd": draft["deduction_80dd"],
                "deduction_80e": draft["deduction_80e"],
                "deduction_80tta": draft["deduction_80tta"],
                "home_loan_interest": draft["home_loan_interest"],
                "other_deductions": draft["other_deductions"],
                "other_income": draft["other_income"],
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

@router.delete("/draft/{draft_id}")
async def delete_draft(draft_id: str, request: Request):
    """
    Delete a specific draft by ID (only if it belongs to the current user)
    """
    try:
        # Extract user_id from headers
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            logger.warning("No user_id provided in headers for draft deletion request")
            raise HTTPException(status_code=401, detail="User identification required")
        
        # Delete the draft
        query = """
        DELETE FROM "UserFinancials"
        WHERE session_id = $1 AND is_draft = TRUE AND status = 'draft'
        AND user_id = $2
        """
        
        result = await db_manager.execute_query(query, draft_id, user_id)
        
        logger.info(f"Draft {draft_id} deleted for user {user_id}")
        
        return {
            "success": True,
            "message": "Draft deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete draft {draft_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete draft")

async def save_financial_data_draft(session_id: str, financial_data: dict, user_id: str = None):
    """
    Helper function to save financial data as draft during upload
    """
    try:
        query = """
        INSERT INTO "UserFinancials" (
            session_id, user_id, gross_salary, basic_salary, hra_received, rent_paid,
            deduction_80c, deduction_80d, standard_deduction, professional_tax, tds,
            status, is_draft, draft_expires_at, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW()
        )
        """
        
        draft_expires_at = datetime.utcnow() + timedelta(days=7)
        
        await db_manager.execute_query(
            query,
            session_id,
            user_id,
            financial_data.get('gross_salary', 0),
            financial_data.get('basic_salary', 0),
            financial_data.get('hra_received', 0),
            financial_data.get('rent_paid', 0),
            financial_data.get('deduction_80c', 0),
            financial_data.get('deduction_80d', 0),
            financial_data.get('standard_deduction', 50000),
            financial_data.get('professional_tax', 0),
            financial_data.get('tds', 0),
            'draft',
            True,
            draft_expires_at
        )
        
        logger.info(f"Financial data draft saved for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to save financial data draft: {e}")
        # Don't raise exception here as it's not critical for the upload process

