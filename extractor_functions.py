import os
import re
import sys
import json
import chardet
from utils import *
from time import time
import traceback
import pickle


main_tex_name_list = [
    "main",
    "paper",
    "ms",
    "arxiv",
    "root",
    "example",
    "master",
    "sample",
]

main_tex_name_list = [f"{item}.tex" for item in main_tex_name_list]


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


def preextract_tar(tar_filepath, input_dir="files", output_dir="tmp"):
    """
    Creates tmp/{tar_name} directory and extracts tar files and copies them to tmp/tar_name/*.
    Creates tmp/done_{tar_name} file to signal copy_tar that extraction is done.
    """
    tar_name = tar_filepath.split("/")[-1][:-4]
    sh(
        f"(mkdir -p {output_dir}/{tar_name}; tar xf {tar_filepath} -C {output_dir}/{tar_name} && touch {input_dir}/done_{tar_name}; echo finished preload of {tar_name}) &"
    )


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


def convert_tex(
    paper_dir, output_dir="out", main_tex_output_dir="outtxt", arxiv_dict=None
):
    """
    Converts paper tex file automatically. Sends errors to fallback_needed for conversion with convert_tex_semiauto.
    This function is created to work with multiprocessing. paper_dir is the directory for a specific paper in tmp once
    we've extracted the tars in tmp. An example of paper_dir is "tmp/1708.03887v2".
    """
    os.chdir(paper_dir)
    project_dir = "/".join(os.getcwd().split("/")[:-2])
    paper_id = paper_dir.split("/")[-1]
    print("Current directory: " + os.getcwd())
    print("paper_id: " + paper_id)

    try:
        assert len(ls(".")) > 0
        convert_to_utf8(rootdir=".")
        tmp_contents = ls(".")
        num_tex_files = 0
        print(os.listdir())
        for doc in tmp_contents:
            if doc.endswith(".tex"):
                num_tex_files += 1
                tex_doc = doc
        if num_tex_files == 1:
            # if there is only one tex file, use it
            sh(f"timeout 7s pandoc -s {tex_doc} -o {paper_id}.md --wrap=none")
            os.chdir(project_dir)
            sh(f"mv {paper_dir}/{paper_id}.md {output_dir}/{paper_id}.md")
            # TODO: there's a better way to do this, but to make multiprocessing work,
            # I'm going to create a .txt file for each paper and store the main_tex_name in it.
            # This is a hacky way to do it, but it works. Once the extraction is done,
            # we can use the .txt file to get the main_tex_name and store it in the arxiv_dict.
            with open(f"{main_tex_output_dir}/{paper_id}.txt", "w") as f:
                f.write(tex_doc)
            return
        else:
            # if there are multiple tex files,
            # check for the main file based on a common list of names
            filenames_to_ignore = pickle.load(
                open(f"{project_dir}/ignore_dict.pkl", "rb")
            )
            matched_list = [
                (doc.split("/")[-1], doc.split(("/")[1:-1]))
                for name, doc in zip(main_tex_name_list, lsr("."))
                if name in doc.lower()
            ]
            if matched_list:
                main_doc, path_to_doc = matched_list[0]
                # change to that directory and use the common file name
                os.chdir(path_to_doc)
                sh(f"timeout 7s pandoc -s {main_doc} -o {paper_id}.md --wrap=none")
                # go back to root
                os.chdir(project_dir)
                print(f"Current directory: {os.getcwd()}")
                sh(f"mv {paper_dir}/{paper_id}.md {output_dir}/{paper_id}.md")
                with open(f"{main_tex_output_dir}/{paper_id}.txt", "w") as f:
                    f.write(main_doc)
                return
            else:
                list_of_tex_files = [
                    doc for doc in tmp_contents if doc.endswith(".tex")
                ]
                # if items in list_of_tex_files are in filenames_to_ignore, remove them
                matched_list = [
                    doc
                    for doc in list_of_tex_files
                    if doc.split("/")[-1].lower() not in filenames_to_ignore
                ]
                if len(matched_list) == 1:
                    main_doc, path_to_doc = matched_list[0]
                    # change to that directory and use the common file name
                    os.chdir(path_to_doc)
                    sh(f"timeout 7s pandoc -s {main_doc} -o {paper_id}.md --wrap=none")
                    # go back to root
                    os.chdir(project_dir)
                    print(f"Current directory: {os.getcwd()}")
                    sh(f"mv {paper_dir}/{paper_id}.md {output_dir}/{paper_id}.md")
                    with open(f"{main_tex_output_dir}/{paper_id}.txt", "w") as f:
                        f.write(main_doc)
                    return

            if arxiv_dict[paper_id]["main_tex_filename"] != "":
                # if main file was stored in arxiv_dict, use it
                # arxiv_dict is created when we need to use convert_tex_semiauto and manually inputting main tex filename
                main_tex = arxiv_dict[paper_id]["main_tex_filename"]
                sh(f"timeout 7s pandoc -s {main_tex} -o {paper_id}.md --wrap=none")
                os.chdir(project_dir)
                sh(f"mv {paper_dir}/{paper_id}.md out/{paper_id}.md")
                return
            else:
                # can't find main file, so send to fallback_needed for manual conversion with convert_tex_semiauto
                # it's useful to do it this way because then you can go through the fallback_needed folder and
                # manually convert the files in a batch
                print(
                    f"{paper_id} main filename not found in main_tex_dict, sending to fallback_needed"
                )
                os.chdir(project_dir)
                sh(f"mv {paper_dir} fallback_needed")
                return

    except ExitCodeError:
        traceback.print_exc()
        print("Error converting paper. Moving to fallback pile...")
        os.chdir(project_dir)
        print(f"Error: Current directory: {os.getcwd()}")
        sh(f"mv -f {paper_dir} fallback_needed")


def convert_tex_semiauto(rootdir="tmp", paper_id=None, arxiv_dict=None):
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
        convert_to_utf8(rotdir=".")
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
                if doc in main_tex_name_list:
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
                if paper_id in arxiv_dict:
                    # if main file was stored in main_tex_dict, use it
                    main_tex = arxiv_dict[paper_id]
                else:
                    # if there are multiple tex files
                    # and it's not in the above list: prompt user to select one
                    print("Multiple tex files found. Please select the main file: ")
                    main_tex = str(
                        input(
                            f"Enter the main .tex filename here, file extension included (e.g. AIProgress.tex): "
                        )
                    )
                    arxiv_dict[paper_id] = main_tex
                    os.chdir("..")
                    json.dump(arxiv_dict, open("main_tex_dict.json", "w"))
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
