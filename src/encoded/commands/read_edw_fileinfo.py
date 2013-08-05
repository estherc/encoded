""" Console script to obtain file metadata from ENCODE Data Warehouse (EDW)
    and import to encoded database
"""

from pyramid import paster
from sqlalchemy import MetaData, create_engine, select, engine_from_config
import logging
import sys

def make_app():
    logging.basicConfig()
    app = paster.get_app('edw.ini')
    from webtest import TestApp
    environ = {
        'HTTP_ACCEPT': 'application/json',
        'REMOTE_USER': 'IMPORT',
    }
    test_app = TestApp(app, environ)

    print >>sys.stderr, 'Created app'
    return test_app

def make_edw_db():
    # Get configuration
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read('edw.cfg')

    # TODO: Possible command-line option to change to 'dev' settings
    site = 'production'
    engine = config.get(site, 'engine');
    host = config.get(site, 'host');
    db = config.get(site, 'db');
    user = config.get(site, 'user');
    password = config.get(site, 'password');


    # Create db engine (using configured settings when available)
    print >>sys.stderr, \
        'Connecting to', '%s://%s/%s' % (engine, host, db)
    edw_db = create_engine('%s://%s:%s@%s/%s' % 
        (engine, user, password, host, db))
    return edw_db

def import_edw_fileinfo(input_file):
    print >>sys.stderr, 'Importing files from ' + input_file

    from csv import DictReader
    import json

    test_app = make_app()
    url = 'http://localhost:5432/files/'
    #url = 'http://submit-dev.encodedcc.org/files/'
    with open(input_file, 'rb') as f:
        reader = DictReader(f, delimiter='\t')
        for row in reader:
            print row
            test_app.post_json(url, row)

def read_edw_fileinfo(count):

    # Create interface to EDW db and autoreflect the schema
    db = make_edw_db()
    meta = MetaData()
    meta.reflect(bind=db)

    # List tables:
    #print(meta.tables.keys())

    f = meta.tables['edwFile']
    vf = meta.tables['edwValidFile']

    # Make a connection
    conn = db.connect()

    # Get info for ENCODE 3 experiment files (those having ENCSR accession)
    # List files newest first
    query = select([vf.c.licensePlate, vf.c.outputType, vf.c.format, 
                    vf.c.experiment, vf.c.replicate,
                    f.c.edwFileName, f.c.submitFileName, vf.c.ucscDb,
                    vf.c.enrichedIn, f.c.md5]).\
                        where((vf.c.fileId == f.c.id) &
                            (vf.c.experiment.like('ENCSR%'))).\
                                order_by(f.c.endUploadTime.desc()).\
                                limit(count)
    results = conn.execute(query);
    print '\t'.join(['file_accession', 'output_type', 'file_format', 
                      'experiment_accession', 'replicate',
                      'download_path', 'submitted_file_name', 'assembly',
                      'enriched', 'md5sum'
                      ])
    for row in results:
        print '\t'.join(row)

def main():
    import argparse
    default_count = 10
    parser = argparse.ArgumentParser(
        description='Read validated ENCODE 3 file info at EDW')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', '--count', type=int, default=default_count,
                        help='number of files to show -- most recently submitted first (default %s)'
                            % default_count)
    group.add_argument('-i', '--import_file',
                        help='import to server from named file')
    args = parser.parse_args()
    if args.import_file:
        import_edw_fileinfo(args.import_file)
    else:
        read_edw_fileinfo(args.count)

if __name__ == '__main__':
    main()
