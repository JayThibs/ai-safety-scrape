import os
import re
import sys
import json
import chardet
from utils import *
from time import time
import traceback
import pickle
from tika import parser


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

main_tex_name_substrings = ["nips", "iclr", "conference", "corl", "neurips", "icml"]

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
    if os.path.exists(f"{output_dir}/{tar_name}"):
        print(f"{tar_name} already extracted.")
        return
    sh(
        f"(mkdir -p {output_dir}/{tar_name}; tar xf {tar_filepath} -C {output_dir}/{tar_name}; echo finished preload of {tar_name}) &"
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
    paper_dir,
    arxiv_dict,
    output_dir="out",
    main_tex_output_dir="outtxt",
    manual_conversion=False,
):
    """
    Converts paper tex file automatically. Sends errors to fallback_needed for conversion with convert_tex_semiauto.
    This function is created to work with multiprocessing. paper_dir is the directory for a specific paper in tmp once
    we've extracted the tars in tmp. An example of paper_dir is "tmp/1708.03887v2".
    """

    try:
        paper_id = paper_dir.split("/")[-1]
        if os.path.exists(f"{output_dir}/{paper_id}.md"):
            print(f"{paper_id}.md already exists.")
            sh(f"mv {paper_dir} done")
            return
        os.chdir(paper_dir)
        paper_dir_full = os.getcwd()
        project_dir = "/".join(os.getcwd().split("/")[:-2])
        number_id = str(paper_id.split("v")[0])
        print("Current directory: " + os.getcwd())
        print("paper_id: " + paper_id)
        assert len(ls(".")) > 0
        convert_to_utf8(rootdir=".")
        paper_dir_root = ls(".")
        paper_dir_all_files = lsr(".")
        num_tex_files = num_pdf_files = root_tex_files = 0
        print(os.listdir())
        main_pdf = None
        for file in paper_dir_all_files:
            if file.endswith(".tex"):
                num_tex_files += 1
            elif file.endswith(".pdf"):
                if re.findall(r"(\d{4}\.\d{4,5})", file):
                    main_pdf = file
                num_pdf_files += 1
        if num_pdf_files > 0 and num_tex_files == 0:
            print("Paper only contains PDF. Not LaTeX files. Skipping conversion.")
            os.chdir(project_dir)
            arxiv_dict[number_id]["source_filetype"] = "pdf"
            arxiv_dict[number_id]["converted_with"] = ""
            json.dump(arxiv_dict, open("arxiv_dict.json", "w"))
            sh(f"mv -f {paper_dir} fallback_needed/pdf_only")
            return
        for doc in paper_dir_root:
            if doc.endswith(".tex"):
                root_tex_files += 1
                main_doc = doc
        if root_tex_files == 1:
            # if there is only one tex file, use it
            sh(
                f"if ! timeout 7s pandoc -s {main_doc} -o {paper_id}.md --wrap=none; then touch {paper_id}_pandoc_failed; fi"
            )
            if os.path.exists(f"{paper_id}_pandoc_failed") and not manual_conversion:
                print(f"{paper_id} failed to convert with pandoc.")
                os.chdir(project_dir)
                if not manual_conversion:
                    sh(f"mv -f {paper_dir} errored/pandoc_failures/")
                return
            if not manual_conversion:
                with open(f"{paper_id}.md", "r") as f:
                    paper_text = f.read()
                arxiv_dict[number_id]["text"] = paper_text
                arxiv_dict[number_id]["main_tex_filename"] = main_doc
                json.dump(arxiv_dict, open(f"{project_dir}/arxiv_dict.json", "w"))
                os.chdir(project_dir)
                sh(f"mv {paper_dir}/{paper_id}.md {output_dir}/{paper_id}.md")
                # TODO: there's a better way to do this, but to make multiprocessing work,
                # I'm going to create a .txt file for each paper and store the main_tex_name in it.
                # This is a hacky way to do it, but it works. Once the extraction is done,
                # we can use the .txt file to get the main_tex_name and store it in the arxiv_dict.
                with open(f"{main_tex_output_dir}/{paper_id}.txt", "w") as f:
                    f.write(main_doc)
                return
            else:
                return main_doc
        else:
            # if there are multiple tex files,
            # check for the main file based on a common list of names
            filenames_to_ignore = pickle.load(
                open(f"{project_dir}/ignore_dict.pkl", "rb")
            )
            print(filenames_to_ignore)
            os.chdir(paper_dir_full)
            list_of_tex_files = [
                doc.split("/")[-1] for doc in ls(".") if doc.endswith(".tex")
            ]
            print(list_of_tex_files)
            print(main_tex_name_list)
            matched_list = [
                doc for doc in list_of_tex_files if doc.lower() in main_tex_name_list
            ]
            if len(matched_list) == 0:
                # if there are no matches with main list, try substring list
                # these are typically conference names with a lot of variations (e.g. "icml2020.tex")
                for tex_substring in main_tex_name_substrings:
                    matched_list = [
                        doc for doc in list_of_tex_files if tex_substring in doc.lower()
                    ]
                    if len(matched_list) > 0:
                        break
            print(matched_list)
            if matched_list:
                main_doc = matched_list[0]
                # change to that directory and use the common file name
                sh(
                    f"if ! timeout 7s pandoc -s {main_doc} -o {paper_id}.md --wrap=none; then touch {paper_id}_pandoc_failed; fi"
                )
                if (
                    os.path.exists(f"{paper_id}_pandoc_failed")
                    and not manual_conversion
                ):
                    print(f"{paper_id} failed to convert with pandoc.")
                    os.chdir(project_dir)
                    if not manual_conversion:
                        sh(f"mv -f {paper_dir} errored/pandoc_failures/")
                    return
                if not manual_conversion:
                    with open(f"{paper_id}.md", "r") as f:
                        paper_text = f.read()
                    arxiv_dict[number_id]["text"] = paper_text
                    arxiv_dict[number_id]["main_tex_filename"] = main_doc
                    json.dump(arxiv_dict, open(f"{project_dir}/arxiv_dict.json", "w"))
                    # go back to root
                    os.chdir(project_dir)
                    sh(f"mv {paper_dir}/{paper_id}.md {output_dir}/{paper_id}.md")
                    with open(f"{main_tex_output_dir}/{paper_id}.txt", "w") as f:
                        f.write(main_doc)
                    return
                else:
                    return main_doc
            else:
                os.chdir(paper_dir_full)
                list_of_tex_files = [
                    doc.split("/")[-1] for doc in ls(".") if doc.endswith(".tex")
                ]
                # if items in list_of_tex_files are in filenames_to_ignore, remove them
                matched_list = [
                    doc
                    for doc in list_of_tex_files
                    if doc.lower() not in filenames_to_ignore
                ]
                print(matched_list)
                if len(matched_list) == 1:
                    main_doc = matched_list[0]
                    # change to that directory and use the common file name
                    sh(
                        f"if ! timeout 7s pandoc -s {main_doc} -o {paper_id}.md --wrap=none; then touch {paper_id}_pandoc_failed; fi"
                    )
                    if (
                        os.path.exists(f"{paper_id}_pandoc_failed")
                        and not manual_conversion
                    ):
                        print(f"{paper_id} failed to convert with pandoc.")
                        os.chdir(project_dir)
                        if not manual_conversion:
                            sh(f"mv -f {paper_dir} errored/pandoc_failures/")
                        return
                    if not manual_conversion:
                        with open(f"{paper_id}.md", "r") as f:
                            paper_text = f.read()
                        arxiv_dict[number_id]["text"] = paper_text
                        arxiv_dict[number_id]["main_tex_filename"] = main_doc
                        json.dump(
                            arxiv_dict, open(f"{project_dir}/arxiv_dict.json", "w")
                        )
                        # go back to root
                        os.chdir(project_dir)
                        sh(f"mv {paper_dir}/{paper_id}.md {output_dir}/{paper_id}.md")
                        with open(f"{main_tex_output_dir}/{paper_id}.txt", "w") as f:
                            f.write(main_doc)
                        return
                    else:
                        return main_doc

                if arxiv_dict[number_id]["main_tex_filename"] != "":
                    # if main file was stored in arxiv_dict, use it
                    # arxiv_dict is created when we need to use convert_tex_semiauto and manually inputting main tex filename
                    main_tex = arxiv_dict[number_id]["main_tex_filename"]
                    sh(
                        f"if ! timeout 7s pandoc -s {main_doc} -o {paper_id}.md --wrap=none; then touch {paper_id}_pandoc_failed; fi"
                    )
                    if (
                        os.path.exists(f"{paper_id}_pandoc_failed")
                        and not manual_conversion
                    ):
                        print(f"{paper_id} failed to convert with pandoc.")
                        os.chdir(project_dir)
                        if not manual_conversion:
                            sh(f"mv -f {paper_dir} errored/pandoc_failures/")
                        return
                    if not manual_conversion:
                        with open(f"{paper_id}.md", "r") as f:
                            paper_text = f.read()
                        arxiv_dict[number_id]["text"] = paper_text
                        json.dump(
                            arxiv_dict, open(f"{project_dir}/arxiv_dict.json", "w")
                        )
                        os.chdir(project_dir)
                        sh(f"mv {paper_dir}/{paper_id}.md out/{paper_id}.md")
                        return
                    else:
                        return main_tex
                else:
                    # can't find main file, so send to fallback_needed for manual conversion with convert_tex_semiauto
                    # it's useful to do it this way because then you can go through the fallback_needed folder and
                    # manually convert the files in a batch
                    print(
                        f"{paper_id} main filename not found in main_tex_dict, sending to fallback_needed"
                    )
                    os.chdir(project_dir)
                    sh(f"mv -f {paper_dir} fallback_needed/unknown_main_tex/")
                    return

    except:
        try:
            traceback.print_exc()
            if not manual_conversion:
                with open(f"error_log.txt", "a") as f:
                    f.write(f"{traceback.format_exc()}")
                with open(f"{project_dir}/error_log.txt", "a") as f:
                    f.write(f"{paper_id}\n {traceback.format_exc()}\n")
                print("Error converting paper. Moving to fallback pile...")
                os.chdir(project_dir)
                print(f"Error: Current directory: {os.getcwd()}")
                if os.path.exists(f"{paper_dir}_pandoc_failure"):
                    sh(f"mv -f {paper_dir} errored/pandoc_failures/")
                else:
                    sh(f"mv -f {paper_dir} errored/unknown_errors/")
                pass
        except:
            traceback.print_exc()
            print("Error moving paper to fallback pile.")
            pass


def convert_tex_manual(paper_dir, arxiv_dict):
    """
    Puts papers from fallback_needed/pandoc_failures in a queue to be
    converted with convert_tex_manual. This function is run when pandoc fails
    to convert a paper. This is typically because of some missing braces or brackets
    in the tex file. You will need to go into the main tex file and manually
    fix the issue in the file. convert_tex will be ran once in order to show you
    the error so that it's a bit clearer what you need to fix.
    Then, click enter in the terminal to continue.
    """
    fixed_error = False
    while fixed_error == False:
        try:
            main_doc = convert_tex(paper_dir, arxiv_dict, manual_conversion=True)
        except:
            print("Error converting the paper. Please fix the error in the tex file.")
            traceback.print_exc()
            pass

        print("Was the error fixed? (y/n)")
        answer = input()
        if answer == "y":
            fixed_error = True
            break
        else:
            print(f"Opening {main_doc} in text editor. Please fix the error.")
            sh(f"open {main_doc}")
            input("Press enter once you have fixed the error and fixed the tex file.")
            continue


def get_arxiv_ids(bib_file_path):
    with open(bib_file_path, "r") as f:
        bib_string = f.read()
    return re.findall(r"(?:arXiv:|abs/)(\d{4}\.\d{4,5})", bib_string), bib_string
