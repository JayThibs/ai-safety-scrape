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


empty_files, files = count_empty_mds("out")
num_empty_files = len(empty_files)
print(f"{num_empty_files} empty files out of {len(files)}")
print(empty_files)
