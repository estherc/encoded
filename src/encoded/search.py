from .contentbase import Root
from pyramid.view import view_config
from pyelasticsearch import ElasticSearch

from .storage import (
    DBSession,
    CurrentStatement,
)

# temp code for before conference
biosample_count = 0
experiment_count = 0
antibody_count = 0

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
    alphabets = map(chr, range(65, 91))
    accession = ''
    if item[3] == 'biosamples':
        biosample_prefix = 'ENCBS000EA'
        accession = biosample_prefix + alphabets[biosample_count]
        global biosample_count
        biosample_count = biosample_count + 1
    elif item[3] == 'experiments':
        experiment_prefix = 'ENCSR000KA'
        accession = experiment_prefix + alphabets[experiment_count]
        global experiment_count
        experiment_count = experiment_count + 1
    elif item[3] == 'antibodies':
        antibody_prefix = 'ENCBS000BA'
        accession = antibody_prefix + alphabets[antibody_count]
        global antibody_count
        antibody_count = antibody_count + 1
    return accession


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
