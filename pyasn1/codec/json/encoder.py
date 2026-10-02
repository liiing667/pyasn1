#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import base64
import json

from collections import OrderedDict

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
    typeName = None

    def encode(self, value, encodeFun, **options):
        raise error.PyAsn1Error('Not implemented')


class BooleanEncoder(AbstractItemEncoder):
    typeName = 'Boolean'

    def encode(self, value, encodeFun, **options):
        return bool(value)


class IntegerEncoder(AbstractItemEncoder):
    typeName = 'Integer'

    def encode(self, value, encodeFun, **options):
        return int(value)


class EnumeratedEncoder(IntegerEncoder):
    typeName = 'Enumerated'


class BitStringEncoder(AbstractItemEncoder):
    typeName = 'BitString'

    def encode(self, value, encodeFun, **options):
        return value.asBinary()


class OctetStringEncoder(AbstractItemEncoder):
    typeName = 'OctetString'

    def encode(self, value, encodeFun, **options):
        return base64.b64encode(value.asOctets()).decode('ascii')


class NullEncoder(AbstractItemEncoder):
    typeName = 'Null'

    def encode(self, value, encodeFun, **options):
        return None


class ObjectIdentifierEncoder(AbstractItemEncoder):
    typeName = 'ObjectIdentifier'

    def encode(self, value, encodeFun, **options):
        return str(value)


class RelativeOIDEncoder(ObjectIdentifierEncoder):
    typeName = 'RelativeOID'


class RealEncoder(AbstractItemEncoder):
    typeName = 'Real'

    def encode(self, value, encodeFun, **options):
        return float(value)


class TextStringEncoder(AbstractItemEncoder):
    def __init__(self, typeName):
        self.typeName = typeName

    def encode(self, value, encodeFun, **options):
        return str(value)


class SetEncoder(AbstractItemEncoder):
    typeName = 'Set'
    protoDict = dict

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
    typeName = 'Sequence'
    protoDict = OrderedDict


class SequenceOfEncoder(AbstractItemEncoder):
    typeName = 'SequenceOf'

    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise error.PyAsn1Error(
                f"ASN.1 object {value.__class__.__name__} is inconsistent")
        return [encodeFun(subValue, **options) for subValue in value]


class SetOfEncoder(SequenceOfEncoder):
    typeName = 'SetOf'


class ChoiceEncoder(AbstractItemEncoder):
    typeName = 'Choice'

    def encode(self, value, encodeFun, **options):
        inconsistency = value.isInconsistent
        if inconsistency:
            raise error.PyAsn1Error(
                f"ASN.1 object {value.__class__.__name__} is inconsistent")

        substrate = OrderedDict()

        for key, subValue in value.items():
            substrate[key] = encodeFun(subValue, **options)

        return substrate


class AnyEncoder(AbstractItemEncoder):
    typeName = 'Any'

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
    # ambiguous base types
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

        pyObject = concreteEncoder.encode(value, self, **options)

        envelope = {
            'type': concreteEncoder.typeName,
            'value': pyObject
        }

        if LOG:
            LOG('using value codec %s produced: %s'
                % (concreteEncoder.__class__.__name__, repr(envelope)))
            debug.scope.pop()

        return envelope


class Encoder(object):
    SINGLE_ITEM_ENCODER = SingleItemEncoder

    def __init__(self, **options):
        self._singleItemEncoder = self.SINGLE_ITEM_ENCODER(**options)

    def __call__(self, value, **options):
        return json.dumps(
            self._singleItemEncoder(value, **options))


#: Turns ASN.1 object into a self-describing JSON document.
#:
#: Takes any ASN.1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#: and produces a JSON text document. Every value is wrapped in an envelope
#: carrying its ASN.1 base type name, so the decoder needs no schema to
#: recover the type:
#:
#: .. code-block:: json
#:
#:    {"type": "Integer", "value": 42}
#:    {"type": "Sequence", "value": {"field-0": {"type": "Null", "value": null}}}
#:
#: OCTET STRING and ANY values are Base64-encoded strings; OBJECT IDENTIFIER
#: and character string values are strings; SEQUENCE/SET component order and
#: SEQUENCE OF/SET OF element order is preserved by the document order.
#:
#: Parameters
#: ----------
#: asn1Value: any pyasn1 object (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative)
#:     pyasn1 object to encode (or a tree of them)
#:
#: Returns
#: -------
#: : :py:class:`str`
#:     JSON text document
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error
#:     On encoding errors
#:
#: Examples
#: --------
#: Encode ASN.1 value object into JSON text
#:
#: .. code-block:: pycon
#:
#:    >>> encode(Integer(42))
#:    '{"type": "Integer", "value": 42}'
#:
encode = Encoder()
