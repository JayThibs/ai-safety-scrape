import os
import re
import json
import chardet
from utils import *
from time import time
import traceback


def any_to_utf8(b):
    """Detects encoding and converts to utf-8."""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        # try to figure out encoding if not utf-8
        guess = chardet.detect(b)["encoding"]
        if not guess or guess == "UTF-8":
            return
        try:
            return b.decode(guess)
        except (UnicodeDecodeError, LookupError):
            # still cant figure out encoding, give up
            return


def convert_to_utf8(rootdir="."):
    """Converts all files in root folder to utf-8."""
    for doc in ls(rootdir):
        if doc.endswith(".tex"):
            try:
                with open(doc, "rb") as fh:
                    b = fh.read()
                    cont = any_to_utf8(b)
                    if cont is None:
                        return
                fwrite(doc, cont)
            except ExitCodeError:
                traceback.print_exc()
                print(f"Error converting {doc}, will go to /fallback_needed.")
                print("Error converting files to utf-8.")


def preextract_tar(dump):
    """
    Creates tmp2/{dump_name} directory and extracts tar files and copies them to tmp2/dump_name/*.
    Creates tmp2/done_{dump_name} file to signal copy_tar that extraction is done.
    """
    dump_name = dump.split("/")[-1][:-4]
    sh(
        f"(mkdir -p tmp2/{dump_name}; tar xf {dump} -C tmp2/{dump_name} && touch tmp2/done_{dump_name}; echo finished preload of {dump_name}) &"
    )


def copy_tar(dump):
    """Copies tar files from tmp2/{dump_name}/* to tmp/."""
    dump_name = dump.split("/")[-1][:-4]
    # print(dump_name)
    for i in range(120):
        if os.path.exists(f"tmp2/done_{dump_name}"):
            sh(f"mv tmp2/{dump_name}/* tmp")
            return True
        print("waiting for tar...")
        time.sleep(1)

    return False


def mv_files_to_root(rootdir="tmp"):
    """Moves all files in root folder subdirectories to root folder."""
    for doc in ls(rootdir):
        try:
            if os.path.isdir(doc):
                sh(f"find ./{doc} -type f -print0 | xargs -0 mv -t .")
                sh(f"rm -rf {doc}")
        except ExitCodeError:
            traceback.print_exc()
            print(
                "Error moving files to root folder. Likely because there's a file with the same name in the root folder."
            )


def convert_semiauto(rootdir="tmp", paper_id=paper_id, main_tex_dict=main_tex_dict):
    """
    Converts paper tex files semi-automatically. If there are multiple tex files,
    it will check for a list of common "main" file names and use the first one found.
    If there are multiple .tex files and it cannot find a main file, you will be prompted
    to select one.
    """
    print('Changing current directory to "tmp"...')
    os.chdir(rootdir)
    main_match = False
    print("Current directory: " + os.getcwd())
    print("paper_id: " + paper_id)

    try:
        assert len(ls(".")) > 0
        convert_to_utf8(rootdir=".")
        if len(ls(".")) == 1:
            # if there is only one tex file, just convert it
            main_match = True
            doc = ls(".")[0].split("/")[-1]
            sh(f"timeout 7s pandoc -s {doc} -o {paper_id}.md --wrap=none")
        else:
            # if there are multiple tex files,
            # check for the main file based on a common list of names
            for doc in ls("."):
                doc = doc.split("/")[-1][:-4]
                # print(doc)
                if doc in [
                    "main",
                    "Main",
                    "MAIN",
                    "_main",
                    "paper",
                    "Paper",
                    "PAPER",
                    "ms",
                    "arxiv",
                    "arXiv",
                    "example_paper",
                    "root",
                    "example",
                    "00_main",
                    "00_Main",
                    "00-Main",
                    "00-main",
                    "main_arxiv",
                    "main_arXiv",
                    "main-arxiv",
                    "main-arXiv",
                    "Main-arXiv",
                    "master",
                    "Master",
                ]:
                    # if there is a common main file name, use it
                    main_match = True
                    sh(f"timeout 7s pandoc -s {doc}.tex -o {paper_id}.md --wrap=none")
                    break
        if not main_match:
            tmp_contents = os.listdir()
            num_tex_files = 0
            print(os.listdir())
            for doc in tmp_contents:
                if doc.endswith(".tex"):
                    num_tex_files += 1
                    tex_doc = doc
            if num_tex_files == 1:
                # if there is only one tex file, use it
                sh(f"timeout 7s pandoc -s {tex_doc} -o {paper_id}.md --wrap=none")
            else:
                if paper_id in main_tex_dict:
                    # if main file was stored in main_tex_dict, use it
                    main_tex = main_tex_dict[paper_id]
                else:
                    # if there are multiple tex files
                    # and it's not in the above list: prompt user to select one
                    print("Multiple tex files found. Please select the main file: ")
                    main_tex = str(
                        input(
                            f"Enter the main .tex filename here, file extension included (e.g. AIProgress.tex): "
                        )
                    )
                    main_tex_dict[paper_id] = main_tex
                    os.chdir("..")
                    json.dump(main_tex_dict, open("main_tex_dict.json", "w"))
                    os.chdir(rootdir)

                sh(f"timeout 7s pandoc -s {main_tex} -o {paper_id}.md --wrap=none")

        os.chdir("..")
        print("Current directory: " + os.getcwd())
        sh(f"mv tmp/{paper_id}.md out/{paper_id}.md")

    except:
        traceback.print_exc()
        print("Error converting paper. Moving to fallback pile...")
        if os.getcwd().split("/")[-1] == "tmp":
            os.chdir("..")
        # fallback:
        try:
            # move to fallback pile so we can handle it later
            sh(
                f"mkdir -p fallback_needed/{paper_id} && mv tmp/* fallback_needed/{paper_id}/"
            )
        except ExitCodeError:
            traceback.print_exc()

        assert os.path.exists(f"out/{paper_id}.md")  # to send tar to errored pile


def get_arxiv_ids(bib_file_path):
    with open(bib_file_path, "r") as f:
        bib_string = f.read()
    return re.findall(r"(?:arXiv:|abs/)(\d{4}\.\d{4,5})", bib_string), bib_string
