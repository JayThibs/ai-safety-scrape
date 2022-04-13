import os
import re
import chardet
from download_papers import download_arxiv_paper_tars
import arxiv
import pickle
from utils import *
from fix_empty_conversions import (
    mv_empty_mds,
    remove_empty_mds_from_dict,
    remove_empty_texts_from_dict,
)
from extractor_functions import *
import magic

mime = magic.Magic(mime=True)
from tqdm import tqdm
import json
import pandas as pd
import traceback
from pathlib import Path
import multiprocessing as mp


class ArxivPapers:
    def __init__(self, papers_csv_path="ai-alignment-papers.csv"):
        self.papers_csv_path = papers_csv_path

    def fetch_entries(self):
        """
        Fetch all the arxiv entries from the arxiv API.
        """
        print("Setting up directory structure...")
        self.setup()
        print("Downloading all source files for arxiv entries...")
        dl_papers_answer = input("Download papers? (y/n): ")
        if dl_papers_answer == "y":
            self.arxiv_dict = download_arxiv_paper_tars(
                citation_level=self.citation_level, arxiv_dict=self.arxiv_dict
            )
        if ls("files") == []:
            sh(f"mv {self.TARS_DIR}/* files/")
        print("Extracting text and citations from arxiv entries...")

        if automatic_mode == "y":
            self.automatic_extraction()

        if automatic_mode != "y":
            self.manual_extraction()

        mv_empty_mds()
        self.arxiv_dict = remove_empty_mds_from_dict(self.arxiv_dict)
        self.arxiv_dict = remove_empty_texts_from_dict(self.arxiv_dict)
        print("Done extracting text and citations from arxiv entries.")

    def setup(self):

        self.PROJECT_DIR = os.getcwd()
        self.RAW_DIR = Path("data/raw")
        self.INTERIM_DIR = Path("data/interim")
        self.PROCESSED_DIR = Path("data/processed")
        self.TARS_DIR = self.RAW_DIR / "tars"
        self.LATEX_DIR = self.RAW_DIR / "latex_files"
        self.PDFS_DIR = self.INTERIM_DIR / "pdfs"
        self.PKLS_DIR = self.INTERIM_DIR / "pkls"
        self.PROCESSED_TXTS_DIR = self.PROCESSED_DIR / "txts"
        self.PROCESSED_JSONS_DIR = self.PROCESSED_DIR / "jsons"

        if os.path.exists("arxiv_dict_updated.json"):
            self.arxiv_dict = json.load(open("arxiv_dict_updated.json"))
        else:
            self.arxiv_dict = {}

        # arxiv_citations_dict looks like this:
        # {root_paper_id_1: [citation_paper_id_1, citation_paper_id_2, ...], ...}
        # root_paper_id_2: [citation_paper_id_1, citation_paper_id_2, ...], ...}
        # The dictionary is updated in the prepare_extracted_tars function.
        if os.path.exists("arxiv_citations_dict.json"):
            self.arxiv_citations_dict = json.load(open("arxiv_citations_dict.json"))
        else:
            self.arxiv_citations_dict = {}
            json.dump(self.arxiv_citations_dict, open("arxiv_citations_dict.json", "w"))

        if not os.path.exists("ignore_dict.pkl"):
            sh("python filenames_to_ignore.py")

        delete_unwanted_files = input("Delete unwanted files? (y/n) ")
        if delete_unwanted_files == "y":
            sh("rm -rf files")

        # Delete contents before starting?
        # This is useful when you are testing and want to start from scratch
        delete_contents = input("Delete data before starting? (y/n) ")
        if delete_contents == "y":
            are_you_sure = input("Are you sure? (y/n) ")
            if are_you_sure == "y":
                sh(f"rm -rf files errored fallback_needed {self.TARS_DIR}/")
        self.automatic_mode = input("Automatic mode? (y/n): ")

        self.citation_level = str(
            input(
                "Citation level? (0 = original, 1 = citation of original, 2 = citation of citation, etc.): "
            )
        )
        remove_empty_papers = input(
            "Remove papers that text extraction did not work from the json? (y/n) "
        )
        if self.citation_level != "0":
            pass

        if self.automatic_mode == "y":
            sh(f"rm -rf tmp")
        sh("mkdir -p tmp out outtxt errored fallback_needed files")
        sh(
            "mkdir -p fallback_needed/unknown_main_tex fallback_needed/pdf_only errored/pandoc_failures errored/unknown_errors"
        )
        sh(
            f"mkdir -p {self.RAW_DIR} {self.INTERIM_DIR} {self.PROCESSED_DIR} {self.TARS_DIR} {self.LATEX_DIR} {self.PDFS_DIR}"
        )
        sh(
            f"mkdir -p {self.PKLS_DIR} {self.PROCESSED_TXTS_DIR} {self.PROCESSED_JSONS_DIR}"
        )
        # Automatic Mode will go through all the papers in files and try
        # to convert them to markdown.
        # Non-automatic mode will go through the errored papers one by one and
        # ask the use to fix the error in the tex file to fix the conversion error.
        if self.citation_level != "0" and self.automatic_mode == "y":
            if ls("out") != [] and ls("outtxt") != []:
                sh("mv out/* data/processed/txts/")
                sh("mv outtxt/* data/processed/txts/")

        self._create_citations_csv()

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

        self.main_tex_name_substrings = [
            "nips",
            "iclr",
            "conference",
            "corl",
            "neurips",
            "icml",
        ]

        self.main_tex_name_list = [f"{item}.tex" for item in main_tex_name_list]

    def download_arxiv_paper_tars(
        self,
        citation_level="0",
        arxiv_dict={},
        create_dict_only=False,
    ):
        """
        Download arxiv paper tars.
        Args:
            citation_level: 0 = original, 1 = citation of original, 2 = citation of citation, etc.
            create_dict_only: True or False
        """
        if citation_level == "0":
            df = pd.read_csv(self.papers_csv_path, index_col=0)
            df_arxiv = df[df["Url"].str.contains("arxiv") == True]
            papers = list(set(df_arxiv["Url"].values))
            print(f"{len(papers)} papers to download")
        else:
            df = pd.read_csv(f"all_citations_level_{citation_level}.csv", index_col=0)
            papers = list(set(list(df.index)))
            print(f"{len(papers)} papers to download")

        tars = ["None"] * len(papers)

        if ls(self.TARS_DIR):
            tars = [
                tar.split("/")[-1]
                for tar in ls(self.TARS_DIR)
                if tar.endswith(".tar.gz")
            ]
            if len(tars) != len(papers):
                # extend the tars list to match the length of the papers list
                tars = tars + ["None"] * (len(papers) - len(tars))

        incorrect_links_ids = []
        paper_dl_failures = []
        for i, (paper_link, filename) in enumerate(tqdm(zip(papers, tars))):
            paper_link = str(paper_link)
            filename = str(filename)
            paper_id = ".".join(filename.split(".")[:2])
            if (
                os.path.exists(str(self.TARS_DIR / filename))
                and create_dict_only == False
            ):
                print("Already downloaded the " + paper_id + " tar file.")
                continue

            try:
                if "/" in paper_link:
                    paper_id = paper_link.split("/")[-1]
                else:
                    paper_id = paper_link
                paper = next(arxiv.Search(id_list=[paper_id]).results())
                if (
                    citation_level != "0"
                    and paper.get_short_id()[:-2] in arxiv_dict.keys()
                ):
                    print(f"Skipping {paper_id} because it is already in dictionary.")
                    continue
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
                    "abstract": paper.summary.replace("\n", " "),
                    "author_comment": paper.comment,
                    "journal_ref": paper.journal_ref,
                    "doi": paper.doi,
                    "primary_category": paper.primary_category,
                    "categories": paper.categories,
                    "citation_level": citation_level,
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
                paper.download_source(dirpath=str(self.TARS_DIR), filename=tar_filename)
                print("; Downloaded paper: " + paper_id)
            except:
                print("; Could not download paper: " + paper_id)
                paper_dl_failures.append(paper_id)
                pass

        if incorrect_links_ids != []:
            print("Incorrect links:")
            print(incorrect_links_ids)
        if paper_dl_failures != []:
            print("Paper download failures:")
            print(paper_dl_failures)

        with open("arxiv_dict.json", "w") as fp:
            json.dump(arxiv_dict, fp)

        with open(self.PKLS_DIR / "arxiv_paper_tars_list.pkl", "wb") as f:
            pickle.dump(tars, f)

        with open(self.PKLS_DIR / "incorrect_links_ids_list.pkl", "wb") as f:
            pickle.dump(incorrect_links_ids, f)

        with open(self.PKLS_DIR / "paper_dl_failures_list.pkl", "wb") as f:
            pickle.dump(paper_dl_failures, f)

        return arxiv_dict

    def automatic_extraction(self):
        pool = mp.Pool(processes=mp.cpu_count())
        paper_tars = ls("files")
        pool.map(preextract_tar, paper_tars)
        pool.close()
        pool.join()
        paper_folders = ls("tmp")
        for i, paper_folder in enumerate(tqdm(paper_folders)):
            print(f"{i}/{len(paper_folders)}")
            os.chdir(self.PROJECT_DIR)
            done_paper_folder = "done/" + paper_folder.split("/")[-1]
            if os.path.exists(done_paper_folder):
                sh(f"rm -rf {paper_folder}")
                continue
            try:
                print(f"preparing {paper_folder}")
                self._fix_chars_in_dirs(paper_folder)
                self._prepare_extracted_tars(paper_folder)
                self._delete_style_files(
                    paper_folder
                )  # putting this here too to make sure they are deleted
                convert_tex(paper_dir=paper_folder, arxiv_dict=self.arxiv_dict)
                if os.path.exists(paper_folder):
                    sh(f"mv {paper_folder} done")
            except ExitCodeError:
                traceback.print_exc()
                print(f"Error converting {paper_folder}")

    def manual_extraction(self):
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
        for paper_folder in tqdm(pandoc_failures):
            try:
                print(f'Converting errored papers: "{paper_folder}"')
                os.chdir(self.PROJECT_DIR)
                paper_folder = os.getcwd() + "/" + paper_folder
                self.convert_tex_manual(
                    paper_dir=paper_folder, arxiv_dict=self.arxiv_dict
                )
                sh(f"mv {paper_folder} done")
            except ExitCodeError:
                traceback.print_exc()

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
                try:
                    sh(f"mv {paper_dir} done")
                except ExitCodeError:
                    traceback.print_exc()
                    print(f"Error moving {paper_dir} to done.")
                    sh(f"rm -rf {paper_dir}")
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
                if (
                    os.path.exists(f"{paper_id}_pandoc_failed")
                    and not manual_conversion
                ):
                    print(f"{paper_id} failed to convert with pandoc.")
                    os.chdir(project_dir)
                    if not manual_conversion:
                        sh(f"mv -f {paper_dir} errored/pandoc_failures/")
                    return
                if manual_conversion:
                    return main_doc
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
                    doc
                    for doc in list_of_tex_files
                    if doc.lower() in main_tex_name_list
                ]
                if len(matched_list) == 0:
                    # if there are no matches with main list, try substring list
                    # these are typically conference names with a lot of variations (e.g. "icml2020.tex")
                    for tex_substring in main_tex_name_substrings:
                        matched_list = [
                            doc
                            for doc in list_of_tex_files
                            if tex_substring in doc.lower()
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
                    if manual_conversion:
                        return main_doc
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
                        if manual_conversion:
                            return main_doc
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
                        if manual_conversion:
                            return main_doc
                        with open(f"{paper_id}.md", "r") as f:
                            paper_text = f.read()
                        arxiv_dict[number_id]["text"] = paper_text
                        json.dump(
                            arxiv_dict, open(f"{project_dir}/arxiv_dict.json", "w")
                        )
                        os.chdir(project_dir)
                        sh(f"mv {paper_dir}/{paper_id}.md out/{paper_id}.md")
                        return main_doc
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
        project_dir = os.getcwd()
        paper_id = paper_dir.split("/")[-1]
        while fixed_error == False:
            try:
                os.chdir(project_dir)
                sh(f"rm -f {paper_id}_pandoc_failed")
                main_doc = convert_tex(paper_dir, arxiv_dict, manual_conversion=True)
            except:
                print(
                    "Error converting the paper. Please fix the error in the tex file."
                )
                traceback.print_exc()
                pass

            print("Was the error fixed? (y/n)")
            answer = input()
            if answer == "n":
                print("Would you like to use detex instead of pandoc? (y/n)")
                detex_answer = input()
                if detex_answer == "y":
                    os.chdir(paper_dir)
                    sh(f"detex {main_doc} > {paper_id}.md")
                    # open detexed md file to clean it up
                    with open(f"{paper_id}.md", "r") as f:
                        paper_text = f.read()
                    paper_text = re.sub(r"\n\s+\n", "\n", paper_text)
                    paper_text = re.sub("\n{1,}", "\n\n", paper_text)
                    with open(f"{paper_id}.md", "w") as f:
                        f.write(paper_text)
                    fixed_error = True
                    os.chdir(project_dir)
                    sh(f"mv {paper_dir}/{paper_id}.md out/{paper_id}.md")
                    break
            if answer == "y":
                fixed_error = True
                os.chdir(project_dir)
                sh(f"mv {paper_dir}/{paper_id}.md out/{paper_id}.md")
                break
            else:
                print(
                    f"Opening {main_doc} in text editor. Please fix the error. Save and close the file once you are done."
                )
                sh(f"open {main_doc}")
                input(
                    "Press enter once you have fixed the error and fixed the tex file."
                )
                continue

    def _create_citations_csv(self):
        """
        Create a csv file with all the arxiv citations for each paper.
        """
        if self.citation_level != "0":
            print(
                f"Citation level is {self.citation_level}, so we'll create a CSV of the papers at that citation level."
            )
            all_citations = {}
            for paper_id in self.arxiv_citations_dict.keys():
                for citation in self.arxiv_citations_dict[paper_id].keys():
                    all_citations[citation] = True
            all_citations = pd.DataFrame(list(all_citations.keys()))
            all_citations.to_csv(
                f"all_citations_level_{self.citation_level}.csv", index=False
            )
            print(f"Saved CSV of all citations at level {self.citation_level}.")

    def _fix_chars_in_dirs(self, parent):
        for path, folders, files in os.walk(parent):
            for f in files:
                os.rename(
                    os.path.join(path, f), os.path.join(path, f.replace(" ", "_"))
                )
            for folder in folders:
                new_folder_name = folder.translate(
                    {ord(c): "_" for c in " !@#$%^&*()[]{};:,<>?\|`~-=+"}
                )
                if new_folder_name != folder:
                    os.rename(
                        os.path.join(path, folder), os.path.join(path, new_folder_name)
                    )

    def _preextract_tar(tar_filepath, input_dir="files", output_dir="tmp"):
        """
        Creates tmp/{tar_name} directory and extracts tar files and copies them to tmp/tar_name/*.
        Creates tmp/done_{tar_name} file to signal copy_tar that extraction is done.
        """
        tar_name = tar_filepath.split("/")[-1][:-7]
        if os.path.exists(f"{output_dir}/{tar_name}"):
            print(f"{tar_name} already extracted.")
            return
        sh(
            f"(mkdir -p {output_dir}/{tar_name}; tar xf {tar_filepath} -C {output_dir}/{tar_name}; echo finished preload of {tar_name}) &"
        )

    def _prepare_extracted_tars(self, paper_dir_path):
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
                                    arxiv_citations_dict[paper_id].update(
                                        {arxiv_id: True}
                                    )
                            json.dump(
                                arxiv_citations_dict,
                                open("arxiv_citations_dict.json", "w"),
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

    def _delete_style_files(self, paper_dir_path):
        # delete all files with .sty extension
        for doc in lsr(paper_dir_path):
            if doc.endswith(".sty"):
                sh(f"rm {doc}")

    def _any_to_utf8(b):
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

    def _convert_to_utf8(rootdir="."):
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

    def _mv_files_to_root(rootdir="tmp"):
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

    def _get_arxiv_ids(bib_file_path):
        with open(bib_file_path, "r") as f:
            bib_string = f.read()
        return re.findall(r"(?:arXiv:|abs/)(\d{4}\.\d{4,5})", bib_string), bib_string


if __name__ == "__main__":

    arxiv_extractor = ArxivPapers()

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
        if os.path.exists(mdfile):
            arxiv_dict[id]["good_extraction"] = True
        else:
            arxiv_dict[id]["good_extraction"] = False
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

    if remove_empty_papers == "y":
        arxiv_dict = remove_empty_mds_from_dict(arxiv_dict)
        arxiv_dict = remove_empty_texts_from_dict(arxiv_dict)
    json.dump(arxiv_dict, open("arxiv_dict_updated.json", "w"))
    print("Finished updating arxiv_dict_updated.json.")
