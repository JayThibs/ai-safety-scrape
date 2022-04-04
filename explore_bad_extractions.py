import json

arxiv = json.load(open("arxiv_data_list.json"))

for paper in arxiv:
    if paper["citation_level"] == "1" and paper["good_extraction"] == False:
        print(paper["id"])
        print(paper["text"])
