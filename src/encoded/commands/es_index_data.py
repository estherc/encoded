from pyramid import paster
from pyelasticsearch import ElasticSearch, IndexAlreadyExistsError

ES_URL = 'http://localhost:9200'
DOCTYPE = 'basic'
es = ElasticSearch(ES_URL)

COLLECTION_URL = ['antibodies', 'biosamples', 'experiments']
antibodies_mapping = {'basic': {'properties': {'_embedded': {'type': 'nested', 'properties': {'antibody_lot': {'type': 'nested', 'properties': {'source': {'type': 'nested'}}}, 'target': {'type': 'nested', 'properties': {'lab': {'type': 'nested'}, 'award': {'type': 'nested'}, 'submitter': {'type': 'nested'}, 'organism': {'type': 'nested'}, 'date_created': {'type': 'string', 'index': 'not_analyzed'}, 'geneid_dbxref_list': {'type': 'string', 'index': 'not_analyzed'}}}}}}}}
biosamples_mapping = {'basic': {'properties': {'_embedded': {'type': 'nested', 'properties': {'lot_id': {'type': 'string'}, 'donor': {'type': 'nested'}, 'lab': {'type': 'nested'}, 'award': {'type': 'nested'}, 'submitter': {'type': 'nested'}, 'source': {'type': 'nested'}, 'treatments': {'type': 'nested'}, 'constructs': {'type': 'nested'}}}}}}
experiments_mapping = {'basic': {'properties': {'_embedded': {'type': 'nested', 'properties': {'replicates': {'type': 'nested'}}}}}}


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
        resources = item_json.json['_embedded']['resources']
        data = {}
        for link in links:
            if link == 'antibody_lot':
                data['antibody_lot'] = resources[links[link].get('href')]
                data['antibody_lot']['source'] = resources[resources[links[link].get('href')]['_links']['source'].get('href')]
            elif link == 'target':
                data['target'] = item_json.json['_embedded']['resources'][links[link].get('href')]
                data['target']['lab'] = resources[resources[links[link].get('href')]['_links']['lab'].get('href')]
                data['target']['award'] = resources[resources[links[link].get('href')]['_links']['award'].get('href')]
                data['target']['organism'] = resources[resources[links[link].get('href')]['_links']['organism'].get('href')]
                data['target']['submitter'] = resources[resources[links[link].get('href')]['_links']['submitter'].get('href')]
        antibody['_embedded'] = data
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
        resources = item_json.json['_embedded']['resources']
        data = {}
        for link in links:
            if link == 'treatments' and len(links[link]):
                treatments = []
                for treatment in links[link]:
                    treatments.append(resources[treatment.get('href')])
                data['treatments'] = list()
                data['treatments'].append(treatments)
            elif link == 'constructs' and len(links[link]):
                constructs = []
                for construct in links[link]:
                    constructs.append(resources[construct.get('href')])
                data['constructs'] = list()
                data['constructs'].append(constructs)
        data['lab'] = resources[biosample['_links']['lab'].get('href')]
        data['donor'] = resources[biosample['_links']['donor'].get('href')]
        data['award'] = resources[biosample['_links']['award'].get('href')]
        data['source'] = resources[biosample['_links']['source'].get('href')]
        data['submitter'] = resources[biosample['_links']['submitter'].get('href')]
        biosample['_embedded'] = data
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
        data = {}
        for link in links:
            if link == 'replicates' and len(links[link]):
                replicates = []
                for replicate in links[link]:
                    replicates.append(item_json.json['_embedded']['resources'][replicate.get('href')])
                data['replicates'] = list()
                data['replicates'].append(replicates)
        experiment['_embedded'] = data
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
