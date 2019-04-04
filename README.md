## Description

Simple script to find inactive users in a slack workspace. Prints the following:

- Licensed users that hasn't logged in lately
- Free users that hasn't logged in lately
- Licensed users that are members of only one channel

Pythonified from a bash script from [@jannylund](http://github.com/jannylund)

## Usage

Create a Slack API legacy token or an OAuth token with sufficient scope. Copy it into the script and run using Python 3.x:

```
export SLACK_TOKEN="<REDACTED>"
python slack_cleaner.py
```

## TODO

- Use OAuth instead of tokens
- Find multi-channel users only in one channel
