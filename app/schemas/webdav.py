from typing import Optional

from pydantic_xml import BaseXmlModel, element

NS_PARAMS = {
    'ns_attrs': True,
    'ns': 'D',
    'nsmap': {'D': 'DAV:', 'Z': 'urn:schemas-microsoft-com:'}
}


class Collection(BaseXmlModel, tag='collection', **NS_PARAMS):
    actual: bool = element('collection')


class Prop(BaseXmlModel, tag='prop', **NS_PARAMS):
    content_type: str = element(tag='getcontenttype', **NS_PARAMS)
    content_length: Optional[int] = element(tag='getcontentlength', **NS_PARAMS)
    creation_date: Optional[str] = element(tag='creationdate', **NS_PARAMS)
    display_name: Optional[str] = element(tag='displayname', **NS_PARAMS)
    source: Optional[str] = element(tag='source', **NS_PARAMS)
    content_language: Optional[str] = element(tag='getcontentlanguage', **NS_PARAMS)
    last_modified: Optional[str] = element(tag='getlastmodified', **NS_PARAMS)
    e_tag: Optional[str] = element(tag='getetag', **NS_PARAMS)
    resource_type: Optional[Collection] = element(tag='resourcetype', **NS_PARAMS)
    is_collection: Optional[int] = element(tag='iscollection', **NS_PARAMS)

    quota_available_bytes: Optional[int] = element(tag='quota-available-bytes', default=None, **NS_PARAMS)
    quota_used_bytes: Optional[int] = element(tag='quota-used-bytes', default=None, **NS_PARAMS)
    quota: Optional[int] = element(tag='quota', default=None, **NS_PARAMS)
    quotaused: Optional[int] = element(tag='quotaused', default=None, **NS_PARAMS)


class PropStat(BaseXmlModel, tag='propstat', **NS_PARAMS):
    status: str = element(**NS_PARAMS)
    prop: Prop = element(**NS_PARAMS)


class Response(BaseXmlModel, tag='response', **NS_PARAMS):
    href: str = element(**NS_PARAMS)
    propstat: PropStat = element(**NS_PARAMS)


class Multistatus(BaseXmlModel, tag='multistatus', **NS_PARAMS):
    response: list[Response] = element(**NS_PARAMS)
