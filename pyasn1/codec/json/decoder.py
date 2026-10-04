#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
from collections import OrderedDict
import base64
import binascii
import json
import warnings

from pyasn1 import debug
from pyasn1 import error
from pyasn1.compat import _MISSING
from pyasn1.type import base
from pyasn1.type import char
from pyasn1.type import namedtype
from pyasn1.type import univ
from pyasn1.type import useful

__all__ = ['decode', 'JsonDecodeError']

LOG = debug.registerLoggee(__name__, flags=debug.DEBUG_DECODER)


class JsonDecodeError(error.PyAsn1Error):
    """JSON substrate can not be decoded into an ASN.1 value

    The `JsonDecodeError` exception indicates malformed JSON substrate,
    a missing or empty value, an unknown ASN.1 type label or a mismatch
    between the JSON type label and the given ASN.1 schema.
    """


class AbstractScalarPayloadDecoder(object):
    #: JSON type label this decoder expects on the wire
    label = None
    #: ASN.1 type to instantiate when decoding without a schema
    protoType = None

    def __init__(self, label=None, protoType=None):
        if label is not None:
            self.label = label
        if protoType is not None:
            self.protoType = protoType

    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        if asn1Spec is None:
            asn1Spec = self.protoType()
        return asn1Spec.clone(self.toPyValue(pyObject))

    def toPyValue(self, pyObject):
        return pyObject


class BooleanPayloadDecoder(AbstractScalarPayloadDecoder):
    label = 'Boolean'
    protoType = univ.Boolean

    def toPyValue(self, pyObject):
        if not isinstance(pyObject, bool):
            raise JsonDecodeError(
                'JSON value %r is not a Boolean' % (pyObject,))
        return pyObject


class IntegerPayloadDecoder(AbstractScalarPayloadDecoder):
    label = 'Integer'
    protoType = univ.Integer

    def toPyValue(self, pyObject):
        if isinstance(pyObject, bool) or not isinstance(pyObject, int):
            raise JsonDecodeError(
                'JSON value %r is not an Integer' % (pyObject,))
        return pyObject


class BitStringPayloadDecoder(AbstractScalarPayloadDecoder):
    label = 'BitString'
    protoType = univ.BitString

    def toPyValue(self, pyObject):
        if not isinstance(pyObject, str):
            raise JsonDecodeError(
                'JSON value %r is not a BitString' % (pyObject,))
        try:
            return univ.BitString.fromBinaryString(pyObject)
        except (error.PyAsn1Error, ValueError) as exc:
            raise JsonDecodeError(
                'JSON value %r is not a BitString: %s' % (pyObject, exc))

    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        bitString = self.toPyValue(pyObject)
        if asn1Spec is None:
            return bitString
        return asn1Spec.clone(bitString)


class OctetStringPayloadDecoder(AbstractScalarPayloadDecoder):
    label = 'OctetString'
    protoType = univ.OctetString

    def toPyValue(self, pyObject):
        if not isinstance(pyObject, str):
            raise JsonDecodeError(
                'JSON value %r is not an OctetString' % (pyObject,))
        try:
            return base64.b64decode(pyObject.encode('ascii'), validate=True)
        except (UnicodeEncodeError, binascii.Error) as exc:
            raise JsonDecodeError(
                'JSON value %r is not base64: %s' % (pyObject, exc))


class NullPayloadDecoder(AbstractScalarPayloadDecoder):
    label = 'Null'
    protoType = univ.Null

    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        if pyObject is not None:
            raise JsonDecodeError(
                'JSON value %r is not a Null' % (pyObject,))
        if asn1Spec is None:
            asn1Spec = self.protoType()
        return asn1Spec.clone('')


class ObjectIdentifierPayloadDecoder(AbstractScalarPayloadDecoder):
    label = 'ObjectIdentifier'
    protoType = univ.ObjectIdentifier

    def toPyValue(self, pyObject):
        if not isinstance(pyObject, str):
            raise JsonDecodeError(
                'JSON value %r is not an ObjectIdentifier' % (pyObject,))
        return pyObject


class RealPayloadDecoder(AbstractScalarPayloadDecoder):
    label = 'Real'
    protoType = univ.Real

    def toPyValue(self, pyObject):
        if isinstance(pyObject, bool) or not isinstance(pyObject, (int, float)):
            raise JsonDecodeError(
                'JSON value %r is not a Real' % (pyObject,))
        return float(pyObject)


class TextStringPayloadDecoder(AbstractScalarPayloadDecoder):
    def toPyValue(self, pyObject):
        if not isinstance(pyObject, str):
            raise JsonDecodeError(
                'JSON value %r is not a character string' % (pyObject,))
        return pyObject


class AnyPayloadDecoder(OctetStringPayloadDecoder):
    label = 'Any'
    protoType = univ.Any


class SequenceOrSetPayloadDecoder(object):
    label = 'Sequence'
    protoType = univ.Sequence

    def __init__(self, label=None, protoType=None):
        if label is not None:
            self.label = label
        if protoType is not None:
            self.protoType = protoType

    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        if not isinstance(pyObject, dict):
            raise JsonDecodeError(
                'JSON value %r is not a %s object' % (pyObject, self.label))

        if asn1Spec is None or not asn1Spec.componentType:
            components = []
            for name, node in pyObject.items():
                components.append((name, decodeFun(node, **options)))

            componentType = namedtype.NamedTypes(
                *[namedtype.NamedType(name, component)
                  for name, component in components])

            asn1Value = self.protoType(componentType=componentType)

            for idx, (name, component) in enumerate(components):
                asn1Value.setComponentByPosition(idx, component)

            return asn1Value

        asn1Value = asn1Spec.clone()

        componentsTypes = asn1Value.componentType

        for name, node in pyObject.items():
            if name not in componentsTypes:
                raise JsonDecodeError(
                    'JSON field %r is not a component of %s' % (
                        name, asn1Spec.__class__.__name__))
            asn1Value[name] = decodeFun(
                node, componentsTypes[name].asn1Object, **options)

        missing = [componentsTypes[idx].name
                   for idx in range(len(componentsTypes))
                   if not componentsTypes[idx].isOptional
                   and not componentsTypes[idx].isDefaulted
                   and componentsTypes[idx].name not in pyObject]
        if missing:
            raise JsonDecodeError(
                'JSON object misses required %s components: %s' % (
                    asn1Spec.__class__.__name__, ', '.join(missing)))

        return asn1Value


class SequenceOfOrSetOfPayloadDecoder(SequenceOrSetPayloadDecoder):
    label = 'SequenceOf'
    protoType = univ.SequenceOf

    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        if not isinstance(pyObject, list):
            raise JsonDecodeError(
                'JSON value %r is not a %s array' % (pyObject, self.label))

        if asn1Spec is None or asn1Spec.componentType is None:
            asn1Value = self.protoType()
            for node in pyObject:
                asn1Value.append(decodeFun(node, **options))
            return asn1Value

        asn1Value = asn1Spec.clone()

        for node in pyObject:
            asn1Value.append(
                decodeFun(node, asn1Value.componentType, **options))

        return asn1Value


class ChoicePayloadDecoder(SequenceOrSetPayloadDecoder):
    label = 'Choice'
    protoType = univ.Choice

    def __call__(self, pyObject, asn1Spec, decodeFun=None, **options):
        if not isinstance(pyObject, dict) or len(pyObject) != 1:
            raise JsonDecodeError(
                'JSON value %r is not a single-alternative Choice '
                'object' % (pyObject,))

        name, node = next(iter(pyObject.items()))

        if asn1Spec is None or not asn1Spec.componentType:
            component = decodeFun(node, **options)

            asn1Value = self.protoType(componentType=namedtype.NamedTypes(
                namedtype.NamedType(name, component)))
            asn1Value.setComponentByPosition(0, component)

            return asn1Value

        asn1Value = asn1Spec.clone()

        componentsTypes = asn1Value.componentType

        if name not in componentsTypes:
            raise JsonDecodeError(
                'JSON alternative %r is not a component of %s' % (
                    name, asn1Spec.__class__.__name__))

        asn1Value[name] = decodeFun(
            node, componentsTypes[name].asn1Object, **options)

        return asn1Value


#: JSON type label -> payload decoder, used to infer ASN.1 types
#: when no `asn1Spec` is given
LABEL_MAP = {
    'Boolean': BooleanPayloadDecoder(),
    'Integer': IntegerPayloadDecoder(),
    'Enumerated': IntegerPayloadDecoder('Enumerated', univ.Enumerated),
    'BitString': BitStringPayloadDecoder(),
    'OctetString': OctetStringPayloadDecoder(),
    'Null': NullPayloadDecoder(),
    'ObjectIdentifier': ObjectIdentifierPayloadDecoder(),
    'RelativeOID': ObjectIdentifierPayloadDecoder('RelativeOID', univ.RelativeOID),
    'Real': RealPayloadDecoder(),
    'Sequence': SequenceOrSetPayloadDecoder(),
    'Set': SequenceOrSetPayloadDecoder('Set', univ.Set),
    'SequenceOf': SequenceOfOrSetOfPayloadDecoder(),
    'SetOf': SequenceOfOrSetOfPayloadDecoder('SetOf', univ.SetOf),
    'Choice': ChoicePayloadDecoder(),
    'Any': AnyPayloadDecoder(),
    # character string types
    'UTF8String': TextStringPayloadDecoder('UTF8String', char.UTF8String),
    'NumericString': TextStringPayloadDecoder('NumericString', char.NumericString),
    'PrintableString': TextStringPayloadDecoder('PrintableString', char.PrintableString),
    'TeletexString': TextStringPayloadDecoder('TeletexString', char.TeletexString),
    'VideotexString': TextStringPayloadDecoder('VideotexString', char.VideotexString),
    'IA5String': TextStringPayloadDecoder('IA5String', char.IA5String),
    'GraphicString': TextStringPayloadDecoder('GraphicString', char.GraphicString),
    'VisibleString': TextStringPayloadDecoder('VisibleString', char.VisibleString),
    'GeneralString': TextStringPayloadDecoder('GeneralString', char.GeneralString),
    'UniversalString': TextStringPayloadDecoder('UniversalString', char.UniversalString),
    'BMPString': TextStringPayloadDecoder('BMPString', char.BMPString),
    # useful types
    'ObjectDescriptor': TextStringPayloadDecoder('ObjectDescriptor', useful.ObjectDescriptor),
    'GeneralizedTime': TextStringPayloadDecoder('GeneralizedTime', useful.GeneralizedTime),
    'UTCTime': TextStringPayloadDecoder('UTCTime', useful.UTCTime)
}

# Put in ambiguous & non-ambiguous types for faster codec lookup
TYPE_MAP = {
    univ.Boolean.typeId: LABEL_MAP['Boolean'],
    univ.Integer.typeId: LABEL_MAP['Integer'],
    univ.BitString.typeId: LABEL_MAP['BitString'],
    univ.OctetString.typeId: LABEL_MAP['OctetString'],
    univ.Null.typeId: LABEL_MAP['Null'],
    univ.ObjectIdentifier.typeId: LABEL_MAP['ObjectIdentifier'],
    univ.RelativeOID.typeId: LABEL_MAP['RelativeOID'],
    univ.Enumerated.typeId: LABEL_MAP['Enumerated'],
    univ.Real.typeId: LABEL_MAP['Real'],
    # ambiguous base types
    univ.Set.typeId: LABEL_MAP['Set'],
    univ.SetOf.typeId: LABEL_MAP['SetOf'],
    univ.Sequence.typeId: LABEL_MAP['Sequence'],
    univ.SequenceOf.typeId: LABEL_MAP['SequenceOf'],
    univ.Choice.typeId: LABEL_MAP['Choice'],
    univ.Any.typeId: LABEL_MAP['Any'],
    # character string types
    char.UTF8String.typeId: LABEL_MAP['UTF8String'],
    char.NumericString.typeId: LABEL_MAP['NumericString'],
    char.PrintableString.typeId: LABEL_MAP['PrintableString'],
    char.TeletexString.typeId: LABEL_MAP['TeletexString'],
    char.VideotexString.typeId: LABEL_MAP['VideotexString'],
    char.IA5String.typeId: LABEL_MAP['IA5String'],
    char.GraphicString.typeId: LABEL_MAP['GraphicString'],
    char.VisibleString.typeId: LABEL_MAP['VisibleString'],
    char.GeneralString.typeId: LABEL_MAP['GeneralString'],
    char.UniversalString.typeId: LABEL_MAP['UniversalString'],
    char.BMPString.typeId: LABEL_MAP['BMPString'],
    # useful types
    useful.ObjectDescriptor.typeId: LABEL_MAP['ObjectDescriptor'],
    useful.GeneralizedTime.typeId: LABEL_MAP['GeneralizedTime'],
    useful.UTCTime.typeId: LABEL_MAP['UTCTime']
}


class SingleItemDecoder(object):

    LABEL_MAP = LABEL_MAP
    TYPE_MAP = TYPE_MAP

    def __init__(self, labelMap=_MISSING, typeMap=_MISSING, **ignored):
        self._labelMap = labelMap if labelMap is not _MISSING else self.LABEL_MAP
        self._typeMap = typeMap if typeMap is not _MISSING else self.TYPE_MAP

    def __call__(self, pyObject, asn1Spec=None, **options):

        if LOG:
            debug.scope.push(type(pyObject).__name__)
            LOG('decoder called at scope %s, working with '
                'type %s' % (debug.scope, type(pyObject).__name__))

        if not isinstance(pyObject, dict):
            raise JsonDecodeError(
                'JSON value %r is not a typed ASN.1 object' % (pyObject,))

        try:
            label = pyObject['type']
        except KeyError:
            raise JsonDecodeError(
                'JSON object %r misses the "type" label' % (pyObject,))

        if not isinstance(label, str):
            raise JsonDecodeError(
                'JSON type label %r is not a string' % (label,))

        if 'value' not in pyObject:
            raise JsonDecodeError(
                'JSON object of type %r misses the "value"' % (label,))

        pyValue = pyObject['value']

        if asn1Spec is not None:
            if not isinstance(asn1Spec, base.Asn1Item):
                raise error.PyAsn1Error(
                    'asn1Spec is not valid (should be an instance of an ASN.1 '
                    'Item, not %s)' % asn1Spec.__class__.__name__)

            try:
                valueDecoder = self._typeMap[asn1Spec.typeId]

            except KeyError:
                try:
                    valueDecoder = self._labelMap[label]

                except KeyError:
                    raise JsonDecodeError(
                        'Unknown JSON type label %r' % (label,))

            if label != valueDecoder.label:
                raise JsonDecodeError(
                    'JSON type label %r does not match ASN.1 schema '
                    'type %s' % (label, asn1Spec.__class__.__name__))

        else:
            try:
                valueDecoder = self._labelMap[label]

            except KeyError:
                raise JsonDecodeError(
                    'Unknown JSON type label %r' % (label,))

        if LOG:
            LOG('calling decoder %s on JSON type %s '
                '<%s>' % (type(valueDecoder).__name__,
                          label, repr(pyValue)))

        value = valueDecoder(pyValue, asn1Spec, self, **options)

        if LOG:
            LOG('decoder %s produced ASN.1 type %s '
                '<%s>' % (type(valueDecoder).__name__,
                          type(value).__name__, repr(value)))
            debug.scope.pop()

        return value


class Decoder(object):
    SINGLE_ITEM_DECODER = SingleItemDecoder

    def __init__(self, **options):
        self._singleItemDecoder = self.SINGLE_ITEM_DECODER(**options)

    def __call__(self, substrate, asn1Spec=None, **options):
        if isinstance(substrate, bytes):
            substrate = substrate.decode('utf-8')

        if isinstance(substrate, str):
            if not substrate.strip():
                raise JsonDecodeError('JSON substrate is empty')
            try:
                pyObject = json.loads(
                    substrate, object_pairs_hook=OrderedDict)
            except ValueError as exc:
                raise JsonDecodeError(
                    'JSON substrate can not be parsed: %s' % (exc,))

        elif isinstance(substrate, (dict, list)):
            pyObject = substrate

        else:
            raise JsonDecodeError(
                'JSON substrate %r is neither text nor a parsed JSON '
                'object' % (substrate,))

        value = self._singleItemDecoder(
            pyObject, asn1Spec=asn1Spec, **options)

        return value, ''


#: Turns a JSON document into ASN.1 objects.
#:
#: Takes a JSON document (as text or as an already parsed Python object)
#: produced by :py:class:`~pyasn1.codec.json.encoder` and turns it into a
#: tree of ASN.1 objects (e.g. :py:class:`~pyasn1.type.base.PyAsn1Item`
#: derivative).
#:
#: Parameters
#: ----------
#: substrate: :py:class:`str` or :py:class:`bytes` or :py:class:`dict`
#:     JSON document to parse
#:
#: Keyword Args
#: ------------
#: asn1Spec: any pyasn1 type object e.g. :py:class:`~pyasn1.type.base.PyAsn1Item` derivative
#:     A pyasn1 type object to act as a template guiding the decoder. When
#:     not given, the decoder infers ASN.1 types from the JSON type labels
#:     (including open types like `Any` and `Choice`).
#:
#: Returns
#: -------
#: : :py:class:`tuple`
#:     A tuple of a pyasn1 object and the unprocessed trailing substrate
#:     (always empty for JSON)
#:
#: Raises
#: ------
#: ~pyasn1.codec.json.decoder.JsonDecodeError
#:     On decoding errors (a subclass of ~pyasn1.error.PyAsn1Error)
#:
#: Examples
#: --------
#: Decode JSON document into ASN.1 objects with ASN.1 schema
#:
#: .. code-block:: pycon
#:
#:    >>> seq = SequenceOf(componentType=Integer())
#:    >>> s, _ = decode('{"type": "SequenceOf", "value": [...]}', asn1Spec=seq)
#:    >>> str(s)
#:    SequenceOf:
#:     1 2 3
#:
decode = Decoder()

def __getattr__(attr: str):
    if newAttr := {"labelMap": "LABEL_MAP", "typeMap": "TYPE_MAP"}.get(attr):
        warnings.warn(f"{attr} is deprecated. Please use {newAttr} instead.", DeprecationWarning, stacklevel=2)
        return globals()[newAttr]
    raise AttributeError(attr)
