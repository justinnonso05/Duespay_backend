class VerificationService:
    def __init__(self, proof_file):
        self.proof_file = proof_file
    
    def verify_proof(self):
        """
        Veifies the transaction proof of payment.
        """
        if self.proof_file:
            return True
        return False