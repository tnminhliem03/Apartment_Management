from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField
from rest_framework.exceptions import ValidationError


# Create your models here.

class User(AbstractUser):
    pass

class BaseModel(models.Model):
    name = models.CharField(max_length=255)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True

phone_validator = RegexValidator(regex=r'^\d+$', message="Số điện thoại chỉ được chứa các số.")
class Resident(User):
    phone = models.CharField(max_length=11, validators=[phone_validator], unique=True)
    avatar = CloudinaryField(default='avatar_default')
    birthday = models.DateField()
    gender_choices = [('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')]
    gender = models.CharField(max_length=10, choices=gender_choices)
    answered = models.ManyToManyField('Survey', related_name='surveys')

class ItemModel(BaseModel):
    active = models.BooleanField(default=True)
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class Room(BaseModel):
    number = models.CharField(max_length=10, unique=True)
    is_empty = models.BooleanField(default=True)
    square = models.DecimalField(max_digits=5, decimal_places=2)
    image = CloudinaryField()
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.number

class Ownership(ItemModel):
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('room', 'resident', 'start_date')

class Payment(ItemModel):
    amount = models.IntegerField()

class MomoWallet(models.Model):
    partner_code = models.CharField(max_length=20)
    order_id = models.CharField(max_length=50)
    request_id = models.CharField(max_length=50)
    amount = models.IntegerField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class MomoLink(MomoWallet):
    pay_url = models.CharField(max_length=255)
    short_link = models.CharField(max_length=255)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

class MomoPaid(MomoWallet):
    order_info = models.CharField(max_length=255)
    order_type = models.CharField(max_length=50)
    trans_id = models.BigIntegerField()
    pay_type = models.CharField(max_length=20)
    signature = models.CharField(max_length=100)

class VnpayWallet(models.Model):
    txn_ref = models.CharField(max_length=255)
    amount = models.IntegerField()
    order_info = models.CharField(max_length=255)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class VnpayLink(VnpayWallet):
    order_type = models.CharField(max_length=100)
    ip_addr = models.CharField(max_length=45)
    payment_url = models.TextField()
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

class VnpayPaid(VnpayWallet):
    bank_code = models.CharField(max_length=20)
    bank_tran_no = models.CharField(max_length=255)
    card_type = models.CharField(max_length=20)
    pay_date = models.BigIntegerField()
    response_code = models.IntegerField()
    tmn_code = models.CharField(max_length=8)
    transaction_no = models.BigIntegerField()
    transaction_status = models.IntegerField()
    secure_hash = models.CharField(max_length=255)

class Receipt(BaseModel):
    order_id = models.CharField(max_length=255, unique=True)
    pay_choices = [('momo', 'MOMO'), ('vnpay', 'VNPAY')]
    pay_method = models.CharField(max_length=5, choices=pay_choices)
    amount = models.IntegerField()
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

class SecurityCard(ItemModel):
    name_register = models.CharField(max_length=255)
    vehicle_number = models.CharField(max_length=15)
    vehicle_choices = [('bike', 'Xe đạp'), ('motorbike', 'Xe máy'), ('car', 'Xe hơi')]
    type_vehicle = models.CharField(max_length=20, choices=vehicle_choices)

class Package(ItemModel):
    note = models.CharField(max_length=255)
    image = CloudinaryField()

class Complaint(ItemModel):
    content = models.TextField()

class Survey(BaseModel):
    description = models.TextField()
    active = models.BooleanField(default=True)

class SChoice(models.Model):
    content = models.TextField()
    question = models.ForeignKey('SurveyQuestion', related_name='choices', on_delete=models.CASCADE)

    def __str__(self):
        return self.content

class SurveyQuestion(models.Model):
    content = models.TextField()
    type_choices = [('text', 'Tự luận'), ('boolean', 'Yes/No'), ('radiogroup', 'Một lựa chọn'),
                    ('checkbox', 'Nhiều lựa chọn'), ('rating', 'Đánh giá'), ('dropdown', 'Thả xuống'),
                    ('tagbox', 'Thẻ tag'), ('file', 'Tệp'), ('ranking', 'Thứ tự')]
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=50, choices=type_choices)
    survey = models.ForeignKey(Survey, related_name='questions', on_delete=models.CASCADE)

    def __str__(self):
        return self.content

class SurveyAnswer(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    question = models.ForeignKey(SurveyQuestion, related_name='%(class)s_answers', on_delete=models.CASCADE)

    class Meta:
        abstract = True

class SurveyTextAnswer(SurveyAnswer):
    content = models.TextField()

    def __str__(self):
        return self.content

class SurveyChoiceAnswer(SurveyAnswer):
    choice = models.ForeignKey(SChoice, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.choice)

class Notification(BaseModel):
    content = models.TextField()
    active = models.BooleanField(default=True)
