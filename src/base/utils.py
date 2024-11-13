import requests
from django.core.files.base import ContentFile
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import serializers

import urllib.request as urllib2
from functools import partial


@partial
def fb_require_email(strategy, backend, details, user=None, is_new=False, *args, **kwargs):
    if backend.name == "facebook":
        if user and user.email:
            return
        if is_new and not details.get('email'):
            if strategy.request_data().get('email'):
                details['email'] = strategy.request_data().get('email')
                return

            if strategy.request.session.get('email', '') != '':
                details['email'] = strategy.request.session['email']
                return

            token = kwargs['response']['access_token']
            response = requests.get(
                'https://graph.facebook.com/v8.0/me?fields=about,name,email',
                headers={'Authorization': 'Bearer ' + token})
            response.raise_for_status()
            resp = response
            if resp.json().get('email'):
                details['email'] = resp.json().get('email')
            else:
                msg = 'Please allow to email permission or register manually.'
                raise serializers.ValidationError(msg)


@partial
def get_profile_picture(backend, user, response, is_new=False, *args, **kwargs):
    """ Grab facebook and google profice images and save to user model"""

    if backend.name == 'google-oauth2' and is_new:
        if response.get('picture'):
            url = response.get('picture')
            try:
                response = requests.request('GET', url)
                response.raise_for_status()
            except requests.HTTPError:
                pass
            else:
                user.photo.save(
                    '{0}_google.jpg'.format(user.email),
                    ContentFile(response.content),
                    save=False
                )
                user.save()

    if backend.name == 'facebook' and is_new:
        url = 'http://graph.facebook.com/{0}/picture'.format(response['id'])
        try:
            response = requests.request('GET', url, params={'type': 'large'})
            response.raise_for_status()
        except requests.HTTPError:
            pass
        else:
            user.photo.save(
                '{0}_facebook.jpeg'.format(user.email),
                ContentFile(response.content),
                save=False
            )
            user.save()
