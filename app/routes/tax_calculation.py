import logging
from typing import Dict, Optional
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.database import db_manager
from app.models import TaxCalculationRequest, TaxCalculationResponse, RegimeSelectionRequest
from app.services.tax_calculator import tax_calculator

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["tax-calculation"])

@router.post("/calculate-tax")
async def calculate_tax(request: TaxCalculationRequest):
    """
    Calculate tax for both Old and New regimes
    """
    try:
        session_id = str(request.session_id)
        
        # Retrieve financial data from database
        financial_data = await get_financial_data(session_id)
        if not financial_data:
            raise HTTPException(status_code=404, detail="Financial data not found for this session")
        
        # Validate financial data
        is_valid, validation_errors = await tax_calculator.validate_financial_data(financial_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid financial data: {', '.join(validation_errors)}")
        
        # Calculate tax for both regimes
        calculation_details = await tax_calculator.calculate_tax(financial_data)
        
        # Generate recommendations
        recommendations = await tax_calculator.get_tax_recommendations(calculation_details)
        
        # Store results in database
        await store_tax_results(session_id, calculation_details, recommendations)
        
        # Prepare response
        response = TaxCalculationResponse(
            session_id=request.session_id,
            old_regime_tax=calculation_details['old_regime']['total_tax'],
            new_regime_tax=calculation_details['new_regime']['total_tax'],
            best_regime=calculation_details['comparison']['best_regime'],
            tax_savings=calculation_details['comparison']['tax_savings'],
            calculation_details=calculation_details,
            recommendations=recommendations
        )
        
        logger.info(f"Tax calculation completed for session {session_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tax calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during tax calculation")

@router.get("/tax-results/{session_id}")
async def get_tax_results(session_id: str):
    """
    Retrieve tax calculation results for a session
    """
    try:
        # Get tax comparison results
        query = """
        SELECT tc.*, uf.gross_salary, uf.basic_salary
        FROM "TaxComparison" tc
        JOIN "UserFinancials" uf ON tc.session_id = uf.session_id
        WHERE tc.session_id = $1
        """
        
        result = await db_manager.fetch_one(query, session_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Tax results not found for this session")
        
        # Parse JSON fields
        calculation_details = result.get('calculation_details', {})
        recommendations = result.get('recommendations', {})
        
        return {
            "session_id": session_id,
            "gross_salary": result['gross_salary'],
            "basic_salary": result['basic_salary'],
            "old_regime_tax": result['tax_old_regime'],
            "new_regime_tax": result['tax_new_regime'],
            "best_regime": result['best_regime'],
            "selected_regime": result['selected_regime'],
            "calculation_details": calculation_details,
            "recommendations": recommendations,
            "created_at": result['created_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve tax results for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tax results")

@router.post("/select-regime")
async def select_regime(selection: RegimeSelectionRequest):
    """
    Update user's regime selection
    """
    try:
        session_id = str(selection.session_id)
        selected_regime = selection.selected_regime
        
        # Update regime selection in database
        query = """
        UPDATE "TaxComparison"
        SET selected_regime = $1
        WHERE session_id = $2
        """
        
        await db_manager.execute_query(query, selected_regime, session_id)
        
        logger.info(f"Regime selection updated for session {session_id}: {selected_regime}")
        
        return {
            "success": True,
            "session_id": session_id,
            "selected_regime": selected_regime,
            "message": f"Regime selection updated to {selected_regime} regime"
        }
        
    except Exception as e:
        logger.error(f"Failed to update regime selection: {e}")
        raise HTTPException(status_code=500, detail="Failed to update regime selection")

@router.get("/tax-summary/{session_id}")
async def get_tax_summary(session_id: str):
    """
    Get a summary of tax calculation results
    """
    try:
        # Get basic tax summary
        query = """
        SELECT 
            tc.tax_old_regime,
            tc.tax_new_regime,
            tc.best_regime,
            tc.selected_regime,
            uf.gross_salary,
            uf.basic_salary
        FROM "TaxComparison" tc
        JOIN "UserFinancials" uf ON tc.session_id = uf.session_id
        WHERE tc.session_id = $1
        """
        
        result = await db_manager.fetch_one(query, session_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Tax summary not found for this session")
        
        # Calculate savings
        old_tax = result['tax_old_regime']
        new_tax = result['tax_new_regime']
        tax_savings = abs(old_tax - new_tax)
        savings_percentage = (tax_savings / max(old_tax, new_tax)) * 100 if max(old_tax, new_tax) > 0 else 0
        
        return {
            "session_id": session_id,
            "gross_salary": result['gross_salary'],
            "old_regime_tax": old_tax,
            "new_regime_tax": new_tax,
            "best_regime": result['best_regime'],
            "selected_regime": result['selected_regime'],
            "tax_savings": tax_savings,
            "savings_percentage": round(savings_percentage, 2),
            "recommendation": f"Choose {result['best_regime']} regime to save ₹{tax_savings:,.0f}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve tax summary for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tax summary")

async def get_financial_data(session_id: str) -> Optional[Dict]:
    """Helper function to retrieve financial data from database"""
    try:
        query = """
        SELECT financial_year, age, gross_salary, basic_salary, hra_received, rent_paid,
               lta_received, other_exemptions, deduction_80c, deduction_80d, deduction_80dd,
               deduction_80e, deduction_80tta, home_loan_interest, other_deductions,
               other_income, standard_deduction, professional_tax, tds
        FROM "UserFinancials"
        WHERE session_id = $1 AND status = 'completed'
        """
        
        result = await db_manager.fetch_one(query, session_id)
        
        if result:
            return {
                'financial_year': result['financial_year'] or '2024-25',
                'age': result['age'],
                'gross_salary': float(result['gross_salary']),
                'basic_salary': float(result['basic_salary']),
                'hra_received': float(result['hra_received']),
                'rent_paid': float(result['rent_paid']),
                'lta_received': float(result['lta_received']),
                'other_exemptions': float(result['other_exemptions']),
                'deduction_80c': float(result['deduction_80c']),
                'deduction_80d': float(result['deduction_80d']),
                'deduction_80dd': float(result['deduction_80dd']),
                'deduction_80e': float(result['deduction_80e']),
                'deduction_80tta': float(result['deduction_80tta']),
                'home_loan_interest': float(result['home_loan_interest']),
                'other_deductions': float(result['other_deductions']),
                'other_income': float(result['other_income']),
                'standard_deduction': float(result['standard_deduction']),
                'professional_tax': float(result['professional_tax']),
                'tds': float(result['tds'])
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to retrieve financial data for session {session_id}: {e}")
        return None

async def store_tax_results(session_id: str, calculation_details: Dict, recommendations: Dict):
    """Helper function to store tax calculation results in database"""
    try:
        query = """
        INSERT INTO "TaxComparison" (
            session_id, tax_old_regime, tax_new_regime, best_regime,
            calculation_details, recommendations, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (session_id) DO UPDATE SET
            tax_old_regime = EXCLUDED.tax_old_regime,
            tax_new_regime = EXCLUDED.tax_new_regime,
            best_regime = EXCLUDED.best_regime,
            calculation_details = EXCLUDED.calculation_details,
            recommendations = EXCLUDED.recommendations,
            created_at = NOW()
        """
        
        old_tax = calculation_details['old_regime']['total_tax']
        new_tax = calculation_details['new_regime']['total_tax']
        best_regime = calculation_details['comparison']['best_regime']
        
        await db_manager.execute_query(
            query,
            session_id,
            old_tax,
            new_tax,
            best_regime,
            json.dumps(calculation_details),
            json.dumps(recommendations)
        )
        
        logger.info(f"Tax results stored for session {session_id}")
        
    except Exception as e:
        logger.error(f"Failed to store tax results for session {session_id}: {e}")
        # Don't raise exception as this is not critical for the calculation

