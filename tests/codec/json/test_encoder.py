#
# This file is part of pyasn1 software.
#
# Copyright (c) 2026, Simon Pichugin <simon.pichugin@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import json
import sys
import unittest

from tests.base import BaseTestCase

from pyasn1.type import char
from pyasn1.type import namedtype
from pyasn1.type import univ
from pyasn1.type import useful
from pyasn1.codec.json import encoder
from pyasn1.error import PyAsn1Error


class BadAsn1SpecTestCase(BaseTestCase):
    def testBadValueType(self):
        try:
            encoder.encode('not an Asn1Item')

        except PyAsn1Error:
            pass

        else:
            assert 0, 'Invalid value type accepted'


class IntegerEncoderTestCase(BaseTestCase):
    def testPosInt(self):
        assert encoder.encode(univ.Integer(12)) == '{"type": "Integer", "value": 12}'

    def testNegInt(self):
        assert encoder.encode(univ.Integer(-12)) == '{"type": "Integer", "value": -12}'


class BooleanEncoderTestCase(BaseTestCase):
    def testTrue(self):
        assert encoder.encode(univ.Boolean(1)) == '{"type": "Boolean", "value": true}'

    def testFalse(self):
        assert encoder.encode(univ.Boolean(0)) == '{"type": "Boolean", "value": false}'


class BitStringEncoderTestCase(BaseTestCase):
    def testValue(self):
        b = univ.BitString((1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1))
        assert encoder.encode(b) == '{"type": "BitString", "value": "101010011000101"}'


class OctetStringEncoderTestCase(BaseTestCase):
    def testValue(self):
        # base64 of b'Quick brown fox'
        assert encoder.encode(univ.OctetString('Quick brown fox')) == \
            '{"type": "OctetString", "value": "UXVpY2sgYnJvd24gZm94"}'


class NullEncoderTestCase(BaseTestCase):
    def testNull(self):
        assert encoder.encode(univ.Null('')) == '{"type": "Null", "value": null}'


class ObjectIdentifierEncoderTestCase(BaseTestCase):
    def testOne(self):
        assert encoder.encode(univ.ObjectIdentifier((1, 3, 6, 0, 12345))) == \
            '{"type": "ObjectIdentifier", "value": "1.3.6.0.12345"}'


class RelativeOIDEncoderTestCase(BaseTestCase):
    def testOne(self):
        assert encoder.encode(univ.RelativeOID((1, 3, 6, 0, 12345))) == \
            '{"type": "RelativeOID", "value": "1.3.6.0.12345"}'


class RealEncoderTestCase(BaseTestCase):
    def testValue(self):
        assert encoder.encode(univ.Real((123, 10, -2))) == '{"type": "Real", "value": 1.23}'


class EnumeratedEncoderTestCase(BaseTestCase):
    def testValue(self):
        assert encoder.encode(univ.Enumerated(3)) == '{"type": "Enumerated", "value": 3}'


class TextStringEncoderTestCase(BaseTestCase):
    def testUtf8(self):
        assert json.loads(encoder.encode(char.UTF8String('abc'))) == \
            {'type': 'UTF8String', 'value': 'abc'}

    def testIA5(self):
        assert json.loads(encoder.encode(char.IA5String('abc'))) == \
            {'type': 'IA5String', 'value': 'abc'}


class UsefulTypesEncoderTestCase(BaseTestCase):
    def testGeneralizedTime(self):
        assert json.loads(encoder.encode(useful.GeneralizedTime('20231004120000Z'))) == \
            {'type': 'GeneralizedTime', 'value': '20231004120000Z'}

    def testUTCTime(self):
        assert json.loads(encoder.encode(useful.UTCTime('231004120000Z'))) == \
            {'type': 'UTCTime', 'value': '231004120000Z'}

    def testObjectDescriptor(self):
        assert json.loads(encoder.encode(useful.ObjectDescriptor('desc'))) == \
            {'type': 'ObjectDescriptor', 'value': 'desc'}


class AnyEncoderTestCase(BaseTestCase):
    def testValue(self):
        # base64 of b'\x05\x00' (BER NULL)
        assert encoder.encode(univ.Any(b'\x05\x00')) == \
            '{"type": "Any", "value": "BQA="}'


class SequenceEncoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.s = univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('place-holder', univ.Null('')),
            namedtype.OptionalNamedType('first-name', univ.OctetString('')),
            namedtype.DefaultedNamedType('age', univ.Integer(33)),
        ))

    def testSimple(self):
        s = self.s.clone()
        s[0] = univ.Null('')
        s[1] = 'abc'
        s[2] = 123
        assert json.loads(encoder.encode(s)) == {
            'type': 'Sequence',
            'value': {
                'place-holder': {'type': 'Null', 'value': None},
                'first-name': {'type': 'OctetString', 'value': 'YWJj'},
                'age': {'type': 'Integer', 'value': 123}
            }
        }

    def testOrderPreserved(self):
        s = self.s.clone()
        s[0] = univ.Null('')
        s[1] = 'abc'
        s[2] = 123
        assert list(json.loads(encoder.encode(s))['value']) == \
            ['place-holder', 'first-name', 'age']

    def testOptionalComponentOmitted(self):
        s = self.s.clone()
        s[0] = univ.Null('')
        assert json.loads(encoder.encode(s))['value'] == {
            'place-holder': {'type': 'Null', 'value': None},
            'age': {'type': 'Integer', 'value': 33}
        }

    def testDefaultedComponentNotInstantiated(self):
        s = self.s.clone()
        s[0] = univ.Null('')

        assert s.getComponentByName('age', instantiate=False) is univ.noValue
        encoder.encode(s)
        assert s.getComponentByName('age', instantiate=False) is univ.noValue


class SetEncoderTestCase(BaseTestCase):
    def testSimple(self):
        s = univ.Set(componentType=namedtype.NamedTypes(
            namedtype.NamedType('x', univ.Integer(1)),
            namedtype.NamedType('y', univ.Integer(2)),
        ))
        s[0] = 1
        s[1] = 2
        assert json.loads(encoder.encode(s)) == {
            'type': 'Set',
            'value': {
                'x': {'type': 'Integer', 'value': 1},
                'y': {'type': 'Integer', 'value': 2}
            }
        }


class SequenceOfEncoderTestCase(BaseTestCase):
    def testSimple(self):
        s = univ.SequenceOf(componentType=univ.Integer())
        s.extend([3, 1, 2])
        assert json.loads(encoder.encode(s)) == {
            'type': 'SequenceOf',
            'value': [
                {'type': 'Integer', 'value': 3},
                {'type': 'Integer', 'value': 1},
                {'type': 'Integer', 'value': 2}
            ]
        }


class SetOfEncoderTestCase(BaseTestCase):
    def testSimple(self):
        s = univ.SetOf(componentType=univ.Integer())
        s.extend([3, 1, 2])
        assert json.loads(encoder.encode(s)) == {
            'type': 'SetOf',
            'value': [
                {'type': 'Integer', 'value': 3},
                {'type': 'Integer', 'value': 1},
                {'type': 'Integer', 'value': 2}
            ]
        }


class ChoiceEncoderTestCase(BaseTestCase):
    def testSimple(self):
        s = univ.Choice(componentType=namedtype.NamedTypes(
            namedtype.NamedType('number', univ.Integer(0)),
            namedtype.NamedType('string', univ.OctetString())
        ))
        s['number'] = 123
        assert json.loads(encoder.encode(s)) == {
            'type': 'Choice',
            'value': {'number': {'type': 'Integer', 'value': 123}}
        }


class SchemaLessEncoderTestCase(BaseTestCase):
    def testSequence(self):
        s = univ.Sequence()
        s.setComponentByPosition(0, univ.Integer(1))
        s.setComponentByPosition(1, univ.OctetString('abc'))
        assert json.loads(encoder.encode(s)) == {
            'type': 'Sequence',
            'value': {
                'field-0': {'type': 'Integer', 'value': 1},
                'field-1': {'type': 'OctetString', 'value': 'YWJj'}
            }
        }

    def testSequenceOf(self):
        s = univ.SequenceOf()
        s.append(univ.Integer(1))
        assert json.loads(encoder.encode(s)) == {
            'type': 'SequenceOf',
            'value': [{'type': 'Integer', 'value': 1}]
        }


class InconsistentEncoderTestCase(BaseTestCase):
    def testInconsistentSequence(self):
        s = univ.Sequence(componentType=namedtype.NamedTypes(
            namedtype.NamedType('id', univ.Integer())))
        try:
            encoder.encode(s)

        except PyAsn1Error:
            pass

        else:
            assert 0, 'Inconsistent ASN.1 object encoded'


suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
