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
                logger.warning("GEMINI_API_KEY not found - AI advisor will use fallback recommendations")
                self.model = None
                return
            
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
            self.model = None
    
    def generate_initial_question(self) -> Dict:
        """Generate the first contextual question based on financial data and tax results"""
        try:
            # Prepare context for Gemini
            context = self._prepare_financial_context()
            
            # If Gemini is not available, use fallback questions
            if not self.model:
                return self._get_fallback_initial_question(context)
            
            prompt = f"""
            You are a senior Chartered Accountant and Financial Advisor with 15+ years of experience in Indian tax planning and wealth management. You specialize in helping salaried professionals optimize their tax savings and build long-term wealth.
            
            User's Financial Profile:
            {context}
            
            As their personal financial advisor, generate ONE personalized question that:
            1. References specific aspects of their financial data (salary, deductions, tax savings)
            2. Shows you understand their current financial situation
            3. Helps identify their primary financial goal or concern
            4. Is conversational, professional, and encouraging
            5. Is between 25-60 words
            6. Focuses on tax optimization, investment planning, or financial goals
            
            Examples of good questions:
            - "I see you're earning ₹9.7L annually with good HRA benefits. What's your primary financial goal this year - building an emergency fund, planning for retirement, or saving for a major purchase?"
            - "With ₹7,987 in potential tax savings, are you looking to invest this money or do you have other financial priorities like home loan prepayment?"
            
            Return only the question text, no additional formatting or explanations.
            """
            
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            
            # Store context for future questions
            self.conversation_context = {
                'financial_context': context,
                'questions_asked': [question],
                'user_responses': [],
                'insights_gathered': [],
                'advisor_persona': 'Senior CA & Financial Advisor'
            }
            
            logger.info(f"Generated initial question: {question[:50]}...")
            
            return {
                'question': question,
                'round': self.current_round,
                'context': self.conversation_context
            }
            
        except Exception as e:
            logger.error(f"Failed to generate initial question: {e}")
            # Return fallback question if AI fails
            context = self._prepare_financial_context()
            return self._get_fallback_initial_question(context)
    
    def process_user_response(self, question: str, response: str, round: int) -> Dict:
        """Process user response and generate follow-up question or final recommendations"""
        try:
            # Ensure conversation context is properly initialized
            if not hasattr(self, 'conversation_context') or not self.conversation_context:
                self.conversation_context = {
                    'financial_context': self._prepare_financial_context(),
                    'questions_asked': [],
                    'user_responses': [],
                    'insights_gathered': [],
                    'advisor_persona': 'Senior CA & Financial Advisor'
                }
            
            # Update conversation context
            if 'user_responses' not in self.conversation_context:
                self.conversation_context['user_responses'] = []
            if 'questions_asked' not in self.conversation_context:
                self.conversation_context['questions_asked'] = []
            if 'insights_gathered' not in self.conversation_context:
                self.conversation_context['insights_gathered'] = []
                
            # Add the current question to questions_asked if not already there
            if question and question not in self.conversation_context['questions_asked']:
                self.conversation_context['questions_asked'].append(question)
            
            # Add user response
            self.conversation_context['user_responses'].append(response)
            self.current_round = round
            
            # Analyze response for insights (only if Gemini is available)
            if self.model:
                insights = self._analyze_user_response(response)
                self.conversation_context['insights_gathered'].extend(insights)
            else:
                # Simple fallback insights for non-Gemini mode
                insights = [f"User response: {response[:50]}..."]
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
            # If Gemini is not available, use fallback questions
            if not self.model:
                return self._get_fallback_follow_up_question()
            
            conversation_summary = self._get_conversation_summary()
            
            prompt = f"""
            You are a senior CA and Financial Advisor. Continue the conversation professionally.
            
            Financial Context:
            {self.conversation_context['financial_context']}
            
            Conversation So Far:
            {conversation_summary}
            
            Generate ONE follow-up question that:
            1. Builds naturally on their previous response
            2. Gathers specific information for personalized financial advice
            3. Focuses on Indian tax planning, investment strategies, or financial goals
            4. Shows expertise in areas like:
               - Tax-saving investments (ELSS, PPF, EPF, NPS)
               - Insurance planning (term life, health insurance)
               - Retirement planning (EPF, NPS, mutual funds)
               - Emergency fund planning
               - Home loan optimization
               - Children's education planning
            5. Is conversational, professional, and encouraging
            6. Is between 25-60 words
            
            Examples of good follow-up questions:
            - "That's a great goal! For retirement planning, are you currently investing in EPF, and would you like to explore additional options like NPS or ELSS mutual funds?"
            - "I understand you want to save more. Are you currently maximizing your 80C deductions, and would you be interested in learning about tax-saving investment options?"
            
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
            return self._get_fallback_follow_up_question()
    
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
                        "title": "Specific recommendation title",
                        "description": "Detailed explanation with specific amounts and Indian financial products",
                        "action_items": ["Specific step 1", "Specific step 2", "Specific step 3"],
                        "priority": "high|medium|low",
                        "estimated_savings": 50000
                    }}
                ]
            }}
            
            Focus on Indian financial products and tax planning:
            1. Tax Optimization:
               - ELSS mutual funds (₹1.5L limit)
               - PPF (₹1.5L limit)
               - EPF voluntary contributions
               - NPS (₹1.5L + ₹50K additional)
               - Health insurance (₹25K-₹1L)
               - Home loan optimization
            
            2. Investment Advice:
               - Emergency fund (6 months expenses)
               - SIP in equity mutual funds
               - Debt funds for stability
               - Gold investments (SGB, ETFs)
               - Real estate considerations
            
            3. Insurance Planning:
               - Term life insurance (10-15x annual income)
               - Health insurance with family floater
               - Critical illness cover
            
            4. Retirement Planning:
               - EPF optimization
               - NPS contributions
               - Retirement corpus calculation
               - Post-retirement income planning
            
            Provide specific amounts based on their salary and current deductions.
            Prioritize by potential savings and impact.
            Return only valid JSON.
            """
            
            response = self.model.generate_content(prompt)
            question = response.text.strip()
            
            # Check if response is empty or invalid
            if not question or question.startswith('Error') or question.startswith('Sorry'):
                logger.warning("Gemini returned empty or error response, using fallback")
                return self._get_fallback_recommendations()
            
            try:
                recommendations_data = json.loads(response.text.strip())
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Gemini JSON response: {e}")
                logger.warning(f"Response text: {response.text[:200]}...")
                return self._get_fallback_recommendations()
            
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
        # Extract basic financial data for fallback recommendations
        gross_salary = float(self.financial_data.get('gross_salary', 0))
        deduction_80c = float(self.financial_data.get('deduction_80c', 0))
        deduction_80d = float(self.financial_data.get('deduction_80d', 0))
        tax_savings = abs(float(self.tax_results.get('old_regime', {}).get('total_tax', 0)) - 
                         float(self.tax_results.get('new_regime', {}).get('total_tax', 0)))
        
        recommendations = [
            {
                'type': 'tax_optimization',
                'title': 'Optimize Tax Regime Selection',
                'description': f'Based on your calculations, you can save ₹{tax_savings:,.0f} by choosing the recommended tax regime. This is a significant amount that can be invested for long-term wealth building.',
                'action_items': [
                    'Review current tax regime selection',
                    'Calculate potential savings with recommended regime',
                    'Make informed decision before filing ITR'
                ],
                'priority': 'high',
                'estimated_savings': tax_savings
            }
        ]
        
        # Add 80C optimization if not maximized
        if deduction_80c < 150000:
            remaining_80c = 150000 - deduction_80c
            recommendations.append({
                'type': 'tax_optimization',
                'title': 'Maximize 80C Deductions',
                'description': f'You can save additional ₹{remaining_80c:,.0f} in taxes by maximizing your 80C investments through ELSS mutual funds, PPF, or EPF voluntary contributions.',
                'action_items': [
                    'Start SIP in ELSS mutual funds',
                    'Consider PPF investment',
                    'Increase EPF voluntary contributions'
                ],
                'priority': 'high',
                'estimated_savings': remaining_80c * 0.3  # Now both are float
            })
        
        # Add health insurance recommendation if not covered
        if deduction_80d < 25000:
            recommendations.append({
                'type': 'investment_advice',
                'title': 'Health Insurance Planning',
                'description': 'Consider comprehensive health insurance for your family. This provides tax benefits under 80D and protects against medical emergencies.',
                'action_items': [
                    'Research family floater health insurance plans',
                    'Compare coverage and premiums',
                    'Purchase policy before March 31st for current year benefits'
                ],
                'priority': 'medium',
                'estimated_savings': 25000.0
            })
        
        return {
            'recommendations': recommendations,
            'conversation_summary': 'AI service temporarily unavailable - providing general recommendations based on your financial profile',
            'is_final': True,
            'context': self.conversation_context
        }
    
    def get_conversation_context(self) -> Dict:
        """Get current conversation context"""
        return self.conversation_context
    
    def _get_fallback_initial_question(self, context: str) -> Dict:
        """Generate fallback initial question when AI is not available"""
        # Extract key financial data for personalized question
        gross_salary = self.financial_data.get('gross_salary', 0)
        tax_savings = abs(self.tax_results.get('old_regime', {}).get('total_tax', 0) - 
                         self.tax_results.get('new_regime', {}).get('total_tax', 0))
        
        # Generate personalized question based on financial data
        if tax_savings > 5000:
            question = f"I see you're earning ₹{gross_salary:,.0f} annually with ₹{tax_savings:,.0f} in potential tax savings. What's your primary financial goal this year - building an emergency fund, planning for retirement, or maximizing your tax savings?"
        else:
            question = f"With your ₹{gross_salary:,.0f} annual income, what's your main financial priority - building wealth through investments, planning for retirement, or saving for a specific goal?"
        
        # Store context for future questions
        self.conversation_context = {
            'financial_context': context,
            'questions_asked': [question],
            'user_responses': [],
            'insights_gathered': [],
            'advisor_persona': 'Senior CA & Financial Advisor'
        }
        
        return {
            'question': question,
            'round': self.current_round,
            'context': self.conversation_context
        }
    
    def _get_fallback_follow_up_question(self) -> str:
        """Generate fallback follow-up question when AI is not available"""
        questions = [
            "What's your current approach to tax-saving investments? Are you interested in ELSS mutual funds, PPF, or other options?",
            "Do you have health insurance coverage for your family? This can provide both tax benefits and financial protection.",
            "Are you planning to invest your tax savings, or do you have other financial priorities like home loan prepayment?",
            "What's your risk tolerance for investments - are you comfortable with equity mutual funds or prefer safer options like debt funds?"
        ]
        
        # Get a random question or cycle through them
        current_round = self.current_round
        question_index = (current_round - 2) % len(questions)  # -2 because first question is initial
        
        return questions[question_index]
    
    def is_conversation_complete(self) -> bool:
        """Check if conversation is complete"""
        return self.current_round >= self.max_conversation_rounds
