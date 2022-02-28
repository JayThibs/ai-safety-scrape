import argparse
import json
import os
from collections import OrderedDict
from urllib.parse import urlparse

import arxiv_download_download
from arxiv.utils import EntryWriter


def cmd_list(args):
    for name in arxiv_download_download.ALL_ARXIV_PAPERS:
        print(name)


def cmd_fetch(args):
    with EntryWriter(args.name, args.path) as writer:
        for entry in arxiv_download_download.get_arxiv_paper(args.name).fetch_entries():
            writer.write(entry)


def create_arg_parser():
    parser = argparse.ArgumentParser(description="Fetch arxiv papers.")
    subparsers = parser.add_subparsers(
        title="commands", description="valid commands", help="additional help"
    )

    list_cmd = subparsers.add_parser("list", help="List available arxiv papers.")
    list_cmd.set_defaults(func=cmd_list)

    fetch_cmd = subparsers.add_parser("fetch", help="Fetch arxiv papers.")
    fetch_cmd.set_defaults(func=cmd_fetch)
    fetch_cmd.add_argument("name", help="Name of arxiv paper to fetch.")
    fetch_cmd.add_argument(
        "--path", default="data/arxiv_papers", help="Path to save arxiv papers."
    )

    return parser


def main():
    args = create_arg_parser().parse_args()

    if getattr(args, "func", None) is None:
        # No subcommand was given
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()