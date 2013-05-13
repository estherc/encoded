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
    finalResults = []
    for result in results:
        source = result.get('_source')
        finalResults.append(source['description'] + ' (' + source['termID'] + ')')
    return finalResults


def getLabs(term):
    ''' return labs for user '''

    # This should rather be a nested query in Elastic Search
    users = es.search('_uuid:' + term , index=['users'], doc_type=[DOCTYPE])
    users_data = users.get('hits')['hits']
    finalResults = {}
    for user_data in users_data:
        labs = user_data.get('_source')['lab_uuids']
        print labs
        for lab in labs:
            lab_data = es.search('_uuid:' + lab, index=['labs'], doc_type=[DOCTYPE])
            results = lab_data.get('hits')['hits']
            for result in results:
                source = result.get('_source')
                finalResults[source['_uuid']] = source['name']
    return finalResults


def getAwards(term):
    ''' return grants for the lab '''

    labs = es.search('_uuid:' + term, index=['labs'], doc_type=[DOCTYPE])
    labs_data = labs.get('hits')['hits']
    finalResults = {}
    for lab_data in labs_data:
        award_uuids = lab_data.get('_source')['award_uuids']
        for award_uuid in award_uuids:
            awards = es.search('_uuid:' + award_uuid, index=['awards'], doc_type=[DOCTYPE])
            results = (awards.get('hits')['hits'])
            for result in results:
                finalResults[result.get('_source')['_uuid']] = result.get('_source')['number']
    return finalResults


@view_config(name='search', context=Root, subpath_segments=0, request_method='GET')
def search(context, request):
    ''' Landing spot for search'''

    queryTerm = request.GET.get('query')
    index = request.GET.get('index')
    if index == 'ontology':
        return ontology(queryTerm)
    elif index == 'labs':
        return getLabs(queryTerm)
    else:
        return getAwards(queryTerm)
