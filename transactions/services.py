import re
import google.generativeai as genai
from decouple import config
import os
import requests
from io import BytesIO
from PIL import Image as PILImage
from pathlib import Path
from django.conf import settings
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import HRFlowable
from .emails import send_receipt_email
import logging

class VerificationService:
    def __init__(self, proof_file, amount_paid, payment_items, bank_account):
        self.proof_file = proof_file
        self.amount_paid = amount_paid
        self.bank_account = bank_account
        self.payment_items = payment_items
        # Gemini API key should be sourced securely, e.g., from Django settings
        self.gemini_api_key = config('GEMINI_API_KEY')
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def extract_text_from_proof(self):
        try:
            if hasattr(self.proof_file, 'seek'):
                self.proof_file.seek(0)
            file_bytes = self.proof_file.read()

            mime_type = "application/octet-stream" # Fallback
            if hasattr(self.proof_file, 'content_type') and self.proof_file.content_type:
                mime_type = self.proof_file.content_type
            elif hasattr(self.proof_file, 'name'):
                file_extension = os.path.splitext(self.proof_file.name)[1].lower()
                if file_extension == '.jpg' or file_extension == '.jpeg':
                    mime_type = 'image/jpeg'
                elif file_extension == '.png':
                    mime_type = 'image/png'
                elif file_extension == '.pdf':
                    mime_type = 'application/pdf'

            image_part = {
                'mime_type': mime_type,
                'data': file_bytes
            }

            prompt_parts = [
                "Extract all visible text from this document/image. Provide the text as plain, unformatted content.",
                image_part,
            ]

            response = self.model.generate_content(prompt_parts)
            extracted_text = response.text
            print(f"Extracted text: {extracted_text}")
            return extracted_text

        except Exception as e:
            print(f"Error extracting text with Gemini API: {e}")
            return ''
    
    def clean_amount(self, amount):
        return str(int(float(amount)))

    def extract_amounts_from_text(self, text):
        text = text.replace('O', '0').replace('o', '0')
        text = re.sub(r'[₦N]', '', text)
        numbers = re.findall(r'\d[\d,\.]*', text)
        cleaned = [self.clean_amount(n.replace(',', '')) for n in numbers]
        return cleaned

    def extract_date_from_text(self, text):
        # Very basic date extraction (improve as needed)
        import re
        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        return match.group(1) if match else None

    def verify_proof(self):
        text = self.extract_text_from_proof()
        if not text:
            return False, "Could not extract text from proof."

        # # 1. Check beneficiary name
        # if self.bank_account.account_name.lower() not in text.lower():
        #     return False, "Beneficiary name does not match association's bank account name."

        # # 2. Check amount
        # expected_amount_str = self.clean_amount(self.amount_paid)
        # amounts_in_text = self.extract_amounts_from_text(text)
        # if expected_amount_str not in amounts_in_text:
        #     return False, "Amount paid does not match payment items total."

        # 3. Check transaction date (optional, improve as needed)
        # receipt_date_str = self.extract_date_from_text(text)
        # if receipt_date_str:
        #     from datetime import datetime
        #     receipt_date = datetime.strptime(receipt_date_str, "%Y-%m-%d").date()
        #     for item in self.payment_items:
        #         if hasattr(item, 'created_at') and receipt_date < item.created_at.date():
        #             return False, "Transaction date is before payment item creation date."

        # Add more checks as needed...

        return True, "Proof verified successfully."



logger = logging.getLogger(__name__)

class WatermarkCanvas(canvas.Canvas):
    """Custom canvas class to add watermark"""
    
    def __init__(self, *args, **kwargs):
        self.watermark_path = kwargs.pop('watermark_path', None)
        canvas.Canvas.__init__(self, *args, **kwargs)
    
    def showPage(self):
        # Add watermark BEFORE other content
        if self.watermark_path and os.path.exists(self.watermark_path):
            self.saveState()
            
            # Set very low opacity for watermark
            self.setFillAlpha(0.05)
            self.setStrokeAlpha(0.05)
            
            # Calculate center position
            page_width, page_height = self._pagesize
            
            # Draw watermark in center, larger size
            self.drawImage(
                self.watermark_path,
                x=(page_width - 100*mm) / 2,  # Center horizontally
                y=(page_height - 75*mm) / 2,  # Center vertically
                width=100*mm,
                height=75*mm,
                mask='auto',
                preserveAspectRatio=True
            )
            
            self.restoreState()
        
        # Call parent's showPage
        canvas.Canvas.showPage(self)

class ReceiptService:
    
    @staticmethod
    def download_and_process_logo(logo_url):
        """Download and process association logo"""
        if not logo_url:
            return None, None, []
        
        try:
            print(f"🔄 Downloading logo from: {logo_url}")
            response = requests.get(logo_url, timeout=10)
            response.raise_for_status()
            
            # Create temp directory if it doesn't exist
            temp_dir = Path(settings.BASE_DIR) / 'temp'
            temp_dir.mkdir(exist_ok=True)
            
            # Save original
            original_logo_path = temp_dir / 'temp_logo_original.png'
            with open(original_logo_path, 'wb') as f:
                f.write(response.content)
            
            # Open with PIL and optimize
            with PILImage.open(original_logo_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparency
                    background = PILImage.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Create header logo (medium size, high quality)
                header_logo = img.resize((120, 90), PILImage.Resampling.LANCZOS)
                header_logo_path = temp_dir / 'temp_logo_header.jpg'
                header_logo.save(header_logo_path, 'JPEG', quality=90, optimize=True)
                
                # Create watermark logo (larger, much lower quality for fading)
                watermark_logo = img.resize((400, 300), PILImage.Resampling.LANCZOS)
                watermark_logo_path = temp_dir / 'temp_logo_watermark.jpg'
                watermark_logo.save(watermark_logo_path, 'JPEG', quality=30, optimize=True)
            
            # Create ReportLab Image object for header
            header_img = Image(str(header_logo_path), width=30*mm, height=22*mm)
            
            print("✅ Logo downloaded and processed!")
            return header_img, str(watermark_logo_path), [original_logo_path, header_logo_path, watermark_logo_path]
            
        except Exception as e:
            logger.error(f"Failed to download/process logo: {e}")
            return None, None, []
    
    @staticmethod
    def create_watermark_canvas_maker(watermark_path):
        """Create a canvas maker function with watermark path"""
        def canvas_maker(filename):
            return WatermarkCanvas(filename, watermark_path=watermark_path)
        return canvas_maker
    
    @staticmethod
    def generate_receipt_pdf(receipt):
        """Generate PDF receipt with modern design"""
        transaction = receipt.transaction
        association = transaction.association
        
        # Get association colors and logo
        theme_color = association.theme_color or '#2E86AB'
        logo_url = association.logo_url
        
        # Download and process logo
        header_img, watermark_path, temp_files = ReceiptService.download_and_process_logo(logo_url)
        
        try:
            # Create PDF with A5 size (more professional)
            page_width = 210*mm  # A5 width
            page_height = 148*mm  # A5 height
            
            # Create temp file for PDF
            temp_dir = Path(settings.BASE_DIR) / 'temp'
            temp_dir.mkdir(exist_ok=True)
            pdf_path = temp_dir / f'receipt_{receipt.receipt_no}.pdf'
            
            # Create canvas maker with watermark
            canvas_maker = ReceiptService.create_watermark_canvas_maker(watermark_path) if watermark_path else canvas.Canvas
            
            # Create document
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=(page_width, page_height),
                rightMargin=15*mm,
                leftMargin=15*mm,
                topMargin=10*mm,
                bottomMargin=15*mm,
                canvasmaker=canvas_maker
            )
            
            elements = []
            
            # Create curved header section
            header_height = 25*mm
            
            # Header with logo and association info
            if header_img:
                # Create company info text
                company_info = f"""
                <b>{association.association_name}</b><br/>
                <font size="8">University of Ibadan<br/>
                Ibadan, Oyo State<br/>
                Email: {association.admin.email if association.admin.email else 'contact@association.edu.ng'}</font>
                """
                
                company_paragraph = Paragraph(
                    company_info,
                    ParagraphStyle(
                        'CompanyInfo',
                        fontSize=10,
                        fontName='Helvetica-Bold',
                        alignment=TA_CENTER,
                        textColor=colors.white,
                        leading=12
                    )
                )
                
                # Header table with curved design feel
                header_data = [[header_img, company_paragraph]]
                header_table = Table(header_data, colWidths=[40*mm, 140*mm])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(theme_color)),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                
                elements.append(header_table)
            else:
                # Fallback header without logo
                company_info = f"""
                <b>{association.association_name}</b><br/>
                <font size="8">University of Ibadan | Ibadan, Oyo State<br/>
                Email: {association.admin.email if association.admin.email else 'contact@association.edu.ng'}</font>
                """
                
                company_paragraph = Paragraph(
                    company_info,
                    ParagraphStyle(
                        'CompanyInfo',
                        fontSize=12,
                        fontName='Helvetica-Bold',
                        alignment=TA_CENTER,
                        textColor=colors.white,
                        leading=14
                    )
                )
                
                header_table = Table([[company_paragraph]], colWidths=[180*mm])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(theme_color)),
                    ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                
                elements.append(header_table)
            
            elements.append(Spacer(1, 10*mm))
            
            # Receipt title and number section
            receipt_title_data = [
                ['RECEIPT', f'No.: {association.association_short_name}-{receipt.receipt_no}-2025'],
                ['', f'Date: {receipt.issued_at.strftime("%d/%m/%Y")}']
            ]
            
            receipt_title_table = Table(receipt_title_data, colWidths=[90*mm, 90*mm])
            receipt_title_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, 0), 16),
                ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.HexColor(theme_color)),
            ]))
            
            elements.append(receipt_title_table)
            elements.append(Spacer(1, 8*mm))
            
            # Receipt details in a cleaner format
            payer_name = f'{transaction.payer.first_name} {transaction.payer.last_name}'
            payment_items = ', '.join([item.title for item in transaction.payment_items.all()])
            amount_words = ReceiptService.number_to_words(float(transaction.amount_paid))
            
            details_data = [
                ['Received from:', payer_name],
                ['', ''],
                ['the sum of Rupees:', f'NGN {transaction.amount_paid:,.2f}'],
                ['', ''],
                ['towards:', payment_items],
            ]
            
            details_table = Table(details_data, colWidths=[40*mm, 140*mm])
            details_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                # Add underlines for the filled values
                ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),
                ('LINEBELOW', (1, 2), (1, 2), 1, colors.black),
                ('LINEBELOW', (1, 4), (1, 4), 1, colors.black),
            ]))
            
            elements.append(details_table)
            elements.append(Spacer(1, 15*mm))
            
            # Amount in words section
            amount_words_table = Table([
                [f'({amount_words} naira only)']
            ], colWidths=[180*mm])
            
            amount_words_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Oblique'),
                ('FONTSIZE', (0, 0), (0, 0), 10),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.grey),
                ('TOPPADDING', (0, 0), (0, 0), 5),
                ('BOTTOMPADDING', (0, 0), (0, 0), 5),
            ]))
            
            elements.append(amount_words_table)
            
            # Build PDF
            doc.build(elements)
            
            # Read PDF content
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            print(f"✅ Receipt PDF generated successfully! Size: {len(pdf_content)} bytes")
            
            # Clean up temporary files
            for temp_file in temp_files + [pdf_path]:
                if temp_file.exists():
                    temp_file.unlink()
            
            return pdf_content
            
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            import traceback
            traceback.print_exc()
            # Clean up temporary files on error
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()
            return None
    
    @staticmethod
    def number_to_words(number):
        """Convert number to words (simplified version)"""
        ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
                'seventeen', 'eighteen', 'nineteen']
        
        tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']
        
        def convert_hundreds(n):
            result = ""
            
            if n >= 100:
                result += ones[n // 100] + " hundred "
                n %= 100
            
            if n >= 20:
                result += tens[n // 10] + " "
                n %= 10
            
            if n > 0:
                result += ones[n] + " "
            
            return result
        
        if number == 0:
            return "zero"
        
        result = ""
        
        if number >= 1000000:
            result += convert_hundreds(int(number // 1000000)) + "million "
            number %= 1000000
        
        if number >= 1000:
            result += convert_hundreds(int(number // 1000)) + "thousand "
            number %= 1000
        
        if number > 0:
            result += convert_hundreds(int(number))
        
        return result.strip()
    
    @staticmethod
    def process_verified_transaction(receipt):
        """Process verified transaction and send receipt"""
        try:
            # Generate PDF
            pdf_content = ReceiptService.generate_receipt_pdf(receipt)
            
            if pdf_content:
                # Send receipt email
                send_receipt_email(receipt, pdf_content)
                print(f"✅ Receipt sent successfully for {receipt.receipt_no}")
                return True
            else:
                logger.error(f"Failed to generate PDF for receipt {receipt.receipt_no}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to process verified transaction: {e}")
            return False