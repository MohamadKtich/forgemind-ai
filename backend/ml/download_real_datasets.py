"""Download the official real datasets used by ForgeMind training pipelines.

Network access is intentionally not required by the running application. This helper is for
retraining environments that do have internet access. Dataset licenses remain authoritative.
"""
from __future__ import annotations
import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCES={
    "metropt":("https://archive.ics.uci.edu/static/public/791/metropt+3+dataset.zip",ROOT/"data/metropt","CC BY 4.0"),
    "ksdd":("https://go.vicos.si/kolektorsdd",ROOT/"data/ksdd","CC BY-NC-SA 4.0; non-commercial unless permission is obtained"),
}

def download(name:str):
    url,destination,license_text=SOURCES[name];destination.mkdir(parents=True,exist_ok=True);archive=destination/f"{name}.zip"
    print(f"Downloading {name} from the official source ({license_text})")
    request=urllib.request.Request(url,headers={"User-Agent":"ForgeMind-AI/3.0 dataset retraining utility"})
    with urllib.request.urlopen(request,timeout=180) as response,archive.open("wb") as target:shutil.copyfileobj(response,target)
    if not zipfile.is_zipfile(archive):raise RuntimeError(f"The downloaded {name} file is not a ZIP archive. The provider may require browser acceptance.")
    with zipfile.ZipFile(archive) as z:
        destination_root=destination.resolve()
        for member in z.infolist():
            target=(destination/member.filename).resolve()
            if destination_root not in target.parents and target != destination_root:
                raise RuntimeError(f"Unsafe path in dataset archive: {member.filename}")
        z.extractall(destination)
    print(f"Extracted to {destination}")

def main():
    parser=argparse.ArgumentParser();parser.add_argument("dataset",choices=["metropt","ksdd","all"]);parser.add_argument("--accept-ksdd-nc-license",action="store_true");args=parser.parse_args()
    names=list(SOURCES) if args.dataset=="all" else [args.dataset]
    if "ksdd" in names and not args.accept_ksdd_nc_license:raise SystemExit("KSDD is CC BY-NC-SA 4.0. Re-run with --accept-ksdd-nc-license after confirming the intended non-commercial use or obtaining permission.")
    for name in names:download(name)
if __name__=="__main__":main()
