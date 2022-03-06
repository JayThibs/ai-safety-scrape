import os
from utils import *
import magic

mime = magic.Magic(mime=True)
import re
import multiprocessing as mp
import chardet
import bs4
import time
from tqdm import tqdm


sh("mkdir -p tmp tmp2 out done fallback_needed errored")


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


def convert(tex):
    print(tex)
    out_name = tex.split("/")[2:] >> join("_")

    try:
        with open(tex, "rb") as fh:
            b = fh.read()
            cont = any_to_utf8(b)
            if cont is None:
                return
        fwrite(tex, cont)
    except FileNotFoundError:
        # ???

        return

    try:
        os.chdir("tmp")
        sh(f"timeout 10s pandoc -s {tex} -o {out_name}.txt --wrap=none")
        os.chdir("..")
        sh(f"mv tmp/{out_name}.txt out/{out_name}.txt")
    except ExitCodeError:
        import traceback

        traceback.print_exc()
        # fallback:
        try:
            # move to fallback pile so we can handle it later
            if "_extract" in tex.split("/")[:-1] >> join("/"):
                loc = tex.split("/")[:-1] >> join("/")
            else:
                loc = tex
            sh(f"mv {loc} fallback_needed/")

            return

        except ExitCodeError:
            import traceback

            traceback.print_exc()


def preextract_tar(dump):
    """
    Creates tmp2/{dump_name} directory and extracts tar files and copies them to tmp2/dump_name/*.
    Creates tmp2/done_{dump_name} file to signal copy_tar that extraction is done.
    """
    dump_name = dump.split("/")[-1][:-4]
    sh(
        f"(mkdir -p tmp2/{dump_name}; tar xf {dump} -C tmp2/{dump_name} && touch tmp2/done_{dump_name}; echo finished preload of {dump_name}) &"
    )


def copy_tar(dump):
    """Copies tar files from tmp2/{dump_name}/* to tmp/."""
    dump_name = dump.split("/")[-1][:-4]
    for i in range(120):
        if os.path.exists(f"tmp2/done_{dump_name}"):
            sh(f"mv tmp2/{dump_name}/* tmp")
            return True
        print("waiting for tar...")
        time.sleep(1)

    return False


def mv_files_to_root(rootdir="tmp"):
    """Moves all files in root folder subdirectories to root folder."""
    for doc in ls(rootdir):
        if os.path.isdir(doc):
            sh(f"find ./{doc} -type f -print0 | xargs -0 mv -t .")


def convert_semiauto(rootdir="tmp"):
    """
    Converts paper tex files semi-automatically. If there are multiple tex files,
    it will check for a list of common "main" file names and use the first one found.
    If there are multiple .tex files and it cannot find a main file, you will be prompted
    to select one.
    """
    os.chdir(rootdir)
    for doc in ls("."):
        doc = doc.split("/")[-1][:-4]
        if len(ls(".")) == 1:
            # if there is only one tex file, just convert it
            sh(f"pandoc -s {doc}.tex -o {doc}.txt --wrap=none")
        elif doc in ["main", "Main", "MAIN", "paper", "Paper"]:
            # if there is a common main file name, use it
            sh(f"pandoc -s {doc}.tex -o {doc}.txt --wrap=none")
            break
        else:
            # if there are multiple tex files and it's not in the above list: prompt user to select one
            print("Multiple tex files found. Please select the main file: \n")
            print(os.listdir() + "\n")
            main_tex = int(
                input(
                    f"Enter the filename here, file extension included (e.g. AIProgress.tex): "
                )
            )
            sh(f"pandoc -s {main_tex} -o {main_tex}.txt --wrap=none")

    os.chdir("..")


pool = mp.Pool(mp.cpu_count())

files = ls("files")

sh("rm -rf tmp/* tmp2/*")
preextract_tar(files[0])

for i, dump in enumerate(tqdm(files)):
    # extracts tar files to tmp2/{dump_name}/*
    if i + 1 < len(files):
        preextract_tar(files[i + 1])
    try:
        # clear tmp every loop to process only one set of .tex files at a time
        sh("rm -rf tmp/*")
        if not copy_tar(dump):
            # if tmp2/done_{dump_name} is not created, skip this dump
            continue
        # extract
        print(dump)
        sh(f"tar xf {dump} -C tmp")

        # this loop deletes all files in tmp that are not .tex files
        for doc in lsr("tmp"):
            if doc.endswith(".gz"):
                sh(f"gunzip {doc}")
                type = mime.from_file(doc[:-3])
                if type == "application/x-tar":
                    # if tarfile, extract in {doc[:-3]}_extract folder and delete tarfile
                    sh(
                        f"mkdir -p {doc[:-3]}_extract && tar xf {doc[:-3]} -C {doc[:-3]}_extract"
                    )
                    sh(f"rm {doc[:-3]}")
                elif type == "text/x-tex":
                    # if tex, keep it
                    sh(f"mv {doc[:-3]} {doc[:-3]}.tex")
                else:
                    # if not tar or tex, delete file
                    sh(f"rm {doc[:-3]}")

            elif doc.endswith(".pdf"):
                # if pdf, delete file
                sh(f"rm {doc}")

        # process tex files

        mv_files_to_root()
        convert_semiauto()

        # texfiles = list(tex_files())
        # pool.map(convert, texfiles)
        # sh(f"mv {dump} done")
        print(f"marking {dump} as done")
    except:
        pass
        # sh(f"mv {dump} errored")

# pool.close()
# pool.join()
