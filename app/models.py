from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class UserFinancialsBase(BaseModel):
    """Base model for user financial data"""
    financial_year: str = Field(default="2024-25", description="Financial year for tax calculation")
    age: Optional[int] = Field(default=None, ge=18, le=100, description="User age as on March 31st")
    gross_salary: Union[Decimal, float] = Field(..., ge=0, description="Total gross salary")
    basic_salary: Union[Decimal, float] = Field(..., ge=0, description="Basic salary component")
    hra_received: Union[Decimal, float] = Field(default=0, ge=0, description="HRA received")
    rent_paid: Union[Decimal, float] = Field(default=0, ge=0, description="Annual rent paid")
    lta_received: Union[Decimal, float] = Field(default=0, ge=0, description="Leave Travel Allowance received")
    other_exemptions: Union[Decimal, float] = Field(default=0, ge=0, description="Other allowances exempted under Section 10")
    deduction_80c: Union[Decimal, float] = Field(default=0, ge=0, description="80C investments")
    deduction_80d: Union[Decimal, float] = Field(default=0, ge=0, description="80D medical insurance")
    deduction_80dd: Union[Decimal, float] = Field(default=0, ge=0, description="80DD disability care deduction")
    deduction_80e: Union[Decimal, float] = Field(default=0, ge=0, description="80E education loan interest")
    deduction_80tta: Union[Decimal, float] = Field(default=0, ge=0, description="80TTA/80TTB savings interest deduction")
    home_loan_interest: Union[Decimal, float] = Field(default=0, ge=0, description="Interest on home loan (Section 24b)")
    other_deductions: Optional[Union[Decimal, float]] = Field(default=None, ge=0, description="Other deductions (80G, 80U, etc.)")
    other_income: Optional[Union[Decimal, float]] = Field(default=None, ge=0, description="Income from other sources")
    standard_deduction: Union[Decimal, float] = Field(default=50000, ge=0, description="Standard deduction")
    professional_tax: Union[Decimal, float] = Field(default=0, ge=0, description="Professional tax paid")
    tds: Union[Decimal, float] = Field(default=0, ge=0, description="Tax Deducted at Source")
    
    @field_validator('basic_salary')
    @classmethod
    def basic_salary_must_be_less_than_gross(cls, v, info):
        if info.data and 'gross_salary' in info.data and v > info.data['gross_salary']:
            raise ValueError('Basic salary cannot be greater than gross salary')
        return v
    
    @field_validator('deduction_80c')
    @classmethod
    def deduction_80c_limit(cls, v):
        if v > 150000:
            raise ValueError('80C deduction cannot exceed ₹1,50,000')
        return v
    
    @field_validator('deduction_80d')
    @classmethod
    def deduction_80d_limit(cls, v):
        if v > 25000:
            raise ValueError('80D deduction cannot exceed ₹25,000')
        return v
    
    @field_validator('deduction_80dd')
    @classmethod
    def deduction_80dd_limit(cls, v):
        if v > 125000:
            raise ValueError('80DD deduction cannot exceed ₹1,25,000')
        return v
    
    @field_validator('deduction_80e')
    @classmethod
    def deduction_80e_limit(cls, v):
        if v > 40000:
            raise ValueError('80E deduction cannot exceed ₹40,000')
        return v
    
    @field_validator('deduction_80tta')
    @classmethod
    def deduction_80tta_limit(cls, v):
        if v > 10000:
            raise ValueError('80TTA deduction cannot exceed ₹10,000')
        return v
    
    @field_validator('home_loan_interest')
    @classmethod
    def home_loan_interest_limit(cls, v):
        if v > 200000:
            raise ValueError('Home loan interest deduction cannot exceed ₹2,00,000')
        return v
    
    @field_validator('financial_year')
    @classmethod
    def financial_year_format(cls, v):
        import re
        if not re.match(r'^\d{4}-\d{2}$', v):
            raise ValueError('Financial year must be in format YYYY-YY (e.g., 2024-25)')
        return v

class UserFinancialsCreate(UserFinancialsBase):
    """Model for creating new user financial records"""
    session_id: Optional[Union[UUID, str]] = None
    user_id: Optional[str] = None
    pass

class UserFinancialsUpdate(BaseModel):
    """Model for updating user financial records"""
    financial_year: Optional[str] = Field(None)
    age: Optional[int] = Field(None, ge=18, le=100)
    gross_salary: Optional[Decimal] = Field(None, ge=0)
    basic_salary: Optional[Decimal] = Field(None, ge=0)
    hra_received: Optional[Decimal] = Field(None, ge=0)
    rent_paid: Optional[Decimal] = Field(None, ge=0)
    lta_received: Optional[Decimal] = Field(None, ge=0)
    other_exemptions: Optional[Decimal] = Field(None, ge=0)
    deduction_80c: Optional[Decimal] = Field(None, ge=0)
    deduction_80d: Optional[Decimal] = Field(None, ge=0)
    deduction_80dd: Optional[Decimal] = Field(None, ge=0)
    deduction_80e: Optional[Decimal] = Field(None, ge=0)
    deduction_80tta: Optional[Decimal] = Field(None, ge=0)
    home_loan_interest: Optional[Decimal] = Field(None, ge=0)
    other_deductions: Optional[Decimal] = Field(None, ge=0)
    other_income: Optional[Decimal] = Field(None, ge=0)
    standard_deduction: Optional[Decimal] = Field(None, ge=0)
    professional_tax: Optional[Decimal] = Field(None, ge=0)
    tds: Optional[Decimal] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern='^(draft|completed)$')
    draft_expires_at: Optional[datetime] = None
    is_draft: Optional[bool] = None

class UserFinancials(UserFinancialsBase):
    """Complete model for user financial records"""
    session_id: UUID
    status: str = Field(default="completed")
    draft_expires_at: Optional[datetime] = None
    is_draft: bool = Field(default=False)
    created_at: datetime
    
    model_config = {"from_attributes": True}

class DraftResponse(BaseModel):
    """Response model for draft operations"""
    draft_id: UUID
    message: str
    expires_at: datetime

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    database: str
    version: str

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    timestamp: datetime

# Tax Calculation Models
class TaxCalculationRequest(BaseModel):
    """Request model for tax calculation"""
    session_id: UUID

class TaxCalculationResponse(BaseModel):
    """Response model for tax calculation"""
    session_id: UUID
    old_regime_tax: Decimal
    new_regime_tax: Decimal
    best_regime: str
    tax_savings: Decimal
    calculation_details: dict
    recommendations: dict

class TaxComparison(BaseModel):
    """Model for tax comparison results"""
    session_id: UUID
    tax_old_regime: Decimal
    tax_new_regime: Decimal
    best_regime: str
    selected_regime: Optional[str] = None
    calculation_details: Optional[dict] = None
    recommendations: Optional[dict] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}

class RegimeSelectionRequest(BaseModel):
    """Model for regime selection request"""
    session_id: str
    selected_regime: str = Field(..., pattern='^(old|new)$')
    
    model_config = {"from_attributes": True}

class RegimeSelection(BaseModel):
    """Model for regime selection"""
    session_id: UUID
    selected_regime: str = Field(..., pattern='^(old|new)$')
    created_at: datetime
    
    model_config = {"from_attributes": True}

class UserTracking(BaseModel):
    """Model for user tracking and cookie management"""
    user_id: str = Field(..., description="Unique user identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"from_attributes": True}

# AI Advisor Models
class AIAdvisorConversationBase(BaseModel):
    """Base model for AI Advisor conversation"""
    session_id: UUID
    conversation_round: int = Field(..., ge=1, le=4)
    gemini_question: str = Field(..., min_length=10, max_length=500)
    user_response: str = Field(..., min_length=0, max_length=1000)  # Allow empty responses for initial conversation
    conversation_context: Optional[dict] = None

class AIAdvisorConversationCreate(AIAdvisorConversationBase):
    """Model for creating AI Advisor conversation"""
    pass

class AIAdvisorConversation(AIAdvisorConversationBase):
    """Model for AI Advisor conversation with ID and timestamps"""
    conversation_id: UUID
    created_at: datetime
    
    model_config = {"from_attributes": True}

class AIAdvisorRecommendationBase(BaseModel):
    """Base model for AI Advisor recommendations"""
    session_id: UUID
    conversation_id: UUID
    recommendation_type: str = Field(..., pattern='^(tax_optimization|investment_advice|lifestyle_adjustments|long_term_planning)$')
    recommendation_title: str = Field(..., min_length=10, max_length=100)
    recommendation_description: str = Field(..., min_length=20, max_length=500)
    action_items: Optional[list] = None
    priority_level: str = Field(default='medium', pattern='^(low|medium|high)$')
    estimated_savings: Optional[Decimal] = Field(None, ge=0)

class AIAdvisorRecommendationCreate(AIAdvisorRecommendationBase):
    """Model for creating AI Advisor recommendations"""
    pass

class AIAdvisorRecommendation(AIAdvisorRecommendationBase):
    """Model for AI Advisor recommendations with ID and timestamps"""
    recommendation_id: UUID
    created_at: datetime
    
    model_config = {"from_attributes": True}

class AIAdvisorSession(BaseModel):
    """Model for AI Advisor session context"""
    session_id: UUID
    financial_data: dict
    tax_results: dict
    conversation_history: Optional[list] = None
    current_round: int = Field(default=1, ge=1, le=4)
    is_completed: bool = Field(default=False)
    
    model_config = {"from_attributes": True}
