import os
import json
import jsonlines
from utils import *


if os.path.exists("data/reports-and-non-arxiv-papers.jsonl") or os.path.exists("data/reports-and-non-arxiv-papers.json"):
    os.remove("data/reports-and-non-arxiv-papers.jsonl")
    os.remove("data/reports-and-non-arxiv-papers.txt")

text_jsons = ls("data/nonarxiv_json") + ls('data/nonarxiv_json')  #+ os.listdir('data/reports_json/')
json_list = []

for i, filename in enumerate(text_jsons):
    i = str(i)
    paper = json.load(open(filename))
    with jsonlines.open("data/reports-and-non-arxiv-papers.jsonl", "a") as writer:
        writer.write(paper)
    json_list.append(paper)
    print(i)

json.dump(json_list, open("data/reports-and-non-arxiv-papers.json", 'w'))