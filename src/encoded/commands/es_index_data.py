from pyramid import paster
from pyelasticsearch import ElasticSearch, IndexAlreadyExistsError

ES_URL = 'http://localhost:9200'
DOCTYPE = 'basic'
es = ElasticSearch(ES_URL)

COLLECTION_URL = ['antibodies', 'biosamples', 'experiments']
antibodies_mapping = {'basic': {'properties': {'antibody_lot': {'type': 'nested'}, 'target': {'type': 'nested', 'properties': {'date_created': {'type': 'string', 'index': 'not_analyzed'}, 'geneid_dbxref_list': {'type': 'string', 'index': 'not_analyzed'}}}}}}
biosamples_mapping = {'basic': {'properties': {'lot_id': {'type': 'string'}, 'treatments': {'type': 'nested'}, 'constructs': {'type': 'nested'}}}}
experiments_mapping = {'basic': {'properties': {'replicates': {'type': 'nested'}}}}


def index_antibodies(url, testapp, items):
    ''' indexing antibodies in elasticsearch '''

    es.put_mapping(url, 'basic', antibodies_mapping)
    for item in items:
        antibody = {}
        item_url = str(item.get('href'))
        item_json = testapp.get(item_url, headers={'Accept': 'application/json'}, status=200)
        id = str(item_json.json['_links']['self']['href'])[-36:]
        antibody = item_json.json
        del(antibody['_embedded'])
        links = item_json.json['_links']
        for link in links:
            if link == 'antibody_lot':
                antibody['antibody_lot'] = item_json.json['_embedded']['resources'][links[link].get('href')]
            elif link == 'target':
                antibody['target'] = item_json.json['_embedded']['resources'][links[link].get('href')]
        es.index(url, 'basic', antibody, id)
    es.refresh(url)


def index_biosamples(url, testapp, items):
    ''' indexing biosamples in elasticsearch '''

    es.put_mapping(url, 'basic', biosamples_mapping)
    for item in items:
        biosample = {}
        item_url = str(item.get('href'))
        item_json = testapp.get(item_url, headers={'Accept': 'application/json'}, status=200)
        id = str(item_json.json['_links']['self']['href'])[-36:]
        biosample = item_json.json
        del(biosample['_embedded'])
        links = item_json.json['_links']
        for link in links:
            if link == 'treatments' and len(links[link]):
                treatments = []
                for treatment in links[link]:
                    treatments.append(item_json.json['_embedded']['resources'][treatment.get('href')])
                biosample['treatments'] = list()
                biosample['treatments'].append(treatments)
            elif link == 'constructs' and len(links[link]):
                constructs = []
                for construct in links[link]:
                    constructs.append(item_json.json['_embedded']['resources'][construct.get('href')])
                biosample['constructs'] = list()
                biosample['constructs'].append(constructs)
        es.index(url, 'basic', biosample, id)
    es.refresh(url)


def index_experiments(url, testapp, items):
    ''' indexing experiments in elasticsearch '''

    es.put_mapping(url, 'basic', experiments_mapping)
    for item in items:
        experiment = {}
        item_url = str(item.get('href'))
        item_json = testapp.get(item_url, headers={'Accept': 'application/json'}, status=200)
        id = str(item_json.json['_links']['self']['href'])[-36:]
        experiment = item_json.json
        del(experiment['_embedded'])
        links = item_json.json['_links']
        for link in links:
            if link == 'replicates' and len(links[link]):
                replicates = []
                for replicate in links[link]:
                    replicates.append(item_json.json['_embedded']['resources'][replicate.get('href')])
                experiment['replicates'] = list()
                experiment['replicates'].append(replicates)
        es.index(url, 'basic', experiment, id)
    es.refresh(url)


def main():
    app = paster.get_app('dev-masterdata.ini')
    from webtest import TestApp
    environ = {
        'HTTP_ACCEPT': 'application/json',
        'REMOTE_USER': 'IMPORT',
    }
    testapp = TestApp(app, environ)
    for url in COLLECTION_URL:
        res = testapp.get('/' + url + '/', headers={'Accept': 'application/json'}, status=200)
        items = res.json['_links']['items']
        try:
            es.create_index(url)
        except IndexAlreadyExistsError:
            es.delete_index(url)
            es.create_index(url)
        if url == 'antibodies':
            index_antibodies(url, testapp, items)
        elif url == 'biosamples':
            index_biosamples(url, testapp, items)
        elif url == 'experiments':
            index_experiments(url, testapp, items)


if __name__ == '__main__':
    main()
