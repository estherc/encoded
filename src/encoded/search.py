from .contentbase import Root
from pyramid.view import view_config
from pyelasticsearch import ElasticSearch

from .storage import (
    DBSession,
    CurrentStatement,
)

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


@view_config(name='search', context=Root, subpath_segments=0, request_method='GET')
def search(context, request):
    ''' Landing spot for search'''

    queryTerm = request.GET.get('query')
    index = request.GET.get('index')
    if index == 'ontology':
        return ontology(queryTerm)


@view_config(name='generate_accession', context=Root, subpath_segments=0, request_method='GET')
def generateAccession(context, request):
    ''' Generate biosample Accession '''

    item_type = request.get('HTTP_REFERER')
    item = item_type.split('/')
    if item[2] == 'biosamples':
        return 'ENCBS000EAA'
    elif item[2] == 'biosamples':
        return 'ENCSR000EAA'
    elif item[2] == 'antibodies':
        return 'ENCAB000EAA'


@view_config(name='get_data', context=Root, subpath_segments=0, request_method='GET')
def getData(context, request):

    # hard(horrible) coding everything, this method should be gone after the Consortium meeting
    predicate = request.GET.get('collection')
    session = DBSession()
    if predicate == 'award':
        query = session.query(CurrentStatement).filter(CurrentStatement.predicate == 'lab')
    else:
        query = session.query(CurrentStatement).filter(CurrentStatement.predicate == predicate)
    data = {}
    for model in query.all():
        value = ''
        if predicate == 'source':
            value = (model.statement.object)['source_name']
            data[str(model.rid)] = value
        elif predicate == 'antibody_lots':
            if request.GET.get('column') == 'lot':
                value = (model.statement.object)['lot_id']
            else:
                value = (model.statement.object)['product_id']
            data[str(model.rid)] = value
        elif predicate == 'target':
            value = (model.statement.object)['target_label']
            data[str(model.rid)] = value
        elif predicate == 'donor':
            value = (model.statement.object)['donor_id']
            data[str(model.rid)] = value
        elif predicate == 'lab':
            lab = request.GET.get('id')
            if str(model.rid) == lab:
                value = (model.statement.object)['name']
                data[str(model.rid)] = value
        elif predicate == 'award':
            lab = request.GET.get('id')
            if str(model.rid) == lab:
                award_list = (model.statement.object)['award_uuids']
                newQuery = session.query(CurrentStatement).filter(CurrentStatement.predicate == 'award')
                for newModel in newQuery.all():
                    if str(newModel.rid) in award_list:
                        data[str(newModel.rid)] = (newModel.statement.object)['number']
    return data
