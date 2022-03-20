import os
from timeit import repeat
from utils import *
from extractor_functions import *
import magic

mime = magic.Magic(mime=True)
import multiprocessing as mp
from itertools import repeat
from tqdm import tqdm
import json
import pandas as pd
import traceback


sh(
    "mkdir -p tmp out outtxt errored fallback_needed && rm -rf fallback_needed/* && rm -rf out/* && rm -rf error_log.txt && rm -rf errored/*"
)
sh(
    "mkdir -p fallback_needed/unknown_main_tex fallback_needed/pdf_only errored/pandoc_failures errored/unknown_errors"
)
files = ls("files")
ignore_filenames = pd.read_csv("ignore_filenames.csv").values
arxiv_citations_list = []

if os.path.exists("arxiv_dict.json"):
    arxiv_dict = json.load(open("arxiv_dict.json"))
else:
    arxiv_dict = {}

if os.path.exists("arxiv_citations_dict.json"):
    arxiv_citations_dict = json.load(open("arxiv_citations_dict.json"))
else:
    arxiv_citations_dict = {}
    json.dump(arxiv_citations_dict, open("arxiv_citations_dict.json", "w"))

pool = mp.Pool(processes=mp.cpu_count())


def fix_chars_in_dirs(paper_dir_path):
    # replace special characters in directories with underscores
    os.chdir(paper_dir_path)
    print(f"fixing {paper_dir_path}")
    for doc in ls("."):
        if os.path.isdir(doc):
            new_doc_name = doc.translate(
                {ord(c): "_" for c in " !@#$%^&*()[]{};:,<>?\|`~-=+"}
            )
            if new_doc_name != doc:
                os.rename(doc, new_doc_name)

    chdir_up_n(2)
    print(f"finished fixing {paper_dir_path}")


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

                elif doc.endswith(".sty"):
                    # if sty, delete it since it causes issues with pandoc
                    # this file is a LaTeX Style document
                    # (commonly used for formatting for a specific journal/conference)
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


def main_convert(paper_dir_path):
    for i in range(len(files)):
        print(f"{i}/{len(files)}")
        p = mp.Process(target=convert_tex, args=(paper_dir, "md", "out"))

    sh(f"mv {dump} done")
    print(f"marking {dump} as done")


if __name__ == "__main__":

    paper_tars = ls("files")
    pool.map(preextract_tar, paper_tars)
    pool.close()
    pool.join()
    paper_folders = ls("tmp")
    for i, paper_folder in enumerate(tqdm(paper_folders)):
        print(f"{i}/{len(paper_folders)}")
        try:
            print(f"preparing {paper_folder}")
            fix_chars_in_dirs(paper_folder)
            prepare_extracted_tars(paper_folder)
            convert_tex(paper_dir=paper_folder, arxiv_dict=arxiv_dict)
        except ExitCodeError:
            traceback.print_exc()
            print(f"Error converting {paper_folder}")
            sh(f"mv {paper_folder} errored/unknown_errors")

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
            with open(f"{mdfile}", "rb") as f:
                mdtext = f.read()
            mdtext = any_to_utf8(mdtext)
            print(f"{mdtext}")
            arxiv_id = ".".join(mdfile.split("/")[-1].split(".")[0:2]).split("v")[0]
            arxiv_dict[arxiv_id]["text"] = mdtext.split("/")[-1]
        except ExitCodeError and KeyError:
            traceback.print_exc()
            print(f"Error reading {mdfile}")

    for i, main_tex_name_txt in enumerate(tqdm(ls("outtxt"))):
        print(f"{i}/{len(ls('outtxt'))}")
        try:
            # load main_tex_name_txt
            with open(f"{main_tex_name_txt}", "rb") as f:
                main_tex_name = f.read()
            main_tex_name = any_to_utf8(main_tex_name)
            print(f"{main_tex_name}")
            arxiv_id = ".".join(main_tex_name_txt.split("/")[-1].split(".")[0:2]).split(
                "v"
            )[0]
            arxiv_dict[arxiv_id]["main_tex_filename"] = main_tex_name.split("/")[-1]
        except ExitCodeError and KeyError:
            traceback.print_exc()
            print(f"Error reading {main_tex_name_txt}")

    print(arxiv_dict[arxiv_id])
    json.dump(arxiv_dict, open("arxiv_dict_updated.json", "w"))
    print("Finished updating arxiv_dict.json.")
