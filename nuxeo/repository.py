__author__ = 'loopingz'
from document import Document
from urllib import urlencode


class Repository(object):

    def __init__(self, name, service, schemas=[]):
        self._name = name
        self._service = service
        self._schemas = schemas

    def _get_path(self, path):
        if path.startswith('/'):
            return "repo/" + self._name + "/path/" + path
        else:
            return "repo/" + self._name + "/id/" + path

    def get(self, path):
        return self._service.request(self._get_path(path), extra_headers=self._get_extra_headers())

    def fetch(self, path):
        return Document(self.get(path), self)

    def fetch_audit(self, path):
        return self._service.request(self._get_path(path) + "/@audit")

    def fetch_blob(self, path, xpath = 'blobholder:0'):
        return self._service.request(self._get_path(path) + "/@blob/" + xpath, extra_headers=self._get_extra_headers())

    def fetch_rendition(self, path, name):
        return self._service.request(self._get_path(path) + "/@rendition/" + name, extra_headers=self._get_extra_headers())

    def fetch_renditions(self, path):
        renditions = []
        for rendition in self._service.request(self._get_path(path),
                extra_headers=self._get_extra_headers({'enrichers-document':'renditions'}))["contextParameters"]["renditions"]:
            renditions.append(rendition['name'])
        return renditions

    def fetch_acls(self, path):
        acls = []
        for acl in self._service.request(self._get_path(path),
                extra_headers={'enrichers-document':'acls'})["contextParameters"]["acls"]:
            acls.append(acl)
        return acls

    def add_permission(self, uid, params):
        operation = self._service.operation('Document.AddPermission')
        operation.input(uid)
        operation.params(params)
        operation.execute()

    def remove_permission(self, uid, params):
        operation = self._service.operation('Document.RemovePermission')
        operation.input(uid)
        operation.params(params)
        operation.execute()

    def has_permission(self, path, permission):
        return permission in self._service.request(self._get_path(path),
                    extra_headers={'enrichers-document':'permissions'})["contextParameters"]["permissions"]

    def fetch_lock_status(self, path):
        res = self._service.request(self._get_path(path), extra_headers={'fetch-document':'lock'})
        if 'lockOwner' in res:
            return {'lockCreated': res['lockOwner'], 'lockOwner': res['lockOwner']}
        return {}

    def unlock(self, uid):
        operation = self._service.operation('Document.Unlock')
        operation.input(uid)
        return operation.execute()

    def lock(self, uid):
        operation = self._service.operation('Document.Lock')
        operation.input(uid)
        return operation.execute()

    def convert(self, path, options):
        xpath = options['xpath'] if 'xpath' in options else 'blobholder:0'
        path = self._get_path(path) + "/@blob/" + xpath + '/@convert'
        if 'xpath' in options:
            del options['xpath']
        if ("converter" not in options and "type" not in options and "format" not in options):
            raise ValueError("One of converter,type,format is mandatory in options")
        path += "?" + urlencode(options, True)
        return self._service.request(path)

    def update(self, obj, uid=None):
        if isinstance(obj, Document):
            properties = obj.properties
            uid = obj.get_id()
        elif isinstance(obj, dict):
            properties = obj
        else:
            raise Exception("Argument should be either a dict or a Document object")
        body = {
            'entity-type': 'document',
            'uid': uid,
            'properties': properties
        }
        return Document(self._service.request(self._get_path(uid), body=body, method="PUT", extra_headers=self._get_extra_headers()), self)

    def _get_extra_headers(self, extras=dict()):
        extras_header = dict()
        if len(self._schemas) > 0:
            extras_header['X-NXDocumentProperties'] = ",".join(self._schemas)
        extras_header['X-NXRepository'] = self._name
        extras_header.update(extras)
        return extras_header

    def create(self, path, obj):
        body = {
            'entity-type': 'document',
            'type': obj['type'],
            'name': obj['name'],
            'properties': obj['properties']
        }

        return Document(self._service.request(self._get_path(path), body=body, method="POST", extra_headers=self._get_extra_headers()), self)

    def delete(self, path):
        self._service.request(self._get_path(path), method="DELETE")

    def query(self, opts = dict()):
        path = 'query/'
        if 'query' in opts:
            path += 'NXQL'
        elif 'pageProvider' in opts:
            path += opts['pageProvider']
        else:
            raise Exception("Need either a pageProvider or a query")
        path += "?" + urlencode(opts, True)
        result = self._service.request(path, extra_headers=self._get_extra_headers())
        # Mapping entries to Document
        docs = []
        for doc in result['entries']:
            docs.append(Document(doc, self))
        result['entries']=docs
        return result

    def follow_transition(self, uid, name):
        operation = self._service.operation('Document.FollowLifecycleTransition')
        operation.input(uid)
        operation.params({'value': name})
        operation.execute()

    def move(self, uid, dst, name = None):
        operation = self._service.operation('Document.Move')
        operation.input(uid)
        params = {'target': dst}
        if name:
            params['name'] = name
        operation.params(params)
        operation.execute()

    def start_workflow(self, name, path, options):
        return self._service.workflows().start(name, options, url=self._get_path(path) + "/@workflow")

    def fetch_workflows(self, path):
        from workflow import Workflow
        return self._service.workflows()._map(self._service.request(self._get_path(path)+"/@workflow"), Workflow)