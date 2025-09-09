"""
AI Advisor API Routes
Handles conversation management and recommendation generation
"""

import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.database import db_manager
from app.models import (
    AIAdvisorConversationCreate, 
    AIAdvisorRecommendationCreate,
    AIAdvisorSession
)
from app.services.ai_advisor import AIAdvisor

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/ai-advisor", response_class=HTMLResponse)
async def ai_advisor_page():
    """Serve AI Advisor page"""
    try:
        with open("templates/ai_advisor.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="AI Advisor page not found", status_code=404)

@router.post("/api/ai-advisor/start-conversation")
async def start_conversation(request: Request):
    """Initialize AI advisor session and generate first question"""
    try:
        # Get session_id from request
        session_id = request.headers.get('X-Session-ID')
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Get financial data and tax results
        financial_data = await _get_financial_data(session_id)
        tax_results = await _get_tax_results(session_id)
        
        if not financial_data or not tax_results:
            raise HTTPException(status_code=404, detail="Financial data or tax results not found")
        
        # Initialize AI Advisor
        ai_advisor = AIAdvisor(financial_data, tax_results)
        
        # Generate initial question
        result = ai_advisor.generate_initial_question()
        
        # Store initial conversation context
        conversation_data = AIAdvisorConversationCreate(
            session_id=uuid.UUID(session_id),
            conversation_round=result['round'],
            gemini_question=result['question'],
            user_response="",  # Empty for initial question
            conversation_context=result['context']
        )
        
        await _store_conversation(conversation_data)
        
        logger.info(f"Started AI conversation for session {session_id}")
        
        return {
            "success": True,
            "question": result['question'],
            "round": result['round'],
            "session_id": session_id,
            "financial_summary": _prepare_financial_summary(financial_data, tax_results)
        }
        
    except Exception as e:
        logger.error(f"Failed to start conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to start AI conversation")

@router.post("/api/ai-advisor/process-response")
async def process_response(request: Request):
    """Process user response and generate follow-up question or recommendations"""
    try:
        data = await request.json()
        session_id = data.get('session_id')
        question = data.get('question')
        response = data.get('response')
        round_number = data.get('round', 1)
        
        if not all([session_id, question, response]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Get financial data and tax results
        financial_data = await _get_financial_data(session_id)
        tax_results = await _get_tax_results(session_id)
        
        if not financial_data or not tax_results:
            raise HTTPException(status_code=404, detail="Financial data or tax results not found")
        
        # Get existing conversation context from database
        conversation_context = await _get_conversation_context(session_id)
        
        # Initialize AI Advisor with existing context
        ai_advisor = AIAdvisor(financial_data, tax_results)
        if conversation_context:
            ai_advisor.conversation_context = conversation_context
            ai_advisor.current_round = round_number
        
        # Store conversation in database
        conversation_data = AIAdvisorConversationCreate(
            session_id=uuid.UUID(session_id),
            conversation_round=round_number,
            gemini_question=question,
            user_response=response,
            conversation_context=ai_advisor.conversation_context
        )
        
        await _store_conversation(conversation_data)
        
        # Process response
        result = ai_advisor.process_user_response(question, response, round_number)
        
        if result.get('is_final'):
            # Generate and store recommendations
            recommendations = await _generate_and_store_recommendations(
                session_id, result['recommendations']
            )
            
            return {
                "success": True,
                "is_final": True,
                "recommendations": recommendations,
                "conversation_summary": result.get('conversation_summary', ''),
                "session_id": session_id
            }
        else:
            return {
                "success": True,
                "is_final": False,
                "question": result['question'],
                "round": result['round'],
                "session_id": session_id
            }
        
    except Exception as e:
        logger.error(f"Failed to process response: {e}")
        raise HTTPException(status_code=500, detail="Failed to process response")

@router.get("/api/ai-advisor/recommendations/{session_id}")
async def get_recommendations(session_id: str):
    """Get recommendations for a session"""
    try:
        query = """
        SELECT recommendation_type, recommendation_title, recommendation_description,
               action_items, priority_level, estimated_savings, created_at
        FROM "AIAdvisorRecommendations"
        WHERE session_id = $1
        ORDER BY estimated_savings DESC, priority_level DESC
        """
        
        recommendations = await db_manager.fetch_all(query, uuid.UUID(session_id))
        
        return {
            "success": True,
            "recommendations": recommendations,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations")

@router.get("/api/ai-advisor/conversation/{session_id}")
async def get_conversation_history(session_id: str):
    """Get conversation history for a session"""
    try:
        query = """
        SELECT conversation_round, gemini_question, user_response, created_at
        FROM "AIAdvisorConversation"
        WHERE session_id = $1
        ORDER BY conversation_round ASC
        """
        
        conversations = await db_manager.fetch_all(query, uuid.UUID(session_id))
        
        return {
            "success": True,
            "conversations": conversations,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversation history")

# Helper functions
async def _get_conversation_context(session_id: str) -> Optional[Dict]:
    """Get conversation context from database"""
    try:
        query = """
        SELECT conversation_round, gemini_question, user_response, conversation_context
        FROM "AIAdvisorConversation"
        WHERE session_id = $1
        ORDER BY conversation_round ASC
        """
        
        results = await db_manager.fetch_all(query, uuid.UUID(session_id))
        if not results:
            return None
        
        # Reconstruct conversation context from all records
        context = {
            'financial_context': '',
            'questions_asked': [],
            'user_responses': [],
            'insights_gathered': [],
            'advisor_persona': 'Senior CA & Financial Advisor'
        }
        
        for result in results:
            # Add question and response
            if result['gemini_question']:
                context['questions_asked'].append(result['gemini_question'])
            if result['user_response']:
                context['user_responses'].append(result['user_response'])
            
            # Get context from the latest record
            if result['conversation_context']:
                import json
                latest_context = json.loads(result['conversation_context'])
                context.update(latest_context)
        
        return context
        
    except Exception as e:
        logger.error(f"Failed to get conversation context: {e}")
        return None

async def _get_financial_data(session_id: str) -> Optional[Dict]:
    """Get financial data for a session"""
    try:
        query = """
        SELECT gross_salary, basic_salary, hra_received, rent_paid,
               deduction_80c, deduction_80d, standard_deduction, professional_tax, tds
        FROM "UserFinancials"
        WHERE session_id = $1 AND is_draft = FALSE
        """
        
        result = await db_manager.fetch_one(query, uuid.UUID(session_id))
        return dict(result) if result else None
        
    except Exception as e:
        logger.error(f"Failed to get financial data: {e}")
        return None

async def _get_tax_results(session_id: str) -> Optional[Dict]:
    """Get tax results for a session"""
    try:
        query = """
        SELECT tax_old_regime, tax_new_regime, best_regime, calculation_details
        FROM "TaxComparison"
        WHERE session_id = $1
        """
        
        result = await db_manager.fetch_one(query, uuid.UUID(session_id))
        if not result:
            return None
        
        # Format tax results
        old_regime_tax = float(result['tax_old_regime'])
        new_regime_tax = float(result['tax_new_regime'])
        tax_savings = abs(old_regime_tax - new_regime_tax)
        
        return {
            'old_regime': {'total_tax': old_regime_tax},
            'new_regime': {'total_tax': new_regime_tax},
            'best_regime': result['best_regime'],
            'tax_savings': tax_savings,
            'calculation_details': result['calculation_details']
        }
        
    except Exception as e:
        logger.error(f"Failed to get tax results: {e}")
        return None

async def _store_conversation(conversation_data: AIAdvisorConversationCreate) -> None:
    """Store conversation in database"""
    try:
        query = """
        INSERT INTO "AIAdvisorConversation" (
            session_id, conversation_round, gemini_question, user_response, conversation_context
        ) VALUES ($1, $2, $3, $4, $5)
        """
        
        # Convert conversation_context to JSON string
        import json
        context_json = json.dumps(conversation_data.conversation_context) if conversation_data.conversation_context else None
        
        await db_manager.execute_query(
            query,
            conversation_data.session_id,
            conversation_data.conversation_round,
            conversation_data.gemini_question,
            conversation_data.user_response,
            context_json
        )
        
        logger.info(f"Stored conversation for session {conversation_data.session_id}")
        
    except Exception as e:
        logger.error(f"Failed to store conversation: {e}")
        raise

async def _generate_and_store_recommendations(session_id: str, recommendations: List[Dict]) -> List[Dict]:
    """Generate and store recommendations in database"""
    try:
        stored_recommendations = []
        
        for rec in recommendations:
            # Get the latest conversation ID for this session
            conv_query = """
            SELECT conversation_id FROM "AIAdvisorConversation"
            WHERE session_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            conv_result = await db_manager.fetch_one(conv_query, uuid.UUID(session_id))
            if not conv_result:
                continue
            
            conversation_id = conv_result['conversation_id']
            
            # Store recommendation
            rec_data = AIAdvisorRecommendationCreate(
                session_id=uuid.UUID(session_id),
                conversation_id=conversation_id,
                recommendation_type=rec['type'],
                recommendation_title=rec['title'],
                recommendation_description=rec['description'],
                action_items=rec.get('action_items', []),
                priority_level=rec.get('priority', 'medium'),
                estimated_savings=rec.get('estimated_savings', 0)
            )
            
            query = """
            INSERT INTO "AIAdvisorRecommendations" (
                session_id, conversation_id, recommendation_type, recommendation_title,
                recommendation_description, action_items, priority_level, estimated_savings
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING recommendation_id
            """
            
            # Convert action_items to JSON string
            import json
            action_items_json = json.dumps(rec_data.action_items) if rec_data.action_items else None
            
            result = await db_manager.fetch_one(
                query,
                rec_data.session_id,
                rec_data.conversation_id,
                rec_data.recommendation_type,
                rec_data.recommendation_title,
                rec_data.recommendation_description,
                action_items_json,
                rec_data.priority_level,
                rec_data.estimated_savings
            )
            
            stored_recommendations.append({
                'recommendation_id': str(result['recommendation_id']),
                'type': rec['type'],
                'title': rec['title'],
                'description': rec['description'],
                'action_items': rec.get('action_items', []),
                'priority': rec.get('priority', 'medium'),
                'estimated_savings': rec.get('estimated_savings', 0)
            })
        
        logger.info(f"Stored {len(stored_recommendations)} recommendations for session {session_id}")
        return stored_recommendations
        
    except Exception as e:
        logger.error(f"Failed to store recommendations: {e}")
        raise

def _prepare_financial_summary(financial_data: Dict, tax_results: Dict) -> Dict:
    """Prepare financial summary for display"""
    try:
        old_regime_tax = tax_results.get('old_regime', {}).get('total_tax', 0)
        new_regime_tax = tax_results.get('new_regime', {}).get('total_tax', 0)
        tax_savings = abs(old_regime_tax - new_regime_tax)
        
        return {
            'gross_salary': financial_data.get('gross_salary', 0),
            'hra_received': financial_data.get('hra_received', 0),
            'rent_paid': financial_data.get('rent_paid', 0),
            'deduction_80c': financial_data.get('deduction_80c', 0),
            'deduction_80d': financial_data.get('deduction_80d', 0),
            'old_regime_tax': old_regime_tax,
            'new_regime_tax': new_regime_tax,
            'best_regime': tax_results.get('best_regime', 'old'),
            'tax_savings': tax_savings
        }
        
    except Exception as e:
        logger.error(f"Failed to prepare financial summary: {e}")
        return {}
