""" Console script to obtain file metadata from ENCODE Data Warehouse (EDW)
    and import to encoded database
"""

from pyramid import paster
from sqlalchemy import MetaData, create_engine, select
import logging
import sys

DEFAULT_COUNT = 10                 # number of files to show by default

FILE_INFO_FIELDS = ['file_accession',
                    'output_type',
                    'file_format',
                    'experiment_accession',
                    'replicate',
                    'download_path',
                    'submitted_file_name',
                    'assembly',
                    'enriched',
                    'md5sum'
                   ]

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


def make_edw_db(data_host):
    # Get configuration
    import ConfigParser
    config = ConfigParser.ConfigParser()
    config.read('edw.cfg')

    site = 'production'
    engine = config.get(site, 'engine')
    if (data_host):
        host = data_host
    else:
        host = config.get(site, 'host')
    db = config.get(site, 'db')
    user = config.get(site, 'user')
    password = config.get(site, 'password')

    # Create db engine (using configured settings when available)
    print >>sys.stderr, \
        'Connecting to', '%s://%s/%s' % (engine, host, db)
    edw_db = create_engine('%s://%s:%s@%s/%s' %
                          (engine, user, password, host, db))
    return edw_db


def import_edw_fileinfo(input_file):
    print >>sys.stderr, 'Importing file info from ' + input_file

    from csv import DictReader, DictWriter
    import json

    test_app = make_app()
    #url = 'http://localhost:5432/files/'
    # Seth's dev sys
    #url = 'http://184.169.162.173/files/'
    #url = 'http://submit-dev.encodedcc.org/files/'
    #url = 'http://' + app_host + '/files/'
    url = '/files/'
    print >>sys.stderr, 'Posting to ' + url
    with open(input_file, 'rb') as f:
        reader = DictReader(f, delimiter='\t')
        for row in reader:
            test_app.post_json(url, row)
    response = test_app.get(url)
    #print response.json['items']
    fields = (list(FILE_INFO_FIELDS))
    fields.append('@id')
    writer = DictWriter(sys.stdout, delimiter='\t', fieldnames=fields,
                        extrasaction='ignore')
    for row in response.json['items']:
        writer.writerow(row)


def read_encoded_fileinfo(count):
    from csv import DictWriter
    test_app = make_app()
    url = '/files/'
    print >>sys.stderr, 'Exporting file info from app'
    response = test_app.get(url)
    print response.json


def read_edw_fileinfo(count, data_host):
    """ read info from file tables at EDW.
        ENCODE Data Warehouse and format as TSV file with columns from
        encoded File JSON schema
    """
    # Create interface to EDW db and autoreflect the schema
    db = make_edw_db(data_host)
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
    # NOTE: ordering must mirror FILE_INFO_FIELDS
    query = select([vf.c.licensePlate, vf.c.outputType, vf.c.format,
                    vf.c.experiment, vf.c.replicate,
                    f.c.edwFileName, f.c.submitFileName, vf.c.ucscDb,
                    vf.c.enrichedIn, f.c.md5]).\
        where((vf.c.fileId == f.c.id) &
              (vf.c.experiment.like('ENCSR%'))).\
        order_by(f.c.endUploadTime.desc()).\
        limit(count)
    results = conn.execute(query)

    print '\t'.join(FILE_INFO_FIELDS)
    for row in results:
        print '\t'.join(row)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Read validated ENCODE 3 file info at EDW')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-i', '--import_file',
                       help='import to app from named file')
    group.add_argument('-e', '--export', action="store_true",
                       help='export file info from app')
    parser.add_argument('-c', '--count', type=int, default=DEFAULT_COUNT,
                        help='number of files to show; most recently submitted \
                                first (default %s)' % DEFAULT_COUNT)
    parser.add_argument('-d', '--data_host',
                        help='data warehouse host (default from edw.cfg)')
    args = parser.parse_args()
    if args.import_file:
        import_edw_fileinfo(args.import_file)
    elif args.export:
        read_encoded_fileinfo(args.count)
    else:
        read_edw_fileinfo(args.count, args.data_host)

if __name__ == '__main__':
    main()
