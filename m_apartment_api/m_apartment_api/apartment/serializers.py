from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from m_apartment_api import settings
from apartment.models import (Resident, Room, Ownership, Payment, Receipt, SecurityCard, Package, Complaint,
                              Survey, SChoice, SurveyQuestion, SurveyChoiceAnswer, SurveyTextAnswer, Notification,
                              MomoLink, MomoPaid, VnpayLink, VnpayPaid)

class BaseSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'name', 'created_date', 'updated_date']

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['active', 'resident']

class ImageSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['image'] = instance.image.url

        return rep

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resident
        fields = ['id', 'username', 'first_name', 'last_name', 'password', 'email', 'is_staff']
        extra_kwargs = {
            'password': {
                'write_only': True
            }
        }

class RoomSerializer(ImageSerializer):
    class Meta:
        model = Room
        fields = BaseSerializer.Meta.fields + ['number', 'description', 'square', 'image', 'is_empty']

class OwnershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ownership
        fields = BaseSerializer.Meta.fields + ['start_date', 'end_date', 'room'] + ItemSerializer.Meta.fields

class ResidentSerializer(serializers.ModelSerializer):
    rooms = serializers.SerializerMethodField()

    def get_rooms(self, obj):
        ownerships = obj.ownership_set.all()
        rooms = [ownership.room for ownership in ownerships]
        return RoomSerializer(rooms, many=True).data

    def create(self, validated_data):
        data = validated_data.copy()
        resident = Resident(**data)
        resident.set_password(data['password'])
        resident.save()

        return resident

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        # Kiểm tra loại dữ liệu của instance.avatar
        if hasattr(instance.avatar, 'url'):
            rep['avatar'] = instance.avatar.url
        else:
            rep['avatar'] = None

        return rep

    class Meta:
        model = Resident
        fields = ['id', 'username', 'first_name', 'last_name', 'password', 'birthday', 'gender', 'email',
                  'phone', 'avatar', 'date_joined', 'rooms', 'answered']
        extra_kwargs = {
            'password': {
                'write_only': True
            },
            'avatar': {
                'required': False  # Không bắt buộc
            }
        }

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = BaseSerializer.Meta.fields + ['amount'] + ItemSerializer.Meta.fields

class MomoLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = MomoLink
        fields = ['partner_code', 'order_id', 'request_id', 'amount', 'created_date', 'updated_date', 'pay_url',
                  'short_link', 'payment']

class MomoPaidSerializer(serializers.ModelSerializer):
    class Meta:
        model = MomoPaid
        fields = ['partner_code', 'order_id', 'request_id', 'amount', 'created_date', 'updated_date', 'order_info',
                  'order_type', 'trans_id', 'pay_type']

class VnpayLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = VnpayLink
        fields = ['txn_ref', 'amount', 'order_info', 'created_date', 'updated_date', 'order_type',
                  'payment_url', 'payment']

class VnpayPaidSerializer(serializers.ModelSerializer):
    class Meta:
        model = VnpayPaid
        fields = ['txn_ref', 'amount', 'order_info', 'created_date', 'updated_date', 'bank_code', 'bank_tran_no',
                  'card_type', 'pay_date', 'transaction_no', 'transaction_status']

class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = BaseSerializer.Meta.fields + ['order_id', 'amount', 'pay_method', 'payment']

class SecurityCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityCard
        fields = BaseSerializer.Meta.fields + ['name_register', 'vehicle_number', 'type_vehicle'] + ItemSerializer.Meta.fields

class PackageSerializer(ImageSerializer):
    class Meta:
        model = Package
        fields = BaseSerializer.Meta.fields + ['note', 'image'] + ItemSerializer.Meta.fields

class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = BaseSerializer.Meta.fields + ['content', 'resident'] + BaseSerializer.Meta.fields

class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = BaseSerializer.Meta.fields + ['description', 'active']

class SChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SChoice
        fields = ['id', 'content', 'question']

class SurveyQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyQuestion
        fields = ['id', 'content', 'created_date', 'updated_date', 'type', 'survey']

# class SurveyAnswerSerializer(serializers.Serializer):
#     class Meta:
#         model = SurveyAnswer
#         fields = ['id', 'created_date', 'updated_date', 'data']

class SurveyTextAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyTextAnswer
        fields = ['id', 'content', 'created_date', 'updated_date', 'question', 'content']

class SurveyChoiceAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyChoiceAnswer
        fields = ['id', 'choice', 'created_date', 'updated_date', 'question', 'choice']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = BaseSerializer.Meta.fields + ['content', 'active']