'''
TODO

Copyright 2017-2020, Voxel51, Inc.
voxel51.com

Tyler Ganter, tyler@voxel51.com
'''
# pragma pylint: disable=redefined-builtin
# pragma pylint: disable=unused-wildcard-import
# pragma pylint: disable=wildcard-import
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import *
# pragma pylint: enable=redefined-builtin
# pragma pylint: enable=unused-wildcard-import
# pragma pylint: enable=wildcard-import

import logging

import eta.core.data as etad
from eta.core.serial import Serializable
import eta.core.utils as etau


logger = logging.getLogger(__name__)


class LabelsIterator(Serializable):
    '''@todo(Tyler)'''

    @property
    def type(self):
        return self._type

    def __init__(self):
        self._type = etau.get_class_name(self)

    def iter_matches(self, labels):
        raise NotImplementedError("Subclass must implement")

    def attributes(self):
        return super(LabelsIterator, self).attributes() + ["type"]

    @classmethod
    def from_dict(cls, d, *args, **kwargs):
        subcls = etau.get_class(d["type"])
        if not issubclass(subcls, cls):
            raise ValueError(
                "%s not subclass of %s" % (d["type"], etau.get_class_name(cls)))
        return subcls._from_dict(d)

    @classmethod
    def from_condensed_str(cls, s: str):
        '''TODO

        Example inputs:
            "<object attr>:*:<boolean>:occluded:false"
        '''
        parts = s.split(":")
        subcls = _CONDENSED_STRING_CLASS_MAP[parts.pop(0)]

        if not issubclass(subcls, cls):
            raise ValueError(
                "%s not subclass of %s"
                % (etau.get_class_name(subcls), etau.get_class_name(cls)))

        return subcls._from_condensed_strings(*parts)

    @classmethod
    def _from_dict(cls, d, *args, **kwargs):
        raise NotImplementedError("Subclass must implement")

    @classmethod
    def _from_condensed_strings(cls, *args, **kwargs):
        raise NotImplementedError("Subclass must implement")


class AttributeIterator(LabelsIterator):
    '''@todo(Tyler)'''

    _iter_func_name = "Subclass must populate"

    @property
    def attr_type(self):
        return self._attr_type

    @property
    def attr_name(self):
        return self._attr_name

    @property
    def attr_value(self):
        return self._attr_value

    def __init__(self, attr_type="*", attr_name="*", attr_value="*"):
        super(AttributeIterator, self).__init__()
        self._attr_type = attr_type
        self._attr_name = attr_name
        self._attr_value = attr_value

    def iter_matches(self, labels):
        for attr in getattr(labels, self._iter_func_name)(
                attr_type=self.attr_type,
                attr_name=self.attr_name,
                attr_value=self.attr_value
        ):
            yield attr

    def create_attr(self):
        if any(x == "*" for x in
               (self.attr_type, self.attr_name, self.attr_value)):
            raise ValueError("Cannot create attribute if all fields are not"
                             "explicit")

        return etau.get_class(self.attr_type)(name=self.attr_name,
                                              value=self.attr_value)

    def attributes(self):
        return super(AttributeIterator, self).attributes() \
               + ["attr_type", "attr_name", "attr_value"]

    @classmethod
    def _from_dict(cls, d, *args, **kwargs):
        attr_type = d.get("attr_type", "*")
        attr_name = d.get("attr_name", "*")
        attr_value = d.get("attr_value", "*")

        return cls(attr_type=attr_type, attr_name=attr_name,
                   attr_value=attr_value)

    @classmethod
    def _from_condensed_strings(cls, attr_type, attr_name, attr_value):
        attr_type, attr_value = _convert_attr_type_and_value(
            attr_type, attr_value)

        return cls(
            attr_type=attr_type,
            attr_name=attr_name,
            attr_value=attr_value
        )


class ImageAttributeIterator(AttributeIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "iter_image_attrs"


class VideoAttributeIterator(AttributeIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "iter_video_attrs"


class FrameAttributeIterator(AttributeIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "iter_frame_attrs"


class ThingWithLabelIterator(LabelsIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "Subclass must populate"

    @property
    def label(self):
        return self._label

    def __init__(self, label="*"):
        super(ThingWithLabelIterator, self).__init__()
        self._label = label

    def iter_matches(self, labels):
        for thing in getattr(labels, self._iter_func_name)(label=self.label):
            yield thing

    def attributes(self):
        return super(ThingWithLabelIterator, self).attributes() + ["label"]

    @classmethod
    def _from_dict(cls, d, *args, **kwargs):
        label = d.get("label", "*")

        return cls(label=label)

    @classmethod
    def _from_condensed_strings(cls, label):
        return cls(label=label)


class DetectedObjectIterator(ThingWithLabelIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "iter_detected_objects"


class EventIterator(ThingWithLabelIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "iter_events"


class AttrOfThingWithLabelIterator(LabelsIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "Subclass must populate"

    @property
    def label(self):
        return self._label

    @property
    def attr_type(self):
        return self._attr_type

    @property
    def attr_name(self):
        return self._attr_name

    @property
    def attr_value(self):
        return self._attr_value

    def __init__(self, label="*", attr_type="*", attr_name="*", attr_value="*"):
        super(AttrOfThingWithLabelIterator, self).__init__()
        self._label = label
        self._attr_type = attr_type
        self._attr_name = attr_name
        self._attr_value = attr_value

    def iter_matches(self, labels):
        for attr in getattr(labels, self._iter_func_name)(
                attr_type=self.attr_type,
                attr_name=self.attr_name,
                attr_value=self.attr_value
        ):
            yield attr

    def create_attr(self):
        if any(x == "*" for x in
               (self.attr_type, self.attr_name, self.attr_value)):
            raise ValueError("Cannot create attribute if all fields are not"
                             "explicit")

        return etau.get_class(self.attr_type)(name=self.attr_name,
                                              value=self.attr_value)

    def attributes(self):
        return super(AttrOfThingWithLabelIterator, self).attributes() \
               + ["label", "attr_type", "attr_name", "attr_value"]

    @classmethod
    def from_filters(cls, thing_with_label_filter: ThingWithLabelIterator,
                     attr_filter: AttributeIterator):
        return cls(
            label=thing_with_label_filter.label,
            attr_type=attr_filter.attr_type,
            attr_name=attr_filter.attr_name,
            attr_value=attr_filter.attr_value
        )

    @classmethod
    def _from_dict(cls, d, *args, **kwargs):
        label = d.get("label", "*")
        attr_type = d.get("attr_type", "*")
        attr_name = d.get("attr_name", "*")
        attr_value = d.get("attr_value", "*")

        return cls(label=label, attr_type=attr_type, attr_name=attr_name,
                   attr_value=attr_value)

    @classmethod
    def _from_condensed_strings(cls, label, attr_type, attr_name, attr_value):
        attr_type, attr_value = _convert_attr_type_and_value(
            attr_type, attr_value)

        return cls(
            label=label,
            attr_type=attr_type,
            attr_name = attr_name,
            attr_value = attr_value
        )


class DetectedObjectAttributeIterator(AttrOfThingWithLabelIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "iter_detected_object_attrs"


class EventAttributeIterator(AttrOfThingWithLabelIterator):
    '''@todo(Tyler)'''
    _iter_func_name = "iter_event_attrs"


_CONDENSED_STRING_CLASS_MAP = {
    "<image attr>": ImageAttributeIterator,
    "<video attr>": VideoAttributeIterator,
    "<frame attr>": FrameAttributeIterator,
    "<object>": DetectedObjectIterator,
    "<event>": EventIterator,
    "<object attr>": DetectedObjectAttributeIterator,
    "<event attr>": EventAttributeIterator
}

_CONDENSED_STRING_ATTR_TYPE_MAP = {
    "<categorical>": etau.get_class_name(etad.CategoricalAttribute),
    "<boolean>": etau.get_class_name(etad.BooleanAttribute),
    "<numeric>": etau.get_class_name(etad.NumericAttribute)
}

def _convert_attr_type_and_value(attr_type, attr_value):
    '''Parse the condensed form of `attr_type` and transform `attr_value`
    from string to the appropriate type.
    '''
    if attr_type != "*":
        attr_type = _CONDENSED_STRING_ATTR_TYPE_MAP[attr_type]

        if attr_value != "*":
            if issubclass(etau.get_class(attr_type), etad.BooleanAttribute):
                attr_value = _is_true(attr_value)

            elif issubclass(etau.get_class(attr_type), etad.NumericAttribute):
                attr_value = float(attr_value)

    elif attr_value != "*":
        # cannot be of form: attr_type="*", attr_value="explicit value"
        raise ValueError(
            "attr type must be specified if attr value is not '%s'"
            % "*")

    return attr_type, attr_value

def _is_true(thing_to_test):
    '''Cast an arg from client to native boolean'''
    if type(thing_to_test) == bool:
        return thing_to_test
    elif type(thing_to_test) == int or type(thing_to_test) == float:
        return thing_to_test == 1
    elif type(thing_to_test) == str:
        return thing_to_test.lower() == 'true'
    else:
        # make a best guess? hopefully you should never get here
        return bool(thing_to_test)
