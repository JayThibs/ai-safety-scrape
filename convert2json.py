import os
import json
import jsonlines
from dspipe import Pipe
import multiprocessing as mp
from utils import *
from arxiv_extractor import ArxivPapers
from paper2json.tei2json import convert_tei_xml_file_to_s2orc_json


def tei2json(input_file_path, output_file_path):
    try:
        paper = convert_tei_xml_file_to_s2orc_json(input_file_path)
        authors = paper.metadata.authors
        authors = [x.first + " " + x.last for x in authors]
        paper_json = paper.as_json()
        paper_json = {
            "source": "reports",
            "source_filetype": "pdf",
            "converted_with": "grobid",
            "paper_version": str(paper.paper_id),
            "post_title": paper.metadata.title,
            "authors": authors,
            "date_published": str(paper.metadata.year),
            "data_last_modified": "",
            "url": "",
            "abstract": paper.raw_abstract_text,
            "author_comment": "",
            "journal_ref": paper.metadata.venue,
            "doi": paper.metadata.doi,
            "primary_category": "",
            "categories": "",
            "citation_level": "",
            "main_tex_filename": "",
            "text": paper.body_markdown,
            "bibliography_bbl": "",
            "bibliography_bib": paper_json["bib_entries"],
        }

        # save json to file
        with open(output_file_path, "w") as f:
            json.dump(paper_json, f)
    except:
        print("Error converting file: " + str(input_file_path))
        pass


def convert_folder_to_json(input_folder_path, output_folder_path, pipe=True):
    if pipe:
        Pipe(
            source=input_folder_path,
            dest=output_folder_path,
            input_suffix=".xml",
            output_suffix=".json",
        )(tei2json, n_threads)
    else:
        for input_file_path in os.listdir(input_folder_path):
            if input_file_path.endswith(".xml"):
                output_file_path = input_file_path.replace(".xml", ".json")
                output_file_path = os.path.join(output_folder_path, output_file_path)
                tei2json(
                    os.path.join(input_folder_path, input_file_path), output_file_path
                )


if __name__ == "__main__":
    names = ["arxiv_papers", "non_arxiv_papers", "reports"]
    json_folder_paths = []
    tei_files = []
    sh("mkdir -p data/processed/main_jsons")
    for filename in names:
        sh(f"mkdir -p data/pdfs/{filename}")
        sh(f"mkdir -p data/processed/{filename}_jsons")
        sh(f"mkdir -p data/interim/tei/{filename}")
        json_folder_paths.append(f"data/processed/jsons/{filename}_jsons")
        if os.path.exists(f"data/processed/jsonl/{filename}.jsonl"):
            os.remove(f"data/processed/jsonl/{filename}.jsonl")
        tei_files.append(ls(f"data/interim/tei/{filename}"))

    arxivPapers = ArxivPapers()
    if os.listdir("data/raw/pdfs/arxiv_papers") == []:
        arxivPapers.setup()
        arxivPapers.download_arxiv_papers(pdf=True)

    n_threads = mp.cpu_count()
    for i, filename in enumerate(names):
        sh(
            f"grobid_client --input 'data/raw/pdfs/{filename}' --output 'data/interim/tei/{filename}' --n {n_threads}  processFulltextDocument"
        )
        convert_folder_to_json(
            f"data/interim/tei/{filename}", json_folder_paths[i], True
        )

    # Create main json and jsonl files
    json_files = [
        ls(json_folder_paths[0]),
        ls(json_folder_paths[1]),
        ls(json_folder_paths[2]),
    ]
    json_list = []

    for name, text_jsons in zip(names, json_files):
        for i, filename in enumerate(text_jsons):
            i = str(i)
            paper = json.load(open(filename))
            with jsonlines.open(f"data/{name}.jsonl", "a") as writer:
                writer.write(paper)
            with open("data/arxiv.txt", "a") as f:
                # Save the entry in plain text, mainly for debugging
                text = (
                    "    ".join(("\n" + paper["text"].lstrip()).splitlines(True)) + "\n"
                )
                f.write(f"[ENTRY {i}] {text}")
            json_list.append(paper)
            print(i + "/" + str(len(text_jsons)))
        json.dump(json_list, open(f"data/processed/main_jsons/{name}.json", "w"))

    # Deleting tei files which have already been converted to json
    for i, tei_file in enumerate(tei_files):
        tei_files[i] = tei_file[:-8]  # remove extension
    for i, json_file in enumerate(json_files):
        json_files[i] = json_file[:-5].split("/")[-1]  # remove extension
    for json_file in json_files:
        potential_tei_file = "data/interim/tei/arxiv_papers/" + json_file + ".tei.xml"
        if os.path.exists(potential_tei_file):
            os.remove(potential_tei_file)
