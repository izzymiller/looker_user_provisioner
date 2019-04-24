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
from provisioning_utils import create_user, apply_role, get_email_setup, send_mail


#instantiate flask app
app = Flask(__name__)


# I named the URL to be "usr_gen", you can call it whatever you want.
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