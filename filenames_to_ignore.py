import pandas as pd
import csv
import pickle

ignore_list_title = [
    "Approach",
    "Conclusion",
    "Experiments",
    "Figures",
    "Implementation",
    "Appendix",
    "Introduction",
    "Preliminaries",
    "Problem",
    "RelatedWork",
    "RelatedWorks",
    "Related",
    "Background",
    "Methods",
    "math_commands",
    "Results",
    "Supplement",
    "Abstract",
    "Discussion",
    "Evaluation",
    "Methodology",
    "mathcommands",
    "Prelim",
    "Related_Work",
    "Method",
    "Intro",
    "Proofs",
    "Macros",
    "Pseudocode",
    "Conc",
    "Exp",
    "Symbol",
    "Custom",
    "Packages",
    "Glossary",
    "Experiment",
    "Dataset",
    "Model",
    "Concl",
    "Experim",
    "Acks",
    "Data",
    "Metrics",
    "Train",
    "Defs",
    "Comments",
    "Acknowledgements",
    "Analysis",
    "Summary",
    "Background",
    "Theory",
    "Abbrev",
    "Plots",
    "Datasheet",
    "References",
    "Supp",
]


def modify_caps(ignore_list_title):
    ignore_list_lower = []
    for item in ignore_list_title:
        ignore_list_lower.append(f"{item.lower()}.tex")
    return ignore_list_lower


ignore_list = modify_caps(ignore_list_title)
df_ignore = pd.DataFrame(ignore_list)
df_ignore.to_csv("ignore_filenames.csv", index=False, header=False)
df = pd.read_csv("ignore_filenames.csv", header=None)
print(df)


def open_csv_to_dict(csv_file):
    """
    Opens a csv file and returns a dictionary of the contents.
    """
    with open(csv_file) as f:
        ignore_dict = {}
        reader = csv.reader(f)
        for row in reader:
            ignore_dict[row[0]] = True
        return ignore_dict


ignore_dict = open_csv_to_dict("ignore_filenames.csv")
if "Approached" in ignore_dict:
    print("Approach is in ignore_dict")
else:
    print("Approach is not in ignore_dict")

with open("ignore_dict.pkl", "wb") as f:
    pickle.dump(ignore_dict, f)
