import logging
from typing import Dict, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
import math

logger = logging.getLogger(__name__)

class TaxCalculator:
    """Tax calculation service for Indian tax regimes (FY 2024-25)"""
    
    def __init__(self):
        # FY 2024-25 Tax Slabs (Old Regime)
        self.old_regime_slabs = [
            (0, 300000, 0),           # Up to ₹3,00,000
            (300000, 600000, 5),      # ₹3,00,001 to ₹6,00,000
            (600000, 900000, 10),     # ₹6,00,001 to ₹9,00,000
            (900000, 1200000, 15),    # ₹9,00,001 to ₹12,00,000
            (1200000, 1500000, 20),   # ₹12,00,001 to ₹15,00,000
            (1500000, float('inf'), 30)  # Above ₹15,00,000
        ]
        
        # FY 2024-25 Tax Slabs (New Regime)
        self.new_regime_slabs = [
            (0, 300000, 0),           # Up to ₹3,00,000
            (300000, 600000, 5),      # ₹3,00,001 to ₹6,00,000
            (600000, 900000, 10),     # ₹6,00,001 to ₹9,00,000
            (900000, 1200000, 15),    # ₹9,00,001 to ₹12,00,000
            (1200000, 1500000, 20),   # ₹12,00,001 to ₹15,00,000
            (1500000, float('inf'), 30)  # Above ₹15,00,000
        ]
        
        # Cess rate (4% on tax amount)
        self.cess_rate = 0.04
        
        # Maximum deduction limits
        self.max_80c_deduction = 150000
        self.max_80d_deduction = 25000
        self.standard_deduction = 50000
        
    async def calculate_tax(self, financial_data: Dict) -> Dict:
        """
        Calculate tax for both Old and New regimes
        
        Args:
            financial_data: Dictionary containing financial information
            
        Returns:
            Dictionary with tax calculations for both regimes
        """
        try:
            logger.info("Starting tax calculation for both regimes")
            
            # Extract financial data
            gross_salary = float(financial_data.get('gross_salary', 0))
            basic_salary = float(financial_data.get('basic_salary', 0))
            hra_received = float(financial_data.get('hra_received', 0))
            rent_paid = float(financial_data.get('rent_paid', 0))
            deduction_80c = float(financial_data.get('deduction_80c', 0))
            deduction_80d = float(financial_data.get('deduction_80d', 0))
            standard_deduction = float(financial_data.get('standard_deduction', 50000))
            professional_tax = float(financial_data.get('professional_tax', 0))
            tds = float(financial_data.get('tds', 0))
            
            # Calculate Old Regime Tax
            old_regime_tax = await self._calculate_old_regime_tax(
                gross_salary, basic_salary, hra_received, rent_paid,
                deduction_80c, deduction_80d, standard_deduction, professional_tax
            )
            
            # Calculate New Regime Tax
            new_regime_tax = await self._calculate_new_regime_tax(
                gross_salary, professional_tax
            )
            
            # Determine best regime
            best_regime = "old" if old_regime_tax['total_tax'] < new_regime_tax['total_tax'] else "new"
            tax_savings = abs(old_regime_tax['total_tax'] - new_regime_tax['total_tax'])
            
            # Prepare detailed breakdown
            calculation_details = {
                'old_regime': {
                    'gross_income': gross_salary,
                    'deductions': {
                        'hra_exemption': old_regime_tax['hra_exemption'],
                        'standard_deduction': standard_deduction,
                        'section_80c': min(deduction_80c, self.max_80c_deduction),
                        'section_80d': min(deduction_80d, self.max_80d_deduction),
                        'professional_tax': professional_tax,
                        'total_deductions': old_regime_tax['total_deductions']
                    },
                    'taxable_income': old_regime_tax['taxable_income'],
                    'tax_amount': old_regime_tax['tax_amount'],
                    'cess_amount': old_regime_tax['cess_amount'],
                    'total_tax': old_regime_tax['total_tax'],
                    'slab_breakdown': old_regime_tax['slab_breakdown']
                },
                'new_regime': {
                    'gross_income': gross_salary,
                    'deductions': {
                        'standard_deduction': 0,  # No deductions in new regime
                        'professional_tax': professional_tax,
                        'total_deductions': professional_tax
                    },
                    'taxable_income': new_regime_tax['taxable_income'],
                    'tax_amount': new_regime_tax['tax_amount'],
                    'cess_amount': new_regime_tax['cess_amount'],
                    'total_tax': new_regime_tax['total_tax'],
                    'slab_breakdown': new_regime_tax['slab_breakdown']
                },
                'comparison': {
                    'best_regime': best_regime,
                    'tax_savings': tax_savings,
                    'savings_percentage': (tax_savings / max(old_regime_tax['total_tax'], new_regime_tax['total_tax'])) * 100 if max(old_regime_tax['total_tax'], new_regime_tax['total_tax']) > 0 else 0
                }
            }
            
            logger.info(f"Tax calculation completed. Best regime: {best_regime}")
            return calculation_details
            
        except Exception as e:
            logger.error(f"Tax calculation failed: {e}")
            raise
    
    async def _calculate_old_regime_tax(self, gross_salary: float, basic_salary: float,
                                      hra_received: float, rent_paid: float,
                                      deduction_80c: float, deduction_80d: float,
                                      standard_deduction: float, professional_tax: float) -> Dict:
        """Calculate tax under Old Regime with all deductions"""
        try:
            # Calculate HRA exemption
            hra_exemption = await self._calculate_hra_exemption(
                basic_salary, hra_received, rent_paid
            )
            
            # Calculate total deductions
            total_deductions = (
                hra_exemption +
                standard_deduction +
                min(deduction_80c, self.max_80c_deduction) +
                min(deduction_80d, self.max_80d_deduction) +
                professional_tax
            )
            
            # Calculate taxable income
            taxable_income = gross_salary - total_deductions
            
            # Calculate tax using slabs
            tax_amount, slab_breakdown = await self._calculate_tax_by_slabs(
                taxable_income, self.old_regime_slabs
            )
            
            # Calculate cess
            cess_amount = tax_amount * self.cess_rate
            
            # Total tax
            total_tax = tax_amount + cess_amount
            
            return {
                'hra_exemption': hra_exemption,
                'total_deductions': total_deductions,
                'taxable_income': taxable_income,
                'tax_amount': tax_amount,
                'cess_amount': cess_amount,
                'total_tax': total_tax,
                'slab_breakdown': slab_breakdown
            }
            
        except Exception as e:
            logger.error(f"Old regime tax calculation failed: {e}")
            raise
    
    async def _calculate_new_regime_tax(self, gross_salary: float, professional_tax: float) -> Dict:
        """Calculate tax under New Regime (no deductions except professional tax)"""
        try:
            # In new regime, only professional tax is deductible
            total_deductions = professional_tax
            
            # Calculate taxable income
            taxable_income = gross_salary - total_deductions
            
            # Calculate tax using slabs
            tax_amount, slab_breakdown = await self._calculate_tax_by_slabs(
                taxable_income, self.new_regime_slabs
            )
            
            # Calculate cess
            cess_amount = tax_amount * self.cess_rate
            
            # Total tax
            total_tax = tax_amount + cess_amount
            
            return {
                'total_deductions': total_deductions,
                'taxable_income': taxable_income,
                'tax_amount': tax_amount,
                'cess_amount': cess_amount,
                'total_tax': total_tax,
                'slab_breakdown': slab_breakdown
            }
            
        except Exception as e:
            logger.error(f"New regime tax calculation failed: {e}")
            raise
    
    async def _calculate_hra_exemption(self, basic_salary: float, hra_received: float, rent_paid: float) -> float:
        """Calculate HRA exemption under Section 10(13A)"""
        try:
            if hra_received == 0 or rent_paid == 0:
                return 0
            
            # HRA exemption is the minimum of:
            # 1. Actual HRA received
            # 2. Rent paid - 10% of basic salary
            # 3. 50% of basic salary (metro cities) or 40% (non-metro cities)
            
            # For simplicity, assuming metro city (50% of basic salary)
            metro_hra_limit = basic_salary * 0.5
            
            # Rent paid minus 10% of basic salary
            rent_minus_basic = rent_paid - (basic_salary * 0.1)
            
            # Calculate exemption
            hra_exemption = min(
                hra_received,
                rent_minus_basic,
                metro_hra_limit
            )
            
            # Ensure exemption is not negative
            return max(0, hra_exemption)
            
        except Exception as e:
            logger.error(f"HRA exemption calculation failed: {e}")
            return 0
    
    async def _calculate_tax_by_slabs(self, taxable_income: float, slabs: list) -> Tuple[float, list]:
        """Calculate tax using progressive slab system"""
        try:
            if taxable_income <= 0:
                return 0, []
            
            total_tax = 0
            slab_breakdown = []
            
            for i, (lower_limit, upper_limit, rate) in enumerate(slabs):
                if taxable_income <= lower_limit:
                    break
                
                # Calculate income in this slab
                slab_income = min(taxable_income - lower_limit, upper_limit - lower_limit)
                
                if slab_income > 0:
                    # Calculate tax for this slab
                    slab_tax = slab_income * (rate / 100)
                    total_tax += slab_tax
                    
                    # Store breakdown
                    slab_breakdown.append({
                        'slab': f"{lower_limit:,.0f} - {upper_limit:,.0f}",
                        'rate': f"{rate}%",
                        'income': slab_income,
                        'tax': slab_tax
                    })
            
            return total_tax, slab_breakdown
            
        except Exception as e:
            logger.error(f"Slab-based tax calculation failed: {e}")
            return 0, []
    
    async def get_tax_recommendations(self, calculation_details: Dict) -> Dict:
        """Generate tax-saving recommendations based on calculations"""
        try:
            recommendations = []
            
            old_regime = calculation_details['old_regime']
            new_regime = calculation_details['new_regime']
            comparison = calculation_details['comparison']
            
            # Basic recommendation
            if comparison['best_regime'] == 'old':
                recommendations.append({
                    'type': 'regime_choice',
                    'title': 'Choose Old Tax Regime',
                    'description': f'Old regime saves you ₹{comparison["tax_savings"]:,.0f} compared to new regime',
                    'priority': 'high'
                })
            else:
                recommendations.append({
                    'type': 'regime_choice',
                    'title': 'Choose New Tax Regime',
                    'description': f'New regime saves you ₹{comparison["tax_savings"]:,.0f} compared to old regime',
                    'priority': 'high'
                })
            
            # Deduction optimization recommendations
            if old_regime['deductions']['section_80c'] < self.max_80c_deduction:
                remaining_80c = self.max_80c_deduction - old_regime['deductions']['section_80c']
                if remaining_80c > 10000:  # Only suggest if significant amount
                    recommendations.append({
                        'type': 'deduction_optimization',
                        'title': 'Optimize 80C Deductions',
                        'description': f'You can save up to ₹{remaining_80c:,.0f} more in 80C investments (EPF, ELSS, PPF)',
                        'priority': 'medium'
                    })
            
            if old_regime['deductions']['section_80d'] < self.max_80d_deduction:
                remaining_80d = self.max_80d_deduction - old_regime['deductions']['section_80d']
                if remaining_80d > 5000:  # Only suggest if significant amount
                    recommendations.append({
                        'type': 'deduction_optimization',
                        'title': 'Optimize 80D Deductions',
                        'description': f'You can save up to ₹{remaining_80d:,.0f} more in health insurance premiums',
                        'priority': 'medium'
                    })
            
            # HRA optimization
            if old_regime['deductions']['hra_exemption'] == 0 and old_regime['gross_income'] > 600000:
                recommendations.append({
                    'type': 'hra_optimization',
                    'title': 'Consider HRA Benefits',
                    'description': 'If you pay rent, you could save tax through HRA exemption',
                    'priority': 'low'
                })
            
            # Professional tax optimization
            if old_regime['deductions']['professional_tax'] == 0:
                recommendations.append({
                    'type': 'professional_tax',
                    'title': 'Professional Tax Deduction',
                    'description': 'Professional tax paid to state government is deductible',
                    'priority': 'low'
                })
            
            return {
                'recommendations': recommendations,
                'summary': {
                    'total_recommendations': len(recommendations),
                    'high_priority': len([r for r in recommendations if r['priority'] == 'high']),
                    'medium_priority': len([r for r in recommendations if r['priority'] == 'medium']),
                    'low_priority': len([r for r in recommendations if r['priority'] == 'low'])
                }
            }
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return {'recommendations': [], 'summary': {'total_recommendations': 0}}
    
    async def validate_financial_data(self, financial_data: Dict) -> Tuple[bool, list]:
        """Validate financial data for tax calculation"""
        try:
            errors = []
            
            # Check required fields
            required_fields = ['gross_salary', 'basic_salary']
            for field in required_fields:
                if field not in financial_data or financial_data[field] <= 0:
                    errors.append(f"{field.replace('_', ' ').title()} is required and must be positive")
            
            # Check basic salary vs gross salary
            if 'gross_salary' in financial_data and 'basic_salary' in financial_data:
                if financial_data['basic_salary'] > financial_data['gross_salary']:
                    errors.append("Basic salary cannot be greater than gross salary")
            
            # Check deduction limits
            if 'deduction_80c' in financial_data and financial_data['deduction_80c'] > self.max_80c_deduction:
                errors.append(f"80C deduction cannot exceed ₹{self.max_80c_deduction:,}")
            
            if 'deduction_80d' in financial_data and financial_data['deduction_80d'] > self.max_80d_deduction:
                errors.append(f"80D deduction cannot exceed ₹{self.max_80d_deduction:,}")
            
            # Check reasonable salary ranges
            if 'gross_salary' in financial_data:
                gross = financial_data['gross_salary']
                if gross < 300000:
                    errors.append("Gross salary seems too low for salaried employee")
                elif gross > 50000000:
                    errors.append("Gross salary seems unreasonably high")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Financial data validation failed: {e}")
            return False, [f"Validation error: {str(e)}"]

# Create global tax calculator instance
tax_calculator = TaxCalculator()

