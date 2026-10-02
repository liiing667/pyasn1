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
        assert json.loads(encoder.encode(univ.Integer(12))) == {
            'type': 'Integer', 'value': 12}

    def testNegInt(self):
        assert json.loads(encoder.encode(univ.Integer(-12))) == {
            'type': 'Integer', 'value': -12}


class BooleanEncoderTestCase(BaseTestCase):
    def testTrue(self):
        assert json.loads(encoder.encode(univ.Boolean(1))) == {
            'type': 'Boolean', 'value': True}

    def testFalse(self):
        assert json.loads(encoder.encode(univ.Boolean(0))) == {
            'type': 'Boolean', 'value': False}


class BitStringEncoderTestCase(BaseTestCase):
    def testValue(self):
        assert json.loads(encoder.encode(univ.BitString((1, 0, 1)))) == {
            'type': 'BitString', 'value': '101'}


class OctetStringEncoderTestCase(BaseTestCase):
    def testValue(self):
        assert json.loads(encoder.encode(univ.OctetString(b'fox'))) == {
            'type': 'OctetString', 'value': 'Zm94'}

    def testEmpty(self):
        assert json.loads(encoder.encode(univ.OctetString(b''))) == {
            'type': 'OctetString', 'value': ''}


class NullEncoderTestCase(BaseTestCase):
    def testNull(self):
        assert json.loads(encoder.encode(univ.Null(''))) == {
            'type': 'Null', 'value': None}


class ObjectIdentifierEncoderTestCase(BaseTestCase):
    def testValue(self):
        assert json.loads(
            encoder.encode(univ.ObjectIdentifier('1.3.6.1.4.1.0'))) == {
                'type': 'ObjectIdentifier', 'value': '1.3.6.1.4.1.0'}


class RealEncoderTestCase(BaseTestCase):
    def testValue(self):
        assert json.loads(encoder.encode(univ.Real(1.5))) == {
            'type': 'Real', 'value': 1.5}


class TextStringEncoderTestCase(BaseTestCase):
    def testUtf8(self):
        assert json.loads(encoder.encode(char.UTF8String('fox'))) == {
            'type': 'UTF8String', 'value': 'fox'}

    def testPrintable(self):
        assert json.loads(encoder.encode(char.PrintableString('fox'))) == {
            'type': 'PrintableString', 'value': 'fox'}


class SequenceEncoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null('')),
                namedtype.OptionalNamedType('first-name', univ.OctetString()),
                namedtype.DefaultedNamedType('age', univ.Integer(33))
            )
        )

    def testEmpty(self):
        self.s.clear()
        self.s.setComponentByPosition(0, univ.Null(''))
        assert json.loads(encoder.encode(self.s)) == {
            'type': 'Sequence',
            'value': {'place-holder': {'type': 'Null', 'value': None},
                      'age': {'type': 'Integer', 'value': 33}}}

    def testFilled(self):
        self.s.setComponentByPosition(0, univ.Null(''))
        self.s.setComponentByPosition(1, univ.OctetString(b'fox'))
        self.s.setComponentByPosition(2, univ.Integer(1))
        assert json.loads(encoder.encode(self.s)) == {
            'type': 'Sequence',
            'value': {'place-holder': {'type': 'Null', 'value': None},
                      'first-name': {'type': 'OctetString', 'value': 'Zm94'},
                      'age': {'type': 'Integer', 'value': 1}}}

    def testOrderPreserved(self):
        self.s.setComponentByPosition(0, univ.Null(''))
        self.s.setComponentByPosition(1, univ.OctetString(b'fox'))
        self.s.setComponentByPosition(2, univ.Integer(1))

        envelope = json.loads(
            encoder.encode(self.s), object_pairs_hook=OrderedDict)

        assert list(envelope['value']) == ['place-holder', 'first-name', 'age']

    def testInconsistent(self):
        s = univ.Sequence(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('first-name', univ.OctetString())
            )
        )

        try:
            encoder.encode(s)

        except PyAsn1Error:
            pass

        else:
            assert 0, 'encoded inconsistent sequence'


class SchemaLessSequenceEncoderTestCase(BaseTestCase):
    def testDynamicFieldNames(self):
        s = univ.Sequence()
        s.setComponentByPosition(0, univ.Integer(1))
        s.setComponentByPosition(1, univ.Null(''))

        assert json.loads(encoder.encode(s)) == {
            'type': 'Sequence',
            'value': {'field-0': {'type': 'Integer', 'value': 1},
                      'field-1': {'type': 'Null', 'value': None}}}


class SequenceOfEncoderTestCase(BaseTestCase):
    def testEmpty(self):
        s = univ.SequenceOf()
        assert json.loads(encoder.encode(s)) == {
            'type': 'SequenceOf', 'value': []}

    def testOrderPreserved(self):
        s = univ.SequenceOf(componentType=univ.Integer())
        s.extend([3, 1, 2])
        assert json.loads(encoder.encode(s)) == {
            'type': 'SequenceOf',
            'value': [{'type': 'Integer', 'value': 3},
                      {'type': 'Integer', 'value': 1},
                      {'type': 'Integer', 'value': 2}]}


class SetEncoderTestCase(BaseTestCase):
    def testFilled(self):
        s = univ.Set(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null('')),
                namedtype.NamedType('status', univ.Boolean(True))
            )
        )
        s.setComponentByPosition(0, univ.Null(''))
        s.setComponentByPosition(1, univ.Boolean(False))

        envelope = json.loads(
            encoder.encode(s), object_pairs_hook=OrderedDict)

        assert envelope['type'] == 'Set'
        assert list(envelope['value']) == ['place-holder', 'status']


class ChoiceEncoderTestCase(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)

        self.s = univ.Choice(
            componentType=namedtype.NamedTypes(
                namedtype.NamedType('place-holder', univ.Null('')),
                namedtype.NamedType('number', univ.Integer(0))
            )
        )

    def testEmpty(self):
        try:
            encoder.encode(self.s)

        except PyAsn1Error:
            pass

        else:
            assert 0, 'encoded unset choice'

    def testFilled(self):
        self.s.setComponentByPosition(0, univ.Null(''))
        assert json.loads(encoder.encode(self.s)) == {
            'type': 'Choice',
            'value': {'place-holder': {'type': 'Null', 'value': None}}}


class AnyEncoderTestCase(BaseTestCase):
    def testSimple(self):
        s = univ.Any(b'\x04\x03fox')
        assert json.loads(encoder.encode(s)) == {
            'type': 'Any', 'value': 'BANmb3g='}


suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite)
