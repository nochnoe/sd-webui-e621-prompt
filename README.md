# sd-webui-e621-prompt

Request tags of an image from e621, inspired by [`sd-webui-gelbooru-prompt`](https://github.com/antis0007/sd-webui-gelbooru-prompt).

**Note**: I'm not a Python developer and haven't touched this language for a few years. This extension was hacked together using some other sd-webui extensions sources, stackoverflow answers and pure luck. Feel free to submit PR's fixing this unholy mess.

## Development

1. Clone into `extensions` folder
2. `cp .env.example .env` for setting `PYTHONPATH`. It is required for IDE autocompletions to work (tested with vscode, if you use PyCharm your mileage may vary). If you using unix-like OS, replace semicolon with a colon
