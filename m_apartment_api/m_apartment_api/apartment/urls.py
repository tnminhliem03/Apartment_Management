from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework import routers
from apartment import views

r = routers.DefaultRouter()
r.register('users', views.UserViewSet, basename='users')
r.register('residents', views.ResidentViewSet, basename='residents')
r.register('ownerships', views.OwnershipViewSet, basename='ownerships')
r.register('rooms', views.RoomViewSet, basename='rooms')
r.register('complaints', views.ComplaintViewSet, basename='complaints')
r.register('packages', views.PackageViewSet, basename='packages')
r.register('security_cards', views.SecurityCardViewSet, basename='security_cards')
r.register('payments', views.PaymentViewSet, basename='payments')
r.register('momo_links', views.MomoLinkViewSet, basename='momo_links')
r.register('momo_paids', views.MomoPaidViewSet, basename='momo_paids')
r.register('vnpay_links', views.VnpayLinkViewSet, basename='vnpay_links')
r.register('vnpay_paids', views.VnpayPaidViewSet, basename='vnpay_paids')
r.register('receipts', views.ReceiptViewSet, basename='receipts')
r.register('surveys', views.SurveyViewSet, basename='surveys')
r.register('s_choices', views.SChoiceViewSet, basename='s_choices')
r.register('s_questions', views.SurveyQuestionViewSet, basename='s_questions')
r.register('s_answers', views.SurveyAnswerViewSet, basename='s_answers')
r.register('s_text_answers', views.SurveyTextAnswerViewSet, basename='s_text_answers')
r.register('s_choice_answers', views.SurveyChoiceAnswerViewSet, basename='s_choice_answers')
r.register('email', views.SendEmail, basename='email')
r.register('notifications', views.NotificationViewSet, basename='notifications')


urlpatterns = [
    path('', include(r.urls)),
    path('paid', views.save_payment, name='paid'),
    # path('admin/', admin.site.urls),
]