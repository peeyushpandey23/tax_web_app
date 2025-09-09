import logging
from typing import Dict, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
import math

logger = logging.getLogger(__name__)

class TaxCalculator:
    """Tax calculation service for Indian tax regimes (FY 2024-25)"""
    
    def __init__(self):
        # FY 2024-25 Tax Slabs (Old Regime) - CORRECTED
        self.old_regime_slabs = [
            (0, 250000, 0),           # Up to ₹2,50,000
            (250000, 500000, 5),       # ₹2,50,001 to ₹5,00,000
            (500000, 1000000, 20),     # ₹5,00,001 to ₹10,00,000
            (1000000, float('inf'), 30)  # Above ₹10,00,000
        ]
        
        # FY 2024-25 Tax Slabs (New Regime) - CORRECTED
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
        self.max_80dd_deduction = 125000
        self.max_80e_deduction = 40000
        self.max_80tta_deduction = 10000
        self.max_home_loan_interest = 200000
        self.standard_deduction = 50000
        
        # Section 87A rebate limits
        self.old_regime_rebate_limit = 500000
        self.old_regime_rebate_amount = 12500
        self.new_regime_rebate_limit = 700000
        self.new_regime_rebate_amount = 25000
        
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
            financial_year = financial_data.get('financial_year', '2024-25')
            age = financial_data.get('age', 30)  # Default age if not provided
            gross_salary = float(financial_data.get('gross_salary', 0))
            basic_salary = float(financial_data.get('basic_salary', 0))
            hra_received = float(financial_data.get('hra_received', 0))
            rent_paid = float(financial_data.get('rent_paid', 0))
            lta_received = float(financial_data.get('lta_received', 0))
            other_exemptions = float(financial_data.get('other_exemptions', 0))
            deduction_80c = float(financial_data.get('deduction_80c', 0))
            deduction_80d = float(financial_data.get('deduction_80d', 0))
            deduction_80dd = float(financial_data.get('deduction_80dd', 0))
            deduction_80e = float(financial_data.get('deduction_80e', 0))
            deduction_80tta = float(financial_data.get('deduction_80tta', 0))
            home_loan_interest = float(financial_data.get('home_loan_interest', 0))
            other_deductions = float(financial_data.get('other_deductions', 0))
            other_income = float(financial_data.get('other_income', 0))
            standard_deduction = float(financial_data.get('standard_deduction', 50000))
            professional_tax = float(financial_data.get('professional_tax', 0))
            tds = float(financial_data.get('tds', 0))
            
            # Calculate Old Regime Tax
            old_regime_tax = await self._calculate_old_regime_tax(
                financial_year, age, gross_salary, basic_salary, hra_received, rent_paid,
                lta_received, other_exemptions, deduction_80c, deduction_80d,
                deduction_80dd, deduction_80e, deduction_80tta, home_loan_interest,
                other_deductions, other_income, standard_deduction, professional_tax
            )
            
            # Calculate New Regime Tax
            new_regime_tax = await self._calculate_new_regime_tax(
                financial_year, age, gross_salary, other_income, standard_deduction, professional_tax
            )
            
            # Determine best regime
            best_regime = "old" if old_regime_tax['total_tax'] < new_regime_tax['total_tax'] else "new"
            tax_savings = abs(old_regime_tax['total_tax'] - new_regime_tax['total_tax'])
            
            # Prepare detailed breakdown
            calculation_details = {
                'financial_year': financial_year,
                'age': age,
                'old_regime': {
                    'gross_total_income': gross_salary + other_income,
                    'exemptions': {
                        'hra_exemption': old_regime_tax['hra_exemption'],
                        'lta_exemption': old_regime_tax['lta_exemption'],
                        'other_exemptions': other_exemptions,
                        'total_exemptions': old_regime_tax['total_exemptions']
                    },
                    'deductions': {
                        'standard_deduction': standard_deduction,
                        'section_80c': min(deduction_80c, self.max_80c_deduction),
                        'section_80d': min(deduction_80d, self.max_80d_deduction),
                        'section_80dd': min(deduction_80dd, self.max_80dd_deduction),
                        'section_80e': min(deduction_80e, self.max_80e_deduction),
                        'section_80tta': min(deduction_80tta, self.max_80tta_deduction),
                        'home_loan_interest': min(home_loan_interest, self.max_home_loan_interest),
                        'other_deductions': other_deductions,
                        'professional_tax': professional_tax,
                        'total_deductions': old_regime_tax['total_deductions']
                    },
                    'taxable_income': old_regime_tax['taxable_income'],
                    'tax_amount': old_regime_tax['tax_amount'],
                    'rebate_87a': old_regime_tax['rebate_87a'],
                    'tax_after_rebate': old_regime_tax['tax_after_rebate'],
                    'cess_amount': old_regime_tax['cess_amount'],
                    'total_tax': old_regime_tax['total_tax'],
                    'slab_breakdown': old_regime_tax['slab_breakdown']
                },
                'new_regime': {
                    'gross_total_income': gross_salary + other_income,
                    'deductions': {
                        'standard_deduction': standard_deduction,
                        'professional_tax': professional_tax,
                        'total_deductions': standard_deduction + professional_tax
                    },
                    'taxable_income': new_regime_tax['taxable_income'],
                    'tax_amount': new_regime_tax['tax_amount'],
                    'rebate_87a': new_regime_tax['rebate_87a'],
                    'tax_after_rebate': new_regime_tax['tax_after_rebate'],
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
    
    async def _calculate_old_regime_tax(self, financial_year: str, age: int, gross_salary: float, 
                                       basic_salary: float, hra_received: float, rent_paid: float,
                                       lta_received: float, other_exemptions: float, deduction_80c: float,
                                       deduction_80d: float, deduction_80dd: float, deduction_80e: float,
                                       deduction_80tta: float, home_loan_interest: float, other_deductions: float,
                                       other_income: float, standard_deduction: float, professional_tax: float) -> Dict:
        """Calculate tax under Old Regime with all deductions and exemptions"""
        try:
            # Calculate exemptions
            hra_exemption = await self._calculate_hra_exemption(basic_salary, hra_received, rent_paid)
            lta_exemption = await self._calculate_lta_exemption(lta_received)
            
            total_exemptions = hra_exemption + lta_exemption + other_exemptions
            
            # Calculate total deductions under Chapter VI-A
            total_chapter_6a_deductions = (
                min(deduction_80c, self.max_80c_deduction) +
                min(deduction_80d, self.max_80d_deduction) +
                min(deduction_80dd, self.max_80dd_deduction) +
                min(deduction_80e, self.max_80e_deduction) +
                min(deduction_80tta, self.max_80tta_deduction) +
                min(home_loan_interest, self.max_home_loan_interest) +
                other_deductions
            )
            
            # Calculate total deductions
            total_deductions = (
                total_exemptions +
                standard_deduction +
                total_chapter_6a_deductions +
                professional_tax
            )
            
            # Calculate gross total income
            gross_total_income = gross_salary + other_income
            
            # Calculate taxable income
            taxable_income = gross_total_income - total_deductions
            
            # Calculate tax using slabs
            tax_amount, slab_breakdown = await self._calculate_tax_by_slabs(
                taxable_income, self.old_regime_slabs
            )
            
            # Calculate Section 87A rebate
            rebate_87a = await self._calculate_section_87a_rebate(
                taxable_income, tax_amount, self.old_regime_rebate_limit, self.old_regime_rebate_amount
            )
            
            # Tax after rebate
            tax_after_rebate = max(0, tax_amount - rebate_87a)
            
            # Calculate cess
            cess_amount = tax_after_rebate * self.cess_rate
            
            # Total tax
            total_tax = tax_after_rebate + cess_amount
            
            return {
                'hra_exemption': hra_exemption,
                'lta_exemption': lta_exemption,
                'total_exemptions': total_exemptions,
                'total_deductions': total_deductions,
                'taxable_income': taxable_income,
                'tax_amount': tax_amount,
                'rebate_87a': rebate_87a,
                'tax_after_rebate': tax_after_rebate,
                'cess_amount': cess_amount,
                'total_tax': total_tax,
                'slab_breakdown': slab_breakdown
            }
            
        except Exception as e:
            logger.error(f"Old regime tax calculation failed: {e}")
            raise
    
    async def _calculate_new_regime_tax(self, financial_year: str, age: int, gross_salary: float, 
                                      other_income: float, standard_deduction: float, professional_tax: float) -> Dict:
        """Calculate tax under New Regime with standard deduction and professional tax only"""
        try:
            # In new regime, only standard deduction and professional tax are deductible
            total_deductions = standard_deduction + professional_tax
            
            # Calculate gross total income
            gross_total_income = gross_salary + other_income
            
            # Calculate taxable income
            taxable_income = gross_total_income - total_deductions
            
            # Calculate tax using slabs
            tax_amount, slab_breakdown = await self._calculate_tax_by_slabs(
                taxable_income, self.new_regime_slabs
            )
            
            # Calculate Section 87A rebate
            rebate_87a = await self._calculate_section_87a_rebate(
                taxable_income, tax_amount, self.new_regime_rebate_limit, self.new_regime_rebate_amount
            )
            
            # Tax after rebate
            tax_after_rebate = max(0, tax_amount - rebate_87a)
            
            # Calculate cess
            cess_amount = tax_after_rebate * self.cess_rate
            
            # Total tax
            total_tax = tax_after_rebate + cess_amount
            
            return {
                'total_deductions': total_deductions,
                'taxable_income': taxable_income,
                'tax_amount': tax_amount,
                'rebate_87a': rebate_87a,
                'tax_after_rebate': tax_after_rebate,
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
    
    async def _calculate_lta_exemption(self, lta_received: float) -> float:
        """Calculate LTA exemption under Section 10(5)"""
        try:
            # LTA exemption is limited to actual LTA received
            # For simplicity, assuming full exemption (in practice, there are specific rules)
            return lta_received  # LTA exemption is typically the amount received
            
        except Exception as e:
            logger.error(f"LTA exemption calculation failed: {e}")
            return 0
    
    async def _calculate_section_87a_rebate(self, taxable_income: float, tax_amount: float, 
                                          rebate_limit: float, rebate_amount: float) -> float:
        """Calculate Section 87A rebate"""
        try:
            if taxable_income <= rebate_limit:
                return min(tax_amount, rebate_amount)
            return 0
            
        except Exception as e:
            logger.error(f"Section 87A rebate calculation failed: {e}")
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
            if old_regime['exemptions']['hra_exemption'] == 0 and old_regime['gross_total_income'] > 600000:
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
            
            # Check age if provided
            if 'age' in financial_data and financial_data['age'] is not None:
                age = financial_data['age']
                if age < 18 or age > 100:
                    errors.append("Age must be between 18 and 100 years")
            
            # Check financial year format
            if 'financial_year' in financial_data:
                import re
                fy = financial_data['financial_year']
                if not re.match(r'^\d{4}-\d{2}$', fy):
                    errors.append("Financial year must be in format YYYY-YY (e.g., 2024-25)")
            
            # Check basic salary vs gross salary
            if 'gross_salary' in financial_data and 'basic_salary' in financial_data:
                if financial_data['basic_salary'] > financial_data['gross_salary']:
                    errors.append("Basic salary cannot be greater than gross salary")
            
            # Check deduction limits
            deduction_limits = {
                'deduction_80c': self.max_80c_deduction,
                'deduction_80d': self.max_80d_deduction,
                'deduction_80dd': self.max_80dd_deduction,
                'deduction_80e': self.max_80e_deduction,
                'deduction_80tta': self.max_80tta_deduction,
                'home_loan_interest': self.max_home_loan_interest
            }
            
            for field, limit in deduction_limits.items():
                if field in financial_data and financial_data[field] > limit:
                    errors.append(f"{field.replace('_', ' ').title()} cannot exceed ₹{limit:,}")
            
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

