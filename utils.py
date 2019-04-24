import lookerapi as looker
import os
import re
import time
from lookerapi.rest import ApiException
from pprint import pprint
import sendgrid
from sendgrid.helpers.mail import *


def create_user(client,firstname,lastname,email):
	#Instantiate UserAPI
	userApi = looker.UserApi(client)
	newuser = {
	  "first_name": "{}".format(firstname),
	  "last_name": "{}".format(lastname),
	  "email": "{}".format(email)}
	try: 
		# Create User
		api_response = userApi.create_user(body=newuser)
		pprint('successfully created user {}'.format(userid))
		userid = api_response.id
	except ApiException as e:
		print("Exception when calling UserApi->create_user: %s\n" % e)
	#Create credentials
	try: 
		body = looker.CredentialsEmail(email = email)
		api_response = userApi.create_user_credentials_email(userid, body=body)
		pprint('successfully created user credentials')
	except ApiException as e:
		print("Exception when calling UserApi->create_user_credentials_email: %s\n" % e)
	return userid

def apply_role(client,userid,roleId):
	userApi = looker.UserApi(client)
	body =[roleId]

	try: 
		# Set User Roles
		api_response = userApi.set_user_roles(userid, body)
		pprint('successfully set role')
	except ApiException as e:
		print("Exception when calling userApi->set_user_roles: %s\n" % e)


def get_email_setup(client,userid):
	userApi = looker.UserApi(client)
	user_id = userid

	try: 
		# Create Token
		api_response = userApi.create_user_credentials_email_password_reset(user_id)
		pprint('successfully generated reset url')
		url = api_response.password_reset_url
		print('RESET URL = {}'.format(url))
		return url
	except ApiException as e:
		print("Exception when calling UserApi->create_user_credentials_email_password_reset: %s\n" % e)

def send_mail(url,email):
	sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
	from_email = Email("theemailtobesentfrom")
	to_email = Email(email)
	subject = "Welcome to Looker "
	content = Content("text/plain", "Whatever you want your email to say. Click this link to get set up {}".format(url))
	mail = Mail(from_email, subject, to_email, content)
	response = sg.client.mail.send.post(request_body=mail.get())
	pprint('successfully sent reset email')
