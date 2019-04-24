Hey Looker Community,

A few times in recent history, I've had to come up with a way to automatically create users in Looker, whether it was so that a form-based signup for an event didn't have to be manual, to automate specific *types* of users being created, or just cause I was lazy. I figured the world at large might benefit from my work.

Bear in mind that I'm just a curious Community Manager, not an API wizard— So if you see a mistake, or can think of a way better way to do this, *please* share it in a reply! That said, here's my workflow:

## 1. Collect new users
This kinda has to be step one, for obvious reasons. I'm sure there's a zillion ways to do this, but for a rolling signup, I think the simplest is a [google form](https://www.google.com/forms/about/) that dumps emails/names/user attributes into a google sheet. 

At Looker, we often get requests to access our learning environment, and because we don't necessarily want everyone to automatically be granted access, we actually just manually enter their names into a google sheet (pulling back the curtain there!). You might also have some kind of security considerations that would make you not want to just let anyone use a form, but I leave that puzzling up to you. (You could also use the google forms feature to automatically collect email addresses, and only allow addresses from your organization to proceed).

This is the main part of the process I'll let you figure out yourself, but for the rest of this walkthrough, I'll assume that email addresses for your new users will be input into a google sheet on a rolling basis. 

## 2. Let's get those values out of that sheet

There's also a couple options here (two good ones, I guess). 
In this lazier project, I used Zapier to yank emails out of a google sheet and pipe them to my script.
This flow looks like:
1. [Google Forms Trigger](https://zapier.com/apps/google-forms/integrations/triggerapp)— New Response in Spreadsheet
2. Action— POST response to webhook
3. [Google Sheets Action](https://zapier.com/apps/google-sheets/integrations)— Lookup Spreadsheet Row
    - I just grab any new values in column a
4. Google Sheets Action— Update Spreadsheet Row
    - I just move the values to column b (or c, or wherever you want to keep your log of users. You can also use another worksheet)

If you don't want to use Zapier, you can also do this in python/the language of your choice directly. 
There's a python quickstart here: https://developers.google.com/sheets/api/quickstart/python.
And a package that's not half bad here: https://github.com/burnash/gspread.

You could set your script to run every 5 or 10 minutes, and check for any values in column A each time, moving them to column B afterwards. 
Example using the gspread package and python:
```
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_new_users():
	scope = ['https://spreadsheets.google.com/feeds']
	creds = --generate creds by manner of your choice: https://gspread.readthedocs.io/en/latest/oauth2.html--
	client = gspread.authorize(creds)
 
	# Find a workbook by name and open the first sheet
	sheet = client.open_by_url('docs.google.com/spreadsheets/d/spreadsheeturl')
	worksheet = sheet.get_worksheet(0)
    #Grab all values in column 1
    new_users = worksheet.col_values(1)
    return new_users
```

The only practical difference between these two methods would be that if you use zapier, your microservice (this is a big word, and I'm not sure what it means) purely needs to be reactive and accept POST requests. If you end up using gspread or similar to check for results, then you need to have it run on a schedule actively.

My examples rely on a POST from Zapier. I told you I was lazy :smile:! 

## 3. The Meat of the process
Now we have to make a script that creates new Looker users and properly provisions them. There's a bunch of steps here. I'm going to be referencing the [python SDK](https://github.com/llooker/python_sdk), but the endpoints will be the same regardless of if you're using cURL or Ruby. 

Let's walk through the full flow first, and then figure out what each function does. I set my script up as a flask app. Here's the full script
```
#Housekeeping
import lookerapi as looker
from flask import Flask, request, abort
import requests
import json
import os
import re
import time
from lookerapi.rest import ApiException
from pprint import pprint
from provisioning_utils import create_user, create_proj, create_model, create_model_set, create_role, apply_role, get_email_setup, send_mail


#instantiate flask app
app = Flask(__name__)


# I named the URL to hit "usr_gen", you can call it whatever you want.
# You'll probably want to restrict the methods to POST, like here
# You'll also probably want to add some basic secret-based authentication, at the very least. 
@app.route('/usr_gen', methods=['POST'])


def usr_gen():
	if request.method == 'POST':
		data = request.get_json()
        # I have zapier parse out the fields I want and send them pre-named
		firstname = data['name'].split(' ',1)[0]
		lastname = data['name'].split(' ',1)[1]
		email = data['email']

		# API creation process
		base_url = 'https://your.looker.com:19999/api/3.0/'
        #secrets are stored in environment variables
		client_id = os.environ['apikey']
		client_secret = os.environ['apisecret']

		unauthenticated_client = looker.ApiClient(base_url)
		unauthenticated_authApi = looker.ApiAuthApi(unauthenticated_client)
		token = unauthenticated_authApi.login(client_id=client_id, client_secret=client_secret)
		client = looker.ApiClient(base_url, 'Authorization', 'token ' + token.access_token)

		#User Creation Process
		user_id = create_user(client,firstname,lastname,email)
		apply_role(client,user_id,role_id)
         # If you want to add user attributes, add the user to groups, etc
         # you'll probably want to add another function here
		reset_url = get_email_setup(client,user_id)
		send_mail(reset_url,email)

		#Email send
		print('User Created')
		return '', 200
	else:
		abort(400)


```
Let's break those functions out. 
1. create_user.This is pretty simple! We take the name + email from the sheet, and create a new blank user with those details. Each of these functions is designed to be standalone if it needs to be.
    ```
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
		userid = api_response.id
        pprint('successfully created user {}'.format(userid))
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
	```
2. apply_role. You can use a role you've chosen manually if you want to set the same role for every user, or you can set it programmatically from some options if you'd like. Mine just uses the same role every time.
```
def apply_role(client,userid,roleId):
	userApi = looker.UserApi(client)
	body =[roleId]

	try: 
		# Set User Roles
		api_response = userApi.set_user_roles(userid, body)
		pprint('successfully set role')
	except ApiException as e:
		print("Exception when calling userApi->set_user_roles: %s\n" % e)
```

<br>

   ***2.5**: If you want to set user_attributes here, you'll want to create another function that hits the set_user_attribute_user_value endpoint: https://github.com/llooker/python_sdk/blob/master/docs/UserApi.md#set_user_attribute_user_value*


<br>
 
3. reset_url. This hits the create_user_credentials_email_password_reset endpoint to get a password reset URL. The catch is that we need an account setup url, not a password reset url. We can do this using some dark, ancient, magic— changing https://your.looker.com/password/reset/7kdgYB5QjdsXbgnxsqFN5bfqgZx7rxc to https://your.looker.com/account/setup/7kdgYB5QjdsXbgnxsqFN5bfqgZx7rxc. 

```
def get_email_setup(client,userid):
	userApi = looker.UserApi(client)
	user_id = userid

	try: 
		# Create Token
		api_response = userApi.create_user_credentials_email_password_reset(user_id)
		url = api_response.password_reset_url
        pprint('successfully generated reset url')
        #edit URL to be account setup
        url = url.replace('password/reset','account/setup')
		print('RESET URL = {}'.format(url))
		return url
	except ApiException as e:
		print("Exception when calling UserApi->create_user_credentials_email_password_reset: %s\n" % e)
```
4. Send the setup email!. I use sendgrid— They have a free tier that should cover your Looker welcome emails and then some.
```
import sendgrid
from sendgrid.helpers.mail import *
def send_mail(url,email):
	sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
	from_email = Email("theemailtobesentfrom")
	to_email = Email(email)
	subject = "Welcome to Looker "
	content = Content("text/plain", "Whatever you want your email to say. Click this link to get set up {}".format(url))
	mail = Mail(from_email, subject, to_email, content)
	response = sg.client.mail.send.post(request_body=mail.get())
	pprint('successfully sent reset email')

```

And hey presto, you've automatically configured a user! 

As I said in the intro, I'm sure there's better and more efficient ways to do this, and I'm super eager to hear them :slight_smile:

If someone has anything more streamlined, share it! Hopefully this helps out as a framework if you're looking to build something similar. It's worked well for me in the past. 