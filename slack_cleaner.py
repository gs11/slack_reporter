import requests
import json
from datetime import datetime, timedelta


TOKEN = "<inser token here>"
USERS_LIST_URL = "https://slack.com/api/users.list?token=" + TOKEN
ACCESS_LOGS_URL = "https://slack.com/api/team.accessLogs?token=" + TOKEN + "&count=1000"
SLACK_BOT_ID = "USLACKBOT"
PERIOD = 90


def get_users_list():
    print("Fetching all users...", end="", flush=True)
    response = requests.get(USERS_LIST_URL)
    response_json = response.json()
    if response_json["ok"] is False:
        raise Exception("Slack API returned error: " + response_json["error"])
    print("done")
    return response_json


def get_lately_logged_in_users():
    users = set()
    nintety_days_ago = (
        datetime.now() - timedelta(days=PERIOD)).timestamp()
    page = 0

    print("Fetching access logs", end="", flush=True)
    while True:
        response = requests.get(ACCESS_LOGS_URL + "&page=" + str(page))
        response_json = response.json()
        if response_json["ok"] is False:
            raise Exception("Slack API returned error: " +
                            response_json["error"])
        for entry in response_json["logins"]:
            if entry["date_last"] > nintety_days_ago:
                users.add(entry["username"])
            else:
                print("done")
                return users
        print(".", end="", flush=True)
        page += 1
    return users


def filter_users(all_users, user_type):
    users = set()
    if user_type == "licensed":
        is_ultra_restricted = False
    else:
        is_ultra_restricted = True
    for user in all_users["members"]:
        if user["deleted"] is False and user["is_bot"] is False and user["is_ultra_restricted"] is is_ultra_restricted and user["id"] != SLACK_BOT_ID:
            users.add(user["name"])
    return users


def print_inactive_users(all_users, user_type):
    users = filter_users(all_users, user_type)
    print("------------------------------------------")
    print("These " + user_type + " users have not logged in during the last " +
          str(PERIOD) + " days:")
    for user in users.difference(active_users):
        print(" - " + user)


if __name__ == "__main__":
    all_users = get_users_list()
    active_users = get_lately_logged_in_users()

    print_inactive_users(all_users, "licensed")
    print_inactive_users(all_users, "free")
