import os
from timeit import repeat
from download_papers import download_arxiv_paper_tars
from utils import *
from fix_empty_conversions import mv_empty_mds, remove_empty_mds_from_dict
from extractor_functions import *
import magic

mime = magic.Magic(mime=True)
import multiprocessing as mp
from itertools import repeat
from tqdm import tqdm
import json
import pandas as pd
import traceback
from pathlib import Path


CODE_DIR = Path(".") / "code-projects/gpt-ai-safety"
RAW_DIR = Path("data/raw")
INTERIM_DIR = Path("data/interim")
PROCESSED_DIR = Path("data/processed")
TARS_DIR = RAW_DIR / "tars"
LATEX_DIR = RAW_DIR / "latex_files"
PDFS_DIR = RAW_DIR / "pdfs"
PKLS_DIR = INTERIM_DIR / "pkls"
EXTRACTED_TARS_DIR = INTERIM_DIR / "extracted_tars"
MERGE_TEX_DIR = INTERIM_DIR / "merge_latex_files"
PROCESSED_TXTS_DIR = PROCESSED_DIR / "txts"
PROCESSED_JSONS_DIR = PROCESSED_DIR / "jsons"


project_dir = os.getcwd()
ignore_filenames = pd.read_csv("ignore_filenames.csv").values
arxiv_citations_list = []

if os.path.exists("arxiv_dict_updated.json"):
    arxiv_dict = json.load(open("arxiv_dict_updated.json"))
else:
    arxiv_dict = {}

# arxiv_citations_dict looks like this:
# {root_paper_id_1: [citation_paper_id_1, citation_paper_id_2, ...],
# root_paper_id_2: [citation_paper_id_1, citation_paper_id_2, ...], ...}
# The dictionary is updated in the prepare_extracted_tars function.
if os.path.exists("arxiv_citations_dict.json"):
    arxiv_citations_dict = json.load(open("arxiv_citations_dict.json"))
else:
    arxiv_citations_dict = {}
    json.dump(arxiv_citations_dict, open("arxiv_citations_dict.json", "w"))

pool = mp.Pool(processes=mp.cpu_count())


def fix_chars_in_dirs(parent):
    for path, folders, files in os.walk(parent):
        for f in files:
            os.rename(os.path.join(path, f), os.path.join(path, f.replace(" ", "_")))
        for folder in folders:
            new_folder_name = folder.translate(
                {ord(c): "_" for c in " !@#$%^&*()[]{};:,<>?\|`~-=+"}
            )
            if new_folder_name != folder:
                os.rename(
                    os.path.join(path, folder), os.path.join(path, new_folder_name)
                )


def prepare_extracted_tars(paper_dir_path):
    # extracts tar files to tmp/{dump_name}/*
    paper_id = paper_dir_path.split("/")[-1]
    try:
        # load arxiv_citations_dict json to add citations to paper_id
        arxiv_citations_dict = json.load(open("arxiv_citations_dict.json"))
        try:
            for doc in lsr(paper_dir_path):
                if doc.endswith(".gz"):
                    sh(f"gunzip {doc}")
            for doc in lsr(paper_dir_path):
                if doc.endswith(".tar"):
                    # if tarfile, extract in {doc[:-3]}_extract folder and delete tarfile
                    sh(
                        f"mkdir -p {doc[:-3]}_extract && tar xf {doc[:-3]} -C {doc[:-3]}_extract"
                    )
                    sh(f"rm {doc[:-3]}")
        except:
            pass
        for doc in lsr(paper_dir_path):
            try:
                if doc.endswith(".tex"):
                    # if tex, do nothing and keep it
                    pass

                elif doc.endswith(".sty"):
                    # if sty, delete it since it causes issues with pandoc
                    # this file is a LaTeX Style document
                    # (commonly used for formatting for a specific journal/conference)
                    sh(f"rm {doc}")

                elif doc.endswith(".bbl") or doc.endswith(".bib"):
                    # if bbl, extract arxiv ids from citations, add to list, and delete bbl
                    arxiv_citations, bibliography = get_arxiv_ids(doc)
                    if len(arxiv_citations) > 0:
                        for arxiv_id in arxiv_citations:
                            if arxiv_citations_dict.get(paper_id) is None:
                                arxiv_citations_dict[paper_id] = {arxiv_id: True}
                            else:
                                arxiv_citations_dict[paper_id].update({arxiv_id: True})
                        json.dump(
                            arxiv_citations_dict, open("arxiv_citations_dict.json", "w")
                        )
                        id = paper_id.split("v")[0]  # remove version number
                        arxiv_dict[id]["arxiv_citations"] = arxiv_citations_dict[
                            paper_id
                        ]
                    if doc.endswith(".bbl"):
                        arxiv_dict[id]["bibliography_bbl"] = bibliography
                    elif doc.endswith(".bib"):
                        arxiv_dict[id]["bibliography_bib"] = bibliography
                    json.dump(arxiv_dict, open("arxiv_dict.json", "w"))

                # check if filename has no extension, this is likely a .tex file
                # if so, add .tex to the filename
                # these files are typically named with the arxiv id (e.g. 1801.01234)
                elif re.findall(
                    r"(\d{4}\.\d{4,5})", doc.split("/")[-1]
                ) != [] and not doc.endswith(".pdf"):
                    # add .tex to filename
                    sh(f"mv {doc} {doc}.tex")

                elif doc.endswith(".DS_Store"):
                    # delete .DS_Store files
                    sh(f"rm {doc}")

                else:
                    pass
                    # if not .tex or .bbl, just delete file
                    # sh(f"rm {doc}")
            except ExitCodeError:
                traceback.print_exc()
                print(f"Error deleting file: {doc}")
    except Exception:
        traceback.print_exc()
        print(f"Error deleting files in {paper_id}")


def delete_style_files(paper_dir_path):
    # delete all files with .sty extension
    for doc in lsr(paper_dir_path):
        if doc.endswith(".sty"):
            sh(f"rm {doc}")


if __name__ == "__main__":

    # Delete contents before starting?
    # This is useful when you are testing and want to start from scratch
    delete_contents = input("Delete data before starting? (y/n) ")
    if delete_contents == "y":
        are_you_sure = input("Are you sure? (y/n) ")
        if are_you_sure == "y":
            sh(f"rm -rf files errored fallback_needed {TARS_DIR}/")
    automatic_mode = input("Automatic mode? (y/n): ")

    citation_level = str(
        input(
            "Citation level? (0 = original, 1 = citation of original, 2 = citation of citation, etc.): "
        )
    )
    if citation_level != "0":
        print(
            f"Citation level is {citation_level}, so we'll create a CSV of the papers at that citation level."
        )
        all_citations = {}
        for paper_id in arxiv_citations_dict.keys():
            for citation in arxiv_citations_dict[paper_id].keys():
                all_citations[citation] = True
        all_citations = pd.DataFrame(list(all_citations.keys()))
        all_citations.to_csv(f"all_citations_level_{citation_level}.csv", index=False)
        print(f"Saved CSV of all citations at level {citation_level}.")
    if automatic_mode == "y":
        sh(f"rm -rf tmp")
    sh("mkdir -p tmp out outtxt errored fallback_needed files")
    sh(
        "mkdir -p fallback_needed/unknown_main_tex fallback_needed/pdf_only errored/pandoc_failures errored/unknown_errors"
    )
    sh(
        f"mkdir -p {RAW_DIR} {INTERIM_DIR} {PROCESSED_DIR} {TARS_DIR} {LATEX_DIR} {PDFS_DIR}"
    )
    sh(
        f"mkdir -p {PKLS_DIR} {EXTRACTED_TARS_DIR} {MERGE_TEX_DIR} {PROCESSED_TXTS_DIR} {PROCESSED_JSONS_DIR}"
    )
    # Automatic Mode will go through all the papers in files and try
    # to convert them to markdown.
    # Non-automatic mode will go through the errored papers one by one and
    # ask the use to fix the error in the tex file to fix the conversion error.
    if citation_level != "0" and automatic_mode == "y":
        if ls("out") != [] and ls("outtxt") != []:
            sh("mv out/* data/processed/txts/")
            sh("mv outtxt/* data/processed/txts/")

    dl_papers_answer = input("Download papers? (y/n): ")
    if dl_papers_answer == "y":
        arxiv_dict = download_arxiv_paper_tars(
            citation_level=citation_level, arxiv_dict=arxiv_dict
        )
    if ls("files") == []:
        sh(f"mv {TARS_DIR}/* files/")

    if automatic_mode == "y":
        paper_tars = ls("files")
        pool.map(preextract_tar, paper_tars)
        pool.close()
        pool.join()
        paper_folders = ls("tmp")
        for i, paper_folder in enumerate(tqdm(paper_folders)):
            print(f"{i}/{len(paper_folders)}")
            os.chdir(project_dir)
            done_paper_folder = "done/" + paper_folder.split("/")[-1]
            if os.path.exists(done_paper_folder):
                sh(f"rm -rf {paper_folder}")
                continue
            try:
                print(f"preparing {paper_folder}")
                fix_chars_in_dirs(paper_folder)
                prepare_extracted_tars(paper_folder)
                delete_style_files(
                    paper_folder
                )  # putting this here too to make sure they are deleted
                convert_tex(paper_dir=paper_folder, arxiv_dict=arxiv_dict)
                if os.path.exists(paper_folder):
                    sh(f"mv {paper_folder} done")
            except ExitCodeError:
                traceback.print_exc()
                print(f"Error converting {paper_folder}")

    if automatic_mode != "y":
        if ls("tmp") == []:
            for paper_folder in ls("errored/pandoc_failures/"):
                if os.path.isdir(paper_folder):
                    sh(f"mv {paper_folder} tmp")
        pandoc_failures = ls("tmp")
        for paper_folder in pandoc_failures:
            if os.path.isdir(paper_folder):
                for file in ls(paper_folder):
                    if file.endswith("_failed"):
                        sh(f"rm {file}")
        for i, paper_folder in enumerate(tqdm(pandoc_failures)):
            try:
                print(f'Converting errored papers: "{paper_folder}"')
                os.chdir(project_dir)
                paper_folder = os.getcwd() + "/" + paper_folder
                convert_tex_manual(paper_dir=paper_folder, arxiv_dict=arxiv_dict)
                sh(f"mv {paper_folder} done")
            except ExitCodeError:
                traceback.print_exc()

    mv_empty_mds()

    # TODO: Make the pandoc conversion work with multiprocessing
    # with mp.Manager() as manager:
    #     d = manager.dict()
    #     d.update(arxiv_dict)
    #     with manager.Pool() as pool:
    #         print(paper_folders)
    #         print(len(paper_folders))
    #         pool.starmap(convert_tex, zip(paper_folders, repeat(d, len(paper_folders))))
    # `d` is a DictProxy object that can be converted to dict
    # pprint.pprint(dict(d))

    # pool.map(convert_tex, paper_folders, initargs=(arxiv_dict,))
    # pool.close()
    # pool.join()
    print("Finished converting all papers.")
    print("Updating arxiv_dict.json...")
    # loop through files in out/ and outtxt/ and add to arxiv_dict
    for i, mdfile in enumerate(tqdm(ls("out"))):
        print(f"{i}/{len(ls('out'))}")
        try:
            mdfile = mdfile.split("/")[-1]
            id = mdfile.split("v")[0]
            with open(f"out/{mdfile}", "r") as f:
                text = f.read()
            arxiv_dict[id]["text"] = text
        except ExitCodeError and KeyError:
            traceback.print_exc()
            print(f"Error reading {mdfile}")

    for i, main_tex_name_txt in enumerate(tqdm(ls("outtxt"))):
        print(f"{i}/{len(ls('outtxt'))}")
        try:
            # load main_tex_name_txt
            with open(f"{main_tex_name_txt}", "r") as f:
                main_tex_name = f.read()
            arxiv_id = main_tex_name_txt.split("/")[-1].split("v")[0]
            arxiv_dict[arxiv_id]["main_tex_filename"] = main_tex_name.split("/")[-1]
        except ExitCodeError and KeyError:
            traceback.print_exc()
            print(f"Error reading {main_tex_name_txt}")

    arxiv_dict = remove_empty_mds_from_dict(arxiv_dict)
    json.dump(arxiv_dict, open("arxiv_dict_updated.json", "w"))
    print("Finished updating arxiv_dict_updated.json.")
