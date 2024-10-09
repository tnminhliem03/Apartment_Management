from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apartment.models import (Resident, Room, Ownership, Payment, Receipt, SecurityCard, Package, Complaint,
                              Survey, Notification)
from apartment.views import SendEmail

# @receiver(post_save, sender=Resident)
# @receiver(post_save, sender=Room)
# @receiver(post_save, sender=Ownership)
# @receiver(post_save, sender=Payment)
# @receiver(post_save, sender=Receipt)
# @receiver(post_save, sender=SecurityCard)
# @receiver(post_save, sender=Package)
# @receiver(post_save, sender=Complaint)
# @receiver(post_save, sender=Survey)
# @receiver(post_save, sender=Notification)
# def realtime_data(sender, instance, created, **kwargs):
#     action = "được tạo" if created else "được cập nhật"
#     notify_users(f"{instance} {action}.")

# @receiver(post_delete, sender=Resident)
# @receiver(post_delete, sender=Room)
# @receiver(post_delete, sender=Ownership)
# @receiver(post_delete, sender=Payment)
# @receiver(post_delete, sender=Receipt)
# @receiver(post_delete, sender=SecurityCard)
# @receiver(post_delete, sender=Package)
# @receiver(post_delete, sender=Complaint)
# @receiver(post_delete, sender=Survey)
# @receiver(post_delete, sender=Notification)
# def delete_data(sender, instance, **kwargs):
#     notify_users(f"{instance} đã bị xóa.")


# Gửi thông báo qua Email bằng MailJet
@receiver(post_save, sender=Payment)
@receiver(post_save, sender=Receipt)
@receiver(post_save, sender=Package)
def send_notification(sender, instance, created, **kwargs):
    if created:
        email_view = SendEmail()

        if isinstance(instance, Payment):
            message = f"Bạn có một hóa đơn mới cần được thanh toán: {instance.name}. Tổng tiền: {instance.amount}"
        elif isinstance(instance, Receipt):
            message = f"Bạn vừa thanh toán thành công 1 hóa đơn: {instance.name}"
        elif isinstance(instance, Package):
            message = "Bạn có 1 đơn hàng vừa được giao đến. Hãy kiểm tra tủ đồ trên hệ thống nhé!"

        result = email_view.send_email(message)
        if result["status"] == "error":
            print(result["message"])

# Cập nhật phòng khi có chủ mới
@receiver(post_save, sender=Ownership)
def update_room_on_create_resident(sender, instance, **kwargs):
    if instance.room:
        instance.room.is_empty = False
        instance.room.save()

@receiver(post_delete, sender=Ownership)
def update_room_on_delete_resident(sender, instance, **kwargs):
    if instance.room:
        instance.room.is_empty = True
        instance.room.save()

# Tạo thanh toán mới
def create_payment(name, amount, resident_id):
    Payment.objects.create(name=name, amount=amount, resident_id=resident_id)

# Xử lý khi tạo thẻ giữ xe mới
@receiver(post_save, sender=SecurityCard)
def create_payment_for_sc(sender, instance, created, **kwargs):
    if created:
        if instance.type_vehicle == 'bike':
            create_payment('Phí gửi xe đạp tháng', '900000', instance.resident.id)
        elif instance.type_vehicle == 'motorbike':
            create_payment('Phí gửi xe máy tháng', '150000', instance.resident.id)
        elif instance.type_vehicle == 'car':
            create_payment('Phí gửi xe hơi tháng', '1600000', instance.resident.id)