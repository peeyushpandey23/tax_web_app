from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class UserFinancialsBase(BaseModel):
    """Base model for user financial data"""
    gross_salary: Union[Decimal, float] = Field(..., ge=0, description="Total gross salary")
    basic_salary: Union[Decimal, float] = Field(..., ge=0, description="Basic salary component")
    hra_received: Union[Decimal, float] = Field(default=0, ge=0, description="HRA received")
    rent_paid: Union[Decimal, float] = Field(default=0, ge=0, description="Annual rent paid")
    deduction_80c: Union[Decimal, float] = Field(default=0, ge=0, description="80C investments")
    deduction_80d: Union[Decimal, float] = Field(default=0, ge=0, description="80D medical insurance")
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

class UserFinancialsCreate(UserFinancialsBase):
    """Model for creating new user financial records"""
    session_id: Optional[Union[UUID, str]] = None
    pass

class UserFinancialsUpdate(BaseModel):
    """Model for updating user financial records"""
    gross_salary: Optional[Decimal] = Field(None, ge=0)
    basic_salary: Optional[Decimal] = Field(None, ge=0)
    hra_received: Optional[Decimal] = Field(None, ge=0)
    rent_paid: Optional[Decimal] = Field(None, ge=0)
    deduction_80c: Optional[Decimal] = Field(None, ge=0)
    deduction_80d: Optional[Decimal] = Field(None, ge=0)
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

class RegimeSelection(BaseModel):
    """Model for regime selection"""
    session_id: UUID
    selected_regime: str = Field(..., pattern='^(old|new)$')
