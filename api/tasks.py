from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings




@shared_task(bind=True)
def test_func(self):
    for i in range(10):
        print(i)
    return "Done"


@shared_task
def send_payment_success_email(email, invoice_id, amount, plan, date):
    subject = "Payment Successful - Premium Subscription"
    message = (
        f"Hello,\n\nThank you for your payment!\n\n"
        f"Invoice ID: {invoice_id}\n"
        f"Plan: {plan}\n"
        f"Amount: ${amount}\n"
        f"Date: {date}\n\n"
        f"Your premium subscription is now active.\n"
        f"Enjoy the benefits of your premium plan!"
    )
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list)
    
    