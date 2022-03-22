import os
import pandas as pd
from pathlib import Path
from urllib import request
from bs4 import BeautifulSoup
import arxiv
import tarfile
import pickle
from urllib.error import HTTPError
import json
from utils import *


RAW_DIR = Path("data/raw")
TARS_DIR = RAW_DIR / "tars"
INTERIM_DIR = Path("data/interim")
PKLS_DIR = INTERIM_DIR / "pkls"
PROCESSED_DIR = Path("data/processed")
PROCESSED_JSONS_DIR = PROCESSED_DIR / "jsons"


def download_arxiv_paper_tars(
    citation_level=0,
    create_dict_only=False,
):
    df = pd.read_csv("ai-alignment-papers.csv", index_col=0)
    df_arxiv = df[df["Url"].str.contains("arxiv") == True]
    papers = list(set(df_arxiv["Url"].values))

    if os.path.exists(str(PKLS_DIR / "arxiv_paper_tars_list.pkl")):
        with open(str(PKLS_DIR / "arxiv_paper_tars_list.pkl"), "rb") as f:
            tars = pickle.load(f)
    else:
        tars = ["0"] * len(papers)

    if len(tars) != len(papers):
        # this likely means we've added more papers to the list
        tars = ["0"] * len(papers)
    incorrect_links_ids = []
    paper_dl_failures = []
    arxiv_dict = {}
    for i, (paper_link, filename) in enumerate(zip(papers[0:10], tars[0:10])):
        paper_id = ".".join(filename.split(".")[:2])

        if os.path.exists(str(TARS_DIR / filename)) and create_dict_only == False:
            print("Already downloaded the " + paper_id + " tar file.")
            continue

        try:
            paper_id = paper_link.split("/")[-1]
            paper = next(arxiv.Search(id_list=[paper_id]).results())
            arxiv_dict[paper.get_short_id()[:-2]] = {
                "source": "arxiv",
                "source_filetype": "latex",
                "converted_with": "pandoc",
                "paper_version": str(paper.get_short_id()),
                "post_title": paper.title,
                "authors": [str(x) for x in paper.authors],
                "date_published": str(paper.published),
                "data_last_modified": str(paper.updated),
                "url": str(paper.entry_id),
                "abstract": paper.summary,
                "author_comment": paper.comment,
                "journal_ref": paper.journal_ref,
                "doi": paper.doi,
                "primary_category": paper.primary_category,
                "categories": paper.categories,
                "citation_level": citation_level,  # 0 = original, 1 = citation of original, 2 = citation of citation, etc.
                "main_tex_filename": "",
                "text": "",
                "bibliography_bbl": "",
                "bibliography_bib": "",
            }
            tar_filename = paper.entry_id.split("/")[-1] + ".tar.gz"
            tars[i] = tar_filename
            if create_dict_only:
                print("Added " + paper.get_short_id()[:-2] + " to json.")
                continue
        except:
            incorrect_links_ids.append([paper_link, paper_id])
            pass

        try:
            paper.download_source(dirpath=str(TARS_DIR), filename=tar_filename)
            print("Downloaded paper: " + paper_id)
        except HTTPError:
            print("Could not download paper: " + paper_id)
            paper_dl_failures.append(paper_id)
            pass

    if incorrect_links_ids != []:
        print("Incorrect links:")
        print(incorrect_links_ids)
    if paper_dl_failures != []:
        print("Paper download failures:")
        print(paper_dl_failures)

    with open(PROCESSED_JSONS_DIR / "arxiv_dict.json", "w") as fp:
        json.dump(arxiv_dict, fp)

    with open(PKLS_DIR / "arxiv_paper_tars_list.pkl", "wb") as f:
        pickle.dump(tars, f)

    with open(PKLS_DIR / "incorrect_links_ids_list.pkl", "wb") as f:
        pickle.dump(incorrect_links_ids, f)

    with open(PKLS_DIR / "paper_dl_failures_list.pkl", "wb") as f:
        pickle.dump(paper_dl_failures, f)
