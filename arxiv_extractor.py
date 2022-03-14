import os
import re
from utils import *
import magic

mime = magic.Magic(mime=True)
import multiprocessing as mp
import chardet
import time
from tqdm import tqdm
import json
import pandas as pd
import traceback


sh("mkdir -p tmp out done fallback_needed errored && rm -rf tmp/*")
files = ls("files")
ignore_filenames = pd.read_csv("ignore_filenames.csv").values
arxiv_citations_list = []

if os.path.exists("main_tex_dict.json"):
    main_tex_dict = json.load(open("main_tex_dict.json"))
else:
    main_tex_dict = {}

pool = mp.Pool(processes=mp.cpu_count())

def worker():
    """worker function"""
    print 'Worker'
    return

if __name__ == '__main__':
    jobs = []
    for i in range(len(files)):
        p = mp.Process(target=preextract_tar, args=(files[i],))
        jobs.append(p)
        p.start()
        p.join()
        print(f"{i}/{len(files)}")


for i, dump in enumerate(tqdm(files)):
    # extracts tar files to tmp/{dump_name}/*

    paper_id = dump.split("/")[-1][:-4]
    try:
        # clear tmp every loop to process only one set of .tex files at a time
        sh("rm -rf tmp/*")
        if not copy_tar(dump):
            # if tmp2/done_{dump_name} is not created, skip this dump
            continue
        # extract
        # print(dump)
        sh(f"tar xf {dump} -C tmp")
        # replace special characters in file names with underscores
        os.chdir("tmp")
        for doc in os.listdir():
            # print(doc)
            if os.path.isdir(doc):
                new_doc_name = doc.translate(
                    {ord(c): "_" for c in " !@#$%^&*()[]{};:,<>?\|`~-=+"}
                )
                if new_doc_name != doc:
                    os.rename(doc, new_doc_name)
        os.chdir("..")
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
        convert_semiauto("tmp", paper_id, main_tex_dict)
        list_of_paper_folders = ls("tmp")
        pool.map(convert, list_of_paper_folders)

        sh(f"mv {dump} done")
        print(f"marking {dump} as done")
    except:
        sh(f"mv {dump} errored")
        pass
