from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.contrib import admin
from django import forms
from django.urls import path
from django.db.models import Count
from django.template.response import TemplateResponse
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission
from apartment.models import (Resident, Room, Ownership, Payment, Receipt, SecurityCard, Package, Complaint,
                              Survey, SChoice, SurveyQuestion, SurveyTextAnswer, SurveyChoiceAnswer, Notification,
                              MomoLink, MomoPaid, VnpayLink, VnpayPaid)

class MyApartmentAdminSite(admin.AdminSite):
    site_header = 'HỆ THỐNG QUẢN LÝ CHUNG CƯ'

    def get_urls(self):
        return [path('survey-stats/', self.stats_view)] + super().get_urls()

    def stats_view(self, request):
        # Đếm tổng số câu hỏi có trong 1 phiếu khảo sát
        question_stats = (Survey.objects.annotate(question_count = Count('questions')).
                          values('id', 'name', 'question_count'))
        # Đếm tổng số câu trả lời có trong 1 câu hỏi
        answer_stats = (
            SurveyQuestion.objects.annotate(answer_count=Count('surveytextanswer_answers', distinct=True) +
                                                         Count('surveychoiceanswer_answers', distinct=True))
            .values('id', 'content', 'answer_count')
        )

        # Đếm tổng số người thực hiện 1 phiếu khảo sát
        resident_stats = (Survey.objects.annotate(resident_count= Count('surveys')).
                          values('id', 'name', 'resident_count'))
        return TemplateResponse(request, 'admin/stats.html', {
            'question_stats': question_stats,
            'answer_stats': answer_stats,
            'resident_stats': resident_stats
        })


admin_site = MyApartmentAdminSite(name='MyAdmin')


class ResidentForm(forms.ModelForm):
    class Meta:
        model = Resident
        fields = '__all__'

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user

class MyResidentAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name', 'gender', 'email', 'is_active']
    search_fields = ['username', 'first_name', 'last_name']
    readonly_fields = ['answered']
    form = ResidentForm

class MyRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'number', 'description', 'square', 'is_empty']
    search_fields = ['name', 'number', 'description']
    list_filter = ['is_empty']
    readonly_fields = ['is_empty']

class MyOwnershipAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'start_date', 'end_date', 'active', 'room', 'resident']
    search_fields = ['name', 'resident']

class MyPaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'amount', 'created_date', 'updated_date', 'active', 'resident']
    search_fields = ['name']

class MyMomoLinkAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'request_id', 'amount', 'created_date', 'payment', 'pay_url']
    search_fields = ['order_id', 'request_id']
    readonly_fields = ['order_id', 'request_id', 'amount', 'created_date', 'payment', 'pay_url']

class MyMomoPaidAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'request_id', 'amount', 'created_date', 'order_type', 'pay_type']
    search_fields = ['order_id', 'request_id', 'order_info']
    list_filter = ['pay_type']
    readonly_fields = ['order_id', 'request_id', 'amount', 'created_date', 'order_type', 'pay_type']

class MyVnpayLinkAdmin(admin.ModelAdmin):
    list_display = ['txn_ref', 'amount', 'created_date', 'payment', 'payment_url']
    search_fields = ['txn_ref']
    readonly_fields = ['txn_ref', 'amount', 'created_date', 'payment', 'payment_url']

class MyVnpayPaidAdmin(admin.ModelAdmin):
    list_display = ['txn_ref', 'amount', 'created_date', 'bank_code', 'card_type']
    search_fields = ['txn_ref', 'order_info']
    list_filter = ['bank_code']
    readonly_fields = ['txn_ref', 'amount', 'created_date', 'bank_code', 'card_type']

class MyReceiptAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'order_id', 'pay_method', 'amount', 'created_date', 'payment']
    search_fields = ['name', 'order_id', 'pay_method']
    readonly_fields = ['id', 'name', 'order_id', 'pay_method', 'amount', 'created_date', 'payment']

class MySecurityCardAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'name_register', 'vehicle_number', 'type_vehicle', 'created_date',
                    'updated_date', 'active', 'resident']

class MyPackageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'note', 'created_date', 'updated_date', 'active', 'resident']
    search_fields = ['name', 'resident']

class MyComplaintAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'content', 'created_date', 'active', 'resident']
    # readonly_fields = ['id', 'name', 'content', 'created_date', 'resident']
    search_fields = ['name', 'resident']

class SChoiceInline(admin.TabularInline):
    model = SChoice
    extra = 1  # Shows one empty form for adding a question

class SurveyQuestionInline(admin.TabularInline):
    model = SurveyQuestion
    extra = 1
    inlines = [SChoiceInline]

class MySurveyAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description', 'created_date', 'updated_date', 'active']
    search_fields = ['name', 'description']

class MySChoiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'content', 'question']

class MySurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'content', 'created_date', 'type', 'survey']
    list_filter = ['survey']
    inlines = [SChoiceInline]

class MySurveyTextAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_date', 'question', 'content']

class MySurveyChoiceAnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_date', 'question', 'choice']

class MyNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_date', 'updated_date', 'active']
    search_fields = ['name', 'content']


# Register your models here.
admin_site.register(Resident, MyResidentAdmin)
admin_site.register(Room, MyRoomAdmin)
admin_site.register(Ownership, MyOwnershipAdmin)
admin_site.register(Payment, MyPaymentAdmin)
admin_site.register(MomoLink, MyMomoLinkAdmin)
admin_site.register(MomoPaid, MyMomoPaidAdmin)
admin_site.register(VnpayLink, MyVnpayLinkAdmin)
admin_site.register(VnpayPaid, MyVnpayPaidAdmin)
admin_site.register(Receipt, MyReceiptAdmin)
admin_site.register(SecurityCard, MySecurityCardAdmin)
admin_site.register(Package, MyPackageAdmin)
admin_site.register(Complaint, MyComplaintAdmin)
admin_site.register(Survey, MySurveyAdmin)
admin_site.register(SChoice, MySChoiceAdmin)
admin_site.register(SurveyQuestion, MySurveyQuestionAdmin)
admin_site.register(SurveyTextAnswer, MySurveyTextAnswerAdmin)
admin_site.register(SurveyChoiceAnswer, MySurveyChoiceAnswerAdmin)
admin_site.register(Notification, MyNotificationAdmin)
admin_site.register(Group, GroupAdmin)
admin_site.register(Permission)