import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_mail(body, to, subject):   #pass the email body, recipient email address, and email subject as parameters

    smtp_host = "smtpHost.xyz.com"  # Replace with your SMTP host
    smtp_port = 25

    '''
    #uncomment this block if you are using outlook to trigger mail and comment the above 2 lines. Also, make sure to provide the correct outlook email address and password in the below lines.
    smtp_host = "smtp.office365.com"
    smtp_port = 587
    outlook_user = "example@xyz.com"
    outlook_password = ""
    '''

    html_body = f"""
    <html>
    <head>
        <style> body {{ font-family: Consolas, monospace; font-size: 14px; }} </style>
    </head>
    <body>
    <pre style="font-family: Consolas, Courier New, monospace; font-size: 15px;">{body}</pre>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = "example@xyz.com"  # Replace with your sender email
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    # === Send the email ===
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            # Uncomment if using port 587 (STARTTLS). If you are using outlook to trigger mail
            #server.starttls()
            # Uncomment and use only if login is required:
            #server.login("outlook_user", "outlook_password")
            server.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print("Failed to send email:", e)

