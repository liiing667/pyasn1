#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import json
import sys
import unittest

from collections import OrderedDict

from tests.base import BaseTestCase

from pyasn1.type import namedtype
from pyasn1.type import univ
from pyasn1.type import char
from pyasn1.codec.json import decoder
from pyasn1.codec.json import encoder
from pyasn1.error import PyAsn1Error


class EmptyOrMalformedDocumentTestCase(BaseTestCase):
    def _assertError(self, substrate):
        try:
            decoder.decode(substrate)

        except PyAsn1Error:
            pass

        else:
            assert 0, 'tolerated %r' % (substrate,)

    def testEmptyStr(self):
        self._assertError('')

    def testEmptyBytes(self):
        self._assertError(b'')

    def testInvalidJson(self):
        self._assertError('not a json document')

    def testEnvelopeNotObject(self):
        self._assertError('[1, 2]')
        self._assertError('"scalar"')
        self._assertError('42')

    def testMissingTypeKey(self):
        self._assertError('{"value": 1}')

    def testMissingValueKey(self):
        self._assertError('{"type": "Integer"}')

    def testUnknownType(self):
        self._assertError('{"type": "Bogus", "value": 1}')

    def testNonTextSubstrate(self):
        self._assertError(None)
        self._assertError(42)


class IntegerDecoderTestCase(BaseTestCase):
    def testWithSpec(self):
        value, rest = decoder.decode(
            '{"type": "Integer", "value": 42}', asn1Spec=univ.Integer())

        assert value == univ.Integer(42)
        assert rest == ''

    def testWithoutSpec(self):
        value, rest = decoder.decode('{"type": "Integer", "value": -42}')

        assert value == univ.Integer(-42)
        assert type(value) is univ.Integer
        assert rest == ''


class BooleanDecoderTestCase(BaseTestCase):
    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "Boolean", "value": true}', asn1Spec=univ.Boolean())

        assert value == univ.Boolean(True)

    def testWithoutSpec(self):
        value, _ = decoder.decode('{"type": "Boolean", "value": false}')

        assert value == univ.Boolean(False)
        assert type(value) is univ.Boolean


class NullDecoderTestCase(BaseTestCase):
    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "Null", "value": null}', asn1Spec=univ.Null())

        assert value == univ.Null('')

    def testWithoutSpec(self):
        value, _ = decoder.decode('{"type": "Null", "value": null}')

        assert value == univ.Null('')
        assert type(value) is univ.Null


class OctetStringDecoderTestCase(BaseTestCase):
    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "OctetString", "value": "Zm94"}',
            asn1Spec=univ.OctetString())

        assert value == univ.OctetString(b'fox')

    def testWithoutSpec(self):
        value, _ = decoder.decode(
            '{"type": "OctetString", "value": "Zm94"}')

        assert value == univ.OctetString(b'fox')
        assert type(value) is univ.OctetString

    def testBadBase64(self):
        try:
            decoder.decode(
                '{"type": "OctetString", "value": "@@@"}',
                asn1Spec=univ.OctetString())

        except PyAsn1Error:
            pass

        else:
            assert 0, 'bad base64 tolerated'


class ObjectIdentifierDecoderTestCase(BaseTestCase):
    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "ObjectIdentifier", "value": "1.3.6"}',
            asn1Spec=univ.ObjectIdentifier())

        assert value == univ.ObjectIdentifier('1.3.6')

    def testWithoutSpec(self):
        value, _ = decoder.decode(
            '{"type": "ObjectIdentifier", "value": "1.3.6"}')

        assert value == univ.ObjectIdentifier('1.3.6')
        assert type(value) is univ.ObjectIdentifier


class TextStringDecoderTestCase(BaseTestCase):
    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "UTF8String", "value": "fox"}',
            asn1Spec=char.UTF8String())

        assert value == char.UTF8String('fox')

    def testWithoutSpec(self):
        value, _ = decoder.decode(
            '{"type": "UTF8String", "value": "fox"}')

        assert value == char.UTF8String('fox')
        assert type(value) is char.UTF8String


class BytesSubstrateTestCase(BaseTestCase):
    def testBytesAccepted(self):
        value, rest = decoder.decode(
            b'{"type": "Integer", "value": 42}')

        assert value == univ.Integer(42)
        assert rest == ''


class ChoiceTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        class MyChoice(univ.Choice):
            componentType = namedtype.NamedTypes(
                namedtype.NamedType('number', univ.Integer()),
                namedtype.NamedType('oid', univ.ObjectIdentifier())
            )

        self.MyChoice = MyChoice

    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "Choice", "value": {"oid": {"type": "ObjectIdentifier", "value": "1.3.6"}}}',
            asn1Spec=self.MyChoice())

        assert value.getComponentByName('oid') == univ.ObjectIdentifier('1.3.6')

    def testWithoutSpec(self):
        value, _ = decoder.decode(
            '{"type": "Choice", "value": {"oid": {"type": "ObjectIdentifier", "value": "1.3.6"}}}')

        assert type(value) is univ.Choice
        assert value.getComponentByName('oid') == univ.ObjectIdentifier('1.3.6')

    def testUnknownComponent(self):
        try:
            decoder.decode(
                '{"type": "Choice", "value": {"nope": {"type": "Integer", "value": 1}}}',
                asn1Spec=self.MyChoice())

        except PyAsn1Error:
            pass

        else:
            assert 0, 'unknown choice component tolerated'

    def testEmptyObjectWithSpec(self):
        try:
            decoder.decode(
                '{"type": "Choice", "value": {}}', asn1Spec=self.MyChoice())

        except PyAsn1Error:
            pass

        else:
            assert 0, 'empty choice tolerated'


class SequenceTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        class MyChoice(univ.Choice):
            componentType = namedtype.NamedTypes(
                namedtype.NamedType('number', univ.Integer()),
                namedtype.NamedType('oid', univ.ObjectIdentifier())
            )

        class MySequence(univ.Sequence):
            componentType = namedtype.NamedTypes(
                namedtype.NamedType('a-number', univ.Integer()),
                namedtype.NamedType('a-bool', univ.Boolean()),
                namedtype.OptionalNamedType('a-choice', MyChoice())
            )

        self.MyChoice = MyChoice
        self.MySequence = MySequence

        self.asn1Value = MySequence()
        self.asn1Value.setComponentByName('a-number', 42)
        self.asn1Value.setComponentByName('a-bool', True)

        choice = self.asn1Value.setComponentByName(
            'a-choice').getComponentByName('a-choice')
        choice.setComponentByName(
            'oid', univ.ObjectIdentifier('1.3.6'))

        self.payload = encoder.encode(self.asn1Value)

    def testRoundTripWithSpec(self):
        value, rest = decoder.decode(
            self.payload, asn1Spec=self.MySequence())

        assert value == self.asn1Value
        assert rest == ''

    def testOrderPreservedWithSpec(self):
        envelope = json.loads(self.payload, object_pairs_hook=OrderedDict)

        assert list(envelope['value']) == ['a-number', 'a-bool', 'a-choice']

    def testRoundTripWithoutSpec(self):
        value, rest = decoder.decode(self.payload)

        assert rest == ''
        assert type(value) is univ.Sequence
        assert value.getComponentByName('a-number') == univ.Integer(42)
        assert value.getComponentByName('a-bool') == univ.Boolean(True)

        nestedChoice = value.getComponentByName('a-choice')
        assert type(nestedChoice) is univ.Choice
        assert nestedChoice.getComponentByName('oid') == univ.ObjectIdentifier('1.3.6')

        assert encoder.encode(value) == self.payload


class SequenceOfTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.asn1Value = univ.SequenceOf(componentType=univ.Integer())
        self.asn1Value.extend([3, 1, 2])

        self.payload = encoder.encode(self.asn1Value)

    def testRoundTripWithSpec(self):
        value, rest = decoder.decode(
            self.payload, asn1Spec=univ.SequenceOf(componentType=univ.Integer()))

        assert rest == ''
        assert [int(x) for x in value] == [3, 1, 2]

    def testRoundTripWithoutSpec(self):
        value, _ = decoder.decode(self.payload)

        assert type(value) is univ.SequenceOf
        assert [int(x) for x in value] == [3, 1, 2]
        assert encoder.encode(value) == self.payload

    def testArrayExpected(self):
        try:
            decoder.decode(
                '{"type": "SequenceOf", "value": 5}')

        except PyAsn1Error:
            pass

        else:
            assert 0, 'non-array SequenceOf tolerated'


class SetTestCase(BaseTestCase):
    def testRoundTripOrderPreserved(self):
        asn1Value = univ.Set(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('z', univ.Integer(0)),
                namedtype.NamedType('a', univ.Boolean(True))
            )
        )
        asn1Value.setComponentByName('z', 7)
        asn1Value.setComponentByName('a', False)

        payload = encoder.encode(asn1Value)

        value, rest = decoder.decode(
            payload,
            asn1Spec=univ.Set(componentType=asn1Value.componentType))

        assert rest == ''
        assert value == asn1Value

        envelope = json.loads(payload, object_pairs_hook=OrderedDict)
        assert list(envelope['value']) == ['z', 'a']

    def testWithoutSpec(self):
        payload = (
            '{"type": "Set", "value": {'
            '"z": {"type": "Integer", "value": 7}, '
            '"a": {"type": "Boolean", "value": false}}}')

        value, _ = decoder.decode(payload)

        assert type(value) is univ.Set
        assert value.getComponentByName('z') == univ.Integer(7)
        assert value.getComponentByName('a') == univ.Boolean(False)
        assert encoder.encode(value) == payload


class AnyDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.asn1Value = univ.Any(b'\x04\x03fox')
        self.payload = encoder.encode(self.asn1Value)

    def testWithSpec(self):
        value, rest = decoder.decode(
            self.payload, asn1Spec=univ.Any())

        assert value == self.asn1Value
        assert rest == ''

    def testWithoutSpec(self):
        value, rest = decoder.decode(self.payload)

        assert rest == ''
        assert type(value) is univ.Any
        assert value.asOctets() == b'\x04\x03fox'
        assert encoder.encode(value) == self.payload


class BadSpecTestCase(BaseTestCase):
    def testInvalidAsn1Spec(self):
        try:
            decoder.decode(
                '{"type": "Integer", "value": 1}', asn1Spec='not-a-spec')

        except PyAsn1Error:
            pass

        else:
            assert 0, 'invalid asn1Spec tolerated'


suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
