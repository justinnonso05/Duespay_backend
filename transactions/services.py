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
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import HRFlowable
from .emails import send_receipt_email
import logging
from datetime import datetime

class VerificationService:
    def __init__(self, proof_file, amount_paid, payment_items, bank_account):
        self.proof_file = proof_file
        self.amount_paid = amount_paid
        self.bank_account = bank_account
        self.payment_items = payment_items
        self.gemini_api_key = config('GEMINI_API_KEY')
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def extract_text_from_proof(self):
        try:
            if hasattr(self.proof_file, 'seek'):
                self.proof_file.seek(0)
            file_bytes = self.proof_file.read()

            mime_type = "application/octet-stream"
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
        import re
        match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        return match.group(1) if match else None

    def verify_proof(self):
        text = self.extract_text_from_proof()
        if not text:
            return False, "Could not extract text from proof."
        return True, "Proof verified successfully."

logger = logging.getLogger(__name__)

class WatermarkCanvas(canvas.Canvas):
    """Custom canvas class to add watermark"""
    
    def __init__(self, *args, **kwargs):
        self.watermark_path = kwargs.pop('watermark_path', None)
        super().__init__(*args, **kwargs)
    
    def showPage(self):
        # Add watermark to every page
        if self.watermark_path and os.path.exists(self.watermark_path):
            self.saveState()
            
            # Set low opacity for watermark
            self.setFillAlpha(0.08)
            self.setStrokeAlpha(0.08)
            
            # Get page dimensions
            page_width, page_height = self._pagesize
            
            # Calculate center position for watermark
            watermark_width = 120*mm
            watermark_height = 90*mm
            x = (page_width - watermark_width) / 2
            y = (page_height - watermark_height) / 2
            
            # Draw watermark image
            self.drawImage(
                self.watermark_path,
                x=x,
                y=y,
                width=watermark_width,
                height=watermark_height,
                mask='auto',
                preserveAspectRatio=True
            )
            
            self.restoreState()
        
        # Call parent's showPage
        super().showPage()

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
            
            # Open with PIL and create circular mask
            with PILImage.open(original_logo_path) as img:
                # Convert to RGBA if not already
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # Create a square image (crop if needed)
                size = min(img.size)
                left = (img.width - size) // 2
                top = (img.height - size) // 2
                img = img.crop((left, top, left + size, top + size))
                
                # Create circular mask
                mask = PILImage.new('L', (size, size), 0)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, size, size), fill=255)
                
                # Apply circular mask
                circular_img = PILImage.new('RGBA', (size, size), (255, 255, 255, 0))
                circular_img.paste(img, (0, 0))
                circular_img.putalpha(mask)
                
                # Create transparent background for header logo (will blend with header color)
                background = PILImage.new('RGBA', (size, size), (255, 255, 255, 0))
                background.paste(circular_img, (0, 0), circular_img)
                
                # Create header logo (medium size, high quality) - keep transparency
                header_logo = background.resize((100, 100), PILImage.Resampling.LANCZOS)
                header_logo_path = temp_dir / 'temp_logo_header.png'
                header_logo.save(header_logo_path, 'PNG')
                
                # Create watermark logo (larger size for background)
                watermark_logo = background.resize((300, 300), PILImage.Resampling.LANCZOS)
                watermark_logo_path = temp_dir / 'temp_logo_watermark.png'
                watermark_logo.save(watermark_logo_path, 'PNG')
            
            # Create ReportLab Image object for header
            header_img = Image(str(header_logo_path), width=25*mm, height=25*mm)
            
            print("✅ Logo downloaded and processed!")
            return header_img, str(watermark_logo_path), [original_logo_path, header_logo_path, watermark_logo_path]
            
        except Exception as e:
            logger.error(f"Failed to download/process logo: {e}")
            return None, None, []
    
    @staticmethod
    def generate_receipt_pdf(receipt):
        """Generate PDF receipt with modern styling"""
        transaction = receipt.transaction
        association = transaction.association
        
        # Get association colors and logo
        theme_color = association.theme_color or '#7C3AED'
        logo_url = association.logo_url
        
        # Download and process logo
        header_img, watermark_path, temp_files = ReceiptService.download_and_process_logo(logo_url)
        
        try:
            # Create PDF with A4 size
            page_width, page_height = A4
            
            # Create temp file for PDF
            temp_dir = Path(settings.BASE_DIR) / 'temp'
            temp_dir.mkdir(exist_ok=True)
            pdf_path = temp_dir / f'receipt_{receipt.receipt_no}.pdf'
            
            # Create custom canvas with watermark
            def canvas_maker(filename):
                return WatermarkCanvas(filename, watermark_path=watermark_path, pagesize=A4)
            
            # Create document with smaller content area
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=30*mm,
                leftMargin=30*mm,
                topMargin=25*mm,
                bottomMargin=25*mm,
                canvasmaker=canvas_maker
            )
            
            elements = []
            
            # Convert theme color to ReportLab color
            theme_rgb = ReceiptService.hex_to_rgb(theme_color)
            theme_reportlab_color = colors.Color(theme_rgb[0]/255, theme_rgb[1]/255, theme_rgb[2]/255)
            
            # Header section with dynamic theme color
            header_data = []
            if header_img:
                # Plain text without HTML tags - split into two rows
                association_name_line1 = association.association_name.upper()
                association_name_line2 = f"({association.association_short_name.upper()})"
                current_date = datetime.now().strftime("%B %d, %Y")
                
                header_data = [
                    [header_img, association_name_line1, f'Date: {current_date}'],
                    ['', association_name_line2, '']
                ]
                
                header_table = Table(header_data, colWidths=[25*mm, 90*mm, 35*mm])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), theme_reportlab_color),
                    ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (1, 0), (1, 0), 12),
                    ('FONTNAME', (1, 1), (1, 1), 'Helvetica'),
                    ('FONTSIZE', (1, 1), (1, 1), 10),
                    ('FONTNAME', (2, 0), (2, 0), 'Helvetica'),
                    ('FONTSIZE', (2, 0), (2, 0), 9),
                    ('TEXTCOLOR', (1, 0), (-1, -1), colors.white),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                    ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('SPAN', (0, 0), (0, 1)),  # Span logo across both rows
                ]))
            else:
                # Fallback without logo
                association_name_line1 = association.association_name.upper()
                association_name_line2 = f"({association.association_short_name.upper()})"
                current_date = datetime.now().strftime("%B %d, %Y")
                
                header_data = [
                    [association_name_line1, f'Date: {current_date}'],
                    [association_name_line2, '']
                ]
                
                header_table = Table(header_data, colWidths=[115*mm, 35*mm])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), theme_reportlab_color),
                    ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (0, 0), 12),
                    ('FONTNAME', (0, 1), (0, 1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (0, 1), 10),
                    ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
                    ('FONTSIZE', (1, 0), (1, 0), 9),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
        
            elements.append(header_table)
            elements.append(Spacer(1, 8*mm))
            
            # Title section
            title_text = f"<b>PAYMENT RECEIPT</b>"
            title_paragraph = Paragraph(title_text, ParagraphStyle(
                'TitleStyle',
                fontSize=16,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER,
                textColor=theme_reportlab_color,
                spaceAfter=8*mm
            ))
            
            elements.append(title_paragraph)
            
            # Format receipt number properly: SHORTNAME/NO/25
            current_year_short = str(datetime.now().year)[-2:]
            formatted_receipt_no = f"{association.association_short_name.upper()}/{receipt.receipt_no.split('_')[-1]}/{current_year_short}"
            
            # Receipt details in modern card layout
            payer_name = f'{transaction.payer.first_name} {transaction.payer.last_name}'.upper()
            payment_items = ', '.join([item.title for item in transaction.payment_items.all()])
            amount_words = ReceiptService.number_to_words(float(transaction.amount_paid))
            
            # Main content in a clean bordered box
            receipt_data = [
                ['Receipt Number:', formatted_receipt_no],
                ['', ''],
                ['Received From:', payer_name],
                ['', ''],
                ['Amount in Words:', f'{amount_words.title()} Naira Only'],
                ['', ''],
                ['Payment For:', payment_items],
                ['', ''],
                ['Amount Paid:', f'₦{transaction.amount_paid:,.2f}'],
            ]
            
            receipt_table = Table(receipt_data, colWidths=[45*mm, 105*mm])
            receipt_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 8), (1, 8), 'Helvetica-Bold'),  # Amount row
                ('FONTSIZE', (1, 8), (1, 8), 14),  # Amount row
                ('TEXTCOLOR', (1, 8), (1, 8), theme_reportlab_color),  # Amount color
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                # Modern border
                ('BOX', (0, 0), (-1, -1), 1.5, colors.grey),
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.98, 0.98, 0.98)),
                # Underlines for data fields
                ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),
                ('LINEBELOW', (1, 2), (1, 2), 1, colors.black),
                ('LINEBELOW', (1, 4), (1, 4), 1, colors.black),
                ('LINEBELOW', (1, 6), (1, 6), 1, colors.black),
            ]))
            
            elements.append(receipt_table)
            elements.append(Spacer(1, 15*mm))
            
            # Modern signature section
            signature_data = [
                ['STAMP', 'AUTHORIZED SIGNATURE'],
                ['', ''],
                ['', ''],
                ['', '____________________'],
            ]
            
            signature_table = Table(signature_data, colWidths=[75*mm, 75*mm])
            signature_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (1, 3), (1, 3), 'Helvetica'),
                ('FONTSIZE', (1, 3), (1, 3), 9),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            elements.append(signature_table)
            
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
        """Convert number to words"""
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

    @staticmethod
    def hex_to_rgb(hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))