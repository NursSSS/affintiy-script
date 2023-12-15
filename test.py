# investor = {
#     "customer_id": None,
#     "reporting_email": None,
#     "capital_call": "capital_call@example.com",
#     "kyc_email": "kyc@example.com"
# }
#
# email_addresses = [
#     investor[key] for key in ['reporting_email', 'capital_call', 'kyc_email']
#     if investor[key] is not None
# ]
#
# email_addresses = tuple(email_addresses)
# print(email_addresses)


# email_addresses = ['test@email.com',
#                    'example@email.com,example123@email.com,example235@email.com',
#                    'example123@email.com,example162@email.com']
#
# split_emails = [email.strip() for addresses in email_addresses for email in addresses.split(',')]
# print(split_emails)

# UID = 'UID01865'
#
# # Assuming the numeric part starts at index 3
# numeric_part = int(UID[3:])
# numeric_part += 1
#
# # Format the UID with leading zeros to make it 5 digits
# UID = f"UID{numeric_part}"
#
# print(UID)

# import os
# from dotenv import dotenv_values
#
# config = dotenv_values(".env")
# app_host = config.get("APP_HOST")
# # app_host = os.environ.get("APP_HOST")
# print(app_host)

from jinja2 import Environment, FileSystemLoader

template_dir = "email"

# Create a Jinja2 environment with the FileSystemLoader
env = Environment(loader=FileSystemLoader(template_dir))

# Your HTML template file name
template_file = "user_invitation_mail_from_merchant.html"

template_context = {
    'title': 'My Page',
    'heading': 'Welcome to my website',
    'content': 'This is the content of my page.',
}

# Load the template
template = env.get_template(template_file)

# Render the template with the context
rendered_html = template.render(template_context)

print(rendered_html)


