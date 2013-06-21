from pyramid import paster
from pyelasticsearch import ElasticSearch, IndexAlreadyExistsError
from ordereddict import OrderedDict

ES_URL = 'http://localhost:9200'
DOCTYPE = 'basic'
es = ElasticSearch(ES_URL)

basic_mapping = {'basic': {}}
targets_mapping = {'basic': {'properties': {'geneid_dbxref_list': {'type': 'string', 'index': 'not_analyzed'}, 'date_created': {'type': 'string', 'index': 'not_analyzed'}}}}
biosamples_mapping = {'basic': {'properties': {'lot_id': {'type': 'string'}, 'donor': {'type': 'nested'}, 'lab': {'type': 'nested'}, 'award': {'type': 'nested'}, 'submitter': {'type': 'nested'}, 'source': {'type': 'nested'}, 'treatments': {'type': 'nested'}, 'constructs': {'type': 'nested'}}}}
experiments_mapping = {'basic': {'properties': {'replicates': {'type': 'nested'}}}}
libraries_mapping = {'basic': {'properties': {'size_range': {'type': 'string'}}}}
replicates_mapping = {'basic': {'properties': {'library': {'properties': {'size_range': {'type': 'string'}}}}}}
antibodies_mapping = {'basic': {'properties': {'target': {'properties': {'geneid_dbxref_list': {'type': 'string', 'index': 'not_analyzed'}, 'date_created': {'type': 'string', 'index': 'not_analyzed'}}}}}}

COLLECTION_URL = OrderedDict([
    ('/awards/', ['awards', basic_mapping]),
    ('/labs/', ['labs', basic_mapping]),
    ('/users/', ['submitters', basic_mapping]),
    ('/organisms/', ['organisms', basic_mapping]),
    ('/sources/', ['sources', basic_mapping]),
    ('/targets/', ['targets', targets_mapping]),
    ('/antibody-lots/', ['antibody_lots', basic_mapping]),
    ('/validations/', ['validations', basic_mapping]),
    ('/antibodies/', ['antibody_approvals', antibodies_mapping]),
    ('/donors/', ['donors', basic_mapping]),
    ('/treatments/', ['treatments', basic_mapping]),
    ('/constructs/', ['constructs', basic_mapping]),
    ('/biosamples/', ['biosamples', biosamples_mapping]),
    ('/platforms/', ['platforms', basic_mapping]),
    ('/libraries/', ['libraries', libraries_mapping]),
    ('/assays/', ['assays', basic_mapping]),
    ('/replicates/', ['replicates', replicates_mapping]),
    ('/experiments/', ['experiments', experiments_mapping])
])

key_links = ['profile', 'self', 'collection', 'files', 'documents', 'experiments']


def main():
    app = paster.get_app('dev-masterdata.ini')
    from webtest import TestApp
    environ = {
        'HTTP_ACCEPT': 'application/json',
        'REMOTE_USER': 'IMPORT',
    }
    testapp = TestApp(app, environ)

    print ""
    print "*******************************************************************"
    print ""
    print "Indexing ENCODE Data in Elastic Search"
    print ""

    for url in COLLECTION_URL:
        print "Indexing " + COLLECTION_URL.get(url)[0] + " ...."
        res = testapp.get(url, headers={'Accept': 'application/json'}, status=200)
        items = res.json['_links']['items']

        # try creating index, if it exists already delete it and create it again and generate mapping
        index = COLLECTION_URL.get(url)[0]
        try:
            es.create_index(index)
        except IndexAlreadyExistsError:
            es.delete_index(index)
            es.create_index(index)
        es.put_mapping(index, DOCTYPE, COLLECTION_URL.get(url)[1])

        for item in items:
            item_json = testapp.get(str(item.get('href')), headers={'Accept': 'application/json'}, status=200)
            document_id = str(item_json.json['_links']['self']['href'])[-36:]
            document = item_json.json
            if '_embedded' in document:
                # Get rid of embedded object from the document
                del(document['_embedded'])
                links = item_json.json['_links']
                for link in links:
                    if not isinstance(links[link], list):
                        if link not in key_links and links[link].get('href') in item_json.json['_embedded']['resources']:
                            id = links[link].get('href')[-36:]
                            sub_index = COLLECTION_URL.get(str(links[link].get('href'))[:-36])[0]
                            sub_document = es.get(sub_index, DOCTYPE, id)
                            document[link] = sub_document['_source']
                    else:
                        for list_link in links[link]:
                            data_items = []
                            if link not in key_links and list_link.get('href') in item_json.json['_embedded']['resources']:
                                id = list_link.get('href')[-36:]
                                sub_index = COLLECTION_URL.get(str(list_link.get('href'))[:-36])[0]
                                sub_document = es.get(sub_index, DOCTYPE, id)
                                data_items.append(sub_document['_source'])
                        document[link] = data_items
                    es.index(index, DOCTYPE, document, document_id)
            else:
                es.index(index, DOCTYPE, document, document_id)
        es.refresh(index)
        count = es.count('*:*', index=index)
        print "Finished indexing " + str(count['count']) + " " + COLLECTION_URL.get(url)[0]


if __name__ == '__main__':
    main()
