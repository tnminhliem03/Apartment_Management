import json
from django.core.management.base import BaseCommand
from django.apps import apps
from datetime import datetime, date
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Export all data to a pure JSON format'

    def handle(self, *args, **options):
        all_data = {}

        for app in apps.get_app_configs():
            for model in app.get_models():
                model_name = model.__name__.lower() + 's'  # Đổi tên thành số nhiều
                all_data[model_name] = {}

                objects = model.objects.all()
                for obj in objects:
                    entry = {}
                    for field in model._meta.fields:
                        if field.name in ['pk', 'id']:
                            continue  # Bỏ qua pk và id
                        value = getattr(obj, field.name)
                        entry[field.name] = self.serialize_value(value)

                    # Sử dụng ID của đối tượng làm khóa
                    all_data[model_name][str(obj.pk)] = entry

        with open('all_data.json', 'w', encoding='utf-8') as json_file:
            json.dump(all_data, json_file, ensure_ascii=False, indent=4)

    def serialize_value(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, ContentType):
            return str(value)
        elif hasattr(value, 'username') and hasattr(value, 'email'):
            return {
                "username": value.username,
                "email": value.email,
            }
        elif isinstance(value, str):
            if value.startswith('image/upload/'):
                return f"https://res.cloudinary.com/dr1frcopo/{value}"  # Thay YOUR_CLOUD_NAME
            return value
        elif hasattr(value, 'url'):
            return value.url
        elif hasattr(value, 'pk'):
            return value.pk
        elif isinstance(value, list):
            return [self.serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: self.serialize_value(v) for k, v in value.items()}

        return str(value)
