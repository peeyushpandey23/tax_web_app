"""
AI Advisor Service with Gemini Integration
Handles intelligent question generation and recommendation logic
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from decimal import Decimal

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.config import settings
from app.models import AIAdvisorConversationCreate, AIAdvisorRecommendationCreate

logger = logging.getLogger(__name__)

class AIAdvisor:
    """AI Advisor service with Gemini integration for intelligent financial advice"""
    
    def __init__(self, financial_data: Dict, tax_results: Dict):
        self.financial_data = financial_data
        self.tax_results = tax_results
        self.conversation_context = {}
        self.max_conversation_rounds = 4
        self.current_round = 1
        
        # Initialize Gemini
        self._setup_gemini()
    
    def _setup_gemini(self) -> None:
        """Initialize Gemini AI with safety settings"""
        try:
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not found in environment variables")
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Configure safety settings
            self.safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',
                safety_settings=self.safety_settings
            )
            
            logger.info("Gemini AI initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {e}")
            raise
    
    def generate_initial_question(self) -> Dict:
        """Generate the first contextual question based on financial data and tax results"""
        try:
            # Prepare context for Gemini
            context = self._prepare_financial_context()
            
            prompt = f"""
            You are a professional financial advisor helping with tax optimization and investment planning.
            
            User's Financial Profile:
            {context}
            
            Generate ONE contextual question that:
            1. References specific aspects of their financial data
            2. Is personalized to their situation
            3. Helps understand their primary financial goal
            4. Is conversational and engaging
            5. Is between 20-50 words
            
            Focus on the most significant financial opportunity you see in their data.
            Return only the question text, no additional formatting.
            """
            
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            
            # Store context for future questions
            self.conversation_context = {
                'financial_context': context,
                'questions_asked': [question],
                'user_responses': [],
                'insights_gathered': []
            }
            
            logger.info(f"Generated initial question: {question[:50]}...")
            
            return {
                'question': question,
                'round': self.current_round,
                'context': self.conversation_context
            }
            
        except Exception as e:
            logger.error(f"Failed to generate initial question: {e}")
            raise
    
    def process_user_response(self, question: str, response: str, round: int) -> Dict:
        """Process user response and generate follow-up question or final recommendations"""
        try:
            # Ensure conversation context is properly initialized
            if not hasattr(self, 'conversation_context') or not self.conversation_context:
                self.conversation_context = {
                    'financial_context': {},
                    'questions_asked': [],
                    'user_responses': [],
                    'insights_gathered': []
                }
            
            # Update conversation context
            if 'user_responses' not in self.conversation_context:
                self.conversation_context['user_responses'] = []
            if 'questions_asked' not in self.conversation_context:
                self.conversation_context['questions_asked'] = []
            if 'insights_gathered' not in self.conversation_context:
                self.conversation_context['insights_gathered'] = []
                
            self.conversation_context['user_responses'].append(response)
            self.current_round = round
            
            # Analyze response for insights
            insights = self._analyze_user_response(response)
            self.conversation_context['insights_gathered'].extend(insights)
            
            # Check if we have enough information for recommendations
            if self._should_generate_recommendations():
                logger.info("Sufficient information gathered, generating recommendations")
                return self._generate_final_recommendations()
            
            # Generate follow-up question
            follow_up_question = self._generate_follow_up_question()
            
            return {
                'question': follow_up_question,
                'round': self.current_round + 1,
                'context': self.conversation_context,
                'is_final': False
            }
            
        except Exception as e:
            logger.error(f"Failed to process user response: {e}")
            raise
    
    def _prepare_financial_context(self) -> str:
        """Prepare financial context for AI analysis"""
        try:
            # Extract key financial data
            gross_salary = self.financial_data.get('gross_salary', 0)
            hra_received = self.financial_data.get('hra_received', 0)
            rent_paid = self.financial_data.get('rent_paid', 0)
            deduction_80c = self.financial_data.get('deduction_80c', 0)
            deduction_80d = self.financial_data.get('deduction_80d', 0)
            
            # Extract tax results
            old_regime_tax = self.tax_results.get('old_regime', {}).get('total_tax', 0)
            new_regime_tax = self.tax_results.get('new_regime', {}).get('total_tax', 0)
            best_regime = self.tax_results.get('best_regime', 'old')
            tax_savings = abs(old_regime_tax - new_regime_tax)
            
            context = f"""
            Gross Salary: ₹{gross_salary:,.0f}
            HRA Received: ₹{hra_received:,.0f}
            Rent Paid: ₹{rent_paid:,.0f}
            80C Deductions: ₹{deduction_80c:,.0f}
            80D Deductions: ₹{deduction_80d:,.0f}
            
            Tax Analysis:
            Old Regime Tax: ₹{old_regime_tax:,.0f}
            New Regime Tax: ₹{new_regime_tax:,.0f}
            Recommended Regime: {best_regime.title()}
            Potential Tax Savings: ₹{tax_savings:,.0f}
            """
            
            return context.strip()
            
        except Exception as e:
            logger.error(f"Failed to prepare financial context: {e}")
            return "Financial data analysis in progress..."
    
    def _analyze_user_response(self, response: str) -> List[str]:
        """Analyze user response to extract key insights"""
        try:
            prompt = f"""
            Analyze this user response for financial planning insights:
            "{response}"
            
            Extract meaningful insights about:
            1. Financial goals (short-term vs long-term)
            2. Risk tolerance (conservative, moderate, aggressive)
            3. Investment preferences
            4. Lifestyle priorities
            5. Tax optimization interests
            
            Be specific and actionable. If the user mentions retirement, savings, investments, 
            or any financial goals, extract those insights. Don't say "Cannot be determined" 
            unless the response is completely unrelated to finances.
            
            Return insights as a simple list, one per line.
            """
            
            ai_response = self.model.generate_content(prompt)
            insights = [line.strip() for line in ai_response.text.split('\n') if line.strip()]
            
            logger.info(f"Extracted insights: {insights}")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to analyze user response: {e}")
            return []
    
    def _should_generate_recommendations(self) -> bool:
        """Determine if we have enough information for recommendations"""
        # Always ask at least 2 questions minimum
        if self.current_round < 2:
            return False
            
        # Generate recommendations if:
        # 1. We've asked 4+ questions (minimum for good recommendations), OR
        # 2. We have clear insights about goals AND risk tolerance (not just mentioned)
        if self.current_round >= 4:
            return True
        
        insights = self.conversation_context.get('insights_gathered', [])
        
        # Check for actual goal insights (not just "Cannot be determined")
        has_goals = any(
            'goal' in insight.lower() and 'cannot be determined' not in insight.lower() 
            for insight in insights
        )
        
        # Check for actual risk tolerance insights (not just "Cannot be determined")
        has_risk = any(
            ('risk' in insight.lower() or 'conservative' in insight.lower() or 'aggressive' in insight.lower()) 
            and 'cannot be determined' not in insight.lower()
            for insight in insights
        )
        
        # Also check if user explicitly asks for recommendations
        user_responses = self.conversation_context.get('user_responses', [])
        user_wants_recommendations = any(
            'recommendation' in response.lower() or 'advice' in response.lower() or 'suggest' in response.lower()
            for response in user_responses
        )
        
        return (has_goals and has_risk) or user_wants_recommendations
    
    def _generate_follow_up_question(self) -> str:
        """Generate contextual follow-up question based on conversation so far"""
        try:
            conversation_summary = self._get_conversation_summary()
            
            prompt = f"""
            You are a financial advisor continuing a conversation.
            
            Financial Context:
            {self.conversation_context['financial_context']}
            
            Conversation So Far:
            {conversation_summary}
            
            Generate ONE follow-up question that:
            1. Builds on previous responses
            2. Gathers missing information for personalized advice
            3. Is specific to their financial situation
            4. Helps determine the best recommendations
            5. Is conversational and natural
            6. Is between 20-50 words
            
            Focus on gathering information needed for actionable recommendations.
            Return only the question text.
            """
            
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            
            # Update context
            self.conversation_context['questions_asked'].append(question)
            
            logger.info(f"Generated follow-up question: {question[:50]}...")
            return question
            
        except Exception as e:
            logger.error(f"Failed to generate follow-up question: {e}")
            return "What's your primary financial goal for this year?"
    
    def _get_conversation_summary(self) -> str:
        """Get summary of conversation so far"""
        questions = self.conversation_context.get('questions_asked', [])
        responses = self.conversation_context.get('user_responses', [])
        
        summary = ""
        for i, (q, r) in enumerate(zip(questions, responses), 1):
            summary += f"Q{i}: {q}\nA{i}: {r}\n\n"
        
        return summary.strip()
    
    def _generate_final_recommendations(self) -> Dict:
        """Generate personalized recommendations based on complete conversation"""
        try:
            conversation_summary = self._get_conversation_summary()
            
            prompt = f"""
            You are a financial advisor providing personalized recommendations.
            
            Financial Profile:
            {self.conversation_context['financial_context']}
            
            Complete Conversation:
            {conversation_summary}
            
            Generate personalized recommendations in this JSON format:
            {{
                "recommendations": [
                    {{
                        "type": "tax_optimization|investment_advice|lifestyle_adjustments|long_term_planning",
                        "title": "Brief recommendation title",
                        "description": "Detailed explanation",
                        "action_items": ["Step 1", "Step 2", "Step 3"],
                        "priority": "high|medium|low",
                        "estimated_savings": 50000
                    }}
                ]
            }}
            
            Focus on:
            1. Tax optimization opportunities
            2. Investment strategies based on risk tolerance
            3. Lifestyle adjustments for better financial health
            4. Long-term wealth building
            
            Prioritize by potential savings amount.
            Provide specific, actionable steps.
            Return only valid JSON.
            """
            
            response = self.model.generate_content(prompt)
            recommendations_data = json.loads(response.text.strip())
            
            logger.info(f"Generated {len(recommendations_data['recommendations'])} recommendations")
            
            return {
                'recommendations': recommendations_data['recommendations'],
                'conversation_summary': conversation_summary,
                'is_final': True,
                'context': self.conversation_context
            }
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            # Return fallback recommendations
            return self._get_fallback_recommendations()
    
    def _get_fallback_recommendations(self) -> Dict:
        """Provide fallback recommendations if AI fails"""
        return {
            'recommendations': [
                {
                    'type': 'tax_optimization',
                    'title': 'Optimize Tax Regime Selection',
                    'description': 'Consider switching to the recommended tax regime for better savings.',
                    'action_items': ['Review current tax regime', 'Calculate potential savings', 'Make informed decision'],
                    'priority': 'high',
                    'estimated_savings': 25000
                }
            ],
            'conversation_summary': 'AI service temporarily unavailable',
            'is_final': True,
            'context': self.conversation_context
        }
    
    def get_conversation_context(self) -> Dict:
        """Get current conversation context"""
        return self.conversation_context
    
    def is_conversation_complete(self) -> bool:
        """Check if conversation is complete"""
        return self.current_round >= self.max_conversation_rounds
