import json
import uuid
import random
import hmac
import hashlib
import requests
from rest_framework import viewsets, generics, parsers, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password
from apartment.models import (User, Resident, Room, Ownership, Payment, Receipt, SecurityCard, Package, Complaint,
                              Survey, SChoice, SurveyQuestion, SurveyChoiceAnswer, SurveyTextAnswer, Notification,
                                MomoLink, MomoPaid, VnpayLink, VnpayPaid)
from apartment import serializers, paginators, perms
from m_apartment_api import settings
from datetime import datetime
from mailjet_rest import Client
from django.shortcuts import render
from firebase_admin import db
from apartment.vnpay import vnpay

# Create your views here.
def write_data(model, pk, fields):
    ref = db.reference(f"{model}/{pk}")
    ref.set(fields)

def read_data(model, pk):
    ref = db.reference(f"{model}/{pk}")
    data = ref.get()
    return data

vnp = vnpay()

# Thêm khảo sát vừa thực hiện vào danh sách các khảo sát đã trả lời của Resident
def add_survey_for_resident(resident, survey):
    resident.answered.add(survey)

# Kiểm tra trạng thái payment
def check_active_payment(payment):
    if (payment.active == 1):
        return 1

# Kiểm tra receipt đã có chưa
def check_receipt(order_id):
    if Receipt.objects.filter(order_id=order_id).exists():
        return 0
    return 1

# Cập nhật trạng thái payment
def update_active_payment(payment):
    if check_active_payment(payment):
        setattr(payment, 'active', '0')
        payment.save()

# Tạo receipt mới khi đã thanh toán
def create_receipt(payment, order_id, pay_type):
    Receipt.objects.create(name=f'Hóa đơn {payment.name}', amount=payment.amount, payment=payment,
                           order_id=order_id, pay_type=pay_type)

# momo
# Tạo chữ kí Momo
def create_signature(rawSignature):
    h = hmac.new(bytes(settings.MOMO_SECRET_KEY, 'ascii'), bytes(rawSignature, 'ascii'), hashlib.sha256)
    signature = h.hexdigest()
    return signature

# Tạo link thanh toán Momo
def create_link_momo(payment):
    endpoint = "https://test-payment.momo.vn/v2/gateway/api/create"
    orderInfo = "Thanh toan hoa don so " + str(payment.id) + " bang Momo"
    redirectUrl = settings.MOMO_RETURN_URL
    ipnUrl = "https://momo.vn"
    amount = payment.amount
    orderId = "MOMO" + ''.join(filter(str.isdigit, str(uuid.uuid4())))
    requestId = "MOMO" + ''.join(filter(str.isdigit, str(uuid.uuid4())))
    extraData = ""  # pass empty value or Encode base64 JsonString
    partnerName = "L Apartment"
    requestType = "payWithMethod"
    storeId = "L Apartment Payment"
    orderGroupId = ""
    autoCapture = True
    lang = "vi"
    orderGroupId = ""

    rawSignature = "accessKey=" + settings.MOMO_ACCESS_KEY + "&amount=" + str(amount) + "&extraData=" + extraData + "&ipnUrl=" + ipnUrl + "&orderId=" + orderId \
                   + "&orderInfo=" + orderInfo + "&partnerCode=" + settings.MOMO_PARTNER_CODE + "&redirectUrl=" + redirectUrl \
                   + "&requestId=" + requestId + "&requestType=" + requestType

    signature = create_signature(rawSignature)

    data = {
        'partnerCode': settings.MOMO_PARTNER_CODE,
        'orderId': orderId,
        'partnerName': partnerName,
        'storeId': storeId,
        'ipnUrl': ipnUrl,
        'amount': amount,
        'lang': lang,
        'requestType': requestType,
        'redirectUrl': redirectUrl,
        'autoCapture': autoCapture,
        'orderInfo': orderInfo,
        'requestId': requestId,
        'extraData': extraData,
        'signature': signature,
        'orderGroupId': orderGroupId
    }
    data = json.dumps(data)
    clen = len(data)
    response = requests.post(endpoint, data=data,
                             headers={'Content-Type': 'application/json', 'Content-Length': str(clen)})

    print(response.json())

    return response.json()

# Lưu thông tin thanh toán
def save_payment(request):
    # momo
    check_momo = request.GET.get('partnerCode', None)
    order_id = request.GET.get('orderId')

    # vnpay
    check_vnp = request.GET.get('vnp_Amount', None)
    txn_ref = request.GET.get('vnp_TxnRef')

    if check_momo is not None and not MomoPaid.objects.filter(order_id=order_id):
        momo_link = MomoLink.objects.get(order_id=order_id)
        payment_momo = momo_link.payment
        MomoPaid.objects.create(partner_code=request.GET.get('partnerCode'), order_id=order_id,
                            request_id=request.GET.get('requestId'), amount=request.GET.get('amount'),
                            order_info=request.GET.get('orderInfo'), order_type=request.GET.get('orderType'),
                            trans_id=request.GET.get('transId'), pay_type=request.GET.get('payType'),
                            signature=request.GET.get('signature'))

        if check_receipt(order_id) and check_active_payment(payment_momo):
            create_receipt(payment_momo, order_id, "momo")
            update_active_payment(payment_momo)

    elif check_vnp is not None and not VnpayPaid.objects.filter(txn_ref=txn_ref):
        vnpay_link = VnpayLink.objects.get(txn_ref=txn_ref)
        payment_vnp = vnpay_link.payment
        VnpayPaid.objects.create(txn_ref=txn_ref, amount=request.GET.get('vnp_Amount'),
                                 order_info=request.GET.get('vnp_OrderInfo'),
                                 bank_code=request.GET.get('vnp_BankCode'),
                                 bank_tran_no=request.GET.get('vnp_BankTranNo'),
                                 card_type=request.GET.get('vnp_CardType'),
                                 pay_date=request.GET.get('vnp_PayDate'),
                                 response_code=request.GET.get('vnp_ResponseCode'),
                                 tmn_code=request.GET.get('vnp_TmnCode'),
                                 transaction_no=request.GET.get('vnp_TransactionNo'),
                                 transaction_status=request.GET.get('vnp_TransactionStatus'),
                                 secure_hash=request.GET.get('vnp_SecureHash'))

        if check_receipt(txn_ref) and check_active_payment(payment_vnp):
            create_receipt(payment_vnp, txn_ref, "vnpay")
            update_active_payment(payment_vnp)

    return render(request, "payment/paid.html")

# Kiểm tra trạng thái Momo
def transaction_status(orderId, requestId):
    endpoint = "https://test-payment.momo.vn/v2/gateway/api/query"
    rawSignature = "accessKey=" + settings.MOMO_ACCESS_KEY + "&orderId=" + orderId + "&partnerCode=" + settings.MOMO_PARTNER_CODE + "&requestId=" + requestId

    signature = create_signature(rawSignature)

    data = {
        'partnerCode': settings.MOMO_PARTNER_CODE,
        'orderId': orderId,
        'lang': 'vi',
        'requestId': requestId,
        'signature': signature,
    }
    data = json.dumps(data)
    clen = len(data)
    response = requests.post(endpoint, data=data,
                             headers={'Content-Type': 'application/json', 'Content-Length': str(clen)})
    return response.json()

# vnpay
# Tạo link thanh toán VnPay
def create_link_vnpay(request, payment):
    order_type = "billpayment"
    order_id = "VNP" + ''.join(filter(str.isdigit, str(uuid.uuid4())))
    amount = payment.amount
    order_desc = "Thanh toán hóa đơn " + str(payment.name) + " bằng VNPay"
    bank_code = request.data.get('bank_code')
    language = "vn"
    ipaddr = get_client_ip(request)
    # Build URL Payment
    vnp.requestData['vnp_Version'] = '2.1.0'
    vnp.requestData['vnp_Command'] = 'pay'
    vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
    vnp.requestData['vnp_Amount'] = int(amount) * 100
    vnp.requestData['vnp_CurrCode'] = 'VND'
    vnp.requestData['vnp_TxnRef'] = order_id
    vnp.requestData['vnp_OrderInfo'] = order_desc
    vnp.requestData['vnp_OrderType'] = order_type
    # Check language, default: vn
    if language and language != '':
        vnp.requestData['vnp_Locale'] = language
    else:
        vnp.requestData['vnp_Locale'] = 'vn'
        # Check bank_code, if bank_code is empty, customer will be selected bank on VNPAY
    if bank_code and bank_code != "":
        vnp.requestData['vnp_BankCode'] = bank_code

    vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp.requestData['vnp_IpAddr'] = ipaddr
    vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
    vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
    payment_data = {
        'vnp_TxnRef': order_id,
        'vnp_Amount': amount,
        'vnp_OrderInfo': order_desc,
        'vnp_OrderType': order_type,
        'language': language,
        'vnp_IpAddr': ipaddr,
        'payment_url': vnpay_payment_url
    }

    return payment_data

# Lấy ip của máy
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# Tạo hàm random
n = random.randint(10**11, 10**12 - 1)
n_str = str(n)
while len(n_str) < 12:
    n_str = '0' + n_str

class UserViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = User.objects.filter(is_staff=True)
    serializer_class = serializers.UserSerializer
    pagination_class = paginators.BasePaginator
    parser_classes = [parsers.MultiPartParser, ]

class ResidentViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Resident.objects.filter(is_active=True)
    serializer_class = serializers.ResidentSerializer
    pagination_class = paginators.BasePaginator
    parser_classes = [parsers.MultiPartParser, ]

    def get_permissions(self):
        if self.action in ('update_profile', 'get_current_resident'):
            return [perms.Owner()]
        return [permissions.AllowAny()]

    @action(methods=['get'], url_path='current', detail=False)
    def get_current_resident(self, request):
        return Response(serializers.ResidentSerializer(request.user.resident).data)

    @action(methods=['patch'], url_path='profile', detail=True)
    def update_profile(self, request, pk):
        resident = self.get_object()
        for k, v in request.data.items():
            if k == 'password':
                v = make_password(v)
            setattr(resident, k, v)
        resident.save()

        return Response(serializers.ResidentSerializer(resident).data)

class RoomViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Room.objects.all()
    serializer_class = serializers.RoomSerializer
    pagination_class = paginators.BasePaginator
    parser_classes = [parsers.MultiPartParser, ]

    def get_queryset(self):
        queryset = self.queryset

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)

        n = self.request.query_params.get('n')
        if n:
            queryset = queryset.filter(number__icontains=n)

        return queryset

class OwnershipViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Ownership.objects.all()
    serializer_class = serializers.OwnershipSerializer
    pagination_class = paginators.BasePaginator
    parser_classes = [parsers.MultiPartParser, ]

class PaymentViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Payment.objects.all()
    serializer_class = serializers.PaymentSerializer
    pagination_class = paginators.BasePaginator

    def get_permissions(self):
        if self.action in ['new_link_momo', 'new_link_vnp']:
            return [perms.Owner()]

        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = self.queryset

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)

        r_id = self.request.query_params.get('r_id')
        if r_id:
            queryset = queryset.filter(resident_id=r_id)

        return queryset

    # momo
    @action(methods=['post'], url_path='paid-momo', detail=True)
    def new_link_momo(self, request, pk):
        pay_momo_view = self.get_object()
        if check_active_payment(pay_momo_view):
            pay_momo_data = create_link_momo(pay_momo_view)
            MomoLink.objects.create(partner_code=pay_momo_data['partnerCode'], order_id=pay_momo_data['orderId'],
                                    request_id=pay_momo_data['requestId'], amount=pay_momo_data['amount'],
                                    pay_url=pay_momo_data['payUrl'], short_link=pay_momo_data['shortLink'],
                                    payment=pay_momo_view)
        else:
            return Response({"error": "Hóa đơn đã được thanh toán trước đó!"}, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_200_OK, data=pay_momo_data)

    @action(methods=['post'], url_path='transaction-status', detail=False)
    def check_transaction_status(self, request):
        order_id = request.data.get('order_id')
        request_id = request.data.get('request_id')
        status_momo_data = transaction_status(order_id, request_id)
        return Response(status=status.HTTP_200_OK, data=status_momo_data)

    # vnpay
    @action(methods=['post'], url_path='paid-vnp', detail=True)
    def new_link_vnp(self, request, pk):
        pay_vnp_view = self.get_object()
        if check_active_payment(pay_vnp_view):
            pay_vnp_data = create_link_vnpay(request, pay_vnp_view)
            VnpayLink.objects.create(txn_ref=pay_vnp_data['vnp_TxnRef'], amount=pay_vnp_data['vnp_Amount'],
                                     order_info=pay_vnp_data['vnp_OrderInfo'],
                                     order_type=pay_vnp_data['vnp_OrderType'],
                                     ip_addr=pay_vnp_data['vnp_IpAddr'], payment=pay_vnp_view,
                                     payment_url=pay_vnp_data['payment_url'])
        else:
            return Response({"error": "Hóa đơn đã được thanh toán trước đó!"}, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_200_OK, data=pay_vnp_data)

class MomoLinkViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = MomoLink.objects.all()
    serializer_class = serializers.MomoLinkSerializer
    pagination_class = paginators.BasePaginator

class MomoPaidViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = MomoPaid.objects.all()
    serializer_class = serializers.MomoPaidSerializer
    pagination_class = paginators.BasePaginator

class VnpayLinkViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = VnpayLink.objects.all()
    serializer_class = serializers.VnpayLinkSerializer
    pagination_class = paginators.BasePaginator

class VnpayPaidViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = VnpayPaid.objects.all()
    serializer_class = serializers.VnpayPaidSerializer
    pagination_class = paginators.BasePaginator

class ReceiptViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Receipt.objects.all()
    serializer_class = serializers.ReceiptSerializer
    paginator_class = paginators.BasePaginator

    def get_queryset(self):
        queryset = self.queryset

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)

        r_id = self.request.query_params.get('r_id')
        if r_id:
            queryset = queryset.filter(resident_id=r_id)

        return queryset

class SecurityCardViewSet(viewsets.ViewSet, generics.ListAPIView, generics.DestroyAPIView):
    queryset = SecurityCard.objects.filter(active=True)
    serializer_class = serializers.SecurityCardSerializer
    pagination_class = paginators.BasePaginator

    def get_permissions(self):
        if self.action in ['create_sc', 'updated_sc']:
            return [perms.Owner()]

        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = self.queryset

        user_id = self.request.query_params.get('resident_id')
        if user_id:
            queryset = queryset.filter(resident_id=user_id)

        return queryset


    @action(methods=['post'], url_path='add-sc', detail=False)
    def create_sc(self, request):
        sc = SecurityCard.objects.create(name='Thẻ giữ xe',
                                         name_register=request.data.get('name_register'),
                                         vehicle_number=request.data.get('vehicle_number'),
                                         type_vehicle = request.data.get('type_vehicle'),
                                         resident_id=request.user.id)

        return Response(serializers.SecurityCardSerializer(sc).data, status=status.HTTP_201_CREATED)

    @action(methods=['patch'], url_path='update-sc', detail=True)
    def updated_sc(self, request, pk):
        sc = self.get_object()
        for k, v in request.data.items():
            setattr(sc, k, v)
        sc.save()

        return Response(serializers.SecurityCardSerializer(sc).data, status=status.HTTP_200_OK)

class PackageViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Package.objects.all()
    serializer_class = serializers.PackageSerializer
    pagination_class = paginators.BasePaginator
    parser_classes = [parsers.MultiPartParser, ]

    def get_queryset(self):
        queryset = self.queryset

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)

        r_id = self.request.query_params.get('r_id')
        if r_id:
            queryset = queryset.filter(resident_id=r_id)

        return queryset

class ComplaintViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Complaint.objects.all()
    serializer_class = serializers.ComplaintSerializer
    pagination_class = paginators.BasePaginator
    parser_classes = [parsers.MultiPartParser, ]

    def get_permissions(self):
        if self.action == 'add_complaint':
            return [perms.Owner()]

        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = self.queryset

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)

        r_id = self.request.query_params.get('r_id')
        if r_id:
            queryset = queryset.filter(resident_id=r_id)

        return queryset

    @action(methods=['post'], url_path='create-complaint', detail=False)
    def add_complaint(self, request):
        comp = Complaint.objects.create(name=request.data.get('name'), content=request.data.get('content'),
                                        resident_id=request.user.id)
        return Response(serializers.ComplaintSerializer(comp).data, status=status.HTTP_201_CREATED)

class SurveyViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Survey.objects.all()
    serializer_class = serializers.SurveySerializer
    pagination_class = paginators.BasePaginator

    def get_queryset(self):
        queryset = self.queryset

        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(name__icontains=q)

        d = self.request.query_params.get('d')
        if d:
            queryset = queryset.filter(description__icontains=d)

        return queryset

class SChoiceViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = SChoice.objects.all()
    serializer_class = serializers.SChoiceSerializer
    pagination_class = paginators.BasePaginator

class SurveyQuestionViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = SurveyQuestion.objects.all()
    serializer_class = serializers.SurveyQuestionSerializer
    pagination_class = paginators.BasePaginator

class SurveyAnswerViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action == 'submit_answers':
            return [perms.Owner()]

        return [permissions.AllowAny()]

    @action(methods=['post'], url_path='submit-answers', detail=False)
    def submit_answers(self, request):
        question_id = request.data.get('question_id')
        resident = Resident.objects.get(id=request.user.id)

        try:
            question = SurveyQuestion.objects.get(id=question_id)
            survey = question.survey
        except SurveyQuestion.DoesNotExist:
            return Response({"error": "Question not found."}, status=status.HTTP_404_NOT_FOUND)

        choice_data = request.data.get('data')

        if question.type in ['text', 'rating']:
            SurveyTextAnswer.objects.create(question_id=question_id, content=choice_data)

        elif question.type in ['radiogroup', 'checkbox', 'dropdown', 'tagbox']:
            if isinstance(choice_data, list):
                for choice in choice_data:
                    try:
                        choice_instance = SChoice.objects.get(content=choice)
                        SurveyChoiceAnswer.objects.create(question_id=question_id, choice=choice_instance)
                    except SChoice.DoesNotExist:
                        return Response({"error": f"Invalid choice: {choice} does not exist."},
                                        status=status.HTTP_400_BAD_REQUEST)
            else:
                try:
                    choice_instance = SChoice.objects.get(content=choice_data)
                    SurveyChoiceAnswer.objects.create(question_id=question_id, choice=choice_instance)
                except SChoice.DoesNotExist:
                    return Response({"error": f"Invalid choice: {choice_data} does not exist."},
                                    status=status.HTTP_400_BAD_REQUEST)

        elif question.type == 'boolean':
            SurveyTextAnswer.objects.create(question_id=question_id, content='Có' if choice_data else 'Không')

        elif question.type == 'ranking':
            for item in choice_data:
                SurveyTextAnswer.objects.create(question_id=question_id, content=item)

        add_survey_for_resident(resident=resident, survey=survey)
        return Response({"message": "Answers submitted successfully."}, status=status.HTTP_201_CREATED)

class SurveyTextAnswerViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = SurveyTextAnswer.objects.all()
    serializer_class = serializers.SurveyTextAnswerSerializer
    pagination_class = paginators.BasePaginator

class SurveyChoiceAnswerViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = SurveyChoiceAnswer.objects.all()
    serializer_class = serializers.SurveyChoiceAnswerSerializer
    pagination_class = paginators.BasePaginator

class NotificationViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationSerializer
    pagination_class = paginators.BasePaginator

class SendEmail(viewsets.ViewSet):
    @action(methods=["POST"], url_path="send-email", detail=False)
    def send_notification_email(self, request):
        message = request.data.get('message', 'Không có nội dung')
        result = self.send_email(message)
        return Response(result)
        # return Response({'message': 'Đã gửi mail thành công!'})

    def send_email(self, message):
        api_key = settings.MAILJET_API_KEY
        api_secret = settings.MAILJET_SECRET_KEY
        mailjet = Client(auth=(api_key, api_secret), version='v3.1')

        data = {
            'Messages': [
                {
                    'From': {
                        'Email': settings.MAILJET_EMAIL_SENDER,
                        'Name': 'LT House'
                    },
                    'To': [
                        {
                            'Email': settings.MAILJET_EMAIL_TARGET,
                            'Name': 'Recipient Name'
                        }
                    ],
                    'Subject': 'LT House xin được gửi thông báo',
                    'TextPart': message,
                }
            ]
        }

        try:
            result = mailjet.send.create(data=data)
            if result.status_code != 200:
                return {"status": "error", "message": "Không thể gửi email, vui lòng kiểm tra lại."}

            return {"status": "success", "message": f"Email đã được gửi thành công với nội dung: {message}"}
        except Exception as e:
            return {"status": "error", "message": "Đã xảy ra lỗi không xác định."}