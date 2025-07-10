import requests
import time
import hmac
import hashlib
import base64
import uuid
from django.conf import settings
from urllib.parse import urlencode
from django.utils import timezone

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
        verify_data = {
            'amt': amt,
            'rid': refId,
            'pid': oid,
            'scd': self.MERCHANT_ID,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        max_retries = 3
        base_delay = 1

        for attempt in range(1, max_retries + 1):
            try:
                print(f"eSewa verify attempt {attempt} with data: {verify_data}")
                response = requests.post(self.ESEWA_VERIFY_URL, data=verify_data, headers=headers, timeout=30)
                print(f"Response status: {response.status_code}")
                print(f"Response text: {response.text}")
            except requests.RequestException as e:
                if attempt == max_retries:
                    return False, f'Network error: {e}'
                time.sleep(base_delay * (2 ** (attempt - 1)))
                continue

            if response.status_code != 200:
                if attempt == max_retries:
                    return False, f'HTTP Error {response.status_code}'
                time.sleep(base_delay * (2 ** (attempt - 1)))
                continue

            if 'Success' in response.text or 'SUCCESS' in response.text:
                return True, 'Payment verified successfully'
            else:
                return False, response.text

        return False, 'Verification retry limit reached'

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
