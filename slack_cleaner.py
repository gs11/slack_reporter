from datetime import datetime, timedelta
from urllib import request
import argparse
import json
import os
import re

TOKEN = os.getenv('SLACKTOKEN')
USERS_LIST_URL = "https://slack.com/api/users.list?token=" + TOKEN
ACCESS_LOGS_URL = "https://slack.com/api/team.accessLogs?token=" + TOKEN + "&count=1000"
CONVERSATIONS_LIST_URL = "https://slack.com/api/conversations.list?token=" + TOKEN + "&limit=1000&exclude_archived=true"
CONVERSATIONS_MEMBERS_URL = "https://slack.com/api/conversations.members?token=" + TOKEN + "&limit=1000"
SLACK_BOT_ID = "USLACKBOT"
PERIOD = 90

# Ignore bots.
def is_active(user):
    return user["deleted"] is False and user["is_bot"] is False and user["id"] != SLACK_BOT_ID

def is_owner(user):
    return is_active(user) and user["is_owner"] is True

def is_admin(user):
    return is_active(user) and user["is_admin"] is True

def is_member(user):
    return is_active(user) and not is_admin(user) and not is_licensed(user) and not is_free(user)

# Multichannel-guest
def is_licensed(user):
    return is_active(user) and not is_free(user) and user["is_restricted"] is True

# Single-channel guests
def is_free(user):
    return is_active(user) and user["is_ultra_restricted"] is True


def get_users_list():
    users = {}

    print("Fetching all users...", end="", flush=True)
    response = request.urlopen(USERS_LIST_URL)
    response_json = json.loads(response.read().decode(response.info().get_content_charset()))
    if response_json["ok"] is False:
        raise Exception("Slack API returned error: " + response_json["error"])

    members = response_json["members"]
    print("done ({} users)".format(len(members)))
    print("- {} owners.".format(len([u for u in members if is_owner(u)])))
    print("- {} administrators.".format(len([u for u in members if is_admin(u)])))
    print("- {} full members.".format(len([u for u in members if is_member(u)])))
    print("- {} multichannel guests.".format(len([u for u in members if is_licensed(u)])))
    print("- {} singlechannel guests.".format(len([u for u in members if is_free(u)])))
    print("- {} deactivated users.".format(len([u for u in members if not is_active(u)])))

    for user in members:
        if is_active(user):
            users[user["id"]] = user
    return users


def get_conversations_list(private = False, filter=".*"):
    conversations = {}
    if private:
        channel_types = "private_channel"
    else:
        channel_types = "public_channel"

    print("Fetching {} conversations for filter '{}'...".format(channel_types, filter), end="", flush=True)
    response = request.urlopen(CONVERSATIONS_LIST_URL + "&types=" + channel_types)
    response_json = json.loads(response.read().decode(response.info().get_content_charset()))
    if response_json["ok"] is False:
        raise Exception("Slack API returned error: " + response_json["error"])

    pattern = re.compile(filter)
    for channel in response_json["channels"]:
        if pattern.match(channel["name"]) != None:
            conversations[channel["id"]] = channel

    print("done ({}/{} channels)".format(len(conversations), len(response_json["channels"])))
    return conversations


def get_lately_logged_in_users():
    users = {}
    nintety_days_ago = (
        datetime.now() - timedelta(days=PERIOD)).timestamp()
    page = 0

    print("Fetching access logs", end="", flush=True)
    entries = 0
    while True:
        response = request.urlopen(ACCESS_LOGS_URL + "&page=" + str(page))
        response_json = json.loads(response.read().decode(response.info().get_content_charset()))

        if response_json["ok"] is False:
            raise Exception("Slack API returned error: " + response_json["error"])
        for login in response_json["logins"]:
            if login["date_last"] > nintety_days_ago:
                if login["user_id"] not in users:
                    users[login["user_id"]] = login["date_last"]
                entries += 1
            else:
                print("done ({} entries)".format(entries))
                return users
        print(".", end="", flush=True)
        page += 1
    return users


def get_users_and_channels(channels):
    user_channels = {}
    print("Fetching all members of each channel...")
    for chan in channels:
        if channels[chan]["num_members"] > 0:
            response = request.urlopen(CONVERSATIONS_MEMBERS_URL + "&channel=" + chan)
            response_json = json.loads(response.read().decode(response.info().get_content_charset()))
            print("- #" + channels[chan]["name"] + " ({} members)".format(len(response_json["members"])))
            for member in response_json["members"]:
                if member not in user_channels:
                    user_channels[member] = []
                user_channels[member].append(channels[chan]["name"])

    return user_channels


def filter_users(all_users, user_type):
    users = {}
    if user_type == "licensed":
        is_single_channel_user = False
    else:
        is_single_channel_user = True
    for id, user in all_users.items():
        if is_active(user) and is_free(user) == is_single_channel_user:
            users[id] = user
    return users


def print_inactive_users(all_users, active_users, user_type):
    print_separator()
    users = filter_users(all_users, user_type)
    print("These " + user_type + " users have not logged in during the last " + str(PERIOD) + " days:")
    inactive_users = set(users.keys()) - set(active_users.keys())
    for user in inactive_users:
        print(" - " + all_users[user]["profile"]["email"])
    print_separator()


def print_single_channel_licensed_users(all_users, users_and_channels):
    print_separator()
    print("These licensed users are members of less than 2 channels:")
    for user, channels in users_and_channels.items():
        if len(channels) < 2 and user in all_users and is_licensed(all_users[user]):
            print(" - " + all_users[user]["profile"]["email"] + "(" + user + ") belongs to #" + ", #".join(channels))
    print_separator()


def print_private_channels():
    print_separator()
    print("Listing all (non-archived) private channels:")
    channels = get_conversations_list(private = True)
    for chan in channels:
        print("- #" + channels[chan]["name"])
    print_separator()

# A report with user list and channels the user belong to.
def print_users_and_channels(all_users, users_and_channels):
    email_channels = {}
    for user, channels in users_and_channels.items():
        if user in all_users and all_users[user]["profile"]["email"]:
            email = all_users[user]["profile"]["email"]
            email_channels[email] = channels

    print_separator()
    for email, channels in sorted(email_channels.items()):
        print(" - " + email + " belongs to #" + ", #".join(sorted(channels)))
    print_separator()

# A report of channels and which users belongs to it.
def print_channels_and_users(all_users, users_and_channels):
    channels_user = {}
    for user, channels in users_and_channels.items():
        if user in all_users and all_users[user]["profile"]["email"]:
            email = all_users[user]["profile"]["email"]
            for channel in channels:
                if not channel in channels_user:
                    channels_user[channel] = []
                channels_user[channel].append(email)

    print_separator()
    for channel, users in sorted(channels_user.items()):
        print_separator()
        print("Members of #" + channel)
        for user in sorted(users):
            print(" - " + user)
    print_separator()

def print_separator():
    print("------------------------------------------")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Slack client for user reporting.')
    parser.add_argument('--channels',
                        dest='channels',
                        help='Limit reporting to channels', 
                        default='.*')
    parser.add_argument('--report',
                        dest='report',
                        help='Report type: inactive, channel', 
                        choices=['inactive', 'channel', 'private', 'user'],
                        default='inactive')
    args = parser.parse_args()

    if args.report == "inactive":
        all_users = get_users_list()
        all_channels = get_conversations_list(private = False, filter=args.channels)
        users_and_channels = get_users_and_channels(all_channels)
        active_users = get_lately_logged_in_users()
        print_inactive_users(all_users, active_users, "licensed")
        print_inactive_users(all_users, active_users, "free")
        print_single_channel_licensed_users(all_users, users_and_channels)
    elif args.report == "user":
        all_users = get_users_list()
        all_channels = get_conversations_list(private = False, filter=args.channels)
        users_and_channels = get_users_and_channels(all_channels)
        print_users_and_channels(all_users, users_and_channels)
    elif args.report == "channel":
        all_users = get_users_list()
        all_channels = get_conversations_list(private = False, filter=args.channels)
        users_and_channels = get_users_and_channels(all_channels)
        print_channels_and_users(all_users, users_and_channels)
    elif args.report == "private":
        print_private_channels()
