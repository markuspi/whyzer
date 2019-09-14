#!/usr/bin/env python3
# -.- coding: UTF-8 -.-

import re
import sys
import argparse
import pandas as pd
import seaborn as sns

from os.path import join
from matplotlib import pyplot as plt
from datetime import datetime
from collections import defaultdict
from wordcloud import WordCloud

weekdays = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

languages = {
    "en": {
        "date_content": r'^(\d\d/\d\d/\d\d\d\d, \d\d:\d\d) - (.*)$',
        "deleted": r'^This message was deleted$',
        "media": r'^<Media omitted>$',
        "date_format": "%d/%m/%Y, %H:%M",
        "created": r'^.* created Group "(.*)"$',
        "rename": r'^.* changed the subject from ".*" to "(.*)"$'
    },
    "de": {
        "date_content": r'^(\d\d.\d\d.\d\d, \d\d:\d\d) - (.*)$',
        "deleted": r'^Diese Nachricht wurde gelöscht.$',
        "media": r'^<Medien ausgeschlossen>$',
        "date_format": "%d.%m.%y, %H:%M",
        "created": r'^.* hat die Gruppe „(.*)“ erstellt.$',
        "rename": r'^.* hat den Betreff von „.*“ zu „(.*)“ geändert.$'
    }
}


class Parser:
    def __init__(self, language, aliases=None, multipart=True, cw="common_words/de.txt"):
        if type(language) == str:
            # treat parameter as language code
            language = languages[language]
        self.regex_date_content = re.compile(language['date_content'])
        self.regex_message = re.compile(r'^(.*?): (.*)$', re.DOTALL)
        self.regex_deleted = re.compile(language['deleted'])
        self.regex_media = re.compile(language['media'])
        self.regex_words = re.compile(r"[\w'-]+")
        self.regex_created = re.compile(language['created'])
        self.regex_rename = re.compile(language['rename'])
        self.date_format = language['date_format']

        self.date_buffer = None
        self.content_buffer = ""
        self.chat_name = None

        self.aliases = aliases if aliases else {}
        self.multipart = multipart

        self.member_msg_count = defaultdict(int)
        self.msgs = []

        self.all_words = ""

        with open(cw) as f:
            self.common_words = [line.strip() for line in f]

    def handle_text_message(self, date, author, body):
        # multipart: if two messages are sent in less than 3 minutes by the same author,
        # they are combined into one message
        # initiator: if a question (containing "?") is posted after 24 hours of silence

        multipart = False
        initiator = True

        if self.multipart and len(self.msgs) > 0:
            diff = (date - self.msgs[-1][1]).total_seconds()

            if diff < 60 * 60 * 24 or "?" not in body:
                initiator = False

            if self.msgs[-1][0] == author and diff < 60 * 3:
                multipart = True

        for word in self.regex_words.finditer(body):
            word = word.group(0).lower()
            if word not in self.common_words:
                self.all_words += " " + word
        self.all_words += ". "

        if multipart:
            self.msgs[-1][2] += len(body)
            self.msgs[-1][3] += 1
        else:
            self.msgs.append([author, date, len(body), 1, initiator])

    def handle_entry(self):
        if self.date_buffer is None:
            print("No entry was found. Make sure you used the right language code.", file=sys.stderr)
            sys.exit(1)

        try:
            date = datetime.strptime(self.date_buffer, self.date_format)
        except ValueError as e:
            print("Error while parsing date. Make sure you used the right language code.", file=sys.stderr)
            print(e)
            sys.exit(1)

        message = self.regex_message.match(self.content_buffer)
        if message:
            # chat message
            author = message.group(1)
            body = message.group(2)

            if author in self.aliases:
                author = self.aliases[author]
            if " " in author and "+" not in author:
                author = author.split(" ")[0]

            if self.regex_deleted.match(body):
                pass
            elif self.regex_media.match(body):
                pass
            else:
                self.handle_text_message(date, author, body)
        else:
            created = self.regex_created.match(self.content_buffer)
            if created:
                self.chat_name = created.group(1)
                print("Created:", self.chat_name)

            rename = self.regex_rename.match(self.content_buffer)
            if rename:
                self.chat_name = rename.group(1)
                print("Renamed:", self.chat_name)

            pass

    def parse_line(self, line):
        match = self.regex_date_content.match(line)

        if match:
            if self.date_buffer:
                self.handle_entry()
            # line is a new entry
            self.date_buffer = match.group(1)
            self.content_buffer = match.group(2)
        else:
            # line is continuation
            self.content_buffer += "\n" + line

    def parse_file(self, fp):
        print("Parsing file...")
        i = 0
        for line in fp:
            self.parse_line(line)
            i += 1
            if i % 500 == 0:
                print(i, "lines parsed")
        self.handle_entry()
        print("Done parsing.", i, "lines,", len(self.msgs), "messages")

    def parse_file_by_name(self, filename):
        with open(filename) as fp:
            self.parse_file(fp)

    def visualize(self, show_plots=True, save_dir="out"):
        msgs = pd.DataFrame(self.msgs, columns=["member", "date", "body_len", "parts", "initiator"])
        msgs_per_member = msgs.groupby("member").agg({"date": "count", "body_len": "mean", "initiator": "sum"})

        prefix = ""
        if self.chat_name:
            prefix = '"' + self.chat_name[:20] + (self.chat_name[20:] and "...") + '": '

        def show_and_save(name):
            if save_dir:
                plt.savefig(join(save_dir, name + ".png"), bbox_inches='tight')
            if show_plots:
                plt.show()

        count_per_member = msgs_per_member['date'].sort_values(ascending=False).head(20)
        len_per_member = msgs_per_member['body_len'].sort_values(ascending=False).head(20)
        init_per_member = msgs_per_member['initiator'].sort_values(ascending=False).head(20)
        heat_data = msgs['date'].groupby([msgs['date'].dt.weekday, msgs['date'].dt.hour]).count()
        heat_data.rename("msg_count", inplace=True)
        heat_data.index.rename(["day", "hour"], inplace=True)
        heat_pivot = pd.pivot_table(heat_data.to_frame(), values="msg_count", index=['day'], columns=['hour'])
        heat_pivot.index = heat_pivot.index.map(lambda x: weekdays[x])

        count_plot = count_per_member.plot(kind="bar", color="teal", legend=None,
                                           title=prefix + "Most active chat members")
        count_plot.set_xlabel("Chat Member")
        count_plot.set_ylabel("Message Count")
        show_and_save("count")

        len_plot = len_per_member.plot(kind="bar", color="orange",  title=prefix + "Average Message Length")
        len_plot.set_xlabel("Chat Member")
        len_plot.set_ylabel("Message Length [Characters]")
        show_and_save("len")

        init_plot = init_per_member.plot(kind="bar", color="lime", title=prefix + "Conversation Initiator")
        init_plot.set_xlabel("Chat Member")
        init_plot.set_ylabel("Initiated Conversations")
        show_and_save("init")

        plt.figure(figsize=(16, 5))
        sns.heatmap(heat_pivot, cmap="Greens", cbar=False, annot=True, fmt=".0f")
        plt.title(prefix + "Chat Activity")
        show_and_save("activity")

        cloud = WordCloud().generate(self.all_words)
        plt.imshow(cloud, interpolation="bilinear")
        plt.title(prefix + "Common Words")
        plt.axis("off")
        show_and_save("cloud")

        if save_dir:
            print("Plots saved to dir: '%s'" % save_dir)


if __name__ == '__main__':
    argp = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                   description="Analyzes exported WhatsApp chats")
    argp.add_argument("--lang", default="en", choices=languages.keys(),
                      help="Phone language used while exporting the chat. Determines date format etc. "
                           "This is independent of the language used in chat")
    argp.add_argument("chatfile", type=argparse.FileType(mode="r", encoding="UTF-8"),
                      help="Exported WhatsApp Chat file (usually .txt)")
    argp.add_argument("--save", metavar="DIR", default=None, help="Directory in which plots get saved")
    argp.add_argument("--no-plots", action="store_true", help="Don't show plots")
    args = argp.parse_args()

    p = Parser(args.lang)
    p.parse_file(args.chatfile)
    p.visualize(show_plots=not args.no_plots, save_dir=args.save)

