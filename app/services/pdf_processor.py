import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import tempfile
import os

# PDF processing libraries
import PyPDF2
from pdf2image import convert_from_path
import pytesseract
from PIL import Image

# AI/ML
import google.generativeai as genai

from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF processing service for salary slips and Form 16 documents"""
    
    def __init__(self):
        self.gemini_client = None
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_client = genai.GenerativeModel('gemini-pro')
        
        # Document type patterns
        self.salary_slip_patterns = [
            'salary', 'pay slip', 'payslip', 'monthly', 'basic salary', 'gross salary'
        ]
        self.form16_patterns = [
            'form 16', 'form16', 'annual', 'tax deduction', 'tds', 'income tax'
        ]
    
    async def process_pdf(self, pdf_file_path: str, document_type: str = None, password: str = None) -> Dict:
        """
        Process PDF file and extract financial data
        
        Args:
            pdf_file_path: Path to the PDF file
            document_type: Type of document ('salary_slip', 'form16', or None for auto-detect)
            password: Password for password-protected PDFs
        
        Returns:
            Dictionary containing extracted financial data
        """
        try:
            logger.info(f"Processing PDF: {pdf_file_path}")
            if password:
                logger.info("Processing password-protected PDF")
            
            # Auto-detect document type if not specified
            if not document_type:
                document_type = await self._detect_document_type(pdf_file_path, password)
                logger.info(f"Detected document type: {document_type}")
            
            # Extract text using multiple methods
            extracted_text = await self._extract_text(pdf_file_path, password)
            logger.info(f"Text extraction completed. Length: {len(extracted_text)} characters")
            
            # Debug: Log first part of extracted text
            if extracted_text:
                logger.debug(f"Extracted text preview: {extracted_text[:200]}...")
            else:
                logger.warning("No text extracted from PDF")
            
            # Use Gemini to structure and validate data
            structured_data = await self._structure_data_with_ai(extracted_text, document_type)
            
            # Log extraction results
            non_zero_fields = {k: v for k, v in structured_data.items() if isinstance(v, (int, float)) and v > 0}
            logger.info(f"Data extraction completed. Non-zero fields: {len(non_zero_fields)}")
            logger.info(f"Extracted values: {non_zero_fields}")
            
            # Apply document type specific processing
            if document_type == 'salary_slip':
                structured_data = await self._process_salary_slip_data(structured_data)
            elif document_type == 'form16':
                structured_data = await self._process_form16_data(structured_data)
            
            logger.info("PDF processing completed successfully")
            return {
                'success': True,
                'document_type': document_type,
                'extracted_data': structured_data,
                'raw_text': extracted_text[:500],  # First 500 chars for debugging
                'debug_info': {
                    'text_length': len(extracted_text),
                    'non_zero_fields': len(non_zero_fields),
                    'extraction_method': 'AI' if self.gemini_client else 'Fallback'
                }
            }
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'document_type': document_type,
                'debug_info': {
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            }
    
    async def _detect_document_type(self, pdf_file_path: str, password: str = None) -> str:
        """Auto-detect document type based on content"""
        try:
            # Extract text for analysis
            text = await self._extract_text(pdf_file_path, password)
            text_lower = text.lower()
            
            # Check for salary slip patterns
            salary_score = sum(1 for pattern in self.salary_slip_patterns if pattern in text_lower)
            
            # Check for Form 16 patterns
            form16_score = sum(1 for pattern in self.form16_patterns if pattern in text_lower)
            
            # Determine document type
            if salary_score > form16_score:
                return 'salary_slip'
            elif form16_score > salary_score:
                return 'form16'
            else:
                # Default to salary slip if unclear
                return 'salary_slip'
                
        except Exception as e:
            logger.warning(f"Document type detection failed: {e}")
            return 'salary_slip'  # Default fallback
    
    async def _extract_text(self, pdf_file_path: str, password: str = None) -> str:
        """Extract text from PDF using multiple methods"""
        try:
            extracted_text = ""
            
            # Method 1: PyPDF2 text extraction
            try:
                with open(pdf_file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    # Check if PDF is encrypted
                    if pdf_reader.is_encrypted:
                        if password:
                            try:
                                pdf_reader.decrypt(password)
                                logger.info("Successfully decrypted password-protected PDF")
                            except Exception as e:
                                logger.error(f"Failed to decrypt PDF with provided password: {e}")
                                raise ValueError("Invalid password for PDF")
                        else:
                            logger.error("PDF is password-protected but no password provided")
                            raise ValueError("PDF is password-protected. Please provide the password.")
                    
                    for page in pdf_reader.pages:
                        text = page.extract_text()
                        if text:
                            extracted_text += text + "\n"
                
                logger.info("PyPDF2 text extraction completed")
                
            except Exception as e:
                logger.warning(f"PyPDF2 extraction failed: {e}")
                raise e
            
            # Method 2: OCR if PyPDF2 didn't extract enough text
            if len(extracted_text.strip()) < 100:  # Threshold for insufficient text
                logger.info("Insufficient text from PyPDF2, attempting OCR")
                ocr_text = await self._extract_text_with_ocr(pdf_file_path)
                if ocr_text:
                    extracted_text = ocr_text
                    logger.info("OCR text extraction completed")
            
            return extracted_text.strip()
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise
    
    async def _extract_text_with_ocr(self, pdf_file_path: str) -> str:
        """Extract text using OCR (pytesseract) with image preprocessing"""
        try:
            logger.info("Starting OCR text extraction with preprocessing")
            
            # Convert PDF to images with higher DPI for better OCR
            images = convert_from_path(pdf_file_path, dpi=400, fmt='PNG')
            
            extracted_text = ""
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1} with OCR")
                
                # Preprocess image for better OCR
                processed_image = await self._preprocess_image_for_ocr(image)
                
                # Try multiple OCR configurations
                text = await self._extract_text_with_multiple_configs(processed_image)
                
                if text.strip():
                    extracted_text += f"Page {i+1}:\n{text}\n"
                    logger.info(f"Page {i+1}: Extracted {len(text)} characters")
                else:
                    logger.warning(f"Page {i+1}: No text extracted")
            
            logger.info(f"OCR extraction completed. Total text length: {len(extracted_text)}")
            return extracted_text.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    async def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Preprocess image to improve OCR accuracy"""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Resize if too small (OCR works better on larger images)
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000/width, 1000/height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image  # Return original image if preprocessing fails
    
    async def _extract_text_with_multiple_configs(self, image: Image.Image) -> str:
        """Try multiple OCR configurations to get best results"""
        try:
            # OCR configurations to try
            configs = [
                '--oem 3 --psm 6',  # Default config - uniform block of text
                '--oem 3 --psm 4',  # Single column of text
                '--oem 3 --psm 3',  # Fully automatic page segmentation
                '--oem 3 --psm 11', # Sparse text
                '--oem 3 --psm 12', # Single text line
            ]
            
            best_text = ""
            best_length = 0
            
            for config in configs:
                try:
                    text = pytesseract.image_to_string(image, lang='eng', config=config)
                    if len(text.strip()) > best_length:
                        best_text = text
                        best_length = len(text.strip())
                except Exception as e:
                    logger.debug(f"OCR config '{config}' failed: {e}")
                    continue
            
            return best_text
            
        except Exception as e:
            logger.error(f"Multi-config OCR failed: {e}")
            # Fallback to basic OCR
            return pytesseract.image_to_string(image, lang='eng')
    
    async def _structure_data_with_ai(self, raw_text: str, document_type: str) -> Dict:
        """Use Gemini AI to structure and validate extracted data"""
        try:
            if not self.gemini_client:
                logger.warning("Gemini API not configured, using fallback parsing")
                return await self._fallback_data_parsing(raw_text, document_type)
            
            # Create prompt for Gemini
            prompt = self._create_ai_prompt(raw_text, document_type)
            
            # Get AI response
            response = await asyncio.to_thread(
                self.gemini_client.generate_content, prompt
            )
            
            # Parse AI response
            structured_data = await self._parse_ai_response(response.text, document_type)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"AI data structuring failed: {e}")
            return await self._fallback_data_parsing(raw_text, document_type)
    
    def _create_ai_prompt(self, raw_text: str, document_type: str) -> str:
        """Create AI prompt for data extraction"""
        if document_type == 'salary_slip':
            return f"""
            You are an expert at extracting financial data from Indian salary slips. Analyze the following salary slip text and extract the required information.

            IMPORTANT: Return ONLY a valid JSON object with these exact fields:
            {{
                "gross_salary": <number>,
                "basic_salary": <number>,
                "hra_received": <number>,
                "rent_paid": <number>,
                "deduction_80c": <number>,
                "deduction_80d": <number>,
                "standard_deduction": <number>,
                "professional_tax": <number>,
                "tds": <number>
            }}

            FIELD MAPPING GUIDELINES:
            - "gross_salary": Look for "Gross Salary", "Total Earnings", "Gross Pay", "Total Gross", or similar
            - "basic_salary": Look for "Basic", "Basic Salary", "Basic Pay", or similar
            - "hra_received": Look for "HRA", "House Rent Allowance", "Housing Allowance", or similar
            - "rent_paid": Usually not in salary slip, set to 0 unless explicitly mentioned
            - "deduction_80c": Look for "80C", "PF", "PPF", "ELSS", "Life Insurance", "Provident Fund", or similar tax-saving investments
            - "deduction_80d": Look for "80D", "Medical Insurance", "Health Insurance", "Mediclaim", or similar
            - "standard_deduction": Set to 50000 (standard deduction for FY 2023-24) unless a different amount is explicitly mentioned
            - "professional_tax": Look for "Professional Tax", "PT", or similar
            - "tds": Look for "TDS", "Tax Deducted at Source", "Income Tax", or similar

            EXTRACTION RULES:
            1. Extract only numerical values (remove currency symbols, commas)
            2. If a field is not found or unclear, set it to 0
            3. Look for patterns like "₹ 50,000", "Rs. 50000", "50,000.00"
            4. Consider both "Earnings" and "Deductions" sections
            5. Monthly amounts should be returned as-is (don't annualize)
            6. Return ONLY the JSON object, no explanations or additional text

            SALARY SLIP TEXT:
            {raw_text[:3000]}
            """
        else:  # Form 16
            return f"""
            You are an expert at extracting financial data from Indian Form 16 documents. Analyze the following Form 16 text and extract the required information.

            IMPORTANT: Return ONLY a valid JSON object with these exact fields:
            {{
                "gross_salary": <number>,
                "basic_salary": <number>,
                "hra_received": <number>,
                "rent_paid": <number>,
                "deduction_80c": <number>,
                "deduction_80d": <number>,
                "standard_deduction": <number>,
                "professional_tax": <number>,
                "tds": <number>
            }}

            FIELD MAPPING GUIDELINES:
            - "gross_salary": Look for "Gross Total Income", "Total Income", "Salary Income", or similar (annual amount)
            - "basic_salary": Look for "Basic Salary" in salary breakup (annual amount)
            - "hra_received": Look for "HRA Received", "House Rent Allowance", or similar (annual amount)
            - "rent_paid": Look for "HRA Exemption", "Rent Paid", or calculate from HRA exemption details
            - "deduction_80c": Look for "Section 80C", "Deduction u/s 80C", or similar
            - "deduction_80d": Look for "Section 80D", "Deduction u/s 80D", "Medical Insurance Premium", or similar
            - "standard_deduction": Look for "Standard Deduction" or set to 50000 if not found
            - "professional_tax": Look for "Professional Tax", "PT", or similar
            - "tds": Look for "Tax Deducted at Source", "TDS", "Total Tax Deducted", or similar

            EXTRACTION RULES:
            1. Form 16 contains ANNUAL amounts, return them as-is
            2. Extract only numerical values (remove currency symbols, commas)
            3. If a field is not found, set it to 0
            4. Look for patterns like "₹ 6,00,000", "Rs. 600000", "6,00,000.00"
            5. Check both "Income Details" and "Deduction Details" sections
            6. Return ONLY the JSON object, no explanations or additional text

            FORM 16 TEXT:
            {raw_text[:3000]}
            """
    
    async def _parse_ai_response(self, ai_response: str, document_type: str) -> Dict:
        """Parse AI response and extract structured data"""
        try:
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                
                # Validate and clean data
                cleaned_data = {}
                for field in [
                    'gross_salary', 'basic_salary', 'hra_received', 'rent_paid',
                    'deduction_80c', 'deduction_80d', 'standard_deduction',
                    'professional_tax', 'tds'
                ]:
                    value = data.get(field, 0)
                    # Convert to float and handle None values
                    if value is None:
                        cleaned_data[field] = 0.0
                    else:
                        try:
                            cleaned_data[field] = float(value)
                        except (ValueError, TypeError):
                            cleaned_data[field] = 0.0
                
                return cleaned_data
            else:
                raise ValueError("No JSON found in AI response")
                
        except Exception as e:
            logger.error(f"AI response parsing failed: {e}")
            # Return default values
            return {
                'gross_salary': 0.0,
                'basic_salary': 0.0,
                'hra_received': 0.0,
                'rent_paid': 0.0,
                'deduction_80c': 0.0,
                'deduction_80d': 0.0,
                'standard_deduction': 50000.0,
                'professional_tax': 0.0,
                'tds': 0.0
            }
    
    async def _fallback_data_parsing(self, raw_text: str, document_type: str) -> Dict:
        """Enhanced fallback data parsing when AI is not available"""
        try:
            import re
            
            logger.info("Using fallback parsing for data extraction")
            
            # Initialize data structure
            data = {
                'gross_salary': 0.0,
                'basic_salary': 0.0,
                'hra_received': 0.0,
                'rent_paid': 0.0,
                'deduction_80c': 0.0,
                'deduction_80d': 0.0,
                'standard_deduction': 50000.0,
                'professional_tax': 0.0,
                'tds': 0.0
            }
            
            # Clean and normalize text
            text_clean = re.sub(r'\s+', ' ', raw_text.lower())
            
            # Enhanced regex patterns for different fields
            patterns = {
                'gross_salary': [
                    r'gross\s+salary\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'total\s+earnings\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'gross\s+pay\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'total\s+gross\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                ],
                'basic_salary': [
                    r'basic\s+salary\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'basic\s+pay\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'basic\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                ],
                'hra_received': [
                    r'hra\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'house\s+rent\s+allowance\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'housing\s+allowance\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                ],
                'deduction_80c': [
                    r'80c\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'pf\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'provident\s+fund\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'ppf\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'elss\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                ],
                'deduction_80d': [
                    r'80d\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'medical\s+insurance\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'health\s+insurance\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'mediclaim\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                ],
                'professional_tax': [
                    r'professional\s+tax\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'pt\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                ],
                'tds': [
                    r'tds\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'tax\s+deducted\s+at\s+source\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                    r'income\s+tax\s*:?\s*₹?\s*([\d,]+\.?\d*)',
                ]
            }
            
            # Extract data using patterns
            for field, field_patterns in patterns.items():
                for pattern in field_patterns:
                    matches = re.findall(pattern, text_clean)
                    if matches:
                        try:
                            # Take the first match and clean it
                            amount_str = matches[0].replace(',', '')
                            amount = float(amount_str)
                            data[field] = amount
                            logger.info(f"Fallback extraction - {field}: {amount}")
                            break  # Stop after first successful match for this field
                        except ValueError:
                            continue
            
            # Additional context-based extraction
            await self._context_based_extraction(text_clean, data)
            
            # Validate extracted data
            data = await self._validate_extracted_data(data, document_type)
            
            logger.info(f"Fallback parsing completed: {sum(1 for v in data.values() if v > 0)} fields extracted")
            return data
            
        except Exception as e:
            logger.error(f"Fallback parsing failed: {e}")
            return {
                'gross_salary': 0.0,
                'basic_salary': 0.0,
                'hra_received': 0.0,
                'rent_paid': 0.0,
                'deduction_80c': 0.0,
                'deduction_80d': 0.0,
                'standard_deduction': 50000.0,
                'professional_tax': 0.0,
                'tds': 0.0
            }
    
    async def _context_based_extraction(self, text: str, data: Dict) -> None:
        """Extract data using context and position-based heuristics"""
        try:
            import re
            
            # Split text into lines for better context analysis
            lines = text.split('\n')
            
            # Look for table-like structures
            for i, line in enumerate(lines):
                line_clean = line.strip()
                
                # Look for earnings/deductions sections
                if 'earnings' in line_clean or 'income' in line_clean:
                    # Process next few lines for earnings
                    for j in range(i+1, min(i+10, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                            
                        # Look for amount patterns in earnings section
                        amounts = re.findall(r'₹?\s*([\d,]+\.?\d*)', next_line)
                        if amounts:
                            amount_str = amounts[-1].replace(',', '')  # Take last amount (usually the value)
                            try:
                                amount = float(amount_str)
                                
                                # Context-based field assignment
                                if 'basic' in next_line and data['basic_salary'] == 0:
                                    data['basic_salary'] = amount
                                elif 'hra' in next_line and data['hra_received'] == 0:
                                    data['hra_received'] = amount
                                elif ('gross' in next_line or 'total' in next_line) and data['gross_salary'] == 0:
                                    data['gross_salary'] = amount
                            except ValueError:
                                continue
                
                # Look for deductions section
                elif 'deductions' in line_clean or 'deduction' in line_clean:
                    # Process next few lines for deductions
                    for j in range(i+1, min(i+10, len(lines))):
                        next_line = lines[j].strip()
                        if not next_line:
                            continue
                            
                        amounts = re.findall(r'₹?\s*([\d,]+\.?\d*)', next_line)
                        if amounts:
                            amount_str = amounts[-1].replace(',', '')
                            try:
                                amount = float(amount_str)
                                
                                if ('pf' in next_line or 'provident' in next_line) and data['deduction_80c'] == 0:
                                    data['deduction_80c'] = amount
                                elif 'professional' in next_line and data['professional_tax'] == 0:
                                    data['professional_tax'] = amount
                                elif 'tds' in next_line and data['tds'] == 0:
                                    data['tds'] = amount
                            except ValueError:
                                continue
                                
        except Exception as e:
            logger.warning(f"Context-based extraction failed: {e}")
    
    async def _validate_extracted_data(self, data: Dict, document_type: str) -> Dict:
        """Validate and clean extracted data"""
        try:
            # Ensure all values are positive
            for key, value in data.items():
                if value < 0:
                    data[key] = 0.0
            
            # Basic validation rules
            if data['gross_salary'] > 0 and data['basic_salary'] > data['gross_salary']:
                # Basic salary can't be more than gross salary
                data['basic_salary'] = 0.0
            
            if data['hra_received'] > data['gross_salary']:
                # HRA can't be more than gross salary
                data['hra_received'] = 0.0
            
            # Ensure standard deduction is set
            if data['standard_deduction'] == 0:
                data['standard_deduction'] = 50000.0
            
            return data
            
        except Exception as e:
            logger.warning(f"Data validation failed: {e}")
            return data
    
    async def _process_salary_slip_data(self, data: Dict) -> Dict:
        """Process salary slip specific data (monthly to annual conversion)"""
        # Note: This will be handled by the salary aggregator service
        # For now, return data as-is
        return data
    
    async def _process_form16_data(self, data: Dict) -> Dict:
        """Process Form 16 specific data (already annual)"""
        # Form 16 data is already annual, no conversion needed
        return data

# Create global PDF processor instance
pdf_processor = PDFProcessor()

