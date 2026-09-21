import os
import threading
import logging
from decimal import Decimal
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

ADMIN_NOTIFICATION_EMAILS = [
    "atikahmedridoy@gmail.com",
    "metrobazar2025@gmail.com",
    "admin@metrobazar.online",
]

def _build_order_html(order):
    """
    Build beautiful, responsive HTML email template for Admin order notification.
    """
    snapshot = order.delivery_address_snapshot or {}
    cust_name = snapshot.get("recipient_name") or (order.user.first_name if order.user else "Customer") or "Customer"
    cust_phone = snapshot.get("recipient_phone") or (order.user.phone_number if order.user else "N/A") or "N/A"
    cust_email = snapshot.get("recipient_email") or (order.user.email if order.user else "N/A") or "N/A"
    
    street = snapshot.get("street_address") or snapshot.get("details") or ""
    city = snapshot.get("city") or snapshot.get("area") or "Rangpur"
    address_str = f"{street}, {city}".strip(", ")

    # Determine delivery zone label
    fee = float(order.delivery_fee or 0)
    zone_label = "Inside Rangpur" if fee <= 30 else "Outside Rangpur"
    if order.note and "Outside" in order.note:
        zone_label = "Outside Rangpur"
    elif order.note and "Inside" in order.note:
        zone_label = "Inside Rangpur"

    # Items table rows
    items_rows_html = ""
    for item in order.items.all():
        p_name = item.product_name_en or "Product"
        unit = item.unit or "1 pc"
        qty = item.quantity
        price = item.unit_price
        subtotal = item.subtotal
        items_rows_html += f"""
        <tr>
          <td style="padding: 10px; border-bottom: 1px solid #eee;">
            <strong style="color: #111;">{p_name}</strong> <span style="font-size: 11px; color: #777;">({unit})</span>
          </td>
          <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{qty}</td>
          <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">৳{price}</td>
          <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right; font-weight: bold; color: #111;">৳{subtotal}</td>
        </tr>
        """

    formatted_time = order.created_at.strftime("%d %b %Y, %I:%M %p") if order.created_at else timezone.now().strftime("%d %b %Y, %I:%M %p")

    discount_row = ""
    if float(order.discount_amount or 0) > 0:
        discount_row = f"""
        <div style="display: flex; justify-content: space-between; padding: 4px 0; color: #16a34a;">
          <span>ডিসকাউন্ট (Discount):</span>
          <span>-৳{order.discount_amount}</span>
        </div>
        """

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>New Order #{order.order_number} - Metro Bazar</title>
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 0; color: #333; }}
    .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid #e1e4e8; }}
    .header {{ background: linear-gradient(135deg, #7533CB 0%, #511fa3 100%); color: #ffffff; padding: 25px 30px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
    .header p {{ margin: 5px 0 0 0; font-size: 13px; opacity: 0.9; }}
    .badge {{ display: inline-block; background: #22c55e; color: #fff; font-weight: bold; padding: 5px 14px; border-radius: 20px; font-size: 13px; margin-top: 10px; }}
    .content {{ padding: 25px 30px; }}
    .section-title {{ font-size: 13px; font-weight: 700; color: #7533CB; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #f0e6ff; padding-bottom: 6px; margin-bottom: 12px; margin-top: 20px; }}
    .info-table {{ width: 100%; font-size: 13px; border-collapse: collapse; }}
    .info-table td {{ padding: 6px 0; vertical-align: top; }}
    .info-label {{ font-weight: 600; color: #666; width: 38%; }}
    .info-val {{ font-weight: 700; color: #111; }}
    .item-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
    .item-table th {{ background-color: #f8f9fa; color: #555; font-weight: 700; text-align: left; padding: 10px; border-bottom: 2px solid #dee2e6; }}
    .total-box {{ background-color: #f9f5ff; border: 1px solid #e9d5ff; border-radius: 8px; padding: 15px 20px; margin-top: 20px; font-size: 13px; }}
    .total-row {{ display: flex; justify-content: space-between; padding: 4px 0; color: #444; }}
    .grand-total {{ font-size: 16px; font-weight: 900; color: #7533CB; border-top: 1px solid #d8b4fe; padding-top: 8px; margin-top: 8px; }}
    .footer {{ background-color: #fafafa; padding: 15px 30px; text-align: center; font-size: 12px; color: #888; border-top: 1px solid #eee; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🚀 নতুন অর্ডার পাওয়া গেছে!</h1>
      <p>মেট্রো বাজার এডমিন প্যানেল নোটিফিকেশন</p>
      <span class="badge">অর্ডার নম্বর: {order.order_number}</span>
    </div>

    <div class="content">
      <!-- Customer Information -->
      <div class="section-title">👤 গ্রাহকের তথ্য (CUSTOMER INFO)</div>
      <table class="info-table">
        <tr>
          <td class="info-label">গ্রাহকের নাম:</td>
          <td class="info-val">{cust_name}</td>
        </tr>
        <tr>
          <td class="info-label">ফোন নম্বর:</td>
          <td class="info-val" style="color: #7533CB;">{cust_phone}</td>
        </tr>
        <tr>
          <td class="info-label">ইমেইল:</td>
          <td class="info-val">{cust_email}</td>
        </tr>
        <tr>
          <td class="info-label">ডেলিভারি ঠিকানা:</td>
          <td class="info-val">{address_str}</td>
        </tr>
        <tr>
          <td class="info-label">ডেলিভারি এলাকা:</td>
          <td class="info-val">{zone_label} (৳{order.delivery_fee})</td>
        </tr>
      </table>

      <!-- Order Items Table -->
      <div class="section-title">📦 অর্ডারকৃত পণ্যের তালিকা (ITEMS)</div>
      <table class="item-table">
        <thead>
          <tr>
            <th>পণ্য</th>
            <th style="text-align: center;">সংখ্যা</th>
            <th style="text-align: center;">মূল্য</th>
            <th style="text-align: right;">মোট</th>
          </tr>
        </thead>
        <tbody>
          {items_rows_html}
        </tbody>
      </table>

      <!-- Financial Receipt Summary -->
      <div class="total-box">
        <div class="total-row">
          <span>পণ্যের মোট (Subtotal):</span>
          <strong>৳{order.subtotal}</strong>
        </div>
        <div class="total-row">
          <span>ডেলিভারি চার্জ (Delivery Fee - {zone_label}):</span>
          <strong>৳{order.delivery_fee}</strong>
        </div>
        {discount_row}
        <div class="total-row grand-total">
          <span>সর্বমোট পরিশোধনীয় মূল্য (Total Payable):</span>
          <span>৳{order.total_amount}</span>
        </div>
      </div>

      <!-- Payment & Status -->
      <div class="section-title">💳 পেমেন্ট ও সময়</div>
      <table class="info-table">
        <tr>
          <td class="info-label">পেমেন্ট মেথড:</td>
          <td class="info-val">Cash on Delivery (ক্যাশ অন ডেলিভারি)</td>
        </tr>
        <tr>
          <td class="info-label">পেমেন্ট স্ট্যাটাস:</td>
          <td class="info-val" style="color: #d97706; text-transform: uppercase;">UNPAID</td>
        </tr>
        <tr>
          <td class="info-label">অর্ডারের সময়:</td>
          <td class="info-val">{formatted_time}</td>
        </tr>
      </table>
    </div>

    <div class="footer">
      <p><strong>মেট্রো বাজার রিয়েলটাইম অর্ডার প্রসেসিং সার্ভিস</strong></p>
      <p>Sender: admin@metrobazar.online | Recipient: metrobazar2025@gmail.com</p>
    </div>
  </div>
</body>
</html>
    """
    return html_content


def _send_email_async(subject, text_content, html_content, from_email, recipient_list):
    """
    Asynchronous helper to send email without blocking the API thread.
    """
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipient_list
        )
        msg.attach_alternative(html_content, "text/html")
        sent_count = msg.send(fail_silently=False)
        print(f"📧 Admin notification email sent successfully ({sent_count}) to {recipient_list}")
        logger.info(f"📧 Admin notification email sent successfully to {recipient_list} for order subject: {subject}")
    except Exception as e:
        print(f"❌ Failed to send admin order notification email to {recipient_list}: {str(e)}")
        logger.error(f"❌ Failed to send admin order notification email: {str(e)}")


def send_admin_order_notification_email(order):
    """
    Trigger async email to admin (metrobazar2025@gmail.com, atikahmedridoy@gmail.com) when a new order is placed.
    """
    try:
        subject = f"🚨 New Order Placed: #{order.order_number} - ৳{order.total_amount}"
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Metro Bazar Admin <admin@metrobazar.online>")
        
        # Plaintext fallback text
        snapshot = order.delivery_address_snapshot or {}
        cust_name = snapshot.get("recipient_name") or (order.user.first_name if order.user else "Customer") or "Customer"
        cust_phone = snapshot.get("recipient_phone") or (order.user.phone_number if order.user else "N/A") or "N/A"
        
        text_content = (
            f"New Order Received!\n"
            f"Order Number: {order.order_number}\n"
            f"Customer: {cust_name} ({cust_phone})\n"
            f"Total Amount: ৳{order.total_amount}\n"
            f"Delivery Fee: ৳{order.delivery_fee}\n"
        )
        
        html_content = _build_order_html(order)
        
        recipients = []
        for em in ADMIN_NOTIFICATION_EMAILS:
            if em and isinstance(em, str):
                for sub in em.split(','):
                    s_clean = sub.strip()
                    if s_clean and s_clean not in recipients:
                        recipients.append(s_clean)

        admin_setting_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", None)
        if admin_setting_email and isinstance(admin_setting_email, str):
            for sub in admin_setting_email.split(','):
                s_clean = sub.strip()
                if s_clean and s_clean not in recipients:
                    recipients.append(s_clean)

        # Execute in non-blocking background thread
        thread = threading.Thread(
            target=_send_email_async,
            args=(subject, text_content, html_content, from_email, recipients),
            daemon=True
        )
        thread.start()
    except Exception as e:
        logger.error(f"Error launching admin order email thread: {e}")
