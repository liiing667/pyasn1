#
# This file is part of pyasn1 software.
#
# Copyright (c) 2026, Simon Pichugin <simon.pichugin@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import sys
import unittest

from tests.base import BaseTestCase

from pyasn1.type import char
from pyasn1.type import namedtype
from pyasn1.type import univ
from pyasn1.type import useful
from pyasn1.codec.json import decoder
from pyasn1.codec.json import encoder
from pyasn1.codec.json.decoder import JsonDecodeError
from pyasn1.error import PyAsn1Error


class BadAsn1SpecTestCase(BaseTestCase):
    def testBadSpec(self):
        try:
            decoder.decode(
                '{"type": "Integer", "value": 1}', asn1Spec='not an Asn1Item')

        except PyAsn1Error:
            pass

        else:
            assert 0, 'Invalid asn1Spec accepted'


class IntegerDecoderTestCase(BaseTestCase):
    def testPosInt(self):
        assert decoder.decode(
            '{"type": "Integer", "value": 12}')[0] == univ.Integer(12)

    def testNegInt(self):
        assert decoder.decode(
            '{"type": "Integer", "value": -12}')[0] == univ.Integer(-12)

    def testInferredType(self):
        value, rest = decoder.decode('{"type": "Integer", "value": 12}')
        assert value == univ.Integer(12)
        assert rest == ''

    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "Integer", "value": 12}', asn1Spec=univ.Integer())
        assert value == univ.Integer(12)


class BooleanDecoderTestCase(BaseTestCase):
    def testTrue(self):
        assert decoder.decode(
            '{"type": "Boolean", "value": true}')[0] == univ.Boolean(True)

    def testFalse(self):
        assert decoder.decode(
            '{"type": "Boolean", "value": false}')[0] == univ.Boolean(False)


class BitStringDecoderTestCase(BaseTestCase):
    def testSimple(self):
        assert decoder.decode(
            '{"type": "BitString", "value": "11111111"}')[0] == \
            univ.BitString(hexValue='ff')


class OctetStringDecoderTestCase(BaseTestCase):
    def testSimple(self):
        assert decoder.decode(
            '{"type": "OctetString", "value": "UXVpY2s="}')[0] == \
            univ.OctetString('Quick')


class NullDecoderTestCase(BaseTestCase):
    def testNull(self):
        assert decoder.decode(
            '{"type": "Null", "value": null}')[0] == univ.Null('')


class ObjectIdentifierDecoderTestCase(BaseTestCase):
    def testOne(self):
        assert decoder.decode(
            '{"type": "ObjectIdentifier", "value": "1.3.6.1"}')[0] == \
            univ.ObjectIdentifier('1.3.6.1')


class EnumeratedDecoderTestCase(BaseTestCase):
    def testSimple(self):
        assert decoder.decode(
            '{"type": "Enumerated", "value": 3}')[0] == univ.Enumerated(3)


class TextStringDecoderTestCase(BaseTestCase):
    def testUtf8(self):
        assert decoder.decode(
            '{"type": "UTF8String", "value": "abc"}')[0] == char.UTF8String('abc')

    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "IA5String", "value": "abc"}',
            asn1Spec=char.IA5String())
        assert value == char.IA5String('abc')


class UsefulTypesDecoderTestCase(BaseTestCase):
    def testGeneralizedTime(self):
        assert decoder.decode(
            '{"type": "GeneralizedTime", "value": "20231004120000Z"}')[0] == \
            useful.GeneralizedTime('20231004120000Z')

    def testUTCTime(self):
        assert decoder.decode(
            '{"type": "UTCTime", "value": "231004120000Z"}')[0] == \
            useful.UTCTime('231004120000Z')


class AnyDecoderTestCase(BaseTestCase):
    def testInferredType(self):
        value, _ = decoder.decode('{"type": "Any", "value": "BQA="}')
        assert value == univ.Any(b'\x05\x00')

    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "Any", "value": "BQA="}', asn1Spec=univ.Any())
        assert value == univ.Any(b'\x05\x00')


class SequenceDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.asn1Spec = univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('id', univ.Integer()),
            namedtype.NamedType('name', char.UTF8String())
        ))

    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "Sequence", "value": {"id": '
            '{"type": "Integer", "value": 5}, "name": '
            '{"type": "UTF8String", "value": "abc"}}}',
            asn1Spec=self.asn1Spec)
        assert value['id'] == 5
        assert value['name'] == 'abc'
        assert list(value.componentType) == ['id', 'name']

    def testInferredType(self):
        value, _ = decoder.decode(
            '{"type": "Sequence", "value": {"id": '
            '{"type": "Integer", "value": 5}, "name": '
            '{"type": "UTF8String", "value": "abc"}}}')
        assert isinstance(value, univ.Sequence)
        assert value['id'] == 5
        assert value['name'] == 'abc'
        assert list(value.componentType) == ['id', 'name']


class SetDecoderTestCase(BaseTestCase):
    def testInferredType(self):
        value, _ = decoder.decode(
            '{"type": "Set", "value": {"z": '
            '{"type": "Integer", "value": 1}, "a": '
            '{"type": "Integer", "value": 2}}}')
        assert isinstance(value, univ.Set)
        assert list(value.componentType) == ['z', 'a']
        assert value['z'] == 1
        assert value['a'] == 2


class SequenceOfDecoderTestCase(BaseTestCase):
    def testWithSpec(self):
        asn1Spec = univ.SequenceOf(componentType=univ.Integer())
        value, _ = decoder.decode(
            '{"type": "SequenceOf", "value": ['
            '{"type": "Integer", "value": 3}, '
            '{"type": "Integer", "value": 1}, '
            '{"type": "Integer", "value": 2}]}',
            asn1Spec=asn1Spec)
        assert [x for x in value] == [3, 1, 2]

    def testInferredType(self):
        value, _ = decoder.decode(
            '{"type": "SequenceOf", "value": ['
            '{"type": "Integer", "value": 3}, '
            '{"type": "Integer", "value": 1}, '
            '{"type": "Integer", "value": 2}]}')
        assert isinstance(value, univ.SequenceOf)
        assert [x for x in value] == [3, 1, 2]

    def testEmpty(self):
        value, _ = decoder.decode('{"type": "SequenceOf", "value": []}')
        assert isinstance(value, univ.SequenceOf)
        assert len(value) == 0


class ChoiceDecoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.asn1Spec = univ.Choice(componentType=namedtype.NamedTypes(
            namedtype.NamedType('number', univ.Integer()),
            namedtype.NamedType('string', char.UTF8String())
        ))

    def testWithSpec(self):
        value, _ = decoder.decode(
            '{"type": "Choice", "value": {"number": '
            '{"type": "Integer", "value": 5}}}',
            asn1Spec=self.asn1Spec)
        assert value.getName() == 'number'
        assert value.getComponent() == 5

    def testInferredType(self):
        value, _ = decoder.decode(
            '{"type": "Choice", "value": {"number": '
            '{"type": "Integer", "value": 5}}}')
        assert isinstance(value, univ.Choice)
        assert value.getName() == 'number'
        assert value.getComponent() == 5


class OpenTypeRoundTripTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.asn1Spec = univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('pick', univ.Choice(componentType=namedtype.NamedTypes(
                namedtype.NamedType('number', univ.Integer()),
                namedtype.NamedType('blob', univ.Any())
            ))),
            namedtype.NamedType('raw', univ.Any())
        ))

    def testRoundTripWithSpec(self):
        initial = self.asn1Spec.clone()
        initial['pick'] = self.asn1Spec.componentType['pick'].asn1Object.clone()
        initial['pick']['blob'] = univ.Any(b'\x05\x00')
        initial['raw'] = univ.Any(b'\x02\x01\x01')

        payload = encoder.encode(initial)

        decoded, _ = decoder.decode(payload, asn1Spec=self.asn1Spec)
        assert decoded == initial

    def testRoundTripInferred(self):
        initial = univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('raw', univ.Any())
        ))
        initial['raw'] = univ.Any(b'\x05\x00')

        payload = encoder.encode(initial)

        decoded, _ = decoder.decode(payload)
        assert decoded == initial
        assert isinstance(decoded['raw'], univ.Any)


class RoundTripTestCase(BaseTestCase):
    def testScalarRoundTrips(self):
        values = [
            univ.Integer(42),
            univ.Boolean(True),
            univ.OctetString(b'\x00\x01\x02'),
            univ.Null(''),
            univ.ObjectIdentifier('1.3.6.1.4'),
            univ.Enumerated(1),
            univ.Real(1.5),
            char.UTF8String('x'),
            useful.GeneralizedTime('20231004120000Z'),
            univ.BitString.fromBinaryString('101')
        ]
        for value in values:
            decoded, _ = decoder.decode(encoder.encode(value))
            assert decoded == value, (value, decoded)

    def testNestedRoundTrip(self):
        initial = univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('oids', univ.SequenceOf(
                componentType=univ.ObjectIdentifier())),
            namedtype.NamedType('when', useful.UTCTime()),
            namedtype.NamedType('pick', univ.Choice(componentType=namedtype.NamedTypes(
                namedtype.NamedType('number', univ.Integer()),
                namedtype.NamedType('text', char.UTF8String())
            )))
        ))
        oids = univ.SequenceOf(componentType=univ.ObjectIdentifier())
        oids.extend(['1.2.3', '2.3.4'])
        initial['oids'] = oids
        initial['when'] = '231004120000Z'
        initial['pick']['text'] = 'abc'

        decoded, _ = decoder.decode(encoder.encode(initial))
        assert decoded == initial
        assert [str(x) for x in decoded['oids']] == ['1.2.3', '2.3.4']


class BytesInputTestCase(BaseTestCase):
    def testBytes(self):
        value, _ = decoder.decode(
            b'{"type": "Integer", "value": 12}')
        assert value == univ.Integer(12)


class ParsedObjectInputTestCase(BaseTestCase):
    def testDict(self):
        value, _ = decoder.decode(
            {'type': 'Integer', 'value': 12})
        assert value == univ.Integer(12)


class ErrorTestCase(BaseTestCase):
    def _assertJsonDecodeError(self, payload, asn1Spec=None):
        try:
            decoder.decode(payload, asn1Spec=asn1Spec)

        except JsonDecodeError:
            pass

        else:
            assert 0, 'Bad JSON %r tolerated' % (payload,)

    def testEmptySubstrate(self):
        self._assertJsonDecodeError('')

    def testBlankSubstrate(self):
        self._assertJsonDecodeError('   ')

    def testMalformedJson(self):
        self._assertJsonDecodeError('not json')

    def testMissingTypeLabel(self):
        self._assertJsonDecodeError('{"value": 1}')

    def testMissingValue(self):
        self._assertJsonDecodeError('{"type": "Integer"}')

    def testEmptyObject(self):
        self._assertJsonDecodeError('{}')

    def testUnknownTypeLabel(self):
        self._assertJsonDecodeError('{"type": "NoSuch", "value": 1}')

    def testNonStringTypeLabel(self):
        self._assertJsonDecodeError('{"type": 1, "value": 1}')

    def testNullInteger(self):
        self._assertJsonDecodeError('{"type": "Integer", "value": null}')

    def testBoolIsNotInteger(self):
        self._assertJsonDecodeError('{"type": "Integer", "value": true}')

    def testIntegerIsNotBoolean(self):
        self._assertJsonDecodeError('{"type": "Boolean", "value": 1}')

    def testBadBase64OctetString(self):
        self._assertJsonDecodeError(
            '{"type": "OctetString", "value": "!!!not base64!!!"}')

    def testNullWithValue(self):
        self._assertJsonDecodeError('{"type": "Null", "value": 0}')

    def testEmptyChoice(self):
        self._assertJsonDecodeError('{"type": "Choice", "value": {}}')

    def testChoiceWithTwoAlternatives(self):
        self._assertJsonDecodeError(
            '{"type": "Choice", "value": {"a": 1, "b": 2}}')

    def testScalarInsteadOfObject(self):
        self._assertJsonDecodeError('123')

    def testArrayInsteadOfObject(self):
        self._assertJsonDecodeError('[]')

    def testLabelSpecMismatch(self):
        self._assertJsonDecodeError(
            '{"type": "OctetString", "value": "AQ=="}',
            asn1Spec=univ.Integer())

    def testUnknownSequenceFieldWithSpec(self):
        self._assertJsonDecodeError(
            '{"type": "Sequence", "value": {"nope": '
            '{"type": "Integer", "value": 1}}}',
            asn1Spec=univ.Sequence(componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()))))

    def testMissingRequiredFieldWithSpec(self):
        self._assertJsonDecodeError(
            '{"type": "Sequence", "value": {}}',
            asn1Spec=univ.Sequence(componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()))))

    def testUnknownChoiceAlternativeWithSpec(self):
        self._assertJsonDecodeError(
            '{"type": "Choice", "value": {"nope": '
            '{"type": "Integer", "value": 1}}}',
            asn1Spec=univ.Choice(componentType=namedtype.NamedTypes(
                namedtype.NamedType('id', univ.Integer()))))

    def testScalarInsteadOfSequence(self):
        self._assertJsonDecodeError(
            '{"type": "Sequence", "value": 1}')

    def testObjectInsteadOfSequenceOf(self):
        self._assertJsonDecodeError(
            '{"type": "SequenceOf", "value": {}}')

    def testUnsupportedSubstrateType(self):
        self._assertJsonDecodeError(123)


suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
