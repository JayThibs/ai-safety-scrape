import pandas as pd
import json
import jsonlines
from utils import *
import arxiv


sh("mkdir -p data/processed/alignment_newsletter")
df = pd.read_csv("data/raw/csvs/alignment_newsletter.csv")
# iterate over all rows
summaries = []
for index, row in df.iterrows():
    if row["summary"] != None:
        if row["Venue"] == "arXiv":
            arxiv.Search(query=row["Title"], max_results=1)
        summary = (
            "Title: "
            + row["Title"]
            + "\n"
            + "Authors: "
            + row["Authors"]
            + "\n"
            + "Summary: "
            + row["summary"]
            + "\n"
            + "My opinion: "
            + str(row["My opinion"])
        )
        summaries.append(summary)
df.to_json(
    "data/processed/alignment_newsletter/alignment_newsletter_summaries.jsonl",
    orient="records",
    lines=True,
)
print(df.head(10))
