#!/usr/bin/env python
from __future__ import print_function
import logging
import sys
from os import path
import json
import argparse
from datetime import datetime
from email.utils import parsedate
import yaml
from TwitterAPI import TwitterAPI


log = logging.getLogger('whatsupbot')
log.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stderr)
ch.setFormatter(logging.Formatter('%(filename)-11s %(lineno)-3d: %(message)s'))
log.addHandler(ch)


def parse(file_path):
    '''Parse a YAML or JSON file.'''
    _, ext = path.splitext(file_path)
    if ext in ('.yaml', '.yml'):
        func = yaml.load
    elif ext == '.json':
        func = json.load
    else:
        raise ValueError("Unrecognized config file type %s" % ext)
    with open(file_path, 'r') as f:
        return func(f)


def last_tweet(api, screen_name):
    '''Hours since last tweet. Returns float/int.'''
    try:
        resp = api.request('statuses/user_timeline', {'screen_name': screen_name, 'count': '1'})
        created_at = parsedate(resp.json()[0]['created_at'])
        dt = datetime(*created_at[:6])
        elasped = (datetime.utcnow() - dt).total_seconds() / 3600.
        logging.getLogger('whatsupbot').debug('@%s elapsed %s', screen_name, elasped)
        return elasped

    except (TypeError, IndexError) as e:
        logging.getLogger('whatsupbot').error('error fetching @%s: %s', screen_name, e)
        return -1


def compose(screen_name, elapsed, hours, sender=None, confirm=False):
    message = ''

    if elapsed == -1:
        if sender == screen_name:
            message = "My timeline isn't showing up in the Twitter API. Can you check on me?"
        else:
            message = "@{}'s timeline isn't showing up in the Twitter API.".format(screen_name)

    elif elapsed > hours:
        if sender == screen_name:
            message = "It's been more than {} hours since my last tweet. Fix me!".format(int(elapsed))
        else:
            message = 'No tweets from @{} in more than {} hours'.format(screen_name, int(elapsed))

    elif confirm:
        if sender == screen_name:
            message = "It's been {} hours since my last tweet".format(int(elapsed))
        else:
            message = '@{} last tweeted {} hours ago'.format(screen_name, int(elapsed))

    return message


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screen_name', default=None, required=False, help='screen name to check')
    parser.add_argument('--from', dest='sender', default=None,
                        help='account that will send DM notifications')
    parser.add_argument('--hours', type=int, default=24,
                        help="Gaps of this many hours are a problem (default: 24)")
    parser.add_argument('--to', dest='recipient', metavar='USER', type=str, default=None,
                        help='user to notify when screen_name is down. If omitted, prints to stdout')
    parser.add_argument('--confirm', action='store_true',
                        help='Always send message with the time of the most recent tweet')
    parser.add_argument('-c', '--config', dest='config_file', metavar='PATH', default=None, type=str,
                        help='bots config file (json or yaml). By default, all accounts in the file will be checked.')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('--key', type=str, help='access token')
    parser.add_argument('--secret', type=str, help='access token secret')
    parser.add_argument('--consumer-key', metavar='KEY', type=str, help='consumer key (aka consumer token)')
    parser.add_argument('--consumer-secret', metavar='SECRET', type=str, help='consumer secret')

    args = parser.parse_args()
    logger = logging.getLogger('whatsupbot')

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.key and args.secret and args.consumer_secret and args.consumer_key:
        api = TwitterAPI(args.consumer_key, args.consumer_secret, args.key, args.secret)
    else:
        api = None

    if getattr(args, 'config_file'):
        conf = parse(args.config_file)
        if not api:
            try:
                sender = conf['users'][args.sender]
                if 'app' in sender:
                    app = conf['apps'][sender['app']]
                elif 'consumer_key' in sender and 'consumer_secret' in sender:
                    app = sender

                api = TwitterAPI(app['consumer_key'], app['consumer_secret'], sender['key'], sender['secret'])

            except:
                pass

    if not api:
        logger.error("unable to set up api")
        exit(1)

    users = conf.get('users', {args.screen_name: {}})
    messages = [
        compose(u, last_tweet(api, u), attrs.get('whatsupbot', {}).get('hours', args.hours), args.sender, args.confirm)
        for u, attrs in users.items() if attrs.get('whatsupbot', True)
    ]
    message = '\n'.join(m for m in messages if m)

    if args.recipient and message:
        recipient = api.request('users/show', {'screen_name': args.recipient})
        id_str = recipient.json().get('id_str')
        payload = {
            "event": {
                "type": "message_create",
                "message_create": {
                    "target": {"recipient_id": id_str}, "message_data": {"text": message}
                }
            }
        }
        resp = api.request('direct_messages/events/new', json.dumps(payload))
        logger.debug('status code %s', resp.status_code)
        if resp.status_code != 200:
            logger.error(resp.text)

    elif message:
        print(message)


if __name__ == '__main__':
    main()
