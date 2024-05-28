# Robot-Framework V2

### Intro

This robot creates prioritized tasks for checking people that might not be active citizens despite being registered as such.

This is done by checking the income of the person and then creating a case in KMD Nova for people without income.

### Arguments

The robot expects a list of approved case workers as input. This is given as a JSON string:

```json
{
    "approved_senders": [
        "azXXXXX"
    ]
}
```

### Linear Flow

The linear framework is used when a robot is just going from A to Z without fetching jobs from an
OpenOrchestrator queue.
The flow of the linear framework is sketched up in the following illustration:

![Linear Flow diagram](Robot-Framework.svg)


## Linting and Github Actions

This template is also setup with flake8 and pylint linting in Github Actions.
This workflow will trigger whenever you push your code to Github.
The workflow is defined under `.github/workflows/Linting.yml`.

