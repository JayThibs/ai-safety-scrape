import json
import pandas as pd

arxiv_citations_dict = json.load(open("arxiv_citations_dict.json"))

all_citations = {}
for paper_id in arxiv_citations_dict.keys():
    for citation in arxiv_citations_dict[paper_id].keys():
        all_citations[citation] = True


all_citations = pd.DataFrame(list(all_citations.keys()))
print(all_citations)
citation_level = str(input("Enter citation level: "))
all_citations.to_csv(f"all_citations_level_{citation_level}.csv", index=False)
