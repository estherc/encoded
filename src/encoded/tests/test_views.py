import pytest

COLLECTION_URLS = [
    '/',
    '/antibodies/',
    '/targets/',
    '/organisms/',
    '/sources/',
    '/validations/',
    '/antibody-lots/',
]

## since we have cleaned up all the errors
## the below should equal the full spreadsheet rows with text in the 'test' col.
COLLECTION_URL_LENGTH = {
    '/awards/': 39,
    '/labs/': 45,
    '/users/': 83,
    '/organisms/': 6,
    '/sources/': 77,
    '/targets/': 30,
    '/antibody-lots/': 29,
    '/validations/': 41,
    '/antibodies/': 30,
    '/donors/': 72,
    '/documents/': 130,
    '/treatments/': 7,
    '/constructs/': 5,
    '/biosamples/': 134,
    '/platforms/': 11,
    '/users/': 84,
    '/files/': 18,
    '/replicates/': 47,
    '/libraries/': 49,
    '/experiments/': 28,

}

COLLECTION_URLS = ['/'] + COLLECTION_URL_LENGTH.keys()


@pytest.mark.parametrize('url', [url for url in COLLECTION_URLS if url != '/users/'])
def test_html(htmltestapp, url):
    res = htmltestapp.get(url, status=200)
    assert res.body.startswith('<!DOCTYPE html>')


@pytest.mark.parametrize('url', COLLECTION_URLS)
def test_json(testapp, url):
    res = testapp.get(url, status=200)
    assert res.json['@type']


def test_json_basic_auth(htmltestapp):
    import base64
    url = '/'
    value = "Authorization: Basic %s" % base64.b64encode('nobody:pass')
    res = htmltestapp.get(url, headers={'Authorization': value}, status=200)
    assert res.json['@id']


def _test_antibody_approval_creation(testapp):
    from urlparse import urlparse
    new_antibody = {'foo': 'bar'}
    res = testapp.post_json('/antibodies/', new_antibody, status=201)
    assert res.location
    assert '/profiles/result' in res.json['@type']['profile']
    assert res.json['items'] == [{'href': urlparse(res.location).path}]
    res = testapp.get(res.location, status=200)
    assert '/profiles/antibody_approval' in res.json['@type']
    data = res.json
    for key in new_antibody:
        assert data[key] == new_antibody[key]
    res = testapp.get('/antibodies/', status=200)
    assert len(res.json['items']) == 1


def __test_sample_data(testapp):

    from .sample_data import test_load_all
    test_load_all(testapp)
    res = testapp.get('/biosamples/', headers={'Accept': 'application/json'}, status=200)
    assert len(res.json['_embedded']['items']) == 1
    res = testapp.get('/labs/', headers={'Accept': 'application/json'}, status=200)
    assert len(res.json['_embedded']['items']) == 2


@pytest.mark.slow
@pytest.mark.parametrize(('url', 'length'), COLLECTION_URL_LENGTH.items())
def test_load_workbook(workbook, testapp, url, length):
    # testdata must come before testapp in the funcargs list for their
    # savepoints to be correctly ordered.
    res = testapp.get(url + '?limit=all', status=200)
    assert len(res.json['items']) >= length
    # extra guys are fine


@pytest.mark.slow
def test_collection_limit(workbook, testapp):
    res = testapp.get('/antibodies/?limit=10', status=200)
    assert len(res.json['items']) == 10


@pytest.mark.parametrize('url', ['/organisms/', '/sources/', '/users/'])
def test_collection_post(testapp, url):
    from .sample_data import URL_COLLECTION
    collection = URL_COLLECTION[url]
    for item in collection:
        res = testapp.post_json(url, item, status=201)
        assert item['_uuid'] in res.location


@pytest.mark.parametrize('url', ['/organisms/', '/sources/'])
def test_collection_post_bad_json(testapp, url):
    collection = [{'foo': 'bar'}]
    for item in collection:
        res = testapp.post_json(url, item, status=422)
        assert res.json['errors']


def test_actions_filtered_by_permission(testapp, anontestapp):
    from .sample_data import URL_COLLECTION
    url = '/sources/'
    collection = URL_COLLECTION[url]
    item = collection[0]
    res = testapp.post_json(url, item, status=201)
    location = res.location

    res = testapp.get(location)
    assert any(action for action in res.json['actions'] if action['name'] == 'edit')

    res = anontestapp.get(location)
    assert not any(action for action in res.json['actions'] if action['name'] == 'edit')


@pytest.mark.parametrize('url', ['/organisms/', '/sources/'])
def test_collection_update(testapp, url, execute_counter):
    from .sample_data import URL_COLLECTION
    collection = URL_COLLECTION[url]
    initial = collection[0]
    res = testapp.post_json(url, initial, status=201)
    item_url = res.json['items'][0]

    with execute_counter.expect(2):
        res = testapp.get(item_url).json

    del initial['_uuid']
    for key in initial:
        assert res[key] == initial[key]

    update = collection[1].copy()
    del update['_uuid']
    testapp.post_json(item_url, update, status=200)

    with execute_counter.expect(2):
        res = testapp.get(item_url).json

    for key in update:
        assert res[key] == update[key]


# TODO Add 2 tests for duplicate UUIDs (see sample_data.py)
def test_post_duplicate_uuid(testapp):
    from .sample_data import BAD_LABS
    testapp.post_json('/labs/', BAD_LABS[0], status=201)
    testapp.post_json('/labs/', BAD_LABS[1], status=409)


def test_post_repeated_uuid(testapp):
    from .sample_data import LABS
    from .sample_data import BAD_AWARDS
    # these are in a funny order but not setting up relationships anyhoo
    for lab in LABS:
        testapp.post_json('/labs/', lab, status=201)

    testapp.post_json('/awards/', BAD_AWARDS[0], status=201)
    testapp.post_json('/awards/', BAD_AWARDS[0], status=409)


def test_users_post(testapp, anontestapp):
    from .sample_data import URL_COLLECTION
    url = '/users/'
    item = URL_COLLECTION[url][0]
    testapp.post_json(url, item, status=201)
    res = anontestapp.get('/@@testing-user',
                          extra_environ={'REMOTE_USER': item['email']})
    assert sorted(res.json['effective_principals']) == [
        'lab:2c334112-288e-4d45-9154-3f404c726daf',
        'remoteuser:%s' % item['email'],
        'system.Authenticated',
        'system.Everyone',
        'userid:e9be360e-d1c7-4cae-9b3a-caf588e8bb6f',
    ]


def test_users_view_details_admin(testapp):
    from .sample_data import URL_COLLECTION
    url = '/users/'
    item = URL_COLLECTION[url][0]
    res = testapp.post_json(url, item, status=201)
    location = res.location
    res = testapp.get(location)

    assert 'email' in res.json


def test_users_view_basic_anon(testapp, anontestapp):
    from .sample_data import URL_COLLECTION
    url = '/users/'
    item = URL_COLLECTION[url][0]
    res = testapp.post_json(url, item, status=201)
    location = res.location
    res = anontestapp.get(location)

    assert 'first_name' in res.json
    assert 'email' not in res.json


def test_users_list_denied_anon(anontestapp):
    anontestapp.get('/users/', status=403)


def test_etags(testapp):
    url = '/organisms/'
    from .sample_data import URL_COLLECTION
    collection = URL_COLLECTION[url]
    item = collection[0]
    res = testapp.post_json(url, item, status=201)
    res = testapp.get(url, status=200)
    etag = res.etag
    res = testapp.get(url, headers={'If-None-Match': etag}, status=304)
    item = collection[1]
    res = testapp.post_json(url, item, status=201)
    res = testapp.get(url, headers={'If-None-Match': etag}, status=200)
    assert res.etag != etag
