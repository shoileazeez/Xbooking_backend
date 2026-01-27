"""
Payment Webhook Views V1
"""
import json
import logging
import time
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from payment.models import PaymentWebhook
from payment.webhooks.v1.handlers import PaystackWebhookHandler, FlutterwaveWebhookHandler
from core.services import EventBus, Event

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """
    Handle Paystack webhook events
    
    POST /api/v1/payment/webhooks/paystack/
    """
    try:
        # Get raw body for signature verification
        raw_body = request.body
        signature_header = request.headers.get('X-Paystack-Signature')
        
        # Parse JSON payload
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Paystack webhook")
            return Response(
                {'error': 'Invalid JSON'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log webhook
        event_type = payload.get('event', 'unknown')
        gateway_event_id = payload.get('data', {}).get('reference', f"paystack_{event_type}_{int(time.time())}")
        
        webhook_log = PaymentWebhook.objects.create(
            payment_method='paystack',
            gateway_event_id=gateway_event_id,
            payload=payload,
            status='pending'
        )
        
        # Initialize handler
        handler = PaystackWebhookHandler()
        
        # Verify signature
        if signature_header:
            if not handler.verify_signature(raw_body, signature_header):
                webhook_log.status = 'failed'
                webhook_log.error_message = 'Invalid signature'
                webhook_log.processed_at = timezone.now()
                webhook_log.save()
                
                logger.error("Paystack signature verification failed")
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Process webhook
        result = handler.process_webhook(event_type, payload)
        
        # Update webhook log
        webhook_log.status = 'processed' if result.get('success') else 'failed'
        webhook_log.error_message = result.get('error') if not result.get('success') else None
        webhook_log.processed_at = timezone.now()
        webhook_log.save()
        
        # Publish webhook received event
        event = Event(
            event_type='WEBHOOK_RECEIVED',
            data={
                'provider': 'paystack',
                'event_type': event_type,
                'success': result.get('success'),
                'webhook_id': str(webhook_log.id)
            },
            source_module='payment'
        )
        EventBus.publish(event)
        
        if result.get('success'):
            return Response({'message': result.get('message', 'OK')}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': result.get('error', 'Processing failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        logger.error(f"Paystack webhook error: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def flutterwave_webhook(request):
    """
    Handle Flutterwave webhook events
    
    POST /api/v1/payment/webhooks/flutterwave/
    """
    try:
        # Get raw body for signature verification
        raw_body = request.body
        signature_header = request.headers.get('verif-hash')
        
        # Parse JSON payload
        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Flutterwave webhook")
            return Response(
                {'error': 'Invalid JSON'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Determine event type (support both 'event' and 'event.type')
        event_type = payload.get('event')
        if not event_type and 'event.type' in payload:
            event_type = payload['event.type']
        if not event_type and 'eventType' in payload:
            event_type = payload['eventType']
        if not event_type:
            event_type = 'unknown'
        logger.error(f"[FW Webhook] Event: {event_type}")
        logger.error(f"[FW Webhook] Payload: {payload}")
        gateway_event_id = payload.get('data', {}).get('tx_ref') or payload.get('data', {}).get('txRef') or f"flutterwave_{event_type}_{int(time.time())}"
        webhook_log = PaymentWebhook.objects.create(
            payment_method='flutterwave',
            gateway_event_id=gateway_event_id,
            payload=payload,
            status='pending'
        )
        # Initialize handler
        handler = FlutterwaveWebhookHandler()
        # Verify signature
        if signature_header:
            request_body_str = raw_body.decode('utf-8')
            if not handler.verify_signature(request_body_str, signature_header):
                webhook_log.status = 'failed'
                webhook_log.error_message = 'Invalid signature'
                webhook_log.processed_at = timezone.now()
                webhook_log.save()
                logger.error("Flutterwave signature verification failed")
                return Response(
                    {'error': 'Invalid signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        # Process webhook
        logger.error(f"[FW Webhook] Processing event: {event_type}")
        # Patch: treat BANK_TRANSFER_TRANSACTION as charge.completed for deposits/payments
        if event_type == 'BANK_TRANSFER_TRANSACTION':
            event_type_for_handler = 'charge.completed'
        else:
            event_type_for_handler = event_type
        result = handler.process_webhook(event_type_for_handler, payload)
        logger.error(f"[FW Webhook] Handler result: {result}")
        # Update webhook log
        webhook_log.status = 'processed' if result.get('success') else 'failed'
        webhook_log.error_message = result.get('error') if not result.get('success') else None
        webhook_log.processed_at = timezone.now()
        webhook_log.save()
        # Publish webhook received event
        event = Event(
            event_type='WEBHOOK_RECEIVED',
            data={
                'provider': 'flutterwave',
                'event_type': event_type,
                'success': result.get('success'),
                'webhook_id': str(webhook_log.id)
            },
            source_module='payment'
        )
        EventBus.publish(event)
        if result.get('success'):
            return Response({'message': result.get('message', 'OK')}, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': result.get('error', 'Processing failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    except Exception as e:
        logger.error(f"Flutterwave webhook error: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
