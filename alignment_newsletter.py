import re
import pandas as pd
import openpyxl
import requests
import json
import jsonlines
from utils import *
import arxiv
from bs4 import BeautifulSoup as bs


sh("mkdir -p data/processed/alignment_newsletter")
# put the alignment_newsletter.xlsx file in the raw/alignment_newsletter folder
# download new excel file here: https://docs.google.com/spreadsheets/d/1PwWbWZ6FPqAgZWOoOcXM8N_tUCuxpEyMbN1NYYC02aM/edit#gid=0
df = pd.read_excel("data/raw/alignment_newsletter/alignment_newsletter.xlsx")
wb = openpyxl.load_workbook("data/raw/alignment_newsletter/alignment_newsletter.xlsx")
ws = wb["Sheet1"]
# iterate over all rows
alignment_newsletter = {}
for index, row in df.iterrows():
    if row["summary"] != None:
        try:
            paper_url = ws.cell(row=index + 1, column=3).hyperlink.target
            newsletter_url = ws.cell(row=index + 1, column=8).hyperlink.target
        except:
            paper_url = ""
            newsletter_url = ""
        if "gradientscience" in paper_url:
            r = requests.get(paper_url)
            arxiv_id = re.findall(r"(?:arXiv:|abs/)(\d{4}\.\d{4,5})", r.text)[0]
        elif "arxiv.org" in paper_url:
            arxiv_id = re.findall(r"(?:arXiv:|abs/)(\d{4}\.\d{4,5})", paper_url)[0]
        else:
            arxiv_id = None
        if row["Venue"] == "arXiv":
            paper = arxiv.Search(id_list=[arxiv_id], max_results=1)
            paper = next(paper.results())
            abstract = paper.summary.replace("\n", " ")
            abs = "Paper abstract: " + abstract + "\n"
        else:
            abs = ""
        summary = (
            "Title: "
            + row["Title"]
            + "\n"
            + "Authors: "
            + row["Authors"]
            + "\n"
            + abs
            + "Summary: "
            + row["summary"]
            + "\n"
            + "My opinion: "
            + str(row["My opinion"])
        )
        alignment_newsletter[paper.get_short_id()[:-2]] = {
            "source": row["Venue"],
            "newsletter_category": row["Category"],
            "highlight": True if row["Highlight"] == "Highlight" else False,
            "newsletter_number": row["Email"],
            "newsletter_url": newsletter_url,
            "summarizer": row["Summarizer"],
            "paper_summary": row["Summary"],
            "opinion": row["My opinion"],
            "prerequisites": row["Prerequisites"],
            "read_more": row["Read more"],
            "paper_version": str(paper.get_short_id()) if abs != "" else None,
            "post_title": paper.title if abs != "" else row["Title"],
            "authors": [str(x) for x in paper.authors] if abs != "" else row["Authors"],
            "date_published": str(paper.published) if abs != "" else row["Year"],
            "data_last_modified": str(paper.updated) if abs != "" else "",
            "url": str(paper.entry_id) if abs != "" else paper_url,
            "abstract": abstract if abs != "" else "",
            "author_comment": paper.comment if abs != "" else "",
            "journal_ref": paper.journal_ref if abs != "" else "",
            "doi": paper.doi if abs != "" else "",
            "primary_category": paper.primary_category if abs != "" else "",
            "categories": paper.categories if abs != "" else "",
            "text": summary,
            "bibliography_bbl": "",
            "bibliography_bib": "",
        }
df.to_json(
    "data/processed/alignment_newsletter/alignment_newsletter_summaries.jsonl",
    orient="records",
    lines=True,
)
print(df.head(10))
