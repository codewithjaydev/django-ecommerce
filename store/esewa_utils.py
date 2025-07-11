import requests
import time
import hmac
import hashlib
import base64
import uuid
from django.conf import settings
from urllib.parse import urlencode
from django.utils import timezone
import json
import logging

class ESewaPayment:
    """
    eSewa Payment Integration Class
    """

    def __init__(self):
        self.MERCHANT_ID = getattr(settings, 'ESEWA_MERCHANT_ID', 'EPAYTEST')
        self.SUCCESS_URL = getattr(settings, 'ESEWA_SUCCESS_URL', 'http://127.0.0.1:8000/payment/success/')
        self.FAILURE_URL = getattr(settings, 'ESEWA_FAILURE_URL', 'http://127.0.0.1:8000/payment/failure/')
        self.ESEWA_URL = getattr(settings, 'ESEWA_URL', 'https://esewa.com.np/epay/main')
        self.ESEWA_VERIFY_URL = getattr(settings, 'ESEWA_VERIFY_URL', 'https://esewa.com.np/epay/transrec')
        self.ESEWA_SECRET_KEY = getattr(settings, 'ESEWA_SECRET_KEY', '8gBm/:&EnhH.1/q')

    def generate_payment_data(self, order, request):
        if order.date_orderd is None:
            order.date_orderd = timezone.now()

        total_amount = f"{order.get_cart_total:.2f}"
        # transaction_id = f"TXN_{order.id}_{order.customer.user.id}_{order.date_orderd.strftime('%Y%m%d%H%M%S')}"
        transaction_id = f"TXN_{order.id}_{order.customer.user.id}_{order.date_orderd.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        payment_data = {
            'amount': total_amount,
            'product_delivery_charge': '0',
            'product_service_charge': '0',
            'tax_amount': '0',
            'total_amount': total_amount,
            'transaction_uuid': transaction_id,
            'product_code': self.MERCHANT_ID,
            'success_url': self.SUCCESS_URL,
            'failure_url': self.FAILURE_URL,
            'signed_field_names': 'total_amount,transaction_uuid,product_code',
        }

        message = f"total_amount={total_amount},transaction_uuid={transaction_id},product_code={self.MERCHANT_ID}"
        signature = hmac.new(
            key=self.ESEWA_SECRET_KEY.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        payment_data['signature'] = base64.b64encode(signature).decode('utf-8')

        return payment_data, transaction_id

    def get_payment_url(self, payment_data):
        return f"{self.ESEWA_URL}?{urlencode(payment_data)}"

    def verify_payment(self, oid, amt, refId):
        from django.conf import settings
        import logging
        logger = logging.getLogger('store.esewa_utils')

        # v2 verification data and headers
        verify_data_v2 = {
            'amount': amt,
            'referenceId': refId,
            'productCode': self.MERCHANT_ID,
        }
        headers_v2 = {'Content-Type': 'application/json'}

        # v1 verification data and headers
        verify_data_v1 = {
            'amt': amt,
            'rid': refId,
            'pid': oid,
            'scd': self.MERCHANT_ID,
        }
        headers_v1 = {'Content-Type': 'application/x-www-form-urlencoded'}

        # Try v2 first if in RC or PROD
        use_v2 = True
        if getattr(settings, 'ESEWA_ENV', 'RC') == 'RC':
            v2_url = getattr(settings, 'ESEWA_VERIFY_URL', self.ESEWA_VERIFY_URL)
            v1_url = getattr(settings, 'ESEWA_VERIFY_URL_V1', None)
        else:
            v2_url = getattr(settings, 'ESEWA_VERIFY_URL', self.ESEWA_VERIFY_URL)
            v1_url = None

        # Try v2 verification
        if use_v2:
            logger.info(f"Trying eSewa v2 verification at {v2_url} with data: {verify_data_v2}")
            try:
                response = requests.post(v2_url, json=verify_data_v2, headers=headers_v2, timeout=30)
                logger.info(f"v2 Response status: {response.status_code}")
                logger.info(f"v2 Response text: {response.text}")
                if response.status_code == 200:
                    try:
                        json_response = response.json()
                        logger.info(f"v2 JSON response: {json_response}")
                        status = json_response.get('status', '').lower()
                        if status == 'complete':
                            logger.info("Payment verification successful (v2)")
                            return True, 'Payment verified successfully (v2)'
                        else:
                            logger.warning(f"Payment verification failed (v2): {json_response}")
                            return False, response.text
                    except Exception as e:
                        logger.error(f"Error parsing v2 JSON response: {e}")
                        logger.error(f"Unclear v2 verification response: {response.text}")
                        return False, f"Unclear v2 verification response: {response.text}"
                elif response.status_code == 404 and v1_url:
                    logger.warning("v2 endpoint returned 404, falling back to v1 endpoint.")
                    # Fall through to v1
                else:
                    logger.error(f"HTTP Error {response.status_code} on v2 endpoint")
                    return False, f'HTTP Error {response.status_code} (v2)'
            except requests.RequestException as e:
                logger.error(f"Network error on v2 attempt: {e}")
                if not v1_url:
                    return False, f'Network error: {e} (v2)'
                # Fall through to v1

        # Try v1 verification if v2 failed and v1_url is available
        if v1_url:
            logger.info(f"Trying eSewa v1 verification at {v1_url} with data: {verify_data_v1}")
            try:
                response = requests.post(v1_url, data=verify_data_v1, headers=headers_v1, timeout=30)
                logger.info(f"v1 Response status: {response.status_code}")
                logger.info(f"v1 Response text: {response.text}")
                if response.status_code == 200:
                    # v1 is XML, so check for <response_code> or <status>
                    if 'success' in response.text.lower() or 'complete' in response.text.lower():
                        logger.info("Payment verification successful (v1)")
                        return True, 'Payment verified successfully (v1)'
                    else:
                        logger.warning(f"Payment verification failed (v1): {response.text}")
                        return False, response.text
                else:
                    logger.error(f"HTTP Error {response.status_code} on v1 endpoint")
                    return False, f'HTTP Error {response.status_code} (v1)'
            except requests.RequestException as e:
                logger.error(f"Network error on v1 attempt: {e}")
                return False, f'Network error: {e} (v1)'

        return False, 'Verification failed: No valid endpoint or all attempts failed.'

    def process_successful_payment(self, order, refId, oid):
        try:
            order.transaction_id = oid
            order.ref_id = refId
            order.complete = True
            # Do not set payment_status to 'completed' automatically; admin will update it
            order.date_orderd = order.date_orderd or timezone.now()
            order.save()
            return True, "Order marked as paid. Awaiting admin status update."
        except Exception as e:
            return False, f"Error saving order: {str(e)}"

    def process_failed_payment(self, order, reason):
        try:
            order.payment_status = 'failed'
            order.payment_error = reason
            order.save()
            return True, "Payment failure processed."
        except Exception as e:
            return False, f"Error saving failed payment: {str(e)}"
