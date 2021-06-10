from fontTools.designspaceLib import DesignSpaceDocument
from glyphsLib.cli import main
from fontTools.ttLib import newTable, TTFont
import shutil
import subprocess
import multiprocessing
import multiprocessing.pool
from pathlib import Path
import argparse
import ufo2ft, ufoLib2, os, glob

def DSIG_modification(font:TTFont):
    font["DSIG"] = newTable("DSIG")     #need that stub dsig
    font["DSIG"].ulVersion = 1
    font["DSIG"].usFlag = 0
    font["DSIG"].usNumSigs = 0
    font["DSIG"].signatureRecords = []
    font["head"].flags |= 1 << 3        #sets flag to always round PPEM to integer

def GASP_set(font:TTFont):
    if "gasp" not in font:
        font["gasp"] = newTable("gasp")
        font["gasp"].gaspRange = {}
    if font["gasp"].gaspRange != {65535: 0x000A}:
        font["gasp"].gaspRange = {65535: 0x000A}


def generate(source:Path, merge:Path) -> None:
    ufoSource = ufoLib2.Font.open(source)
    mergeSource = ufoLib2.Font.open(merge)

    prefix = str(source).split("/")[1]
    prefix = prefix.split("-")[0]

    for glyph in mergeSource:
        if glyph.name not in ufoSource:
            ufoSource.addGlyph(mergeSource[glyph.name])

    ufoSource.lib['com.github.googlei18n.ufo2ft.filters'] = [{ # extra safe :)
        "name": "flattenComponents",
        "pre": 1,
    }]

    static_ttf = ufo2ft.compileTTF(
        ufoSource, 
        removeOverlaps=True, 
        overlapsBackend="pathops", 
        useProductionNames=True,
    )

    DSIG_modification(static_ttf)
    style_name = ufoSource.info.styleName
    print ("["+prefix+"-"+str(style_name)+"] Saving")
    output = "fonts/ttf/"+prefix+"-"+str(style_name)+".ttf"
    GASP_set(static_ttf)
    static_ttf.save(output)



def cleanup():
    # Cleanup
    for ufo in sources.glob("*.ufo"):
        shutil.rmtree(ufo)
    os.remove("sources/Hen_shared.designspace")
    os.remove("sources/Std_shared.designspace")
    os.remove("sources/YujiAkari.designspace")
    os.remove("sources/YujiAkebono.designspace")
    os.remove("sources/YujiBoku.designspace")
    os.remove("sources/YujiMai.designspace")
    os.remove("sources/YujiSyuku.designspace")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="build MPLUS fonts")
    parser.add_argument("-H", "--hentaigana", action="store_true", dest="hentaigana", help="Export Hentaigana fonts")
    parser.add_argument("-S", "--std", action="store_true", dest="std", help="Export Standard fonts")
    parser.add_argument("-A", "--all", action="store_true", dest="all", help="All variants")
    parser.add_argument("-U", "--ufo", action="store_true", dest="sources", help="Regen all sources")
    parser.add_argument("-W", "--clean", action="store_false", dest="clean", help="Don't remove all source files")

    args = parser.parse_args()
    sources = Path("sources")

    if args.all:
        args.hentaigana = True
        args.std = True
        args.sources = True

    if args.sources:
        print ("[Yuji] Generating UFO sources")
        for file in sources.glob("*.glyphs"):
            print ("["+str(file).split("/")[1]+"] generating source")
            main(("glyphs2ufo", str(file), "--write-public-skip-export-glyphs"))
                
        for ufo in sources.glob("*.ufo"): # need to put this command in all the source UFOs to make sure it is implemented
            source = ufoLib2.Font.open(ufo)
            source.lib['com.github.googlei18n.ufo2ft.filters'] = [{
                "name": "flattenComponents",
                "pre": 1,
            }]
            ufoLib2.Font.save(source)

    pool = multiprocessing.pool.Pool(processes=multiprocessing.cpu_count())
    processes = []


    if args.hentaigana:
        processes.append(
            pool.apply_async(
                generate,
                (
                    Path("sources/YujiHentaiganaAkari-Regular.ufo"),
                    Path("sources/HentaiganaShared-Regular.ufo")
                ),
            )
        )
        processes.append(
            pool.apply_async(
                generate,
                (
                    Path("sources/YujiHentaiganaAkebono-Regular.ufo"),
                    Path("sources/HentaiganaShared-Regular.ufo")
                ),
            )
        )

    if args.std:
        processes.append(
            pool.apply_async(
                generate,
                (
                    Path("sources/YujiBoku-Regular.ufo"),
                    Path("sources/StdShared-Regular.ufo")
                ),
            )
        )
        processes.append(
            pool.apply_async(
                generate,
                (
                    Path("sources/YujiMai-Regular.ufo"),
                    Path("sources/StdShared-Regular.ufo")
                ),
            )
        )
        processes.append(
            pool.apply_async(
                generate,
                (
                    Path("sources/YujiSyuku-Regular.ufo"),
                    Path("sources/StdShared-Regular.ufo")
                ),
            )
        )

    pool.close()
    pool.join()
    for process in processes:
        process.get()
    del processes, pool

    if args.clean:
        print ("Cleaning build files")
        cleanup()