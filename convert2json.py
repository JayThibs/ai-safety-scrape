from paper2json.tei2json import convert_tei_xml_file_to_s2orc_json
import json
from dspipe import Pipe
import os
from utils import *
from arxiv_extractor import ArxivPapers
import multiprocessing as mp


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
    sh(
        "mkdir -p data/raw/pdfs/non_arxiv_papers data/raw/pdfs/reports data/raw/pdfs/arxiv data/tei_arxiv"
    )
    sh(
        "mkdir -p data/processed/jsons/non_arxiv_paper_jsons data/processed/jsons/report_jsons data/processed/jsons/arxiv_paper_jsons"
    )
    sh(
        "mkdir -p data/interim/tei/non_arxiv_papers data/interim/tei/reports data/interim/tei/arxiv_papers"
    )
    arxivPapers = ArxivPapers()
    if os.listdir("data/raw/pdfs/arxiv_papers") == []:
        arxivPapers.setup()
        arxivPapers.download_arxiv_papers(pdf=True)
    n_threads = mp.cpu_count()
    if os.listdir("data/raw/pdfs/arxiv_papers") == []:
        sh(
            f"grobid_client --input 'data/raw/pdfs/arxiv_papers' --output 'data/interim/tei/arxiv_papers' --n {n_threads}  processFulltextDocument"
        )
    convert_folder_to_json(
        "data/interim/tei/non_arxiv_papers",
        "data/processed/jsons/non_arxiv_paper_jsons",
        True,
    )
    convert_folder_to_json(
        "data/interim/tei/reports", "data/processed/jsons/report_jsons", True
    )
    convert_folder_to_json(
        "data/interim/tei/arxiv_papers", "data/processed/jsons/arxiv_paper_jsons", True
    )
