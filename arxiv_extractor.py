import os
from utils import *
from extractor_functions import *
import magic

mime = magic.Magic(mime=True)
import multiprocessing as mp
from tqdm import tqdm
import json
import pandas as pd
import traceback
import logging


sh(
    "mkdir -p tmp out done fallback_needed errored && rm -rf tmp/* && rm -rf fallback_needed/*"
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
        print(doc)
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
    # this loop deletes all files in tmp that are not .tex files
    try:
        for doc in lsr("tmp"):
            # print(doc)
            try:
                if doc.endswith(".gz"):
                    sh(f"gunzip {doc}")
                    type = mime.from_file(doc[:-3])
                    if type == "application/x-tar":
                        # if tarfile, extract in {doc[:-3]}_extract folder and delete tarfile
                        sh(
                            f"mkdir -p {doc[:-3]}_extract && tar xf {doc[:-3]} -C {doc[:-3]}_extract"
                        )
                        sh(f"rm {doc[:-3]}")
                    elif type == "text/x-tex":
                        # if tex, keep it
                        pass
                    elif type == "application/x-bbl":
                        # if bbl, keep it
                        pass
                    else:
                        # if not tar or tex, delete file
                        sh(f"rm {doc[:-3]}")

                elif doc.endswith(".tex"):
                    # if tex, do nothing and keep it
                    pass

                elif doc.endswith(".bbl"):
                    # if bbl, extract arxiv ids from citations, add to list, and delete bbl
                    arxiv_citations, bbl = get_arxiv_ids(doc)
                    # load arxiv_citations_dict json and overwrite with new citations
                    arxiv_citations_dict = json.load(open("arxiv_citations_dict.json"))
                    for arxiv_id in arxiv_citations:
                        if arxiv_citations_dict.get(arxiv_id) is None:
                            arxiv_citations_dict[arxiv_id] = [paper_id]
                        else:
                            arxiv_citations_dict[arxiv_id].append(paper_id)
                    json.dump(
                        arxiv_citations_dict, open("arxiv_citations_dict.json", "w")
                    )
                    main_tex_dict[paper_id] = {}
                    main_tex_dict[paper_id]["bibliography"] = bbl
                    json.dump(main_tex_dict, open("main_tex_dict.json", "w"))

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
    paper_folders = ls("tmp")
    pool.close()
    pool.join()
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
            sh(f"mv {paper_folder} fallback_needed")
