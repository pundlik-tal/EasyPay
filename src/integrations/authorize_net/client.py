"""
EasyPay Payment Gateway - Authorize.net Client
"""
import json
import logging
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

from src.core.config import settings
from .models import (
    PaymentRequest,
    PaymentResponse,
    TransactionType,
    TransactionStatus,
    AuthorizeNetCredentials,
    CreditCard,
    BillingAddress
)
from .exceptions import (
    AuthorizeNetError,
    AuthorizeNetAuthenticationError,
    AuthorizeNetTransactionError,
    AuthorizeNetNetworkError,
    AuthorizeNetValidationError
)

logger = logging.getLogger(__name__)


class AuthorizeNetClient:
    """Authorize.net API client for payment processing."""
    
    def __init__(self, credentials: Optional[AuthorizeNetCredentials] = None):
        """
        Initialize Authorize.net client.
        
        Args:
            credentials: Authorize.net credentials. If None, uses settings.
        """
        if credentials:
            self.credentials = credentials
            self.api_url = credentials.api_url or self._get_api_url(credentials.sandbox)
        else:
            self.credentials = AuthorizeNetCredentials(
                api_login_id=settings.AUTHORIZE_NET_API_LOGIN_ID,
                transaction_key=settings.AUTHORIZE_NET_TRANSACTION_KEY,
                sandbox=settings.AUTHORIZE_NET_SANDBOX,
                api_url=settings.get_authorize_net_url()
            )
            self.api_url = settings.get_authorize_net_url()
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "EasyPay-Payment-Gateway/1.0"
            }
        )
        
        logger.info(f"Authorize.net client initialized for {'sandbox' if self.credentials.sandbox else 'production'}")
    
    def _get_api_url(self, sandbox: bool) -> str:
        """Get the appropriate API URL based on environment."""
        if sandbox:
            return "https://apitest.authorize.net/xml/v1/request.api"
        return "https://api.authorize.net/xml/v1/request.api"
    
    async def test_authentication(self) -> bool:
        """
        Test authentication with Authorize.net.
        
        Returns:
            True if authentication is successful
            
        Raises:
            AuthorizeNetAuthenticationError: If authentication fails
        """
        try:
            # Create a simple test request
            test_request = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.credentials.api_login_id,
                        "transactionKey": self.credentials.transaction_key
                    },
                    "refId": "test_auth",
                    "transactionRequest": {
                        "transactionType": "authOnlyTransaction",
                        "amount": "0.01",
                        "payment": {
                            "creditCard": {
                                "cardNumber": "4111111111111111",
                                "expirationDate": "1225",
                                "cardCode": "123"
                            }
                        },
                        "billTo": {
                            "firstName": "Test",
                            "lastName": "User",
                            "address": "123 Test St",
                            "city": "Test City",
                            "state": "CA",
                            "zip": "12345",
                            "country": "US"
                        }
                    }
                }
            }
            
            response = await self._make_request(test_request)
            
            # Check if authentication was successful
            if response.get("messages", {}).get("resultCode") == "Ok":
                logger.info("Authorize.net authentication test successful")
                return True
            else:
                error_msg = response.get("messages", {}).get("message", [{}])[0].get("text", "Authentication failed")
                raise AuthorizeNetAuthenticationError(f"Authentication test failed: {error_msg}")
                
        except AuthorizeNetError:
            raise
        except Exception as e:
            logger.error(f"Authentication test failed with unexpected error: {e}")
            raise AuthorizeNetAuthenticationError(f"Authentication test failed: {str(e)}")
    
    async def charge_credit_card(
        self,
        amount: str,
        credit_card: CreditCard,
        billing_address: BillingAddress,
        order_info: Optional[Dict[str, str]] = None,
        ref_id: Optional[str] = None
    ) -> PaymentResponse:
        """
        Charge a credit card (authorize and capture in one step).
        
        Args:
            amount: Transaction amount in decimal format
            credit_card: Credit card information
            billing_address: Billing address
            order_info: Optional order information
            ref_id: Optional reference ID
            
        Returns:
            PaymentResponse: Transaction response
            
        Raises:
            AuthorizeNetTransactionError: If transaction fails
        """
        try:
            request_data = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.credentials.api_login_id,
                        "transactionKey": self.credentials.transaction_key
                    },
                    "refId": ref_id,
                    "transactionRequest": {
                        "transactionType": "authCaptureTransaction",
                        "amount": amount,
                        "payment": {
                            "creditCard": {
                                "cardNumber": credit_card.card_number,
                                "expirationDate": credit_card.expiration_date,
                                "cardCode": credit_card.card_code
                            }
                        },
                        "billTo": {
                            "firstName": billing_address.first_name,
                            "lastName": billing_address.last_name,
                            "address": billing_address.address,
                            "city": billing_address.city,
                            "state": billing_address.state,
                            "zip": billing_address.zip,
                            "country": billing_address.country
                        }
                    }
                }
            }
            
            if order_info:
                request_data["createTransactionRequest"]["transactionRequest"]["order"] = order_info
            
            response = await self._make_request(request_data)
            return self._parse_transaction_response(response)
            
        except AuthorizeNetError:
            raise
        except Exception as e:
            logger.error(f"Credit card charge failed: {e}")
            raise AuthorizeNetTransactionError(f"Credit card charge failed: {str(e)}")
    
    async def authorize_only(
        self,
        amount: str,
        credit_card: CreditCard,
        billing_address: BillingAddress,
        order_info: Optional[Dict[str, str]] = None,
        ref_id: Optional[str] = None
    ) -> PaymentResponse:
        """
        Authorize a credit card without capturing funds.
        
        Args:
            amount: Transaction amount in decimal format
            credit_card: Credit card information
            billing_address: Billing address
            order_info: Optional order information
            ref_id: Optional reference ID
            
        Returns:
            PaymentResponse: Authorization response
            
        Raises:
            AuthorizeNetTransactionError: If authorization fails
        """
        try:
            request_data = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.credentials.api_login_id,
                        "transactionKey": self.credentials.transaction_key
                    },
                    "refId": ref_id,
                    "transactionRequest": {
                        "transactionType": "authOnlyTransaction",
                        "amount": amount,
                        "payment": {
                            "creditCard": {
                                "cardNumber": credit_card.card_number,
                                "expirationDate": credit_card.expiration_date,
                                "cardCode": credit_card.card_code
                            }
                        },
                        "billTo": {
                            "firstName": billing_address.first_name,
                            "lastName": billing_address.last_name,
                            "address": billing_address.address,
                            "city": billing_address.city,
                            "state": billing_address.state,
                            "zip": billing_address.zip,
                            "country": billing_address.country
                        }
                    }
                }
            }
            
            if order_info:
                request_data["createTransactionRequest"]["transactionRequest"]["order"] = order_info
            
            response = await self._make_request(request_data)
            return self._parse_transaction_response(response)
            
        except AuthorizeNetError:
            raise
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            raise AuthorizeNetTransactionError(f"Authorization failed: {str(e)}")
    
    async def capture(
        self,
        transaction_id: str,
        amount: Optional[str] = None,
        ref_id: Optional[str] = None
    ) -> PaymentResponse:
        """
        Capture previously authorized funds.
        
        Args:
            transaction_id: Original transaction ID
            amount: Amount to capture (if different from authorization)
            ref_id: Optional reference ID
            
        Returns:
            PaymentResponse: Capture response
            
        Raises:
            AuthorizeNetTransactionError: If capture fails
        """
        try:
            request_data = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.credentials.api_login_id,
                        "transactionKey": self.credentials.transaction_key
                    },
                    "refId": ref_id,
                    "transactionRequest": {
                        "transactionType": "priorAuthCaptureTransaction",
                        "refTransId": transaction_id
                    }
                }
            }
            
            if amount:
                request_data["createTransactionRequest"]["transactionRequest"]["amount"] = amount
            
            response = await self._make_request(request_data)
            return self._parse_transaction_response(response)
            
        except AuthorizeNetError:
            raise
        except Exception as e:
            logger.error(f"Capture failed: {e}")
            raise AuthorizeNetTransactionError(f"Capture failed: {str(e)}")
    
    async def refund(
        self,
        transaction_id: str,
        amount: str,
        credit_card: CreditCard,
        ref_id: Optional[str] = None
    ) -> PaymentResponse:
        """
        Refund a transaction.
        
        Args:
            transaction_id: Original transaction ID
            amount: Refund amount
            credit_card: Credit card information
            ref_id: Optional reference ID
            
        Returns:
            PaymentResponse: Refund response
            
        Raises:
            AuthorizeNetTransactionError: If refund fails
        """
        try:
            request_data = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.credentials.api_login_id,
                        "transactionKey": self.credentials.transaction_key
                    },
                    "refId": ref_id,
                    "transactionRequest": {
                        "transactionType": "refundTransaction",
                        "amount": amount,
                        "payment": {
                            "creditCard": {
                                "cardNumber": credit_card.card_number,
                                "expirationDate": credit_card.expiration_date
                            }
                        },
                        "refTransId": transaction_id
                    }
                }
            }
            
            response = await self._make_request(request_data)
            return self._parse_transaction_response(response)
            
        except AuthorizeNetError:
            raise
        except Exception as e:
            logger.error(f"Refund failed: {e}")
            raise AuthorizeNetTransactionError(f"Refund failed: {str(e)}")
    
    async def void_transaction(
        self,
        transaction_id: str,
        ref_id: Optional[str] = None
    ) -> PaymentResponse:
        """
        Void a transaction.
        
        Args:
            transaction_id: Transaction ID to void
            ref_id: Optional reference ID
            
        Returns:
            PaymentResponse: Void response
            
        Raises:
            AuthorizeNetTransactionError: If void fails
        """
        try:
            request_data = {
                "createTransactionRequest": {
                    "merchantAuthentication": {
                        "name": self.credentials.api_login_id,
                        "transactionKey": self.credentials.transaction_key
                    },
                    "refId": ref_id,
                    "transactionRequest": {
                        "transactionType": "voidTransaction",
                        "refTransId": transaction_id
                    }
                }
            }
            
            response = await self._make_request(request_data)
            return self._parse_transaction_response(response)
            
        except AuthorizeNetError:
            raise
        except Exception as e:
            logger.error(f"Void transaction failed: {e}")
            raise AuthorizeNetTransactionError(f"Void transaction failed: {str(e)}")
    
    async def _make_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request to Authorize.net API.
        
        Args:
            data: Request data
            
        Returns:
            Response data
            
        Raises:
            AuthorizeNetNetworkError: If network request fails
        """
        try:
            logger.debug(f"Making request to Authorize.net: {self.api_url}")
            
            response = await self.client.post(
                self.api_url,
                json=data
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error communicating with Authorize.net: {e}")
            raise AuthorizeNetNetworkError(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Authorize.net: {e}")
            raise AuthorizeNetNetworkError("Invalid response format from Authorize.net")
        except Exception as e:
            logger.error(f"Unexpected error communicating with Authorize.net: {e}")
            raise AuthorizeNetNetworkError(f"Unexpected network error: {str(e)}")
    
    def _parse_transaction_response(self, response: Dict[str, Any]) -> PaymentResponse:
        """
        Parse Authorize.net transaction response.
        
        Args:
            response: Raw API response
            
        Returns:
            PaymentResponse: Parsed response
            
        Raises:
            AuthorizeNetTransactionError: If response indicates failure
        """
        try:
            messages = response.get("messages", {})
            result_code = messages.get("resultCode", "Error")
            
            if result_code == "Ok":
                # Successful transaction
                transaction_response = response.get("transactionResponse", {})
                
                return PaymentResponse(
                    transaction_id=transaction_response.get("transId"),
                    status=TransactionStatus.CAPTURED if transaction_response.get("responseCode") == "1" else TransactionStatus.DECLINED,
                    response_code=transaction_response.get("responseCode", "0"),
                    response_text=transaction_response.get("responseText", ""),
                    auth_code=transaction_response.get("authCode"),
                    avs_response=transaction_response.get("avsResultCode"),
                    cvv_response=transaction_response.get("cvvResultCode"),
                    amount=transaction_response.get("amount"),
                    ref_id=response.get("refId"),
                    raw_response=response
                )
            else:
                # Failed transaction
                message_list = messages.get("message", [])
                error_message = message_list[0].get("text", "Transaction failed") if message_list else "Transaction failed"
                error_code = message_list[0].get("code", "0") if message_list else "0"
                
                raise AuthorizeNetTransactionError(
                    message=error_message,
                    response_code=error_code,
                    details={"raw_response": response}
                )
                
        except AuthorizeNetTransactionError:
            raise
        except Exception as e:
            logger.error(f"Error parsing transaction response: {e}")
            raise AuthorizeNetTransactionError(f"Error parsing response: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
