from utils import *
import re

for paper_dir in ls("tmp"):
    if not paper_dir.split("/")[-1] == ".DS_Store":
        for item in ls(paper_dir):
            if item.endswith("_failed"):
                sh(f"rm -f {item}")
