"""
Django management command to generate a secure FILE_UPLOAD_KEY
"""
from django.core.management.base import BaseCommand
import secrets
import string
from datetime import datetime


class Command(BaseCommand):
    help = 'Generate a secure FILE_UPLOAD_KEY for frontend file upload authorization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--length',
            type=int,
            default=64,
            help='Length of the generated key (default: 64)',
        )
        parser.add_argument(
            '--format',
            choices=['base64', 'hex', 'alphanumeric'],
            default='alphanumeric',
            help='Format of the generated key (default: alphanumeric)',
        )

    def handle(self, *args, **options):
        length = options['length']
        fmt = options['format']

        if fmt == 'base64':
            # Generate using URL-safe base64
            import base64
            random_bytes = secrets.token_bytes(length)
            key = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')[:length]
        
        elif fmt == 'hex':
            # Generate hex string
            key = secrets.token_hex(length // 2)[:length]
        
        else:  # alphanumeric
            # Generate alphanumeric with special characters for better security
            chars = string.ascii_letters + string.digits + '-_.'
            key = ''.join(secrets.choice(chars) for _ in range(length))

        self.stdout.write(self.style.SUCCESS(f'\n✅ Generated FILE_UPLOAD_KEY:\n'))
        self.stdout.write(self.style.HTTP_SUCCESS(f'{key}\n'))
        
        # Print instructions
        self.stdout.write(self.style.WARNING('\n📝 Instructions:'))
        self.stdout.write('1. Add to your .env file:')
        self.stdout.write(self.style.HTTP_INFO(f'   FILE_UPLOAD_KEY={key}\n'))
        
        self.stdout.write('2. Frontend should send this key in request headers:')
        self.stdout.write(self.style.HTTP_INFO('   X-File-Upload-Key: {key}\n'))
        self.stdout.write('   OR as query parameter:')
        self.stdout.write(self.style.HTTP_INFO('   ?file_upload_key={key}\n'))
        
        self.stdout.write('3. Usage example with curl:')
        self.stdout.write(self.style.HTTP_INFO(
            f'   curl -X POST http://localhost:8000/api/qr-code/upload/file/ \\\n'
            f'     -H "X-File-Upload-Key: {key}" \\\n'
            f'     -F "file=@image.png"\n'
        ))
        
        self.stdout.write(self.style.SUCCESS('\n✨ Key is ready to use!\n'))
