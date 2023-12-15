# import requests
import json
import psycopg2
import logging
import binascii
import os
import urllib.parse
from dotenv import dotenv_values
from jinja2 import Environment, FileSystemLoader
import yagmail
from typing import Dict

config = dotenv_values(".env")
logger = logging.getLogger(__name__)

images = {
            'main_image': 'email/images/Team.png',
            'facebook_image': 'email/images/Facebook.png',
            'linkedin_image': 'email/images/Linkedin.png',
            'twitter_image': 'email/images/Twitter.png',
        }
html_template_dir = 'email'
html_template_filename = "user_invitation_mail_from_merchant.html"
plain_text_template_filename = "user_invitation_mail_from_merchant.txt"

# url = "config.get("AFFINITY_API_GET_INVESTORS_URL")"
# headers = {"Authorization": config.get("AFFINITY_API_KEY")}
# params = {"page_size": 5}
#
# response = requests.get(url, headers=headers, params=params)
# response_json = response.json()
# list_entries = f'{response_json.get('list_entries', [])}'
# list_entries = list_entries.replace("'", '"')
# investors = json.loads(list_entries)
# print('investors:', investors)

response = """
{
    "list_entries": [
      {
        "customer_id": "CID00099",
        "reporting_email": null,
        "capital_call": "test123@example.com",
        "kyc_email": "test645@example.com"
      },
      {
        "customer_id": "CID00099",
        "reporting_email": "test78@example.com,test12345@example.com",
        "capital_call": null,
        "kyc_email": "test909@example.com"
      },
      {
        "customer_id": null,
        "reporting_email": "reporting@example.com",
        "capital_call": "capital_call@example.com",
        "kyc_email": null
      }
    ]
}
"""

list_entries = json.loads(response)
investors = list_entries["list_entries"]

connection = psycopg2.connect(
    host=config.get("DB_HOST"),
    database=config.get("DB_NAME"),
    user=config.get("DB_USER"),
    password=config.get("DB_PASSWORD")
)

cursor = connection.cursor()

cursor.execute("""SELECT customer_user_id
        FROM "CUSTOMER"."CUSTOMER_USER"
        ORDER BY id DESC
        LIMIT 1;
    """)
customer_user_id = cursor.fetchone()
UID = customer_user_id[0]
email_fields = ['reporting_email', 'capital_call', 'kyc_email']

for investor in investors:
    if investor['customer_id'] is None:
        continue

    email_addresses = [
        investor[key] for key in email_fields
        if investor[key] is not None
    ]

    if len(email_addresses) == 0:
        continue

    email_addresses = [email.strip() for addresses in email_addresses for email in addresses.split(',')]
    email_addresses = tuple(email_addresses)
    customer_master_id = investor['customer_id']

    for email in email_addresses:
        # Check investor for existing
        cursor.execute("""
            SELECT * FROM "CUSTOMER"."CUSTOMER_USER"
            WHERE customer_user_id = %s AND email IN %s
        """, (customer_master_id, email_addresses))
        result = cursor.fetchone()

        if result is not None:
            continue

        # Increment customer_user_id
        numeric_part = int(UID[3:])
        numeric_part += 1
        UID = f"UID{numeric_part}"

        # Create investor
        try:
            cursor.execute("""
                INSERT INTO "CUSTOMER"."CUSTOMER_USER" (email, customer_id, customer_user_id,
                    is_signatory_person, is_primary_account, role, status, email_role, creation_date) 
                VALUES (%s, %s, %s, false, false, 'view', 1, 'report_email', CURRENT_TIMESTAMP)
                RETURNING *;
            """, (email, customer_master_id, UID),)
        except Exception as e:
            print("Error:", e)
            connection.rollback()

        user = cursor.fetchone()
        print(user)

        if user is None:
            logger.log(logging.INFO, f"Error with creating investor with email {email}")
            continue

        logger.log(logging.INFO, f"Investor with email {email} was successfully created")

        # Create UserLog
        cursor.execute("""
                INSERT INTO "temp.users_logs" (customer_user_id, log_id)
                VALUES ((%s), (SELECT "log_id" FROM "temp.users_logs" WHERE "log_id" = USER_INVITED_TO_SIGNUP));
            """, (user['customer_user_id']))

        # Generate invitation token
        token = binascii.hexlify(
            os.urandom(64)
        ).decode()[0:64]
        cursor.execute("""
            INSERT INTO "CUSTOMER"."CUSTOMER_INVITATION_TOKEN" (created_at, token, user_id, notification)
            VALUES (CURRENT_TIMESTAMP, %s, %s, false);
        """, (token, user['customer_user_id']))

        # Find merchant
        cursor.execute("""SELECT *
                FROM "CUSTOMER"."CUSTOMER_MASTER"
                WHERE customer_master_id = %s
            """, (customer_master_id,))
        merchant = cursor.fetchone()

        # We parse the logo url
        encoded_logo = urllib.parse.quote_plus(merchant.merchant_logo_with_name) if isinstance(
            merchant.merchant_logo_with_name, str) else None

        # Generate context
        context = {
            'customer_name': merchant.customer_name,
            'invitation_url': f"{config.get("APP_HOST")}investor/invites/{token}/{user.email}/{encoded_logo}",
            'logo_image': merchant.merchant_logo_with_name,
            'merchant_name': merchant.merchant_display_name,
            'is_alternative_email': merchant.merchant_is_additional
        }
        context.update({k: k for k, v in images.items()})

        # Render email html message
        env = Environment(loader=FileSystemLoader(html_template_dir))
        template = env.get_template(html_template_filename)
        email_html_message = template.render(context)

        # Render email plaintext message
        env = Environment(loader=FileSystemLoader(html_template_dir))
        template = env.get_template(plain_text_template_filename)
        email_plaintext_message = template.render(context)

        to_email = config.get('PORTAL_SENDER_EMAIL') if config.get('EMAIL_TEST_MODE') else user.email
        email_data = {
                'email_host': config.get("EMAIL_HOST"),
                'email_host_port': config.get("EMAIL_PORT"),
                'from_email': config.get("PORTAL_SENDER_EMAIL"),
                'email_username': config.get("EMAIL_HOST_USER"),
                'email_user_pwd': config.get("EMAIL_HOST_PASSWORD")
        }

        # Set up yagmail SMTP client
        yag = yagmail.SMTP(email_data['email_host'], email_data['email_user_pwd'])

        # Compose your email
        email_contents = {'subject': email_plaintext_message, 'contents': template}
        if images:
            for placeholder, path in images.items():
                email_contents[path] = f'cid: {placeholder}'

        # Send the email
        yag.send(to=to_email, **email_contents)

        # Close the SMTP client
        yag.close()
    #
    #
    # def __attach_images_to_email_message(images: Dict[str, str], msg: EmailMultiAlternatives):
    #     for placeholder, path in images.items():
    #         with open(f'./static_templates/{path}', 'rb') as f:
    #             image_data = f.read()
    #         image = MIMEImage(image_data)
    #         image.add_header('Content-ID', f'<{placeholder}>')
    #         msg.attach(image)
        # send_email_to_investor(
        #     InvestorEmailContext(
        #         to_email=invitation_token.user.email,
        #         subject="Invitation To The Portal",
        #         html_template_path=html_template_path,
        #         plain_text_template_path=plain_text_template_path,
        #         template_context=context,
        #         images=images
        #     )
        # )
        connection.commit()

cursor.close()
connection.close()
