# whyzer - WhatsApp Chat Analyzer

### Features
Creates charts about:
* Most active chat members
* Average message length per chat member
* Conversations started per chat member
* Chat activity per hour and day of the week (histogram)
* Commonly used words (word cloud)

### Installation
* Requires python3
* Install dependencies:

```bash
pip install -r requirements.txt
```

### Usage
* Export a WhatsApp Chat on your phone (Options > More > Export Chat)

* Select "without media"

* Transfer the .txt file to your computer (e.g via e-mail or cloud)

* Run `whyzer`:

> A note on the `--lang`option:
> This needs to be the same language like your phone is set to while exporting the chat.
> It is necessary for parsing timestamps and other events.
> The actual language of the chat messages doesn't matter.
```
whyzer.py --lang de --save ./out my-chat.txt
```

* All options:
```
usage: whyzer.py [-h] [--lang {en,de}] [--save DIR] [--no-plots] chatfile

Analyzes exported WhatsApp chats

positional arguments:
  chatfile        Exported WhatsApp Chat file (usually .txt)

optional arguments:
  -h, --help      show this help message and exit
  --lang {en,de}  Phone language used while exporting the chat. Determines
                  date format etc. This is independent of the language used in
                  chat (default: en)
  --save DIR      Directory in which plots get saved (default: None)
  --no-plots      Don't show plots (default: False)

```
