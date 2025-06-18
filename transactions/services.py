import re
import google.generativeai as genai
from decouple import config
import os

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

        # 1. Check beneficiary name
        if self.bank_account.account_name.lower() not in text.lower():
            return False, "Beneficiary name does not match association's bank account name."

        # 2. Check amount
        expected_amount_str = self.clean_amount(self.amount_paid)
        amounts_in_text = self.extract_amounts_from_text(text)
        if expected_amount_str not in amounts_in_text:
            return False, "Amount paid does not match payment items total."

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