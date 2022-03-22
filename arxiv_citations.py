import json
import pandas as pd

arxiv_citations_dict = json.load(open("arxiv_citations_dict.json"))

all_citations = {}
for paper_id in arxiv_citations_dict.keys():
    for citation in arxiv_citations_dict[paper_id].keys():
        all_citations[citation] = True


all_citations = pd.DataFrame(list(all_citations.keys()))
print(all_citations)
print(len(all_citations))
all_citations.to_csv("all_citations.csv", index=False)
