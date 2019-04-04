from urllib import request
import json
from datetime import datetime, timedelta


TOKEN = "<insert token here>"
USERS_LIST_URL = "https://slack.com/api/users.list?token=" + TOKEN
ACCESS_LOGS_URL = "https://slack.com/api/team.accessLogs?token=" + TOKEN + "&count=1000"
# Deprecated but provides the ability to list all channels + all their members in one call
CHANNELS_LIST_URL = "https://slack.com/api/channels.list?token=" + TOKEN + "&count=1000"
SLACK_BOT_ID = "USLACKBOT"
PERIOD = 90


def get_users_list():
    users = {}

    print("Fetching all users...", end="", flush=True)
    response = request.urlopen(USERS_LIST_URL)
    response_json = json.loads(response.read().decode(
        response.info().get_content_charset()))
    if response_json["ok"] is False:
        raise Exception("Slack API returned error: " + response_json["error"])
    print("done ({} users)".format(len(response_json["members"])))

    for user in response_json["members"]:
        if "email" in user["profile"]:
            users[user["id"]] = user
    return users


def get_lately_logged_in_users():
    users = {}
    nintety_days_ago = (
        datetime.now() - timedelta(days=PERIOD)).timestamp()
    page = 0

    print("Fetching access logs", end="", flush=True)
    entries = 0
    while True:
        response = request.urlopen(ACCESS_LOGS_URL + "&page=" + str(page))
        response_json = json.loads(response.read().decode(
            response.info().get_content_charset()))

        if response_json["ok"] is False:
            raise Exception("Slack API returned error: " +
                            response_json["error"])
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


def get_users_and_channels():
    user_channels = {}
    print("Fetching all channels and their members...", end="", flush=True)
    response = request.urlopen(CHANNELS_LIST_URL)
    response_json = json.loads(response.read().decode(
        response.info().get_content_charset()))
    print("done ({} channels)".format(len(response_json["channels"])))
    for channel in response_json["channels"]:
        for member in channel["members"]:
            if member not in user_channels:
                user_channels[member] = []
            user_channels[member].append(channel["id"])
    return user_channels


def filter_users(all_users, user_type):
    users = {}
    if user_type == "licensed":
        is_ultra_restricted = False
    else:
        is_ultra_restricted = True
    for id, user in all_users.items():
        if user["deleted"] is False and user["is_bot"] is False and user["is_ultra_restricted"] is is_ultra_restricted and user["id"] != SLACK_BOT_ID:
            users[id] = user
    return users


def print_inactive_users(all_users, active_users, user_type):
    users = filter_users(all_users, user_type)
    print("------------------------------------------")
    print("These " + user_type + " users have not logged in during the last " +
          str(PERIOD) + " days:")
    inactive_users = set(users.keys()) - set(active_users.keys())
    for user in inactive_users:
        print(" - " + all_users[user]["profile"]["email"])


def print_single_channel_licensed_users(all_users, users_and_channels):
    print("------------------------------------------")
    print("These licensed users are members of less than 2 channels:")
    for user, channels in users_and_channels.items():
        if len(channels) < 2:
            print(" - " + all_users[user]["profile"]["email"])


if __name__ == "__main__":
    all_users = get_users_list()
    active_users = get_lately_logged_in_users()
    users_and_channels = get_users_and_channels()

    print_inactive_users(all_users, active_users, "licensed")
    print_inactive_users(all_users, active_users, "free")
    print_single_channel_licensed_users(all_users, users_and_channels)
