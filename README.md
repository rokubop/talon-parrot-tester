# Parrot Tester

![Version](https://img.shields.io/badge/version-0.8.0-blue)
![Status](https://img.shields.io/badge/status-stable-green)
![License](https://img.shields.io/badge/license-MIT-green)

Parrot Tester is a visualization tool to help you analyze your parrot integration with Talon, showing live data for frames, history, activity, and stats, using your existing `parrot_integration.py` and `patterns.json` files.

![preview](preview.png)

## Installation

### Dependencies

- [**Talon Beta**](https://talon.wiki/Help/beta_talon/)
- **Parrot** - Trained parrot model with `parrot_integration.py` and `patterns.json` files
- [**talon-ui-elements**](https://github.com/rokubop/talon-ui-elements) (v0.14.0+)

### Install

Clone the dependencies and this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

# Dependencies
git clone https://github.com/rokubop/talon-ui-elements

# This repo
git clone https://github.com/rokubop/talon-parrot-tester
```

Done! You can now use the Parrot Tester tool. 🎉

Say "parrot tester" to toggle the UI and start testing!

## How it works

A spy is attached to your existing `parrot_integration.py` file upon UI launch, and restored when the UI is closed.

No destructive edits are done to your `parrot_integration.py` or `patterns.json`.

If you somehow get into an error state, a Talon restart will restore everything to normal.

## Grace thresholds not working

If grace thresholds are not working as expected, you may want to try changing these lines in your `parrot_integration.py`. This bug was discovered as I was testing this tool.

Before:
```python
throttles = {}
if 'throttle' in pattern:
    if name not in pattern['throttle']:
        pattern['throttle'][name] = 0
    throttles = pattern['throttle']
```

After:
```python
throttles = {}
if 'throttle' in pattern:
    # if name not in pattern['throttle']:
    #     pattern['throttle'][name] = 0
    throttles = pattern['throttle']
```

Grace thresholds should now work as expected, but you may need to manually add "throttle" to every pattern now.