from .contentbase import Root
from pyramid.view import view_config
from pyelasticsearch import ElasticSearch

import json

URL = 'http://localhost:9200'
INDEX = 'ontology'
DOCTYPE = 'basic'


def includeme(config):
    config.scan(__name__)


@view_config(name='elasticsearch', context=Root, subpath_segments=0, request_method='GET')
def elasticsearch(context, request):

	data = request.GET.get('q')
	es = ElasticSearch(URL)
	query = {
				'query': {
					'text': {
						'termID':data
					}
				} 
			}
	es_results = es.search(query, index=[INDEX], doc_type=[DOCTYPE])
	results = es_results.get('hits')['hits']
	finalResults = []
	for result in results:
		finalResults.append(result.get('_source')['termID'])
	return finalResults
