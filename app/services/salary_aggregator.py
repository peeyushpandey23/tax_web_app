import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)

class SalaryAggregator:
    """Service for aggregating multiple salary slips and converting to annual amounts"""
    
    def __init__(self):
        self.max_files = 4
        self.months_in_year = 12
    
    async def aggregate_salary_slips(self, salary_data_list: List[Dict], document_type: str) -> Dict:
        """
        Aggregate multiple salary slips into annual totals
        
        Args:
            salary_data_list: List of salary data dictionaries
            document_type: Type of document ('salary_slip' or 'form16')
        
        Returns:
            Dictionary containing aggregated annual financial data
        """
        try:
            if document_type == 'form16':
                # Form 16 is already annual, return as-is
                return salary_data_list[0] if salary_data_list else {}
            
            if len(salary_data_list) == 1:
                # Single salary slip - multiply by 12
                return await self._annualize_single_slip(salary_data_list[0])
            
            elif len(salary_data_list) <= self.max_files:
                # Multiple salary slips - aggregate and interpolate
                return await self._aggregate_multiple_slips(salary_data_list)
            
            else:
                raise ValueError(f"Maximum {self.max_files} salary slips allowed")
                
        except Exception as e:
            logger.error(f"Salary aggregation failed: {e}")
            raise
    
    async def _annualize_single_slip(self, salary_data: Dict) -> Dict:
        """Convert single monthly salary slip to annual amounts"""
        try:
            annual_data = {}
            
            for field, value in salary_data.items():
                if isinstance(value, (int, float)) and field != 'standard_deduction':
                    # Multiply monthly amounts by 12
                    annual_data[field] = value * self.months_in_year
                else:
                    # Keep non-salary fields as-is
                    annual_data[field] = value
            
            logger.info("Single salary slip annualized successfully")
            return annual_data
            
        except Exception as e:
            logger.error(f"Single slip annualization failed: {e}")
            raise
    
    async def _aggregate_multiple_slips(self, salary_data_list: List[Dict]) -> Dict:
        """Aggregate multiple salary slips with interpolation for missing months"""
        try:
            # Validate salary data consistency
            await self._validate_salary_consistency(salary_data_list)
            
            # Aggregate all available data
            aggregated_data = await self._sum_salary_data(salary_data_list)
            
            # Calculate interpolation factor
            interpolation_factor = await self._calculate_interpolation_factor(len(salary_data_list))
            
            # Apply interpolation to get annual totals
            annual_data = await self._apply_interpolation(aggregated_data, interpolation_factor)
            
            logger.info(f"Multiple salary slips aggregated successfully with {len(salary_data_list)} files")
            return annual_data
            
        except Exception as e:
            logger.error(f"Multiple slips aggregation failed: {e}")
            raise
    
    async def _validate_salary_consistency(self, salary_data_list: List[Dict]) -> None:
        """Validate that salary data is consistent across slips"""
        try:
            if not salary_data_list:
                raise ValueError("No salary data provided")
            
            # Check for basic consistency
            first_slip = salary_data_list[0]
            
            for slip in salary_data_list[1:]:
                # Check if basic structure is similar
                if not all(field in slip for field in first_slip.keys()):
                    logger.warning("Salary slip structure varies, proceeding with available data")
                
                # Check for reasonable salary variations (within 20%)
                if 'gross_salary' in first_slip and 'gross_salary' in slip:
                    variation = abs(slip['gross_salary'] - first_slip['gross_salary']) / first_slip['gross_salary']
                    if variation > 0.2:
                        logger.warning(f"Significant salary variation detected: {variation:.2%}")
            
        except Exception as e:
            logger.error(f"Salary consistency validation failed: {e}")
            # Continue processing even if validation fails
    
    async def _sum_salary_data(self, salary_data_list: List[Dict]) -> Dict:
        """Sum up all available salary data"""
        try:
            summed_data = {
                'gross_salary': 0.0,
                'basic_salary': 0.0,
                'hra_received': 0.0,
                'rent_paid': 0.0,
                'deduction_80c': 0.0,
                'deduction_80d': 0.0,
                'standard_deduction': 50000.0,  # Fixed annual amount
                'professional_tax': 0.0,
                'tds': 0.0
            }
            
            for slip in salary_data_list:
                for field in summed_data.keys():
                    if field == 'standard_deduction':
                        # Standard deduction is annual, don't sum
                        continue
                    
                    if field in slip and isinstance(slip[field], (int, float)):
                        summed_data[field] += slip[field]
            
            return summed_data
            
        except Exception as e:
            logger.error(f"Salary data summation failed: {e}")
            raise
    
    async def _calculate_interpolation_factor(self, num_files: int) -> float:
        """Calculate interpolation factor based on number of available files"""
        try:
            # If we have 4 files, we can estimate annual amounts more accurately
            # If we have fewer files, we need to interpolate more
            if num_files == self.max_files:
                # 4 files - assume quarterly data, interpolation factor = 3
                return 3.0
            elif num_files == 3:
                # 3 files - assume quarterly data, interpolation factor = 4
                return 4.0
            elif num_files == 2:
                # 2 files - assume semi-annual data, interpolation factor = 6
                return 6.0
            else:
                # 1 file - monthly data, interpolation factor = 12
                return 12.0
                
        except Exception as e:
            logger.error(f"Interpolation factor calculation failed: {e}")
            return 12.0  # Default fallback
    
    async def _apply_interpolation(self, aggregated_data: Dict, interpolation_factor: float) -> Dict:
        """Apply interpolation to convert aggregated data to annual amounts"""
        try:
            annual_data = {}
            
            for field, value in aggregated_data.items():
                if field == 'standard_deduction':
                    # Standard deduction is already annual
                    annual_data[field] = value
                elif field == 'rent_paid':
                    # Rent paid is typically annual, but if it's monthly, multiply
                    # This is a business logic decision - adjust as needed
                    annual_data[field] = value * interpolation_factor
                else:
                    # All other salary components are monthly, multiply by interpolation factor
                    annual_data[field] = value * interpolation_factor
            
            logger.info(f"Interpolation applied with factor: {interpolation_factor}")
            return annual_data
            
        except Exception as e:
            logger.error(f"Interpolation application failed: {e}")
            raise
    
    async def validate_annual_data(self, annual_data: Dict) -> Tuple[bool, List[str]]:
        """Validate annual financial data for reasonableness"""
        try:
            errors = []
            
            # Check basic salary vs gross salary
            if annual_data.get('basic_salary', 0) > annual_data.get('gross_salary', 0):
                errors.append("Basic salary cannot be greater than gross salary")
            
            # Check deduction limits
            if annual_data.get('deduction_80c', 0) > 150000:
                errors.append("80C deduction cannot exceed ₹1,50,000 annually")
            
            if annual_data.get('deduction_80d', 0) > 25000:
                errors.append("80D deduction cannot exceed ₹25,000 annually")
            
            # Check for reasonable salary ranges
            gross_salary = annual_data.get('gross_salary', 0)
            if gross_salary < 300000:  # ₹25k per month minimum
                errors.append("Gross salary seems too low for salaried employee")
            elif gross_salary > 50000000:  # ₹50L per annum maximum
                errors.append("Gross salary seems unreasonably high")
            
            # Check HRA vs rent paid relationship
            hra_received = annual_data.get('hra_received', 0)
            rent_paid = annual_data.get('rent_paid', 0)
            if hra_received > 0 and rent_paid == 0:
                errors.append("HRA received but no rent paid - please verify")
            
            is_valid = len(errors) == 0
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"Annual data validation failed: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    async def get_processing_summary(self, salary_data_list: List[Dict], final_data: Dict) -> Dict:
        """Generate processing summary for user feedback"""
        try:
            summary = {
                'files_processed': len(salary_data_list),
                'document_type': 'salary_slip' if len(salary_data_list) > 0 else 'form16',
                'interpolation_applied': len(salary_data_list) > 1,
                'annual_conversion': len(salary_data_list) > 0,
                'estimated_accuracy': self._estimate_accuracy(len(salary_data_list)),
                'processing_notes': []
            }
            
            # Add processing notes
            if len(salary_data_list) == 1:
                summary['processing_notes'].append("Single salary slip - monthly amounts multiplied by 12")
            elif len(salary_data_list) > 1:
                summary['processing_notes'].append(f"Multiple salary slips - {len(salary_data_list)} files aggregated")
                summary['processing_notes'].append("Missing months interpolated using available data")
            
            # Add validation notes
            is_valid, errors = await self.validate_annual_data(final_data)
            if not is_valid:
                summary['processing_notes'].extend([f"Warning: {error}" for error in errors])
            
            return summary
            
        except Exception as e:
            logger.error(f"Processing summary generation failed: {e}")
            return {
                'files_processed': 0,
                'document_type': 'unknown',
                'interpolation_applied': False,
                'annual_conversion': False,
                'estimated_accuracy': 'low',
                'processing_notes': [f"Error generating summary: {str(e)}"]
            }
    
    def _estimate_accuracy(self, num_files: int) -> str:
        """Estimate accuracy based on number of files processed"""
        if num_files == 0:
            return 'unknown'
        elif num_files == 1:
            return 'medium'  # Assumes consistent monthly salary
        elif num_files == 2:
            return 'good'     # Semi-annual data
        elif num_files == 3:
            return 'very_good'  # Quarterly data
        elif num_files == 4:
            return 'excellent'   # Quarterly data
        else:
            return 'unknown'

# Create global salary aggregator instance
salary_aggregator = SalaryAggregator()

