from pyramid import paster
from pyelasticsearch import ElasticSearch

ES_URL = 'http://localhost:9200'
DOCTYPE = 'basic'
es = ElasticSearch(ES_URL)

COLLECTION_URL = ['antibodies']
antibodies_mapping = {'basic': {'properties': {'antibody_lot': {'type': 'nested'}}}}
biosamples_mapping = {'basic': {'properties': {'treatment': {'type': 'nested'}}}}
experiments_mapping = {'basic': {'properties': {'library': {'type': 'nested'}}}}


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
        es.delete_index(url)
        es.create_index(url)
        es.put_mapping(url, 'basic', {'basic': {'properties': {'antibody_lot': {'type': 'nested'}}}})
        for item in items:
            item_url = str(item.get('href'))
            item_json = testapp.get(item_url, headers={'Accept': 'application/json'}, status=200)
            id = str(item_json.json['_links']['self']['href'])[-36:]
            links = item_json.json['_links']
            for link in links:
                if link is 'antibody_lot':
                    print links[link]
                #import pdb; pdb.set_trace();

if __name__ == '__main__':
    main()
