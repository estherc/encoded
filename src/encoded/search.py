from .contentbase import Root
from pyramid.view import view_config
from pyelasticsearch import ElasticSearch

URL = 'http://localhost:9200'
DOCTYPE = 'basic'
es = ElasticSearch(URL)


def includeme(config):
    config.scan(__name__)


def ontology(term):
    ''' Searching ontology'''

    es_results = es.search('description:' + term, index=['ontology'], doc_type=[DOCTYPE])
    results = es_results.get('hits')['hits']
    finalResults = {}
    for result in results:
        source = result.get('_source')
        finalResults[source['termID']] = source['description']
    return finalResults


def getDonors(term):
    ''' Searching Donors '''

    es_results = es.search('donor_id:' + term + '*', index=['donors'], doc_type=[DOCTYPE])
    results = es_results.get('hits')['hits']
    finalResults = {}
    for result in results:
        source = result.get('_source')
        finalResults[source['_uuid']] = source['donor_id']
    return finalResults


def getSources(term):
    ''' Searching Sources '''

    es_results = es.search('source_name:' + term, index=['sources'], doc_type=[DOCTYPE])
    results = es_results.get('hits')['hits']
    finalResults = {}
    for result in results:
        source = result.get('_source')
        finalResults[source['_uuid']] = source['source_name']
    return finalResults


@view_config(name='search', context=Root, subpath_segments=0, request_method='GET')
def search(context, request):
    ''' Landing spot for search'''

    queryTerm = request.GET.get('query')
    index = request.GET.get('index')
    if index == 'ontology':
        return ontology(queryTerm)
    elif index == 'donor':
        return getDonors(queryTerm)
    else:
        return getSources(queryTerm)


@view_config(name='generate_accession', context=Root, subpath_segments=0, request_method='GET')
def generateAccession(context, request):
    ''' Generate biosample Accession '''
    accession = 'ENCBSNNNEAA'
    return accession
