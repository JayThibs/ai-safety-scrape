import os
from re import A
import time
import pickle
import tika
import multiprocessing as mp
from multiprocessing import freeze_support
from text_extractor import extractText
import argparse
from itertools import repeat


def main():

    parser = argparse.ArgumentParser(
        description="Adds custom flags for the text extractor."
    )
    parser.add_argument(
        "-o",
        "--overwrite_pkls",
        type=bool,
        help="Overwrites saved pickle files of extracted text.",
        default=False,
    )
    args = parser.parse_args()

    # Tika configuration

    # IMPORTANT: Before running this script, make sure you go through the following steps:
    # 0. The following steps allow you to configure the Tika server to allow extraction of much bigger PDF files.
    # Otherwise, the script will fail when you try to extract bigger files (especially when using multiprocessing).
    # 1. Download: the java runtime (64-bit version) from https://www.java.com/en/download/manual.jsp
    # 2. If you want to update tika version, go to: https://tika.apache.org/download.html
    # 3. Run: java -d64 -jar -Xms40g -Xmx40g tika-server-standard-2.1.0.jar
    # Adjust the memory (40g in this case) to 2/3rds of RAM you have available
    # (Optional): if you know how to use docker, spin one of the containers here instead of downloading tika: https://hub.docker.com/r/apache/tika
    # Note: the code runs slower on Windows if you use Docker because Windows needs to create a linux virtual environment.

    tika.TikaClientOnly = True
    os.environ["TIKA_STARTUP_RETRY"] = "10"
    os.environ["TIKA_SERVER_PORT"] = "9998"
    os.environ["TIKA_SERVER_HOST"] = "localhost"

    # Necesary to avoid the error with multiprocessing
    # For more info (Windows): https://www.kite.com/python/docs/exceptions.RuntimeError
    # If using Linux/MacOS: https://pythonspeed.com/articles/python-multiprocessing/

    PDFS_PATH = "./data/raw/pdfs/"
    PROCESSED_TEXTS_PATH = "./data/processed/texts/"

    def list_of_pdf_filepaths(PDFS_PATH):
        list_of_pdfs = []
        for file in os.listdir(PDFS_PATH):
            if file.endswith(".pdf"):
                list_of_pdfs.append(PDFS_PATH + file)
        return list_of_pdfs

    list_of_pdfs = list_of_pdf_filepaths(PDFS_PATH)

    # Multiprocessing
    start_time = time.time()
    results = []
    with mp.Pool(mp.cpu_count()) as pool:
        results.extend(
            pool.starmap(
                extractText, zip(list_of_pdfs, repeat(args.overwrite_pkls)), chunksize=1
            )
        )
    print("--- %s seconds ---" % (time.time() - start_time))

    # Flatten the list of lists
    results = [item for sublist in results for item in sublist]

    # Save the results
    with open(PROCESSED_TEXTS_PATH + "all_texts.pkl", "wb") as f:
        pickle.dump(results, f)


if __name__ == "__main__":
    freeze_support()
    main()
