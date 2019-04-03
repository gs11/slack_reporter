## Description

Simple script to find inactive users in a slack workspace. Prints the following:

- Licensed users that hasn't logged in lately
- Free users that hasn't logged in lately

Pythonified from a bash script from [@jannylund](http://github.com/jannylund)

## Usage

Create a Slack API legacy token or an OAuth token with sufficient scope. Copy it into the script and run using Python 3.x:

```
python slack_cleaner.sh
```

## TODO

- Use OAuth instead of tokens
- Find multi-channel users only in one channel
