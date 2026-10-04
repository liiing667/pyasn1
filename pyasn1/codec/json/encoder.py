#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
from collections import OrderedDict
import base64
import json
import warnings

from pyasn1 import debug
from pyasn1 import error
from pyasn1.compat import _MISSING
from pyasn1.type import base
from pyasn1.type import char
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['encode']

LOG = debug.registerLoggee(__name__, flags=debug.DEBUG_ENCODER)


class AbstractItemEncoder(object):
    #: JSON type label identifying the ASN.1 type on the wire
    label = None

    def encode(self, value, encodeFun, **options):
        raise error.PyAsn1Error('Not implemented')


class BooleanEncoder(AbstractItemEncoder):
    label = 'Boolean'

    def encode(self, value, encodeFun, **options):
        return bool(value)


class IntegerEncoder(AbstractItemEncoder):
    label = 'Integer'

    def encode(self, value, encodeFun, **options):
        return int(value)


class EnumeratedEncoder(IntegerEncoder):
    label = 'Enumerated'


class BitStringEncoder(AbstractItemEncoder):
    label = 'BitString'

    def encode(self, value, encodeFun, **options):
        return value.asBinary()


class OctetStringEncoder(AbstractItemEncoder):
    label = 'OctetString'

    def encode(self, value, encodeFun, **options):
        return base64.b64encode(value.asOctets()).decode('ascii')


class NullEncoder(AbstractItemEncoder):
    label = 'Null'

    def encode(self, value, encodeFun, **options):
        return None


class ObjectIdentifierEncoder(AbstractItemEncoder):
    label = 'ObjectIdentifier'

    def encode(self, value, encodeFun, **options):
        return str(value)


class RelativeOIDEncoder(ObjectIdentifierEncoder):
    label = 'RelativeOID'


class RealEncoder(AbstractItemEncoder):
    label = 'Real'

    def encode(self, value, encodeFun, **options):
        return float(value)


class TextStringEncoder(AbstractItemEncoder):
    def __init__(self, label):
        self.label = label

    def encode(self, value, encodeFun, **options):
        return str(value)


class SetEncoder(AbstractItemEncoder):
    label = 'Set'
    protoDict = OrderedDict

    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise error.PyAsn1Error(
                f"ASN.1 object {value.__class__.__name__} is inconsistent")

        namedTypes = value.componentType
        substrate = self.protoDict()

        for idx in range(value._componentTypeLen or len(value._dynamicNames)):
            if namedTypes:
                namedType = namedTypes[idx]
                key = namedType.name
                subValue = value.getComponentByPosition(idx, instantiate=False)

                if subValue is univ.noValue:
                    if namedType.isDefaulted:
                        subValue = namedType.asn1Object
                    elif namedType.isOptional:
                        continue
                    else:
                        subValue = namedType.asn1Object

            else:
                key = value._dynamicNames.getNameByPosition(idx)
                subValue = value.getComponentByPosition(idx, instantiate=False)

            substrate[key] = encodeFun(subValue, **options)
        return substrate


class SequenceEncoder(SetEncoder):
    label = 'Sequence'


class SequenceOfEncoder(AbstractItemEncoder):
    label = 'SequenceOf'

    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise error.PyAsn1Error(
                f"ASN.1 object {value.__class__.__name__} is inconsistent")
        return [encodeFun(x, **options) for x in value]


class SetOfEncoder(SequenceOfEncoder):
    label = 'SetOf'


class ChoiceEncoder(AbstractItemEncoder):
    label = 'Choice'
    protoDict = OrderedDict

    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise error.PyAsn1Error(
                f"ASN.1 object {value.__class__.__name__} is inconsistent")

        substrate = self.protoDict()

        for key, subValue in value.items():
            substrate[key] = encodeFun(subValue, **options)

        return substrate


class AnyEncoder(AbstractItemEncoder):
    label = 'Any'

    def encode(self, value, encodeFun, **options):
        return base64.b64encode(value.asOctets()).decode('ascii')


TAG_MAP = {
    univ.Boolean.tagSet: BooleanEncoder(),
    univ.Integer.tagSet: IntegerEncoder(),
    univ.BitString.tagSet: BitStringEncoder(),
    univ.OctetString.tagSet: OctetStringEncoder(),
    univ.Null.tagSet: NullEncoder(),
    univ.ObjectIdentifier.tagSet: ObjectIdentifierEncoder(),
    univ.RelativeOID.tagSet: RelativeOIDEncoder(),
    univ.Enumerated.tagSet: EnumeratedEncoder(),
    univ.Real.tagSet: RealEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.SequenceOf.tagSet: SequenceOfEncoder(),
    univ.SetOf.tagSet: SetOfEncoder(),
    univ.Choice.tagSet: ChoiceEncoder(),
    # character string types
    char.UTF8String.tagSet: TextStringEncoder('UTF8String'),
    char.NumericString.tagSet: TextStringEncoder('NumericString'),
    char.PrintableString.tagSet: TextStringEncoder('PrintableString'),
    char.TeletexString.tagSet: TextStringEncoder('TeletexString'),
    char.VideotexString.tagSet: TextStringEncoder('VideotexString'),
    char.IA5String.tagSet: TextStringEncoder('IA5String'),
    char.GraphicString.tagSet: TextStringEncoder('GraphicString'),
    char.VisibleString.tagSet: TextStringEncoder('VisibleString'),
    char.GeneralString.tagSet: TextStringEncoder('GeneralString'),
    char.UniversalString.tagSet: TextStringEncoder('UniversalString'),
    char.BMPString.tagSet: TextStringEncoder('BMPString'),
    # useful types
    useful.ObjectDescriptor.tagSet: TextStringEncoder('ObjectDescriptor'),
    useful.GeneralizedTime.tagSet: TextStringEncoder('GeneralizedTime'),
    useful.UTCTime.tagSet: TextStringEncoder('UTCTime')
}

# Put in ambiguous & non-ambiguous types for faster codec lookup
TYPE_MAP = {
    univ.Boolean.typeId: BooleanEncoder(),
    univ.Integer.typeId: IntegerEncoder(),
    univ.BitString.typeId: BitStringEncoder(),
    univ.OctetString.typeId: OctetStringEncoder(),
    univ.Null.typeId: NullEncoder(),
    univ.ObjectIdentifier.typeId: ObjectIdentifierEncoder(),
    univ.RelativeOID.typeId: RelativeOIDEncoder(),
    univ.Enumerated.typeId: EnumeratedEncoder(),
    univ.Real.typeId: RealEncoder(),
    # Sequence & Set have same tags as SequenceOf & SetOf
    univ.Set.typeId: SetEncoder(),
    univ.SetOf.typeId: SetOfEncoder(),
    univ.Sequence.typeId: SequenceEncoder(),
    univ.SequenceOf.typeId: SequenceOfEncoder(),
    univ.Choice.typeId: ChoiceEncoder(),
    univ.Any.typeId: AnyEncoder(),
    # character string types
    char.UTF8String.typeId: TextStringEncoder('UTF8String'),
    char.NumericString.typeId: TextStringEncoder('NumericString'),
    char.PrintableString.typeId: TextStringEncoder('PrintableString'),
    char.TeletexString.typeId: TextStringEncoder('TeletexString'),
    char.VideotexString.typeId: TextStringEncoder('VideotexString'),
    char.IA5String.typeId: TextStringEncoder('IA5String'),
    char.GraphicString.typeId: TextStringEncoder('GraphicString'),
    char.VisibleString.typeId: TextStringEncoder('VisibleString'),
    char.GeneralString.typeId: TextStringEncoder('GeneralString'),
    char.UniversalString.typeId: TextStringEncoder('UniversalString'),
    char.BMPString.typeId: TextStringEncoder('BMPString'),
    # useful types
    useful.ObjectDescriptor.typeId: TextStringEncoder('ObjectDescriptor'),
    useful.GeneralizedTime.typeId: TextStringEncoder('GeneralizedTime'),
    useful.UTCTime.typeId: TextStringEncoder('UTCTime')
}


class SingleItemEncoder(object):

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP

    def __init__(self, tagMap=_MISSING, typeMap=_MISSING, **ignored):
        self._tagMap = tagMap if tagMap is not _MISSING else self.TAG_MAP
        self._typeMap = typeMap if typeMap is not _MISSING else self.TYPE_MAP

    def __call__(self, value, **options):
        if not isinstance(value, base.Asn1Item):
            raise error.PyAsn1Error(
                'value is not valid (should be an instance of an ASN.1 Item)')

        if LOG:
            debug.scope.push(type(value).__name__)
            LOG('encoder called for type %s '
                '<%s>' % (type(value).__name__, value.prettyPrint()))

        tagSet = value.tagSet

        try:
            concreteEncoder = self._typeMap[value.typeId]

        except KeyError:
            # use base type for codec lookup to recover untagged types
            baseTagSet = tag.TagSet(
                value.tagSet.baseTag, value.tagSet.baseTag)

            try:
                concreteEncoder = self._tagMap[baseTagSet]

            except KeyError:
                raise error.PyAsn1Error('No encoder for %s' % (value,))

        if LOG:
            LOG('using value codec %s chosen by '
                '%s' % (concreteEncoder.__class__.__name__, tagSet))

        pyObject = concreteEncoder.encode(value, self, **options)

        if LOG:
            LOG('encoder %s produced: '
                '%s' % (type(concreteEncoder).__name__, repr(pyObject)))
            debug.scope.pop()

        return OrderedDict((('type', concreteEncoder.label),
                            ('value', pyObject)))


class Encoder(object):
    SINGLE_ITEM_ENCODER = SingleItemEncoder

    def __init__(self, **options):
        self._singleItemEncoder = self.SINGLE_ITEM_ENCODER(**options)

    def __call__(self, pyObject, asn1Spec=None, **options):
        return json.dumps(
            self._singleItemEncoder(pyObject, **options))


#: Turns ASN.1 object into a JSON document.
#:
#: Takes any ASN.1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#: walks all its components recursively and produces a self-describing JSON
#: document: every value is serialized as an object holding an ASN.1 type
#: label (``type``) and the JSON-mapped value (``value``), so that the
#: decoder can reconstruct the ASN.1 types even without a schema.
#:
#: Parameters
#: ----------
#  asn1Value: any pyasn1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#:     pyasn1 object to encode (or a tree of them)
#:
#: Returns
#: -------
#: : :py:class:`str`
#:     JSON document
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error
#:     On encoding errors
#:
#: Examples
#: --------
#: Encode ASN.1 value object into a JSON document
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> seq.extend([1, 2, 3])
#:    >>> encode(seq)
#:    '{"type": "SequenceOf", "value": [{"type": "Integer", "value": 1}, ...]}'
#:
encode = Encoder()

def __getattr__(attr: str):
    if newAttr := {"tagMap": "TAG_MAP", "typeMap": "TYPE_MAP"}.get(attr):
        warnings.warn(f"{attr} is deprecated. Please use {newAttr} instead.", DeprecationWarning, stacklevel=2)
        return globals()[newAttr]
    raise AttributeError(attr)
