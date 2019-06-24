
import requests
import sys
import yaml
import os
import shutil
import time
import re
import logging

# ================================================
logger = logging.getLogger(__name__)

class DataSource():
    """
    A context-object that downloads and unzips/untars an archive  
    and moves relevant files to an output folder, discarding the rest.

    Makes it a bit easier to download multiple different files from
    diverse sources, unzipping them, and sorting them in folders.

    Enter creates a temporary dir, where the file can be handled.
    Also creates an "out" dir where the files of interest are stored.

    Exit removes this dir, with all superflous files.
    """

    def __init__(self, name, link, filefilter = '.*', 
                 chunksize = 512 * 1024, login = False):
        self.name = name
        self.link = link
        self.chunksize = chunksize 

        self.tmpdir = f'tmp/{self.name}'
        self.outdir = f'out/{self.name}'

        self.filefilter = filefilter

    def __enter__(self):
        """
        Create a temporary directory for storing
        archive file, and other intermediate file
        structures.
        """

        try:
            os.mkdir(self.tmpdir)
        except FileExistsError:
            pass

        try:
            os.mkdir(self.outdir)
        except FileExistsError:
            logger.warning(f' Overwriting {self.outdir}')
            shutil.rmtree(self.outdir)
            os.mkdir(self.outdir)

        return(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up, removing temporary directory.
        Also removes output directory if it is
        empty.
        """

        shutil.rmtree(self.tmpdir)
        if len(os.listdir(self.outdir)) == 0:
            shutil.rmtree(self.outdir)

    def download(self): 
        """
        Grab the file, put it in the tmpdir
        """

        logger.debug(f'Grabbing {self.link}')
        r = requests.get(self.link) 

        if r.ok:
            fname = os.path.split(self.link)[1]
            with open(f'{self.tmpdir}/{fname}', 'wb') as dest:
                for ch in r.iter_content(chunk_size = self.chunksize):
                    if ch:
                        dest.write(ch)
            self.archive = f'{self.tmpdir}/{fname}'

        return(r)

    def retreiveFiles(self):
       shutil.unpack_archive(self.archive, self.tmpdir) 
       contents = os.walk(self.tmpdir)

       tgt = []
       for entry in contents:
           path, _, files = entry 
           relevant = [f for f in files if re.search(self.filefilter, f)]
           tgt += [(path,f) for f in relevant]

       for path, filename in tgt:
           shutil.move(os.path.join(path,filename),f'{self.outdir}/{filename}')

    def get(self):

        r = self.download()
        if r.ok:
            self.retreiveFiles()
        else:
            logger.warning(f'''{self.name} @ {self.link} 
            failed with status code:{r.status_code}')
                            ''')
            pass

if __name__ == '__main__':
    logging.basicConfig(level = 'DEBUG')
    
    configfile = sys.argv[1]

    with open(configfile) as f:
        config = yaml.safe_load(f)

    for site in config['sites']:
        with DataSource(**site) as datasource:
            datasource.get()

