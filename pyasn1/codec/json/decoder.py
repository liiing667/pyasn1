#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import base64
import binascii
import json

from pyasn1 import debug
from pyasn1 import error
from pyasn1.compat import _MISSING
from pyasn1.type import base
from pyasn1.type import char
from pyasn1.type import namedtype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['decode']

LOG = debug.registerLoggee(__name__, flags=debug.DEBUG_DECODER)


def _decodeBase64(jsonValue):
    try:
        return base64.b64decode(jsonValue, validate=True)

    except (binascii.Error, TypeError, ValueError) as exc:
        raise error.PyAsn1Error(
            'Base64 decoding failure: %s' % exc)


class AbstractScalarPayloadDecoder(object):
    def __call__(self, jsonValue, asn1Spec, decodeFun=None, **options):
        return asn1Spec.clone(jsonValue)


class BitStringPayloadDecoder(AbstractScalarPayloadDecoder):
    def __call__(self, jsonValue, asn1Spec, decodeFun=None, **options):
        return asn1Spec.clone(univ.BitString.fromBinaryString(jsonValue))


class OctetStringPayloadDecoder(AbstractScalarPayloadDecoder):
    def __call__(self, jsonValue, asn1Spec, decodeFun=None, **options):
        return asn1Spec.clone(_decodeBase64(jsonValue))


class SequenceOrSetPayloadDecoder(object):
    def __call__(self, jsonValue, asn1Spec, decodeFun=None, **options):
        if not isinstance(jsonValue, dict):
            raise error.PyAsn1Error(
                'JSON object expected for %s, not %s'
                % (asn1Spec.__class__.__name__, type(jsonValue).__name__))

        asn1Value = asn1Spec.clone()

        componentsTypes = asn1Value.componentType

        for field in asn1Value:
            if field in jsonValue:
                asn1Value[field] = decodeFun(
                    jsonValue[field], componentsTypes[field].asn1Object, **options)

        return asn1Value


class SequenceOfOrSetOfPayloadDecoder(object):
    def __call__(self, jsonValue, asn1Spec, decodeFun=None, **options):
        if not isinstance(jsonValue, list):
            raise error.PyAsn1Error(
                'JSON array expected for %s, not %s'
                % (asn1Spec.__class__.__name__, type(jsonValue).__name__))

        asn1Value = asn1Spec.clone()

        for childObject in jsonValue:
            asn1Value.append(
                decodeFun(childObject, asn1Value.componentType, **options))

        return asn1Value


class ChoicePayloadDecoder(object):
    def __call__(self, jsonValue, asn1Spec, decodeFun=None, **options):
        if not isinstance(jsonValue, dict) or not jsonValue:
            raise error.PyAsn1Error(
                'Non-empty JSON object expected for %s, not %s'
                % (asn1Spec.__class__.__name__, type(jsonValue).__name__))

        asn1Value = asn1Spec.clone()

        componentsTypes = asn1Value.componentType

        for field in jsonValue:
            if field not in componentsTypes:
                raise error.PyAsn1Error(
                    'Unknown Choice component %s' % field)

            asn1Value[field] = decodeFun(
                jsonValue[field], componentsTypes[field].asn1Object, **options)
            break

        return asn1Value


TAG_MAP = {
    univ.Integer.tagSet: AbstractScalarPayloadDecoder(),
    univ.Boolean.tagSet: AbstractScalarPayloadDecoder(),
    univ.BitString.tagSet: BitStringPayloadDecoder(),
    univ.OctetString.tagSet: OctetStringPayloadDecoder(),
    univ.Null.tagSet: AbstractScalarPayloadDecoder(),
    univ.ObjectIdentifier.tagSet: AbstractScalarPayloadDecoder(),
    univ.RelativeOID.tagSet: AbstractScalarPayloadDecoder(),
    univ.Enumerated.tagSet: AbstractScalarPayloadDecoder(),
    univ.Real.tagSet: AbstractScalarPayloadDecoder(),
    univ.Sequence.tagSet: SequenceOrSetPayloadDecoder(),  # conflicts with SequenceOf
    univ.Set.tagSet: SequenceOrSetPayloadDecoder(),  # conflicts with SetOf
    univ.Choice.tagSet: ChoicePayloadDecoder(),  # conflicts with Any
    # character string types
    char.UTF8String.tagSet: AbstractScalarPayloadDecoder(),
    char.NumericString.tagSet: AbstractScalarPayloadDecoder(),
    char.PrintableString.tagSet: AbstractScalarPayloadDecoder(),
    char.TeletexString.tagSet: AbstractScalarPayloadDecoder(),
    char.VideotexString.tagSet: AbstractScalarPayloadDecoder(),
    char.IA5String.tagSet: AbstractScalarPayloadDecoder(),
    char.GraphicString.tagSet: AbstractScalarPayloadDecoder(),
    char.VisibleString.tagSet: AbstractScalarPayloadDecoder(),
    char.GeneralString.tagSet: AbstractScalarPayloadDecoder(),
    char.UniversalString.tagSet: AbstractScalarPayloadDecoder(),
    char.BMPString.tagSet: AbstractScalarPayloadDecoder(),
    # useful types
    useful.ObjectDescriptor.tagSet: AbstractScalarPayloadDecoder(),
    useful.GeneralizedTime.tagSet: AbstractScalarPayloadDecoder(),
    useful.UTCTime.tagSet: AbstractScalarPayloadDecoder()
}

# Put in ambiguous & non-ambiguous types for faster codec lookup
TYPE_MAP = {
    univ.Integer.typeId: AbstractScalarPayloadDecoder(),
    univ.Boolean.typeId: AbstractScalarPayloadDecoder(),
    univ.BitString.typeId: BitStringPayloadDecoder(),
    univ.OctetString.typeId: OctetStringPayloadDecoder(),
    univ.Null.typeId: AbstractScalarPayloadDecoder(),
    univ.ObjectIdentifier.typeId: AbstractScalarPayloadDecoder(),
    univ.RelativeOID.typeId: AbstractScalarPayloadDecoder(),
    univ.Enumerated.typeId: AbstractScalarPayloadDecoder(),
    univ.Real.typeId: AbstractScalarPayloadDecoder(),
    # ambiguous base types
    univ.Set.typeId: SequenceOrSetPayloadDecoder(),
    univ.SetOf.typeId: SequenceOfOrSetOfPayloadDecoder(),
    univ.Sequence.typeId: SequenceOrSetPayloadDecoder(),
    univ.SequenceOf.typeId: SequenceOfOrSetOfPayloadDecoder(),
    univ.Choice.typeId: ChoicePayloadDecoder(),
    univ.Any.typeId: OctetStringPayloadDecoder(),
    # character string types
    char.UTF8String.typeId: AbstractScalarPayloadDecoder(),
    char.NumericString.typeId: AbstractScalarPayloadDecoder(),
    char.PrintableString.typeId: AbstractScalarPayloadDecoder(),
    char.TeletexString.typeId: AbstractScalarPayloadDecoder(),
    char.VideotexString.typeId: AbstractScalarPayloadDecoder(),
    char.IA5String.typeId: AbstractScalarPayloadDecoder(),
    char.GraphicString.typeId: AbstractScalarPayloadDecoder(),
    char.VisibleString.typeId: AbstractScalarPayloadDecoder(),
    char.GeneralString.typeId: AbstractScalarPayloadDecoder(),
    char.UniversalString.typeId: AbstractScalarPayloadDecoder(),
    char.BMPString.typeId: AbstractScalarPayloadDecoder(),
    # useful types
    useful.ObjectDescriptor.typeId: AbstractScalarPayloadDecoder(),
    useful.GeneralizedTime.typeId: AbstractScalarPayloadDecoder(),
    useful.UTCTime.typeId: AbstractScalarPayloadDecoder()
}


def _scalarTypelessDecoder(asn1Type):
    def typelessDecoder(jsonValue, decodeFun, **options):
        return asn1Type(jsonValue)

    return typelessDecoder


def _nullTypelessDecoder(jsonValue, decodeFun, **options):
    return univ.Null('')


def _bitStringTypelessDecoder(jsonValue, decodeFun, **options):
    return univ.BitString.fromBinaryString(jsonValue)


def _octetStringTypelessDecoder(jsonValue, decodeFun, **options):
    return univ.OctetString(_decodeBase64(jsonValue))


def _anyTypelessDecoder(jsonValue, decodeFun, **options):
    return univ.Any(_decodeBase64(jsonValue))


def _sequenceTypelessDecoder(jsonValue, decodeFun, **options):
    if not isinstance(jsonValue, dict):
        raise error.PyAsn1Error(
            'JSON object expected for Sequence, not %s'
            % type(jsonValue).__name__)

    children = [
        (name, decodeFun(childObject, None, **options))
        for name, childObject in jsonValue.items()
    ]

    asn1Value = univ.Sequence(
        componentType=namedtype.NamedTypes(
            *[namedtype.NamedType(name, child) for name, child in children]))

    for idx, (name, child) in enumerate(children):
        asn1Value.setComponentByPosition(idx, child)

    return asn1Value


def _setTypelessDecoder(jsonValue, decodeFun, **options):
    if not isinstance(jsonValue, dict):
        raise error.PyAsn1Error(
            'JSON object expected for Set, not %s'
            % type(jsonValue).__name__)

    children = [
        (name, decodeFun(childObject, None, **options))
        for name, childObject in jsonValue.items()
    ]

    asn1Value = univ.Set(
        componentType=namedtype.NamedTypes(
            *[namedtype.NamedType(name, child) for name, child in children]))

    for idx, (name, child) in enumerate(children):
        asn1Value.setComponentByPosition(idx, child)

    return asn1Value


def _sequenceOfTypelessDecoder(jsonValue, decodeFun, **options):
    if not isinstance(jsonValue, list):
        raise error.PyAsn1Error(
            'JSON array expected for SequenceOf, not %s'
            % type(jsonValue).__name__)

    asn1Value = univ.SequenceOf()

    for childObject in jsonValue:
        asn1Value.append(decodeFun(childObject, None, **options))

    return asn1Value


def _setOfTypelessDecoder(jsonValue, decodeFun, **options):
    if not isinstance(jsonValue, list):
        raise error.PyAsn1Error(
            'JSON array expected for SetOf, not %s'
            % type(jsonValue).__name__)

    asn1Value = univ.SetOf()

    for childObject in jsonValue:
        asn1Value.append(decodeFun(childObject, None, **options))

    return asn1Value


def _choiceTypelessDecoder(jsonValue, decodeFun, **options):
    if not isinstance(jsonValue, dict) or len(jsonValue) != 1:
        raise error.PyAsn1Error(
            'Single-key JSON object expected for Choice, not %s'
            % type(jsonValue).__name__)

    name, childObject = next(iter(jsonValue.items()))

    child = decodeFun(childObject, None, **options)

    asn1Value = univ.Choice(
        componentType=namedtype.NamedTypes(
            namedtype.NamedType(name, child)))

    asn1Value.setComponentByName(name, child)

    return asn1Value


#: Maps the ``type`` tag of the JSON envelope onto a decoder building
#: the corresponding ASN.1 value without a schema.
TYPE_NAME_MAP = {
    'Boolean': _scalarTypelessDecoder(univ.Boolean),
    'Integer': _scalarTypelessDecoder(univ.Integer),
    'Enumerated': _scalarTypelessDecoder(univ.Enumerated),
    'Real': _scalarTypelessDecoder(univ.Real),
    'BitString': _bitStringTypelessDecoder,
    'OctetString': _octetStringTypelessDecoder,
    'Null': _nullTypelessDecoder,
    'ObjectIdentifier': _scalarTypelessDecoder(univ.ObjectIdentifier),
    'RelativeOID': _scalarTypelessDecoder(univ.RelativeOID),
    'Sequence': _sequenceTypelessDecoder,
    'Set': _setTypelessDecoder,
    'SequenceOf': _sequenceOfTypelessDecoder,
    'SetOf': _setOfTypelessDecoder,
    'Choice': _choiceTypelessDecoder,
    'Any': _anyTypelessDecoder,
    # character string types
    'UTF8String': _scalarTypelessDecoder(char.UTF8String),
    'NumericString': _scalarTypelessDecoder(char.NumericString),
    'PrintableString': _scalarTypelessDecoder(char.PrintableString),
    'TeletexString': _scalarTypelessDecoder(char.TeletexString),
    'VideotexString': _scalarTypelessDecoder(char.VideotexString),
    'IA5String': _scalarTypelessDecoder(char.IA5String),
    'GraphicString': _scalarTypelessDecoder(char.GraphicString),
    'VisibleString': _scalarTypelessDecoder(char.VisibleString),
    'GeneralString': _scalarTypelessDecoder(char.GeneralString),
    'UniversalString': _scalarTypelessDecoder(char.UniversalString),
    'BMPString': _scalarTypelessDecoder(char.BMPString),
    # useful types
    'ObjectDescriptor': _scalarTypelessDecoder(useful.ObjectDescriptor),
    'GeneralizedTime': _scalarTypelessDecoder(useful.GeneralizedTime),
    'UTCTime': _scalarTypelessDecoder(useful.UTCTime)
}


class SingleItemDecoder(object):

    TAG_MAP = TAG_MAP
    TYPE_MAP = TYPE_MAP

    def __init__(self, tagMap=_MISSING, typeMap=_MISSING, **ignored):
        self._tagMap = tagMap if tagMap is not _MISSING else self.TAG_MAP
        self._typeMap = typeMap if typeMap is not _MISSING else self.TYPE_MAP

    @staticmethod
    def _readEnvelope(pyObject):
        if not isinstance(pyObject, dict):
            raise error.PyAsn1Error(
                'JSON envelope object expected, not %s'
                % type(pyObject).__name__)

        try:
            typeName = pyObject['type']
            jsonValue = pyObject['value']

        except KeyError as exc:
            raise error.PyAsn1Error(
                'Missing %s key in JSON envelope' % exc)

        return typeName, jsonValue

    def __call__(self, pyObject, asn1Spec=None, **options):

        if LOG:
            debug.scope.push(type(pyObject).__name__)
            LOG('decoder called at scope %s, working with '
                'type %s' % (debug.scope, type(pyObject).__name__))

        typeName, jsonValue = self._readEnvelope(pyObject)

        if asn1Spec is None:
            try:
                typelessDecoder = TYPE_NAME_MAP[typeName]

            except KeyError:
                raise error.PyAsn1Error(
                    'Unknown ASN.1 type %s in JSON envelope' % typeName)

            value = typelessDecoder(jsonValue, self, **options)

        else:
            if not isinstance(asn1Spec, base.Asn1Item):
                raise error.PyAsn1Error(
                    'asn1Spec is not valid (should be an instance of an ASN.1 '
                    'Item, not %s)' % asn1Spec.__class__.__name__)

            try:
                valueDecoder = self._typeMap[asn1Spec.typeId]

            except KeyError:
                # use base type for codec lookup to recover untagged types
                baseTagSet = tag.TagSet(
                    asn1Spec.tagSet.baseTag, asn1Spec.tagSet.baseTag)

                try:
                    valueDecoder = self._tagMap[baseTagSet]

                except KeyError:
                    raise error.PyAsn1Error(
                        'Unknown ASN.1 tag %s' % asn1Spec.tagSet)

            if LOG:
                LOG('calling decoder %s on JSON type %s '
                    '<%s>' % (type(valueDecoder).__name__,
                              typeName, repr(jsonValue)))

            value = valueDecoder(jsonValue, asn1Spec, self, **options)

        if LOG:
            LOG('decoder produced ASN.1 type %s '
                '<%s>' % (type(value).__name__, repr(value)))
            debug.scope.pop()

        return value


class Decoder(object):
    SINGLE_ITEM_DECODER = SingleItemDecoder

    def __init__(self, **options):
        self._singleItemDecoder = self.SINGLE_ITEM_DECODER(**options)

    def __call__(self, substrate, asn1Spec=None, **kwargs):
        if not isinstance(substrate, (str, bytes, bytearray)):
            raise error.PyAsn1Error(
                'JSON text expected, not %s' % type(substrate).__name__)

        if not substrate:
            raise error.PyAsn1Error('Empty JSON document')

        try:
            pyObject = json.loads(substrate)

        except ValueError as exc:
            raise error.PyAsn1Error(
                'JSON document parsing failure: %s' % exc)

        return self._singleItemDecoder(
            pyObject, asn1Spec=asn1Spec, **kwargs), ''


#: Turns a JSON document produced by :py:mod:`pyasn1.codec.json.encoder`
#: into ASN.1 objects.
#:
#: Takes a JSON text document and turns it into a tree of ASN.1 objects
#: (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative) which may be
#: a scalar or an arbitrary nested structure.
#:
#: Parameters
#: ----------
#: substrate: :py:class:`str` or :py:class:`bytes`
#:     JSON text document
#:
#: Keyword Args
#: ------------
#: asn1Spec: any pyasn1 type object e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
#:     A pyasn1 type object to act as a template guiding the decoder. When
#:     omitted, the decoder infers ASN.1 types from the ``type`` tags of the
#:     JSON envelopes, reconstructing open types (e.g. ANY, CHOICE) as
#:     universal pyasn1 types.
#:
#: Returns
#: -------
#: : :py:class:`tuple`
#:     A tuple of the decoded pyasn1 object and the unprocessed trailing
#:     substrate (always empty for JSON)
#:
#: Raises
#: ------
#: ~pyasn1.error.PyAsn1Error
#:     On decoding errors
#:
#: Examples
#: --------
#: Decode JSON text into ASN.1 objects with ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> s, _ = decode('{"type": "Integer", "value": 42}', asn1Spec=Integer())
#:    >>> str(s)
#:    '42'
#:
decode = Decoder()
