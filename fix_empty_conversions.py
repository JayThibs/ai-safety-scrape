from utils import *


def count_empty_mds(paper_dir):
    files = ls(paper_dir)
    empty_files = []
    for file in files:
        file.split(".")[-1]
        if file.endswith(".md"):
            if os.stat(file).st_size == 0:
                empty_files.append(file)

    return empty_files, files


def mv_empty_mds():
    sh("mkdir -p fallback_needed/empty_mds")
    empty_files, files = count_empty_mds("out")
    num_empty_files = len(empty_files)
    print(f"{num_empty_files} empty files out of {len(files)}")
    print(empty_files)

    for file in empty_files:
        folder = "done/" + file.split("/")[-1][:-3] + "/"
        sh(f"mv {file} {folder}")
        sh(f"mv {folder} fallback_needed/empty_mds/")

    print("Done moving empty files to fallback_needed/empty_mds")


def remove_empty_mds_from_dict(arxiv_dict):
    empty_mds = [
        empty_md.split("/")[-1][:-2] for empty_md in ls("fallback_needed/empty_mds")
    ]
    print("Removing the following papers from dict since the contents are empty: ")
    print(empty_mds)
    for empty_md in empty_mds:
        arxiv_dict.pop(empty_md, None)
    return arxiv_dict


def remove_empty_texts_from_dict(arxiv_dict):
    total_papers = len(arxiv_dict)
    removed_papers = 0
    for paper in arxiv_dict:
        if len(paper["text"]) < 500 and paper["main_tex_filename"] != "":
            removed_papers += 1
            arxiv_dict.pop(paper["id"], None)
    print(f"{removed_papers} out of {total_papers} papers removed")
    return arxiv_dict
