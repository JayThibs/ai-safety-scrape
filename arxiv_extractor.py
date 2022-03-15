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


sh("mkdir -p tmp out done fallback_needed errored && rm -rf tmp/*")
files = ls("tmp2")
ignore_filenames = pd.read_csv("ignore_filenames.csv").values
arxiv_citations_list = []

if os.path.exists("main_tex_dict.json"):
    main_tex_dict = json.load(open("main_tex_dict.json"))
else:
    main_tex_dict = {}

pool = mp.Pool(processes=mp.cpu_count())

if __name__ == "__main__":
    jobs = []
    for i in range(len(files)):
        print(f"{i}/{len(files)}")
        p = mp.Process(target=preextract_tar, args=(files[i], "tmp2", "tmp"))
        jobs.append(p)
        p.start()
        p.join()


def main_convert():
    for i in range(len(files)):
        print(f"{i}/{len(files)}")
        p = mp.Process(target=convert_tex, args=(files[i], "tmp2", "tmp"))
        jobs.append(p)
        p.start()
        p.join()


def fix_chars_in_dirs(paper_dir_path):
    # replace special characters in directories with underscores
    os.chdir(paper_dir_path)
    for doc in ls("."):
        if os.path.isdir(doc):
            new_doc_name = doc.translate(
                {ord(c): "_" for c in " !@#$%^&*()[]{};:,<>?\|`~-=+"}
            )
            if new_doc_name != doc:
                os.rename(doc, new_doc_name)


for paper_dir in os.listdir("tmp"):
    fix_chars_in_dirs("tmp/" + paper_dir)

for i, tar_filepath in enumerate(tqdm(files)):
    # extracts tar files to tmp/{dump_name}/*
    paper_id = tar_filepath.split("/")[-1][:-4]
    try:
        # this loop deletes all files in tmp that are not .tex files
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
                        sh(f"mv {doc[:-3]} {doc[:-3]}.tex")
                    elif type == "application/x-bbl":
                        # if bbl, keep it
                        sh(f"mv {doc[:-3]} {doc[:-3]}.bbl")
                    else:
                        # if not tar or tex, delete file
                        sh(f"rm {doc[:-3]}")

                elif doc.endswith(".tex"):
                    # if tex, do nothing and keep it
                    pass

                elif doc.endswith(".bbl"):
                    # if bbl, extract arxiv ids from citations, add to list, and delete bbl
                    arxiv_citations, bbl = get_arxiv_ids(doc)
                    arxiv_citations_list.extend(arxiv_citations)
                    main_tex_dict[paper_id]["bibliography"] = bbl
                    sh(f"rm {doc}")

                else:
                    # if not .tex, delete file
                    sh(f"rm {doc}")
            except ExitCodeError:
                traceback.print_exc()
                print(f"Error deleting file: {doc}")

        # process tex files
        print("Processing paper_id:", paper_id)
        print("Moving files to root folder...")
        mv_files_to_root()
        print("Converting paper...")
        convert_tex("tmp", paper_id, main_tex_dict)
        list_of_paper_folders = ls("tmp")
        pool.map(convert, list_of_paper_folders)

        sh(f"mv {dump} done")
        print(f"marking {dump} as done")
    except:
        sh(f"mv {dump} errored")
        pass
