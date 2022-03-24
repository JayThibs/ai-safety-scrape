import json
import pandas as pd

arxiv_dict = json.load(open("arxiv_dict_updated.json"))
citations = pd.read_csv(f"all_citations_level_1.csv", index_col=0)
papers = list(set(list(citations.index)))

for paper in papers:
    paper = str(paper)
    if arxiv_dict[paper]["text"] != "":
        print(paper)
        print(arxiv_dict[paper]["text"])
