from pydantic_xml import BaseXmlModel, element



class Prop(BaseXmlModel, tag='prop', ns_attrs=True, ns='a'):
    content_type: str = element(tag='getcontenttype')
    content_length: int = element(tag='getcontentlength')

class PropStat(BaseXmlModel, tag='propstat', ns_attrs=True, ns='a'):
    status: str = element()
    prop: Prop = element()

class Response(BaseXmlModel, tag='response', ns_attrs=True, ns='a'):
    href: str = element()
    propstat: PropStat = element()

class Multistatus(BaseXmlModel, tag='multistatus', ns_attrs=True, ns='a', nsmap={'a': 'DAV:', 'b': 'urn:uuid:c2f41010-65b3-11d1-a29f-00aa00c14882'}):
     response: Response = element()


