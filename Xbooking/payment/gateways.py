"""
Payment Gateway Integration Module
"""
import requests
from django.conf import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PaystackGateway:
    """Paystack payment gateway integration"""
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def initialize_transaction(self, email, amount, reference, metadata=None, redirect_url=None):
        """
        Initialize a transaction on Paystack
        
        Args:
            email (str): Customer email
            amount (Decimal): Amount in Naira
            reference (str): Unique transaction reference
            metadata (dict): Additional metadata
            redirect_url (str): Optional redirect URL for Paystack callback
            
        Returns:
            dict: Response containing authorization_url and access_code
        """
        try:
            data = {
                "email": email,
                "amount": int(float(amount) * 100),  # Convert to kobo
                "reference": reference,
                "metadata": metadata or {}
            }
            if redirect_url:
                data["callback_url"] = redirect_url
            
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status'):
                    return {
                        'success': True,
                        'authorization_url': response_data['data']['authorization_url'],
                        'access_code': response_data['data']['access_code'],
                        'reference': response_data['data']['reference']
                    }
            
            return {
                'success': False,
                'error': response.json().get('message', 'Failed to initialize transaction'),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API error: {str(e)}")
            return {
                'success': False,
                'error': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Paystack initialization error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_transaction(self, reference):
        """
        Verify a transaction on Paystack
        
        Args:
            reference (str): Transaction reference
            
        Returns:
            dict: Response containing transaction details and status
        """
        try:
            response = requests.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status'):
                    data = response_data['data']
                    return {
                        'success': True,
                        'status': data['status'],
                        'amount': Decimal(str(data['amount'])) / 100,  # Convert from kobo
                        'customer_email': data['customer']['email'],
                        'payment_method': data.get('authorization', {}).get('channel', 'unknown'),
                        'reference': data['reference'],
                        'authorization': data.get('authorization', {})
                    }
            
            return {
                'success': False,
                'error': response.json().get('message', 'Failed to verify transaction'),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack verification error: {str(e)}")
            return {
                'success': False,
                'error': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Paystack verification error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_transfer_recipient(self, type_account, account_number, bank_code, name):
        """
        Create a transfer recipient for payouts
        
        Args:
            type_account (str): 'nuban' for Nigerian bank accounts
            account_number (str): Bank account number
            bank_code (str): Bank code
            name (str): Recipient name
            
        Returns:
            dict: Response containing recipient code
        """
        try:
            data = {
                "type": type_account,
                "account_number": account_number,
                "bank_code": bank_code,
                "name": name
            }
            
            response = requests.post(
                f"{self.base_url}/transferrecipient",
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 201:
                response_data = response.json()
                if response_data.get('status'):
                    return {
                        'success': True,
                        'recipient_code': response_data['data']['recipient_code']
                    }
            
            return {
                'success': False,
                'error': response.json().get('message', 'Failed to create recipient'),
                'status_code': response.status_code
            }
        except Exception as e:
            logger.error(f"Paystack recipient creation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def initiate_transfer(self, source, reason, amount, recipient_code):
        """
        Initiate a transfer/payout
        
        Args:
            source (str): 'balance' for account balance
            reason (str): Reason for transfer
            amount (Decimal): Amount in Naira
            recipient_code (str): Recipient code
            
        Returns:
            dict: Response containing transfer details
        """
        try:
            data = {
                "source": source,
                "reason": reason,
                "amount": int(float(amount) * 100),  # Convert to kobo
                "recipient": recipient_code
            }
            
            response = requests.post(
                f"{self.base_url}/transfer",
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status'):
                    return {
                        'success': True,
                        'transfer_code': response_data['data']['transfer_code'],
                        'reference': response_data['data']['reference']
                    }
            
            return {
                'success': False,
                'error': response.json().get('message', 'Failed to initiate transfer'),
                'status_code': response.status_code
            }
        except Exception as e:
            logger.error(f"Paystack transfer error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class FlutterwaveGateway:
    """Flutterwave payment gateway integration"""
    
    def __init__(self):
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.base_url = "https://api.flutterwave.com/v3"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    def initialize_transaction(self, email, amount, reference, metadata=None, redirect_url=None):
        """
        Initialize a transaction on Flutterwave
        
        Args:
            email (str): Customer email
            amount (Decimal): Amount in Naira
            reference (str): Unique transaction reference (aliased as tx_ref internally)
            metadata (dict): Additional metadata
            redirect_url (str): Optional redirect URL for Flutterwave callback
            
        Returns:
            dict: Response containing payment link
        """
        tx_ref = reference  # Use reference parameter for consistency with Paystack
        try:
            data = {
                "tx_ref": tx_ref,
                "amount": float(amount),
                "currency": "NGN",
                "payment_options": "card,banktransfer,mobilemoneyghana",
                "customer": {
                    "email": email
                },
                "customizations": {
                    "title": metadata.get('order_number', 'Payment') if metadata else 'Payment',
                    "description": metadata.get('description', 'Workspace Booking Payment') if metadata else 'Workspace Booking Payment'
                }
            }
            if redirect_url:
                data["redirect_url"] = redirect_url
            
            response = requests.post(
                f"{self.base_url}/payments",
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 'success':
                    return {
                        'success': True,
                        'authorization_url': response_data['data']['link'],  # Standardize to authorization_url
                        'payment_link': response_data['data']['link'],
                        'reference': tx_ref  # Return the reference we passed in
                    }
            
            return {
                'success': False,
                'error': response.json().get('message', 'Failed to initialize payment'),
                'status_code': response.status_code
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Flutterwave API error: {str(e)}")
            return {
                'success': False,
                'error': f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Flutterwave initialization error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_transaction(self, reference):
        """
        Verify a transaction on Flutterwave
        
        Args:
            refernce (str): refernce 
            
        Returns:
            dict: Response containing transaction details and status
        """
        tx_ref = reference
        
        try:
            response = requests.get(
                f"{self.base_url}/transactions/verify_by_reference?tx_ref={tx_ref}",
                headers=self.headers,
                timeout=30
            )
            # Log the raw response for debugging
            logger.error(f"Flutterwave verify response status: {response.status_code}")
            logger.error(f"Flutterwave verify response text: {response.text}")
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 'success':
                    data = response_data['data']
                    # Use 'charged_amount' if 'amount' is missing
                    amount_val = data.get('amount')
                    if amount_val is None:
                        amount_val = data.get('charged_amount')
                    # Accept both 'success' and 'successful' as status
                    status_val = data.get('status')
                    return {
                        'success': True,
                        'status': status_val,
                        'amount': Decimal(str(amount_val)) if amount_val is not None else None,
                        'customer_email': data.get('customer', {}).get('email', ''),
                        'payment_method': data.get('payment_type', 'unknown'),
                        'reference': data.get('tx_ref'),
                        'currency': data.get('currency')
                    }
            # Try to parse error message if possible
            try:
                error_message = response.json().get('message', 'Failed to verify transaction')
            except Exception:
                error_message = response.text
            return {
                'success': False,
                'error': error_message,
                'status_code': response.status_code
            }
        except Exception as e:
            logger.error(f"Flutterwave verification error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_payment_link(self, reference):
        """
        Get payment link for a transaction
        
        Args:
            reference (str): Transaction reference
            
        Returns:
            str: Payment link URL
        """
        # Flutterwave payment link format
        return f"https://checkout.flutterwave.com/?txref={reference}"
    
    def initiate_transfer(self, account_bank, account_number, amount, narration, beneficiary_name):
        """
        Initiate a transfer/payout via Flutterwave
        
        Args:
            account_bank (str): Bank code
            account_number (str): Recipient account number
            amount (Decimal): Amount in Naira
            narration (str): Transfer description
            beneficiary_name (str): Recipient name
            
        Returns:
            dict: Response containing transfer details
        """
        try:
            data = {
                "account_bank": account_bank,
                "account_number": account_number,
                "amount": float(amount),
                "currency": "NGN",
                "narration": narration,
                "beneficiary_name": beneficiary_name
            }
            
            response = requests.post(
                f"{self.base_url}/transfers",
                json=data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('status') == 'success':
                    return {
                        'success': True,
                        'transfer_id': response_data['data']['id'],
                        'reference': response_data['data']['reference']
                    }
            
            return {
                'success': False,
                'error': response.json().get('message', 'Failed to initiate transfer'),
                'status_code': response.status_code
            }
        except Exception as e:
            logger.error(f"Flutterwave transfer error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
